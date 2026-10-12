"""
Automated 7-Day Server Cache Cleanup Worker for SH-LAB.

Rules & Architecture:
- Evaluates cached game titles in ServerGameCache (is_cached == True).
- Queries UserLibrary records to determine active user counts across accounts.
- If user_count > 0: title is active, orphaned_at is cleared to None.
- If user_count == 0:
  - If orphaned_at is None: arms orphan timer (orphaned_at = utc_now()).
  - If orphaned_at is set: checks elapsed time.
  - If elapsed < 7 days (604,800s): title is retained within grace period.
  - If elapsed >= 7 days (604,800s): eligible for automated purge.
- Purge execution deletes disk files at /data/repo/{title} and updates ServerGameCache:
  is_cached = False, cached_size_bytes = 0, purged_at = utc_now().
"""
import os
import shutil
import logging
import asyncio
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timezone, timedelta
from sqlmodel import Session, select, func

from app.core.config import settings
from app.core.db import engine
from app.models.library import ServerGameCache, UserLibrary

logger = logging.getLogger(__name__)

ORPHAN_RETENTION_SECONDS = 7 * 24 * 3600  # 604,800 seconds (7 days)


def utc_now() -> datetime:
    """Return current UTC timestamp with timezone awareness."""
    return datetime.now(timezone.utc)


