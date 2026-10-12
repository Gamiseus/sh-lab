"""
Background Task Manager & Real-Time Event Streamer for SH-LAB Admin.
Supports non-blocking job execution, progress tracking, and Server-Sent Events (SSE) streaming.
"""
import asyncio
import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, AsyncGenerator

logger = logging.getLogger(__name__)

class AdminTask:
    def __init__(self, task_id: str, task_type: str, name: str):
        self.id = task_id
        self.type = task_type
        self.name = name
        self.status = "running"  # running, completed, failed, cancelled
        self.progress = {
            "current": 0,
            "total": 0,
            "percent": 0,
            "percentage": 0,
            "bytes_downloaded": 0,
            "total_bytes": 0,
            "speed_bytes_sec": 0.0,
            "speed_mb_sec": 0.0,
            "eta_seconds": None,
            "status": "queued",
            "message": "Initializing..."
        }
        self.started_at = datetime.now(timezone.utc).isoformat()
        self.completed_at: Optional[str] = None
        self.logs: List[Dict[str, Any]] = []
        self.max_logs = 1000
        self.error: Optional[str] = None
        self.result: Optional[Any] = None
        self._cancel_requested = False
        self._subscribers: List[asyncio.Queue] = []
        self._lock = asyncio.Lock()

    def log(self, message: str, level: str = "info"):
        """Append log line and push to active SSE subscribers."""
        timestamp = datetime.now(timezone.utc).strftime("%H:%M:%S")
        entry = {
            "timestamp": timestamp,
            "level": level,  # info, success, warning, error
            "message": message
        }
        self.logs.append(entry)
        if len(self.logs) > self.max_logs:
            self.logs.pop(0)

        # Broadcast to SSE queues
        dead_queues = []
        for q in self._subscribers:
            try:
                q.put_nowait({"type": "log", "data": entry})
            except asyncio.QueueFull:
                dead_queues.append(q)
            except Exception:
                dead_queues.append(q)

        for dq in dead_queues:
            if dq in self._subscribers:
                self._subscribers.remove(dq)

    def set_progress(
        self,
        current: int,
        total: int,
        message: str = "",
        speed_bytes_sec: float = 0.0,
        speed_mb_sec: float = 0.0,
        eta_seconds: Optional[float] = None,
        status: Optional[str] = None,
        bytes_downloaded: Optional[int] = None,
        total_bytes: Optional[int] = None,
        **extra
    ):
        """Update progress metrics and notify subscribers."""
        percent = int((current / total * 100)) if total > 0 else 0
        percent = max(0, min(100, percent))
        b_down = bytes_downloaded if bytes_downloaded is not None else current
        t_bytes = total_bytes if total_bytes is not None else total
        self.progress = {
            "current": current,
            "total": total,
            "percent": percent,
            "percentage": percent,
            "bytes_downloaded": b_down,
            "total_bytes": t_bytes,
            "speed_bytes_sec": speed_bytes_sec,
            "speed_mb_sec": speed_mb_sec,
            "eta_seconds": eta_seconds,
            "status": status or self.progress.get("status", "running"),
            "message": message or self.progress.get("message", ""),
            **extra
        }

        # Broadcast progress update
        for q in self._subscribers:
            try:
                q.put_nowait({"type": "progress", "data": self.progress})
            except Exception:
                pass

    def complete(self, result: Optional[Any] = None, message: str = "Task completed successfully."):
        """Mark task as completed."""
        self.status = "completed"
        self.completed_at = datetime.now(timezone.utc).isoformat()
        self.result = result
        self.set_progress(self.progress["total"] or 1, self.progress["total"] or 1, message)
        self.log(f"✓ {message}", level="success")

        for q in self._subscribers:
            try:
                q.put_nowait({"type": "status", "data": {"status": "completed", "result": result}})
            except Exception:
                pass

    def fail(self, error: str):
        """Mark task as failed."""
        self.status = "failed"
        self.completed_at = datetime.now(timezone.utc).isoformat()
        self.error = error
        self.log(f"❌ {error}", level="error")

        for q in self._subscribers:
            try:
                q.put_nowait({"type": "status", "data": {"status": "failed", "error": error}})
            except Exception:
                pass

    def cancel(self):
        """Request task cancellation."""
        self._cancel_requested = True
        self.status = "cancelled"
        self.completed_at = datetime.now(timezone.utc).isoformat()
        self.log("⚠️ Cancellation requested by operator.", level="warning")

        for q in self._subscribers:
            try:
                q.put_nowait({"type": "status", "data": {"status": "cancelled"}})
            except Exception:
                pass

    @property
    def is_cancelled(self) -> bool:
        return self._cancel_requested

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "name": self.name,
            "status": self.status,
            "progress": self.progress,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "log_count": len(self.logs),
            "error": self.error,
            "result": self.result
        }


class TaskManager:
    def __init__(self):
        self._tasks: Dict[str, AdminTask] = {}
        self._history_limit = 50

    def create_task(self, task_type: str, name: str) -> AdminTask:
        """Create and track a new administrative task."""
        task_id = str(uuid.uuid4())[:8]
        task = AdminTask(task_id, task_type, name)
        self._tasks[task_id] = task

        # Prune old completed tasks if limit reached
        completed = [t for t in self._tasks.values() if t.status in ("completed", "failed", "cancelled")]
        if len(completed) > self._history_limit:
            # Sort by started_at and prune oldest
            completed.sort(key=lambda t: t.started_at)
            for old_task in completed[:-self._history_limit]:
                del self._tasks[old_task.id]

        return task

    def get_task(self, task_id: str) -> Optional[AdminTask]:
        return self._tasks.get(task_id)

    def get_active_tasks(self) -> List[Dict[str, Any]]:
        return [t.to_dict() for t in self._tasks.values() if t.status == "running"]

    def get_all_tasks(self, limit: int = 20) -> List[Dict[str, Any]]:
        tasks = list(self._tasks.values())
        tasks.sort(key=lambda t: t.started_at, reverse=True)
        return [t.to_dict() for t in tasks[:limit]]


# Global singleton instance
task_manager = TaskManager()
