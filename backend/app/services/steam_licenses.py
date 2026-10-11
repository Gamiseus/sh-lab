"""
Steam License Import Service.
Extracts owned games from Steam account via SteamCMD licenses_print command.
"""
import asyncio
import logging
import re
import subprocess
import platform
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone

logger = logging.getLogger(__name__)
import httpx

from sqlmodel import Session, select
from app.models.game import Game
from app.models.config import SystemConfig
from app.services.steam_store import SteamStoreService


@dataclass
class LicenseInfo:
    """Represents a single Steam license/package."""
    package_id: int
    app_ids: List[int] = field(default_factory=list)
    license_type: str = ""
    flags: str = ""


@dataclass  
class ImportResult:
    """Result of a license import operation."""
    total_found: int = 0
    imported: int = 0
    skipped_existing: int = 0
    skipped_free: int = 0
    skipped_invalid: int = 0
    skipped_demo: int = 0
    skipped_online_only: int = 0
    errors: List[Dict] = field(default_factory=list)
    games_added: List[str] = field(default_factory=list)


class SteamLicenseService:
    """Service to import owned games from Steam account."""
    
    def __init__(self):
        self.steam_store = SteamStoreService()
        self._import_status: Dict = {}  # Track ongoing imports

    def has_cached_token(self, username: str, steamcmd_path: str) -> bool:
        """
        Check if SteamCMD has a saved machine token / cached credentials
        for the given username in config.vdf.
        """
        import os
        possible_paths = [
            os.path.join(steamcmd_path, "config", "config.vdf"),
            os.path.expanduser("~/.steam/steam/config/config.vdf"),
            os.path.expanduser("~/Steam/config/config.vdf"),
            "/root/Steam/config/config.vdf",
        ]
        user_lower = username.lower().strip()
        for path in possible_paths:
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read().lower()
                        if "accounts" in content and user_lower in content:
                            return True
                except Exception:
                    pass
        return False
    
    async def run_steamcmd(
        self,
        steamcmd_path: str,
        username: str,
        password: str,
        min_commands: List[str],
        auth_code: Optional[str] = None,
        task: Optional[Any] = None
    ) -> Tuple[str, str, int]:
        """
        Run SteamCMD with given commands.
        steamcmd_path should be the DIRECTORY containing steamcmd.
        Returns: (stdout, stderr, return_code)
        """
        import os
        is_windows = platform.system() == "Windows"
        exe_name = "steamcmd.exe" if is_windows else "steamcmd.sh"
        executable = os.path.join(steamcmd_path, exe_name)
        
        if auth_code:
            # Explicit Steam Guard 2FA code provided: authorize and instruct SteamCMD to remember session (1)
            login_args = ["+login", username, password, auth_code, "1"]
            if task:
                task.log("Authenticating with Steam Guard code and saving machine token...", level="info")
        elif self.has_cached_token(username, steamcmd_path):
            # Machine token cached: login password-free
            login_args = ["+login", username]
            if task:
                task.log(f"Logging in as '{username}' using saved machine token (password-free)...", level="info")
        else:
            # Fall back to username and password with remember flag
            login_args = ["+login", username, password, "1"] if password else ["+login", username]
            
        cmd = [
            executable,
            *login_args,
            *min_commands,
            "+quit"
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            stdin=asyncio.subprocess.PIPE
        )

        stdout_lines: List[str] = []
        stderr_lines: List[str] = []

        async def read_out():
            pkg_count = 0
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                text = line.decode("utf-8", errors="replace")
                stdout_lines.append(text)
                stripped = text.strip()
                if not stripped:
                    continue
                masked = stripped.replace(password, "******") if password else stripped
                if any(k in masked for k in ("Logging in", "Logged in OK", "Waiting for", "Steam Guard", "FAILED")):
                    if task:
                        level = "success" if "Logged in OK" in masked else "warning" if "Steam Guard" in masked or "FAILED" in masked else "info"
                        task.log(masked, level=level)
                elif "packageID" in masked:
                    pkg_count += 1
                    if task and pkg_count % 500 == 0:
                        task.log(f"Reading licenses via SteamCMD ({pkg_count} packages detected)...", level="info")
                        task.set_progress(5, 100, f"Reading licenses ({pkg_count} packages)...")

        async def read_err():
            while True:
                line = await process.stderr.readline()
                if not line:
                    break
                text = line.decode("utf-8", errors="replace")
                stderr_lines.append(text)
                stripped = text.strip()
                if stripped and task:
                    masked = stripped.replace(password, "******") if password else stripped
                    task.log(f"[SteamCMD] {masked}", level="warning")

        await asyncio.gather(read_out(), read_err())
        await process.wait()

        return (
            "".join(stdout_lines),
            "".join(stderr_lines),
            process.returncode or 0
        )
    
    async def get_licenses_output(
        self,
        steamcmd_path: str,
        username: str,
        password: str,
        auth_code: Optional[str] = None,
        task: Optional[Any] = None
    ) -> str:
        """Run licenses_print and return raw output."""
        stdout, stderr, code = await self.run_steamcmd(
            steamcmd_path,
            username,
            password,
            ["+licenses_print"],
            auth_code,
            task=task
        )
        
        if code != 0:
            if code == 5:
                raise RuntimeError(
                    "Steam Guard authentication required (exit code 5). "
                    "Please enter your Steam Guard code in the Steam tab or approve the prompt in your Steam Mobile app, then retry."
                )
            raise RuntimeError(f"SteamCMD failed with code {code}: {stderr}")
        
        return stdout
    
    def parse_licenses_output(self, output: str) -> List[LicenseInfo]:
        """
        Parse licenses_print output to extract package and app IDs.
        
        Example output format:
        License packageID 1234 - ...
         - appids: 5678,9012,3456  (or similar format)
        
        Returns list of LicenseInfo with package and app IDs.
        """
        licenses = []
        current_license = None
        
        for line in output.split("\n"):
            line = line.strip()
            
            # Look for license/package lines
            # Pattern: "License packageID XXXXX" or "packageID XXXXX"
            package_match = re.search(r"(?:License\s+)?packageID\s+(\d+)", line, re.IGNORECASE)
            if package_match:
                if current_license:
                    licenses.append(current_license)
                current_license = LicenseInfo(package_id=int(package_match.group(1)))
                continue
            
            # Look for appids line
            # Pattern: "appids : 123,456,789" or "Apps : 123, 456"
            appids_match = re.search(r"(?:appids?|apps)\s*:\s*([\d,\s]+)", line, re.IGNORECASE)
            if appids_match and current_license:
                app_ids_str = appids_match.group(1)
                app_ids = [
                    int(x.strip()) 
                    for x in re.split(r"[,\s]+", app_ids_str) 
                    if x.strip().isdigit()
                ]
                current_license.app_ids.extend(app_ids)
        
        # Don't forget the last license
        if current_license:
            licenses.append(current_license)
        
        return licenses
    
    def extract_unique_app_ids(self, licenses: List[LicenseInfo]) -> List[int]:
        """Extract unique app IDs from all licenses."""
        app_ids = set()
        for lic in licenses:
            app_ids.update(lic.app_ids)
        return sorted(app_ids)
    
    # ----------------------------------------------------------------
    # Filtering constants
    # ----------------------------------------------------------------
    # Steam category IDs that indicate single-player support
    SINGLE_PLAYER_CATEGORIES = {2}  # 2 = Single-player
    # Categories that indicate online/multiplayer gameplay
    ONLINE_CATEGORIES = {1, 36, 38, 49}  # 1=MP, 36=Online MP, 38=Online Co-op, 49=PvP
    # Name suffixes that indicate demos or trials
    DEMO_SUFFIXES = (
        " demo", " trial", " beta", " playtest",
        " prologue", " benchmark", " test",
    )
    
    def _is_demo_by_name(self, name: str) -> bool:
        """Check if a game name indicates it's a demo/trial/beta."""
        lower = name.lower().strip()
        for suffix in self.DEMO_SUFFIXES:
            if lower.endswith(suffix):
                return True
        # Also catch patterns like "Game Name (Demo)" or "Game - Demo"
        if lower.endswith("(demo)") or lower.endswith("(trial)"):
            return True
        return False
    
    def _is_online_only(self, game_data: Dict) -> bool:
        """
        Detect online-only games that can't be played on a local install.
        A game is online-only if it has multiplayer categories but NO
        single-player category.
        """
        # Check PICS-style category IDs (set of ints)
        cat_ids = set(game_data.get("steam_category_ids", []))
        if cat_ids:
            has_singleplayer = bool(cat_ids & self.SINGLE_PLAYER_CATEGORIES)
            has_online = bool(cat_ids & self.ONLINE_CATEGORIES)
            if has_online and not has_singleplayer:
                return True
            return False
        
        # Check Store API-style categories (list of dicts with 'id' key)
        categories = game_data.get("categories", [])
        if isinstance(categories, list) and categories:
            cat_id_set = set()
            for cat in categories:
                if isinstance(cat, dict) and "id" in cat:
                    cat_id_set.add(int(cat["id"]))
            if cat_id_set:
                has_singleplayer = bool(cat_id_set & self.SINGLE_PLAYER_CATEGORIES)
                has_online = bool(cat_id_set & self.ONLINE_CATEGORIES)
                if has_online and not has_singleplayer:
                    return True
        
        return False
    
    def _build_game_object(
        self,
        app_id: int,
        game_data: Dict,
        game_name: str,
    ) -> Game:
        """
        Build a Game ORM object from PICS or Store API data.
        Does NOT add to session or commit — caller handles persistence.
        """
        # Handle both PICS-style and Store API-style data formats
        developer = game_data.get("developer", "")
        if isinstance(developer, list):
            developer = ", ".join(developer)
        elif not developer:
            developers = game_data.get("developers", [])
            developer = ", ".join(developers) if developers else None

        publisher = game_data.get("publisher", "")
        if isinstance(publisher, list):
            publisher = ", ".join(publisher)
        elif not publisher:
            publishers = game_data.get("publishers", [])
            publisher = ", ".join(publishers) if publishers else None

        # Genre handling: PICS gives list of strings, Store API gives list of dicts
        raw_genres = game_data.get("genres", [])
        if raw_genres and isinstance(raw_genres[0], dict):
            genres = [g.get("description") for g in raw_genres]
        else:
            genres = raw_genres or []

        return Game(
            title=game_name,
            steam_app_id=app_id,
            source="steam",
            short_description=game_data.get("short_description"),
            about_the_game=game_data.get("about_the_game"),
            description=game_data.get("detailed_description") or game_data.get("description"),
            developer=developer,
            publisher=publisher,
            header_image=game_data.get("header_image"),
            capsule_image=game_data.get("capsule_image"),
            cover_url=game_data.get("capsule_image") or game_data.get("header_image"),
            background_url=game_data.get("header_image"),
            genres=genres,
            screenshots=game_data.get("screenshots"),
            movies=self._parse_movies(game_data.get("movies") or []),
            categories=game_data.get("categories"),
            platforms=game_data.get("platforms"),
            metacritic_score=game_data.get("metacritic", {}).get("score") if game_data.get("metacritic") else None,
            metacritic_url=game_data.get("metacritic", {}).get("url") if game_data.get("metacritic") else None,
            pc_requirements=self._stringify_requirements(game_data.get("pc_requirements")),
            mac_requirements=self._stringify_requirements(game_data.get("mac_requirements")),
            linux_requirements=self._stringify_requirements(game_data.get("linux_requirements")),
            achievements_total=game_data.get("achievements", {}).get("total") if game_data.get("achievements") else None,
            achievements_highlighted=game_data.get("achievements", {}).get("highlighted") if game_data.get("achievements") else None,
            release_date=game_data.get("release_date", {}).get("date") if isinstance(game_data.get("release_date"), dict) else game_data.get("release_date"),
            price_cents=self._extract_price(game_data.get("price_overview")),
            discount_percent=game_data.get("price_overview", {}).get("discount_percent") if game_data.get("price_overview") else None,
        )

    def filter_game_data(
        self,
        app_id: int,
        game_data: Optional[Dict],
    ) -> Tuple[str, Optional[str], Optional[str]]:
        """
        Run the filtering pipeline on a single game's data.
        Pure function — no DB access, no side effects.

        Returns: (status, game_name_or_None, error_message_or_None)
        Status: "pass", "skipped_free", "skipped_invalid",
                "skipped_demo", "skipped_online_only"
        """
        if not game_data:
            return ("skipped_invalid", None, "No data returned from Steam")

        game_name = game_data.get("name") or game_data.get("title", f"App {app_id}")

        # 1. Type check — must be 'game'
        app_type = game_data.get("type", "unknown")
        if app_type != "game":
            return ("skipped_invalid", game_name, f"Not a game (type: {app_type})")

        # 2. Free-to-play check
        if game_data.get("is_free", False):
            return ("skipped_free", game_name, None)

        # 3. Demo/trial/beta by name
        if self._is_demo_by_name(game_name):
            return ("skipped_demo", game_name, f"Demo/trial: {game_name}")

        # 4. Online-only check
        if self._is_online_only(game_data):
            return ("skipped_online_only", game_name, f"Online-only: {game_name}")

        return ("pass", game_name, None)
    
    def _parse_movies(self, movies: List[Dict]) -> List[Dict]:
        """Parse movie data to extract streaming URLs."""
        result = []
        for movie in movies:
            parsed = {
                "id": movie.get("id"),
                "name": movie.get("name"),
                "thumbnail": movie.get("thumbnail"),
            }
            # Extract MP4 URLs
            if "mp4" in movie:
                parsed["mp4"] = movie["mp4"]
            if "webm" in movie:
                parsed["webm"] = movie["webm"]
            result.append(parsed)
        return result
    
    def _stringify_requirements(self, req: Optional[Dict]) -> Optional[str]:
        """Convert requirements dict to HTML string."""
        if not req:
            return None
        if isinstance(req, str):
            return req
        min_req = req.get("minimum", "")
        rec_req = req.get("recommended", "")
        if rec_req:
            return f"{min_req}<br><br>{rec_req}"
        return min_req
    
    def _extract_price(self, price_overview: Optional[Dict]) -> Optional[int]:
        """Extract price in cents from price_overview."""
        if not price_overview:
            return None
        # price_overview has "final" in cents
        return price_overview.get("final")

    async def import_all_licenses(
        self,
        session: Session,
        steamcmd_path: str,
        username: str,
        password: str,
        batch_size: int = 50,
        delay_seconds: float = 3.0,
        auth_code: Optional[str] = None,
        task: Optional[Any] = None
    ) -> ImportResult:
        """
        Optimized import pipeline:
        1. Run SteamCMD licenses_print
        2. Batch-check DB for existing IDs (single query)
        3. Fetch ALL remaining PICS metadata in one subprocess call
        4. Filter in memory, batch-commit survivors
        """
        result = ImportResult()

        self._import_status = {
            "running": True,
            "phase": "Getting licenses",
            "progress": 0,
            "total": 0,
            "started_at": datetime.now(timezone.utc).isoformat(),
        }

        try:
            # ── Step 1: Get license list from SteamCMD ──────────────
            if task:
                task.set_progress(0, 100, f"Fetching license package list for account '{username}'...")
                task.log(f"Launching SteamCMD to retrieve owned packages for '{username}'...", level="info")

            output = await self.get_licenses_output(
                steamcmd_path, username, password, auth_code, task=task
            )
            licenses = self.parse_licenses_output(output)
            all_app_ids = self.extract_unique_app_ids(licenses)

            result.total_found = len(all_app_ids)
            logger.info(
                f"Found {len(all_app_ids)} unique app IDs from "
                f"{len(licenses)} license packages"
            )
            if task:
                task.log(
                    f"Successfully parsed {len(licenses)} packages ({len(all_app_ids)} unique App IDs found).",
                    level="success"
                )

            # ── Step 2: Batch existence check (one query) ──────────
            self._import_status["phase"] = "Checking existing games"
            if task:
                task.set_progress(10, 100, "Checking catalog for existing games...")
                task.log("Checking database catalog for existing games...", level="info")

            existing_ids: set = set()
            for i in range(0, len(all_app_ids), 500):
                chunk = all_app_ids[i : i + 500]
                rows = session.exec(
                    select(Game.steam_app_id).where(
                        Game.steam_app_id.in_(chunk)
                    )
                ).all()
                existing_ids.update(rows)

            ids_to_process = [aid for aid in all_app_ids if aid not in existing_ids]
            result.skipped_existing = len(existing_ids)
            logger.info(
                f"{result.skipped_existing} already in DB, "
                f"{len(ids_to_process)} to process"
            )
            if task:
                task.log(
                    f"Catalog check: {result.skipped_existing} already in catalog, {len(ids_to_process)} new items to evaluate.",
                    level="info"
                )

            if not ids_to_process:
                self._import_status["phase"] = "Complete"
                self._import_status["running"] = False
                if task:
                    task.set_progress(100, 100, "Catalog is already up to date.")
                    task.log("All owned licenses are already present in your catalog.", level="success")
                return result

            # ── Step 3: Fetch PICS data via fast-lane subprocess ──────
            self._import_status["phase"] = "Fetching metadata (PICS)"
            self._import_status["total"] = len(ids_to_process)
            if task:
                task.set_progress(15, 100, f"Fetching Steam metadata (0/{len(ids_to_process)})...")
                task.log(f"Fetching metadata via Steam PICS protocol for {len(ids_to_process)} items...", level="info")

            last_logged = [0]
            def on_pics_progress(current: int, total: int):
                if task and total > 0:
                    pct = 15 + int((current / total) * 50)
                    task.set_progress(pct, 100, f"Fetching Steam metadata ({current}/{total})...")
                    if current - last_logged[0] >= 300 or current == total:
                        last_logged[0] = current
                        task.log(f"Steam metadata progress: {current}/{total} items processed...", level="info")

            all_pics_data = await self.steam_store.get_app_details_batch(
                ids_to_process,
                progress_callback=on_pics_progress
            )
            valid_pics_count = sum(1 for v in all_pics_data.values() if v)
            logger.info(
                f"PICS returned data for {valid_pics_count} / "
                f"{len(ids_to_process)} apps"
            )
            if task:
                task.log(
                    f"Metadata retrieval complete: {valid_pics_count} of {len(ids_to_process)} apps returned valid metadata.",
                    level="success" if valid_pics_count > 0 else "warning"
                )

            # ── Step 4: Filter + batch commit ──────────────────────
            self._import_status["phase"] = "Filtering & importing"
            if task:
                task.set_progress(65, 100, "Filtering games and saving to catalog...")
                task.log("Filtering games and importing into catalog...", level="info")

            for chunk_start in range(0, len(ids_to_process), batch_size):
                if task and getattr(task, "_cancel_requested", False):
                    task.log("License import cancelled by user request.", level="warning")
                    break

                chunk = ids_to_process[chunk_start : chunk_start + batch_size]
                self._import_status["progress"] = chunk_start
                curr_idx = chunk_start + len(chunk)
                if task and len(ids_to_process) > 0:
                    pct = 65 + int((curr_idx / len(ids_to_process)) * 35)
                    task.set_progress(pct, 100, f"Filtering & importing ({curr_idx}/{len(ids_to_process)})...")

                games_to_add: List[Game] = []
                titles_to_add: List[str] = []

                for app_id in chunk:
                    data = all_pics_data.get(app_id)

                    status, game_name, error = self.filter_game_data(app_id, data)

                    if status == "skipped_free":
                        result.skipped_free += 1
                    elif status == "skipped_invalid":
                        result.skipped_invalid += 1
                    elif status == "skipped_demo":
                        result.skipped_demo += 1
                    elif status == "skipped_online_only":
                        result.skipped_online_only += 1
                    elif status == "pass":
                        assert game_name is not None
                        try:
                            game = self._build_game_object(app_id, data, game_name)
                            games_to_add.append(game)
                            titles_to_add.append(game_name)
                        except Exception as e:
                            logger.error(f"Error building game {app_id}: {e}")
                            result.errors.append({"app_id": app_id, "error": str(e)})

                # Batch commit for this chunk
                if games_to_add:
                    try:
                        for game in games_to_add:
                            session.add(game)
                        session.commit()

                        result.imported += len(games_to_add)
                        result.games_added.extend(titles_to_add)
                        logger.info(
                            f"Committed chunk: {len(games_to_add)} games "
                            f"({chunk_start + len(chunk)}/{len(ids_to_process)})"
                        )
                        if task:
                            preview = ", ".join(titles_to_add[:3]) + ("..." if len(titles_to_add) > 3 else "")
                            task.log(f"Added batch of {len(games_to_add)} games ({preview})", level="info")
                    except Exception as e:
                        session.rollback()
                        logger.warning(
                            f"Batch commit failed, falling back to individual "
                            f"inserts for {len(games_to_add)} games: {e}"
                        )
                        for game, title in zip(games_to_add, titles_to_add):
                            try:
                                session.add(game)
                                session.commit()
                                result.imported += 1
                                result.games_added.append(title)
                            except Exception as inner_e:
                                session.rollback()
                                logger.error(
                                    f"Individual insert failed for "
                                    f"{game.steam_app_id}: {inner_e}"
                                )
                                result.errors.append({
                                    "app_id": game.steam_app_id,
                                    "error": str(inner_e),
                                })

            self._import_status["phase"] = "Complete"
            self._import_status["running"] = False

            if task:
                task.set_progress(100, 100, f"Import complete: {result.imported} new games added.")
                task.log(
                    f"Import breakdown: {result.imported} games added to catalog, "
                    f"{result.skipped_existing} existing in catalog, "
                    f"{result.skipped_free} free games skipped, "
                    f"{result.skipped_demo} demos skipped, "
                    f"{result.skipped_online_only} online-only skipped, "
                    f"{result.skipped_invalid} non-game items (DLCs/tools/software) skipped.",
                    level="success"
                )

            logger.info(
                f"Import complete: {result.imported} imported, "
                f"{result.skipped_free} free, {result.skipped_invalid} non-game, "
                f"{result.skipped_demo} demos, {result.skipped_online_only} online-only, "
                f"{len(result.errors)} errors"
            )

        except Exception as e:
            self._import_status["phase"] = "Error"
            self._import_status["error"] = str(e)
            self._import_status["running"] = False
            raise

        return result
    
    def get_import_status(self) -> Dict:
        """Get current import status."""
        return self._import_status.copy()

    async def import_single_game(
        self,
        session: Session,
        app_id: int,
        preloaded_data: Optional[Dict] = None
    ) -> Tuple[str, Optional[str]]:
        """
        Import a single game by Steam App ID.
        Returns: (status, error_message)
        """
        existing = session.exec(select(Game).where(Game.steam_app_id == app_id)).first()
        if existing:
            return ("skipped_existing", None)

        if preloaded_data is not None:
            game_data = preloaded_data
        else:
            pics_batch = await self.steam_store.get_app_details_batch([app_id])
            game_data = pics_batch.get(app_id)
            if not game_data:
                game_data = await self.steam_store.get_app_details(app_id)

        status, game_name, error = self.filter_game_data(app_id, game_data)
        if status != "pass":
            return (status, error)

        try:
            game = self._build_game_object(app_id, game_data, game_name)
            session.add(game)
            session.commit()
            return ("imported", None)
        except Exception as e:
            session.rollback()
            return ("error", str(e))


async def search_steam_store(query: str, limit: int = 20) -> List[Dict]:
    """
    Search Steam store for games.
    Uses the store search API.
    """
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://store.steampowered.com/api/storesearch/",
                params={
                    "term": query,
                    "l": "english",
                    "cc": "US"
                },
                timeout=10.0
            )
            
            if resp.status_code != 200:
                return []
            
            data = resp.json()
            items = data.get("items", [])
            
            # Return simplified results
            results = []
            for item in items[:limit]:
                results.append({
                    "appid": item.get("id"),
                    "name": item.get("name"),
                    "icon": item.get("tiny_image"),
                    "price": item.get("price", {})
                })
            
            return results
            
    except Exception:
        return []
