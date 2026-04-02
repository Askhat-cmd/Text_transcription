"""Memory v1.1 helpers for Neo MindBot Phase 5."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Iterable, List, Tuple


SNAPSHOT_SCHEMA_VERSION = "1.1"
VALID_STALENESS = {"fresh", "stale", "missing"}
VALID_INTERACTION_MODES = {"coaching", "informational"}
VALID_NERVOUS_STATES = {"hyper", "window", "hypo"}
VALID_REQUEST_FUNCTIONS = {
    "discharge",
    "understand",
    "directive",
    "validation",
    "explore",
    "contact",
}
VALID_ROUTES = {"safe_override", "regulate", "reflect", "practice", "inform", "contact_hold"}


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


def build_snapshot_v11(
    *,
    diagnostics: Dict[str, Any] | None = None,
    route: str | None = None,
    summary_staleness: str = "missing",
    engagement: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    diagnostics = diagnostics or {}
    engagement = engagement or {}
    staleness = summary_staleness if summary_staleness in VALID_STALENESS else "missing"
    chosen_route = route if route in VALID_ROUTES else "reflect"

    return {
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
        "updated_at": datetime.now().isoformat(),
        "diagnostics": {
            "interaction_mode": _coerce_enum(
                diagnostics.get("interaction_mode"), VALID_INTERACTION_MODES, "coaching"
            ),
            "nervous_system_state": _coerce_enum(
                diagnostics.get("nervous_system_state"), VALID_NERVOUS_STATES, "window"
            ),
            "request_function": _coerce_enum(
                diagnostics.get("request_function"), VALID_REQUEST_FUNCTIONS, "understand"
            ),
            "core_theme": str(diagnostics.get("core_theme") or "unspecified_current_issue"),
        },
        "routing": {"last_route": chosen_route},
        "engagement": {
            "last_practice_id": engagement.get("last_practice_id"),
            "last_practice_channel": engagement.get("last_practice_channel"),
            "active_track": engagement.get("active_track"),
        },
        "meta": {
            "summary_staleness": staleness,
            "needs_context_continuity": True,
        },
    }


def validate_snapshot_v11(snapshot: Dict[str, Any]) -> Tuple[bool, List[str]]:
    errors: List[str] = []
    if not isinstance(snapshot, dict):
        return False, ["snapshot must be an object"]

    if str(snapshot.get("schema_version")) != SNAPSHOT_SCHEMA_VERSION:
        errors.append("schema_version must be 1.1")

    diagnostics = snapshot.get("diagnostics")
    if not isinstance(diagnostics, dict):
        errors.append("diagnostics must be an object")
    else:
        if diagnostics.get("interaction_mode") not in VALID_INTERACTION_MODES:
            errors.append("diagnostics.interaction_mode invalid")
        if diagnostics.get("nervous_system_state") not in VALID_NERVOUS_STATES:
            errors.append("diagnostics.nervous_system_state invalid")
        if diagnostics.get("request_function") not in VALID_REQUEST_FUNCTIONS:
            errors.append("diagnostics.request_function invalid")
        if not str(diagnostics.get("core_theme") or "").strip():
            errors.append("diagnostics.core_theme required")

    routing = snapshot.get("routing")
    if not isinstance(routing, dict) or routing.get("last_route") not in VALID_ROUTES:
        errors.append("routing.last_route invalid")

    meta = snapshot.get("meta")
    if not isinstance(meta, dict) or meta.get("summary_staleness") not in VALID_STALENESS:
        errors.append("meta.summary_staleness invalid")

    return len(errors) == 0, errors


def compose_memory_context_v11(
    *,
    summary: str | None,
    summary_updated_at: int | None,
    total_turns: int,
    snapshot: Dict[str, Any] | None,
    recent_turns: Iterable[Any],
    small_window: int = 3,
    large_window: int = 8,
    max_chars: int = 2200,
) -> MemoryContextBundle:
    staleness = resolve_summary_staleness(
        summary=summary,
        summary_updated_at=summary_updated_at,
        total_turns=total_turns,
    )

    snapshot_valid = False
    snapshot_errors: List[str] = []
    if isinstance(snapshot, dict):
        snapshot_valid, snapshot_errors = validate_snapshot_v11(snapshot)

    # Corrupted snapshot fallback: ignore broken fields and rely on recent dialog.
    if isinstance(snapshot, dict) and not snapshot_valid:
        recent = _render_recent_turns(recent_turns, limit=max(large_window, 4))
        return MemoryContextBundle(
            strategy="corrupted_snapshot_recent_dialog",
            staleness=staleness,
            context_text=_trim_context(recent, max_chars=max_chars),
            summary_used=False,
            snapshot_used=False,
            recent_window_used=True,
        )

    snapshot_text = _render_snapshot_subset(snapshot if snapshot_valid else None)
    if staleness == "fresh":
        recent = _render_recent_turns(recent_turns, limit=small_window)
        text = _join_non_empty(
            [
                f"SUMMARY:\n{summary}" if summary else "",
                snapshot_text,
                recent,
            ]
        )
        return MemoryContextBundle(
            strategy="fresh_summary_small_window",
            staleness=staleness,
            context_text=_trim_context(text, max_chars=max_chars),
            summary_used=bool(summary),
            snapshot_used=bool(snapshot_text),
            recent_window_used=bool(recent),
        )

    if staleness == "stale":
        recent = _render_recent_turns(recent_turns, limit=large_window)
        text = _join_non_empty(
            [
                f"SUMMARY (stale):\n{summary}" if summary else "",
                snapshot_text,
                recent,
            ]
        )
        return MemoryContextBundle(
            strategy="stale_summary_large_window",
            staleness=staleness,
            context_text=_trim_context(text, max_chars=max_chars),
            summary_used=bool(summary),
            snapshot_used=bool(snapshot_text),
            recent_window_used=bool(recent),
        )

    recent = _render_recent_turns(recent_turns, limit=large_window)
    text = _join_non_empty([snapshot_text, recent])
    return MemoryContextBundle(
        strategy="missing_summary_snapshot_plus_recent",
        staleness=staleness,
        context_text=_trim_context(text, max_chars=max_chars),
        summary_used=False,
        snapshot_used=bool(snapshot_text),
        recent_window_used=bool(recent),
    )


def _coerce_enum(value: Any, allowed: set[str], fallback: str) -> str:
    normalized = str(value or "").strip().lower()
    return normalized if normalized in allowed else fallback


def _render_recent_turns(recent_turns: Iterable[Any], *, limit: int) -> str:
    items = list(recent_turns or [])[-max(1, limit) :]
    if not items:
        return ""
    lines: List[str] = ["RECENT DIALOG:"]
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
    diagnostics = snapshot.get("diagnostics") or {}
    routing = snapshot.get("routing") or {}
    engagement = snapshot.get("engagement") or {}

    lines = [
        "SNAPSHOT:",
        f"- interaction_mode: {diagnostics.get('interaction_mode')}",
        f"- nervous_system_state: {diagnostics.get('nervous_system_state')}",
        f"- request_function: {diagnostics.get('request_function')}",
        f"- core_theme: {diagnostics.get('core_theme')}",
        f"- last_route: {routing.get('last_route')}",
    ]
    if engagement.get("active_track"):
        lines.append(f"- active_track: {engagement.get('active_track')}")
    return "\n".join(lines)


def _join_non_empty(parts: List[str]) -> str:
    return "\n\n".join([part for part in parts if part])


def _trim_context(text: str, *, max_chars: int) -> str:
    normalized = (text or "").strip()
    if len(normalized) <= max_chars:
        return normalized
    return normalized[:max_chars].rstrip()

