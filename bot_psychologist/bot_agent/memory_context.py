"""Построение контекста памяти для runtime (v1.2 snapshot)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List

from .memory_v12 import validate_snapshot_v12


@dataclass(frozen=True)
class MemoryContextBundle:
    strategy: str
    staleness: str
    context_text: str
    summary_used: bool
    snapshot_used: bool
    recent_window_used: bool

    def as_dict(self) -> Dict[str, Any]:
        return {
            "strategy": self.strategy,
            "staleness": self.staleness,
            "context_text": self.context_text,
            "summary_used": self.summary_used,
            "snapshot_used": self.snapshot_used,
            "recent_window_used": self.recent_window_used,
        }


def resolve_summary_staleness(
    summary: str | None,
    summary_updated_at: int | None,
    total_turns: int,
    *,
    stale_after_turns: int = 8,
) -> str:
    if not summary:
        return "missing"
    if summary_updated_at is None:
        return "stale"
    if summary_updated_at > total_turns:
        return "stale"
    age = max(0, int(total_turns) - int(summary_updated_at))
    return "fresh" if age <= max(1, stale_after_turns) else "stale"


def compose_memory_context(
    *,
    summary: str | None,
    summary_updated_at: int | None,
    total_turns: int,
    snapshot: Dict[str, Any] | None,
    recent_turns: Iterable[Any],
    summary_window_size: int = 5,
    recent_window: int = 4,
    max_chars: int = 2200,
) -> MemoryContextBundle:
    staleness = resolve_summary_staleness(
        summary=summary,
        summary_updated_at=summary_updated_at,
        total_turns=total_turns,
    )

    snapshot_valid = False
    if isinstance(snapshot, dict):
        snapshot_valid, _ = validate_snapshot_v12(snapshot)

    # Поврежденный snapshot игнорируем, работаем только с последним диалогом.
    if isinstance(snapshot, dict) and not snapshot_valid:
        recent = _render_recent_turns(recent_turns, limit=max(8, 4))
        return MemoryContextBundle(
            strategy="corrupted_snapshot_recent_dialog",
            staleness=staleness,
            context_text=_trim_context(recent, max_chars=max_chars),
            summary_used=False,
            snapshot_used=False,
            recent_window_used=True,
        )

    snapshot_text = _render_snapshot_subset(snapshot if snapshot_valid else None)
    summary_mode = bool(summary and total_turns >= max(1, int(summary_window_size)))
    if summary_mode:
        recent = _render_recent_turns(recent_turns, limit=max(1, int(recent_window)))
        summary_block = f"[СВОДКА ДИАЛОГА / CONVERSATION SUMMARY]\n{summary}" if summary else ""
        text = _join_non_empty([summary_block, recent])
        strategy = (
            "fresh_summary_small_window"
            if staleness == "fresh"
            else "stale_summary_large_window"
        )
        return MemoryContextBundle(
            strategy=strategy,
            staleness=staleness,
            context_text=_trim_context(text, max_chars=max_chars),
            summary_used=True,
            snapshot_used=False,
            recent_window_used=bool(recent),
        )

    # Full mode: при отсутствии сводки сохраняем полный релевантный контекст.
    full_limit = max(1, int(total_turns or 0))
    recent = _render_recent_turns(recent_turns, limit=full_limit)
    text = _join_non_empty([snapshot_text, recent])
    strategy = "missing_summary_snapshot_plus_recent" if not summary else "full_recent_dialog"
    return MemoryContextBundle(
        strategy=strategy,
        staleness=staleness,
        context_text=_trim_context(text, max_chars=max_chars),
        summary_used=False,
        snapshot_used=bool(snapshot_text),
        recent_window_used=bool(recent),
    )


def _render_recent_turns(recent_turns: Iterable[Any], *, limit: int) -> str:
    items = list(recent_turns or [])[-max(1, limit) :]
    if not items:
        return ""
    lines: List[str] = ["[ПОСЛЕДНИЙ ДИАЛОГ / RECENT DIALOG]"]
    for turn in items:
        user_text = str(getattr(turn, "user_input", "") or "").strip()
        bot_text = str(getattr(turn, "bot_response", "") or "").strip()
        if user_text:
            lines.append(f"- user: {user_text[:200]}")
        if bot_text:
            lines.append(f"- bot: {bot_text[:200]}")
    return "\n".join(lines)


def _render_snapshot_subset(snapshot: Dict[str, Any] | None) -> str:
    if not snapshot:
        return ""

    lines = [
        "СНИМОК КОНТЕКСТА:",
        f"- nervous_system_state: {snapshot.get('nervous_system_state')}",
        f"- request_function: {snapshot.get('request_function')}",
        f"- core_theme: {snapshot.get('core_theme')}",
        f"- dominant_part: {snapshot.get('dominant_part')}",
        f"- active_quadrant: {snapshot.get('active_quadrant')}",
        f"- last_route: {snapshot.get('_last_route')}",
    ]
    if snapshot.get("active_track"):
        lines.append(f"- active_track: {snapshot.get('active_track')}")
    return "\n".join(lines)


def _join_non_empty(parts: List[str]) -> str:
    return "\n\n".join([part for part in parts if part])


def _trim_context(text: str, *, max_chars: int) -> str:
    normalized = (text or "").strip()
    if len(normalized) <= max_chars:
        return normalized
    return normalized[:max_chars].rstrip()