def evaluate_orphan_retention_status(
    user_count: int,
    orphaned_at: Optional[datetime],
    reference_time: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Evaluate orphan status and purge eligibility matching tests.helpers specification."""
    now = reference_time or utc_now()
    if orphaned_at and orphaned_at.tzinfo is None:
        orphaned_at = orphaned_at.replace(tzinfo=timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    if user_count > 0:
        return {
            "is_orphaned": False,
            "orphaned_at": None,
            "eligible_for_purge": False,
            "seconds_remaining": None,
        }

    if orphaned_at is None:
        return {
            "is_orphaned": True,
            "orphaned_at": now,
            "eligible_for_purge": False,
            "seconds_remaining": ORPHAN_RETENTION_SECONDS,
        }

    elapsed = (now - orphaned_at).total_seconds()
    if elapsed >= ORPHAN_RETENTION_SECONDS:
        return {
            "is_orphaned": True,
            "orphaned_at": orphaned_at,
            "eligible_for_purge": True,
            "seconds_remaining": 0,
        }

    return {
        "is_orphaned": True,
        "orphaned_at": orphaned_at,
        "eligible_for_purge": False,
        "seconds_remaining": round(ORPHAN_RETENTION_SECONDS - elapsed, 1),
    }


def evaluate_title_orphan_status(
    cache_entry: Any,
    user_count: int,
    reference_time: Optional[datetime] = None,
) -> Dict[str, Any]:
    """
    Evaluate whether a ServerGameCache entry is orphaned and eligible for purge.
    Supports ServerGameCache instances, dicts, datetime objects, or None.
    """
    if cache_entry is None or isinstance(cache_entry, datetime):
        orphaned_at = cache_entry
    elif isinstance(cache_entry, dict):
        orphaned_at = cache_entry.get("orphaned_at")
    elif hasattr(cache_entry, "orphaned_at"):
        orphaned_at = getattr(cache_entry, "orphaned_at")
    else:
        orphaned_at = None

    return evaluate_orphan_retention_status(
        user_count=user_count,
        orphaned_at=orphaned_at,
        reference_time=reference_time,
    )


def _safe_purge_disk_repository(title: str) -> int:
    """
    Safely purge game repository files from disk and calculate freed bytes.
    Prevents directory traversal outside GAMES_REPO_PATH.
    """
    repo_path = os.path.abspath(settings.GAMES_REPO_PATH)
    target_dir = os.path.abspath(os.path.join(repo_path, title))

    # Path safety check
    try:
        common = os.path.commonpath([repo_path, target_dir])
        if common != repo_path or target_dir == repo_path:
            logger.error("Path traversal rejected for purge target: %s", target_dir)
            return 0
    except ValueError:
        return 0

    if not os.path.exists(target_dir):
        return 0

    freed_bytes = 0
    try:
        if os.path.isdir(target_dir):
            for root, _, files in os.walk(target_dir):
                for f in files:
                    try:
                        freed_bytes += os.path.getsize(os.path.join(root, f))
                    except OSError:
                        pass
            shutil.rmtree(target_dir, ignore_errors=True)
        else:
            freed_bytes = os.path.getsize(target_dir)
            os.remove(target_dir)
    except Exception as e:
        logger.error("Error deleting repository directory %s: %s", target_dir, e)

    return freed_bytes


def clean_expired_orphans(
    session: Session,
    reference_time: Optional[datetime] = None,
) -> List[Dict[str, Any]]:
    """
    Scan cached games in ServerGameCache, arm new orphans, disarm restored games,
    and purge game files whose orphan duration >= 7 days (604,800 seconds).

    Returns:
        List of dictionaries detailing purged titles and freed bytes.
    """
    now = reference_time or utc_now()
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    # 1. Fetch all cached games
    statement = select(ServerGameCache).where(ServerGameCache.is_cached == True)
    cached_entries = session.exec(statement).all()

    # 2. Batch count active user references per game
    user_counts_query = (
        select(UserLibrary.game_id, func.count(UserLibrary.id))
        .group_by(UserLibrary.game_id)
    )
    user_counts_map = dict(session.exec(user_counts_query).all())

    purged_records: List[Dict[str, Any]] = []

    for entry in cached_entries:
        user_count = user_counts_map.get(entry.game_id, 0)
        status = evaluate_title_orphan_status(entry, user_count, reference_time=now)

        if status["is_orphaned"]:
            if entry.orphaned_at is None:
                entry.orphaned_at = status["orphaned_at"]
                entry.updated_at = now
                session.add(entry)
        else:
            if entry.orphaned_at is not None:
                entry.orphaned_at = None
                entry.updated_at = now
                session.add(entry)

        if status["eligible_for_purge"]:
            # Execute disk purge
            freed_bytes = _safe_purge_disk_repository(entry.title)
            if freed_bytes == 0 and entry.cached_size_bytes > 0:
                freed_bytes = entry.cached_size_bytes

            # Update cache record
            entry.is_cached = False
            entry.cached_size_bytes = 0
            entry.purged_at = now
            entry.updated_at = now

            session.add(entry)
            purged_records.append({
                "game_id": entry.game_id,
                "title": entry.title,
                "freed_bytes": freed_bytes,
                "orphaned_at": entry.orphaned_at,
                "purged_at": now,
                "status": "purged",
            })

    session.commit()
    return purged_records


def sync_orphan_timestamps(
    session: Session,
    reference_time: Optional[datetime] = None,
) -> None:
    """
    Lightweight synchronization routine: updates orphan timestamps across all
    cached games according to current UserLibrary references without deleting files.
    """
    now = reference_time or utc_now()
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    statement = select(ServerGameCache).where(
        (ServerGameCache.is_cached == True) | (ServerGameCache.orphaned_at != None)
    )
    entries = session.exec(statement).all()

    user_counts_query = (
        select(UserLibrary.game_id, func.count(UserLibrary.id))
        .group_by(UserLibrary.game_id)
    )
    user_counts_map = dict(session.exec(user_counts_query).all())

    for entry in entries:
        user_count = user_counts_map.get(entry.game_id, 0)
        if user_count > 0:
            if entry.orphaned_at is not None:
                entry.orphaned_at = None
                entry.updated_at = now
                session.add(entry)
        else:
            if entry.orphaned_at is None:
                entry.orphaned_at = now
                entry.updated_at = now
                session.add(entry)

    session.commit()


def purge_game_cache(
    game_id: int,
    session: Optional[Session] = None,
    reference_time: Optional[datetime] = None,
) -> Optional[Dict[str, Any]]:
    """
    Immediately purge game files from server disk and reset cache record.
    Overrides 7-day orphan retention countdown (for admin on-demand purge).
    """
    def _do_purge(sess: Session) -> Optional[Dict[str, Any]]:
        now = reference_time or utc_now()
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        entry = sess.exec(
            select(ServerGameCache).where(ServerGameCache.game_id == game_id)
        ).first()
        if not entry:
            return None

        freed_bytes = _safe_purge_disk_repository(entry.title)
        if freed_bytes == 0 and entry.cached_size_bytes > 0:
            freed_bytes = entry.cached_size_bytes

        entry.is_cached = False
        entry.cached_size_bytes = 0
        entry.purged_at = now
        entry.updated_at = now
        sess.add(entry)
        sess.commit()

        return {
            "game_id": entry.game_id,
            "title": entry.title,
            "freed_bytes": freed_bytes,
            "purged_at": now,
            "status": "purged",
        }

    if session:
        return _do_purge(session)
    with Session(engine) as sess:
        return _do_purge(sess)


class CacheCleanerService:
    """Service to coordinate automated and on-demand server cache cleanup."""

    def __init__(self, interval_seconds: int = 3600):
        self.interval_seconds = interval_seconds
        self._task: Optional[asyncio.Task] = None
        self._running: bool = False

    def evaluate_title_status(
        self,
        cache_entry: Any,
        user_count: int,
        reference_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        return evaluate_title_orphan_status(cache_entry, user_count, reference_time)

    def run_cleanup_cycle(
        self,
        session: Optional[Session] = None,
        reference_time: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        if session:
            return clean_expired_orphans(session, reference_time=reference_time)
        with Session(engine) as sess:
            return clean_expired_orphans(sess, reference_time=reference_time)

    def sync_all_orphans(
        self,
        session: Optional[Session] = None,
        reference_time: Optional[datetime] = None,
    ) -> None:
        if session:
            sync_orphan_timestamps(session, reference_time=reference_time)
        else:
            with Session(engine) as sess:
                sync_orphan_timestamps(sess, reference_time=reference_time)

    def purge_game_cache(
        self,
        game_id: int,
        session: Optional[Session] = None,
        reference_time: Optional[datetime] = None,
    ) -> Optional[Dict[str, Any]]:
        return purge_game_cache(game_id, session=session, reference_time=reference_time)

    async def start_background_worker(self, interval_seconds: Optional[int] = None) -> None:
        """Start periodic background cleanup loop."""
        if interval_seconds:
            self.interval_seconds = interval_seconds
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._worker_loop())

    async def stop_background_worker(self) -> None:
        """Stop periodic background cleanup loop."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None

    async def _worker_loop(self) -> None:
        logger.info("CacheCleanerService background worker started (interval: %ss)", self.interval_seconds)
        while self._running:
            try:
                await asyncio.to_thread(self.run_cleanup_cycle)
            except Exception as e:
                logger.error("Error during automated cache cleanup cycle: %s", e)
            try:
                await asyncio.sleep(self.interval_seconds)
            except asyncio.CancelledError:
                break
        logger.info("CacheCleanerService background worker stopped")


cache_cleaner = CacheCleanerService()
