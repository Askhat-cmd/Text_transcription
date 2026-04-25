"""Thread state storage for multi-agent runtime."""

from __future__ import annotations

import json
import logging
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

from .contracts.thread_state import ArchivedThread, ThreadState


logger = logging.getLogger(__name__)

_DEFAULT_STORAGE_DIR = Path(
    os.getenv("THREAD_STORAGE_DIR", "bot_psychologist/data/threads")
).resolve()


class ThreadStorage:
    """Persistent storage for active and archived thread states."""

    def __init__(self, storage_dir: Path = _DEFAULT_STORAGE_DIR):
        self._dir = Path(storage_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    def _active_path(self, user_id: str) -> Path:
        return self._dir / f"{user_id}_active.json"

    def _archive_path(self, user_id: str) -> Path:
        return self._dir / f"{user_id}_archive.json"

    def load_active(self, user_id: str) -> Optional[ThreadState]:
        path = self._active_path(user_id)
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            return ThreadState.from_dict(payload)
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.error("[THREAD_STORAGE] load_active failed for user=%s: %s", user_id, exc)
            return None

    def save_active(self, thread: ThreadState) -> None:
        path = self._active_path(thread.user_id)
        payload = json.dumps(thread.to_dict(), ensure_ascii=False, indent=2)
        try:
            with self._lock:
                path.write_text(payload, encoding="utf-8")
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.error(
                "[THREAD_STORAGE] save_active failed for user=%s thread=%s: %s",
                thread.user_id,
                thread.thread_id,
                exc,
            )

    def load_archived(self, user_id: str) -> list[ArchivedThread]:
        path = self._archive_path(user_id)
        if not path.exists():
            return []
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            return [ArchivedThread.from_dict(item) for item in payload]
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.error("[THREAD_STORAGE] load_archived failed for user=%s: %s", user_id, exc)
            return []

    def archive_thread(self, thread: ThreadState, reason: str = "new_thread") -> None:
        archived = self.load_archived(thread.user_id)
        archived.append(
            ArchivedThread(
                thread_id=thread.thread_id,
                core_direction=thread.core_direction,
                closed_loops=list(thread.closed_loops),
                open_loops=list(thread.open_loops),
                final_phase=thread.phase,
                archived_at=datetime.utcnow(),
                archive_reason=reason,
            )
        )
        path = self._archive_path(thread.user_id)
        payload = json.dumps(
            [item.to_dict() for item in archived],
            ensure_ascii=False,
            indent=2,
        )
        with self._lock:
            path.write_text(payload, encoding="utf-8")


thread_storage = ThreadStorage()

