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
        self._multiagent_debug: Dict[str, Dict[int, Dict[str, Any]]] = {}
        self._multiagent_updated: Dict[str, float] = {}
        self._session_stats: Dict[str, Dict[str, Any]] = {}
        self._session_stats_updated: Dict[str, float] = {}
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

            expired_multiagent = [
                key for key, ts in self._multiagent_updated.items()
                if now - ts > self._ttl_seconds
            ]
            for key in expired_multiagent:
                self._multiagent_updated.pop(key, None)
                self._multiagent_debug.pop(key, None)

            expired_stats = [
                key for key, ts in self._session_stats_updated.items()
                if now - ts > self._ttl_seconds
            ]
            for key in expired_stats:
                self._session_stats_updated.pop(key, None)
                self._session_stats.pop(key, None)

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

    def get_last_session_id(self) -> Optional[str]:
        with self._lock:
            if not self._sessions:
                return None
            session_id, _ = max(
                self._sessions.items(),
                key=lambda item: item[1].last_updated,
            )
            return session_id

    def get_last_trace(self, session_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        target_session = session_id or self.get_last_session_id()
        if not target_session:
            return None
        traces = self.get_session_traces(target_session)
        if not traces:
            return None
        payload = dict(traces[-1])
        payload["session_id"] = target_session
        return payload

    def get_recent_traces(
        self,
        session_id: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        target_session = session_id or self.get_last_session_id()
        if not target_session:
            return []
        traces = self.get_session_traces(target_session)
        if not traces:
            return []
        clipped = traces[-max(1, limit):]
        result: List[Dict[str, Any]] = []
        for item in clipped:
            payload = dict(item)
            payload["session_id"] = target_session
            result.append(payload)
        return result

    def save_multiagent_debug(self, session_id: str, turn_index: int, debug: Dict[str, Any]) -> None:
        if not session_id:
            return
        if isinstance(turn_index, bool):
            return
        try:
            normalized_turn = int(turn_index)
        except (TypeError, ValueError):
            return
        payload = dict(debug or {})
        payload["turn_index"] = normalized_turn
        with self._lock:
            session_debug = self._multiagent_debug.get(session_id)
            if session_debug is None:
                session_debug = {}
                self._multiagent_debug[session_id] = session_debug
            session_debug[normalized_turn] = payload
            self._multiagent_updated[session_id] = time.time()
        self.accumulate_session_stats(session_id=session_id, debug=payload)

    def get_multiagent_debug(self, session_id: str, turn_index: int) -> Optional[Dict[str, Any]]:
        if not session_id:
            return None
        if isinstance(turn_index, bool):
            return None
        try:
            normalized_turn = int(turn_index)
        except (TypeError, ValueError):
            return None
        with self._lock:
            session_debug = self._multiagent_debug.get(session_id)
            if not session_debug:
                return None
            payload = session_debug.get(normalized_turn)
            return dict(payload) if isinstance(payload, dict) else None

    def get_latest_multiagent_debug(self, session_id: str) -> Optional[Dict[str, Any]]:
        if not session_id:
            return None
        with self._lock:
            session_debug = self._multiagent_debug.get(session_id)
            if not session_debug:
                return None
            latest_turn = max(session_debug.keys(), default=None)
            if latest_turn is None:
                return None
            payload = session_debug.get(latest_turn)
            return dict(payload) if isinstance(payload, dict) else None

    def accumulate_session_stats(self, session_id: str, debug: Dict[str, Any]) -> None:
        if not session_id:
            return
        if not isinstance(debug, dict):
            return
        with self._lock:
            stats = self._session_stats.get(session_id)
            if not isinstance(stats, dict):
                stats = {
                    "total_turns": 0,
                    "total_tokens": 0,
                    "total_cost_usd": 0.0,
                    "total_latency_ms": 0,
                    "state_trajectory": [],
                    "thread_switches": 0,
                    "safety_events": 0,
                    "validator_blocks": 0,
                }
            stats["total_turns"] = int(stats.get("total_turns", 0) or 0) + 1
            stats["total_tokens"] = int(stats.get("total_tokens", 0) or 0) + int(debug.get("tokens_total") or 0)
            stats["total_cost_usd"] = round(
                float(stats.get("total_cost_usd", 0.0) or 0.0) + float(debug.get("estimated_cost_usd") or 0.0),
                6,
            )
            stats["total_latency_ms"] = int(stats.get("total_latency_ms", 0) or 0) + int(
                debug.get("total_latency_ms") or 0
            )

            state_trajectory = list(stats.get("state_trajectory", []))
            current_state = str(debug.get("nervous_state") or "").strip()
            if current_state and (not state_trajectory or state_trajectory[-1] != current_state):
                state_trajectory.append(current_state)
            stats["state_trajectory"] = state_trajectory

            if str(debug.get("relation_to_thread") or "") == "new_thread":
                stats["thread_switches"] = int(stats.get("thread_switches", 0) or 0) + 1
            if bool(debug.get("safety_flag")):
                stats["safety_events"] = int(stats.get("safety_events", 0) or 0) + 1
            if bool(debug.get("validator_blocked")):
                stats["validator_blocks"] = int(stats.get("validator_blocks", 0) or 0) + 1

            self._session_stats[session_id] = stats
            self._session_stats_updated[session_id] = time.time()

    def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        with self._lock:
            stats = self._session_stats.get(session_id)
            if not isinstance(stats, dict):
                return {
                    "total_turns": 0,
                    "total_tokens": 0,
                    "total_cost_usd": 0.0,
                    "total_latency_ms": 0,
                    "state_trajectory": [],
                    "thread_switches": 0,
                    "safety_events": 0,
                    "validator_blocks": 0,
                }
            return dict(stats)

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

        turns_with_anomalies = sum(1 for t in traces if (t.get("anomalies") or []))

        return {
            "total_turns": total_turns,
            "fast_path_pct": fast_path_pct,
            "avg_llm_time_ms": avg_llm_time_ms,
            "total_cost_usd": round(total_cost_usd, 6),
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
