"""Memory snapshot v1.2 helpers for PRD 12.0 bug-fix sprint."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Tuple


SNAPSHOT_SCHEMA_VERSION = "1.2"
VALID_NERVOUS_STATES = {"window", "hyper", "hypo"}
VALID_REQUEST_FUNCTIONS = {
    "understand",
    "discharge",
    "solution",
    "validation",
    "explore",
    "contact",
}
VALID_QUADRANTS = {"i", "it", "we", "its"}
VALID_ROUTES = {"safe_override", "regulate", "reflect", "practice", "inform", "contact_hold", "contacthold"}


def _coerce_enum(value: Any, allowed: set[str], fallback: str) -> str:
    normalized = str(value or "").strip().lower()
    return normalized if normalized in allowed else fallback


def build_snapshot_v12(
    *,
    diagnostics: Dict[str, Any] | None = None,
    route: str | None = None,
    engagement: Dict[str, Any] | None = None,
    summary_staleness: str = "missing",
) -> Dict[str, Any]:
    diagnostics = diagnostics or {}
    engagement = engagement or {}
    optional = diagnostics.get("optional") if isinstance(diagnostics.get("optional"), dict) else {}

    insights = engagement.get("insights_log")
    if not isinstance(insights, list):
        insights = []

    normalized_route = str(route or "").strip().lower()
    if normalized_route == "contacthold":
        normalized_route = "contact_hold"
    if normalized_route not in VALID_ROUTES:
        normalized_route = "reflect"

    return {
        "nervous_system_state": _coerce_enum(
            diagnostics.get("nervous_system_state"),
            VALID_NERVOUS_STATES,
            "window",
        ),
        "request_function": _coerce_enum(
            diagnostics.get("request_function"),
            VALID_REQUEST_FUNCTIONS,
            "understand",
        ),
        "dominant_part": str(optional.get("dominant_part") or "unknown"),
        "active_quadrant": _coerce_enum(optional.get("active_quadrant"), VALID_QUADRANTS, "i"),
        "core_theme": str(diagnostics.get("core_theme") or "unspecified_current_issue"),
        "last_practice_channel": engagement.get("last_practice_channel"),
        "active_track": engagement.get("active_track"),
        "insights_log": insights,
        "_schema_version": SNAPSHOT_SCHEMA_VERSION,
        "_updated_at": datetime.now().isoformat(),
        "_last_route": normalized_route,
        "_summary_staleness": str(summary_staleness or "missing"),
    }


def validate_snapshot_v12(snapshot: Dict[str, Any]) -> Tuple[bool, List[str]]:
    errors: List[str] = []
    if not isinstance(snapshot, dict):
        return False, ["snapshot must be an object"]

    required_fields = (
        "nervous_system_state",
        "request_function",
        "dominant_part",
        "active_quadrant",
        "core_theme",
        "last_practice_channel",
        "active_track",
        "insights_log",
    )
    for field in required_fields:
        if field not in snapshot:
            errors.append(f"missing_field:{field}")

    if snapshot.get("nervous_system_state") not in VALID_NERVOUS_STATES:
        errors.append("nervous_system_state invalid")
    if snapshot.get("request_function") not in VALID_REQUEST_FUNCTIONS:
        errors.append("request_function invalid")
    if snapshot.get("active_quadrant") not in VALID_QUADRANTS:
        errors.append("active_quadrant invalid")
    if not isinstance(snapshot.get("insights_log"), list):
        errors.append("insights_log must be list")
    if "user_state" in snapshot:
        errors.append("legacy field user_state is forbidden")

    return len(errors) == 0, errors
