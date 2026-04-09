"""Runtime memory updater for Memory v1.1."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable

from .config import config
from .memory_v11 import build_snapshot_v11, compose_memory_context_v11, MemoryContextBundle
from .memory_v12 import build_snapshot_v12
from .summary_manager import summary_manager


@dataclass(frozen=True)
class MemoryUpdateResult:
    snapshot: Dict[str, Any]
    context: MemoryContextBundle


class MemoryUpdater:
    def build_runtime_context(
        self,
        *,
        memory: Any,
        diagnostics: Dict[str, Any] | None,
        route: str | None,
        recent_turns: Iterable[Any] | None = None,
        max_context_chars: int = 2200,
    ) -> MemoryUpdateResult:
        normalized_summary = summary_manager.normalize_summary(getattr(memory, "summary", None))
        total_turns = len(getattr(memory, "turns", []) or [])
        summary_updated_at = getattr(memory, "summary_updated_at", None)
        staleness = summary_manager.staleness(
            normalized_summary,
            summary_updated_at=summary_updated_at,
            total_turns=total_turns,
        )
        legacy_snapshot = build_snapshot_v11(
            diagnostics=diagnostics or {},
            route=route,
            summary_staleness=staleness,
            engagement=self._extract_engagement(memory),
        )
        snapshot = build_snapshot_v12(
            diagnostics=diagnostics or {},
            route=route,
            summary_staleness=staleness,
            engagement=self._extract_engagement(memory),
        )
        context = compose_memory_context_v11(
            summary=normalized_summary,
            summary_updated_at=summary_updated_at,
            total_turns=total_turns,
            snapshot=legacy_snapshot,
            recent_turns=list(recent_turns) if recent_turns is not None else list(getattr(memory, "turns", [])),
            summary_window_size=int(getattr(config, "SUMMARY_WINDOW_SIZE", 5) or 5),
            recent_window=int(getattr(config, "RECENT_WINDOW", 4) or 4),
            max_chars=max_context_chars,
        )
        return MemoryUpdateResult(snapshot=snapshot, context=context)

    def save_snapshot(self, memory: Any, snapshot: Dict[str, Any]) -> None:
        metadata = getattr(memory, "metadata", None)
        if isinstance(metadata, dict):
            metadata["last_state_snapshot_v12"] = snapshot
            metadata["laststatesnapshot"] = snapshot
            metadata.pop("last_state_snapshot_v11", None)
        setattr(memory, "last_state_snapshot_v12", snapshot)
        setattr(memory, "laststatesnapshot", snapshot)
        checkpoint_fn = getattr(memory, "checkpoint", None)
        if callable(checkpoint_fn):
            checkpoint_fn(reason="checkpoint", persist=False)

    @staticmethod
    def _extract_engagement(memory: Any) -> Dict[str, Any]:
        metadata = getattr(memory, "metadata", None)
        if not isinstance(metadata, dict):
            return {}
        return {
            "last_practice_id": metadata.get("last_practice_id"),
            "last_practice_channel": metadata.get("last_practice_channel"),
            "active_track": metadata.get("active_track"),
            "insights_log": metadata.get("insights_log") if isinstance(metadata.get("insights_log"), list) else [],
        }


memory_updater = MemoryUpdater()
