"""In-memory session store for debug traces and blobs (TTL based)."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from threading import Lock
from typing import Any, Dict, List, Optional


DEFAULT_TTL_SECONDS = 30 * 60


@dataclass
class SessionData:
    traces: List[Dict[str, Any]] = field(default_factory=list)
    last_updated: float = field(default_factory=time.time)


class SessionStore:
    def __init__(self, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> None:
        self._ttl_seconds = ttl_seconds
        self._sessions: Dict[str, SessionData] = {}
        self._blobs: Dict[str, Dict[str, Any]] = {}
        self._lock = Lock()

    def cleanup_expired(self) -> None:
        now = time.time()
        with self._lock:
            expired_sessions = [
                key for key, session in self._sessions.items()
                if now - session.last_updated > self._ttl_seconds
            ]
            for key in expired_sessions:
                self._sessions.pop(key, None)

            expired_blobs = [
                key for key, item in self._blobs.items()
                if now - item.get("timestamp", 0) > self._ttl_seconds
            ]
            for key in expired_blobs:
                self._blobs.pop(key, None)

    def append_trace(self, session_id: str, trace: Dict[str, Any]) -> None:
        if not session_id:
            return
        now = time.time()
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                session = SessionData()
                self._sessions[session_id] = session
            session.traces.append(trace)
            session.last_updated = now

    def get_session_traces(self, session_id: str) -> List[Dict[str, Any]]:
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return []
            return list(session.traces)

    def get_session_metrics(self, session_id: str) -> Optional[Dict[str, Any]]:
        traces = self.get_session_traces(session_id)
        if not traces:
            return None

        total_turns = len(traces)
        fast_path_count = sum(1 for t in traces if t.get("fast_path"))
        fast_path_pct = int(round((fast_path_count / total_turns) * 100)) if total_turns else 0

        llm_durations = [t.get("total_duration_ms") for t in traces if isinstance(t.get("total_duration_ms"), (int, float))]
        avg_llm_time_ms = int(round(sum(llm_durations) / len(llm_durations))) if llm_durations else 0

        total_cost_usd = 0.0
        for t in traces:
            cost = t.get("estimated_cost_usd")
            if isinstance(cost, (int, float)):
                total_cost_usd += float(cost)

        sd_distribution = {
            "GREEN": 0,
            "YELLOW": 0,
            "RED": 0,
        }
        for t in traces:
            sd_level = t.get("sd_level") or (t.get("sd_classification") or {}).get("primary")
            if sd_level in sd_distribution:
                sd_distribution[sd_level] += 1

        turns_with_anomalies = sum(1 for t in traces if (t.get("anomalies") or []))

        return {
            "total_turns": total_turns,
            "fast_path_pct": fast_path_pct,
            "avg_llm_time_ms": avg_llm_time_ms,
            "total_cost_usd": round(total_cost_usd, 6),
            "sd_distribution": sd_distribution,
            "turns_with_anomalies": turns_with_anomalies,
        }

    def set_blob(self, blob_id: str, content: str, ttl_seconds: Optional[int] = None) -> None:
        if not blob_id:
            return
        if ttl_seconds is not None:
            self._ttl_seconds = ttl_seconds
        with self._lock:
            self._blobs[blob_id] = {
                "content": content,
                "timestamp": time.time(),
            }

    def save_blob(
        self,
        content: str,
        *,
        session_id: Optional[str] = None,
        ttl_seconds: Optional[int] = None,
    ) -> str:
        """
        Save blob content and return generated blob id.

        Kept as a thin wrapper over ``set_blob`` for compatibility with modules
        that should not manually compose blob ids.
        """
        prefix = (session_id or "blob").strip() or "blob"
        blob_id = f"{prefix}:{uuid.uuid4().hex[:8]}"
        self.set_blob(blob_id, content, ttl_seconds=ttl_seconds)
        return blob_id

    def get_blob(self, blob_id: str) -> Optional[str]:
        if not blob_id:
            return None
        with self._lock:
            item = self._blobs.get(blob_id)
            if not item:
                return None
            return item.get("content")


_SESSION_STORE = SessionStore()


def get_session_store() -> SessionStore:
    return _SESSION_STORE
