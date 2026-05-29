from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


LIVE_FEEDBACK_SCHEMA_VERSION = "live_feedback_v1"

REPO_ROOT = Path(__file__).resolve().parents[3]
LIVE_FEEDBACK_BASE_DIR = REPO_ROOT / "TO_DO_LIST" / "live_feedback" / "PRD-047.7"


@dataclass(frozen=True)
class LiveFeedbackRecord:
    schema_version: str
    session_id: str
    turn_id: str
    created_at_utc: str
    scenario_id: str | None
    user_rating: int | None
    felt_alive: bool | None
    felt_understood: bool | None
    felt_too_rigid: bool | None
    felt_too_generic: bool | None
    felt_too_long: bool | None
    felt_too_short: bool | None
    too_much_practice: bool | None
    too_many_questions: bool | None
    missed_context: bool | None
    safety_concern: bool | None
    comment: str
    trace_summary: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def sanitize_identifier(value: str, *, fallback: str, max_len: int = 96) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"[^a-z0-9_-]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    if not text:
        text = fallback
    return text[:max_len]


def normalize_rating(value: int | str | None) -> int | None:
    if value is None:
        return None
    try:
        rating = int(value)
    except (TypeError, ValueError):
        return None
    if rating < 1:
        return 1
    if rating > 5:
        return 5
    return rating


def _normalize_optional_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    lowered = str(value).strip().lower()
    if lowered in {"1", "true", "yes", "y", "on"}:
        return True
    if lowered in {"0", "false", "no", "n", "off"}:
        return False
    return None


def _clip_text(text: str, *, limit: int) -> str:
    value = str(text or "").strip()
    if len(value) <= limit:
        return value
    return value[: max(0, limit - 1)].rstrip() + "…"


def _hash_user_id(user_id: str) -> str:
    return "u:" + hashlib.sha256(str(user_id or "").encode("utf-8")).hexdigest()[:12]


def _safe_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def build_trace_summary(
    *,
    debug_payload: dict[str, Any] | None,
    user_message_preview: str = "",
    answer_preview: str = "",
    user_id: str | None = None,
) -> dict[str, Any]:
    debug = _safe_dict(debug_payload)
    active_line = _safe_dict(debug.get("active_line"))
    planner = _safe_dict(debug.get("response_planner"))
    drift = _safe_dict(debug.get("planner_drift_guard"))

    trace_summary: dict[str, Any] = {
        "active_line": {
            "user_intent": str(active_line.get("user_intent", "") or ""),
            "continuity_mode": str(active_line.get("continuity_mode", "") or ""),
            "next_meaningful_move": str(planner.get("next_move", "") or ""),
        },
        "response_planner": {
            "next_move": str(planner.get("next_move", "") or ""),
            "answer_shape": str(planner.get("answer_shape", "") or ""),
            "response_depth": str(planner.get("response_depth", "") or ""),
            "question_policy": str(planner.get("question_policy", "") or ""),
            "practice_policy": str(planner.get("practice_policy", "") or ""),
        },
        "planner_drift_guard": {
            "status": str(drift.get("status", "") or ""),
            "severity": str(drift.get("severity", "") or ""),
            "flags": [
                str(flag)
                for flag in list(drift.get("flags", []) or [])
                if str(flag).strip()
            ],
        },
        "writer": {
            "model": str(debug.get("model_used", "") or ""),
            "fallback_used": bool(debug.get("writer_fallback_used", False)),
        },
        "user_message_preview": _clip_text(user_message_preview, limit=180),
        "answer_preview": _clip_text(answer_preview, limit=240),
    }
    if user_id:
        trace_summary["user_id_hash"] = _hash_user_id(user_id)
    return trace_summary


def create_feedback_record(
    *,
    session_id: str,
    turn_id: str,
    scenario_id: str | None = None,
    user_rating: int | str | None = None,
    felt_alive: Any = None,
    felt_understood: Any = None,
    felt_too_rigid: Any = None,
    felt_too_generic: Any = None,
    felt_too_long: Any = None,
    felt_too_short: Any = None,
    too_much_practice: Any = None,
    too_many_questions: Any = None,
    missed_context: Any = None,
    safety_concern: Any = None,
    comment: str = "",
    trace_summary: dict[str, Any] | None = None,
) -> LiveFeedbackRecord:
    return LiveFeedbackRecord(
        schema_version=LIVE_FEEDBACK_SCHEMA_VERSION,
        session_id=sanitize_identifier(session_id, fallback="live_test_session"),
        turn_id=sanitize_identifier(turn_id, fallback="turn_1"),
        created_at_utc=_now_iso(),
        scenario_id=(sanitize_identifier(scenario_id, fallback="scenario") if scenario_id else None),
        user_rating=normalize_rating(user_rating),
        felt_alive=_normalize_optional_bool(felt_alive),
        felt_understood=_normalize_optional_bool(felt_understood),
        felt_too_rigid=_normalize_optional_bool(felt_too_rigid),
        felt_too_generic=_normalize_optional_bool(felt_too_generic),
        felt_too_long=_normalize_optional_bool(felt_too_long),
        felt_too_short=_normalize_optional_bool(felt_too_short),
        too_much_practice=_normalize_optional_bool(too_much_practice),
        too_many_questions=_normalize_optional_bool(too_many_questions),
        missed_context=_normalize_optional_bool(missed_context),
        safety_concern=_normalize_optional_bool(safety_concern),
        comment=_clip_text(comment, limit=1200),
        trace_summary=_safe_dict(trace_summary),
    )


def get_feedback_sessions_dir() -> Path:
    path = LIVE_FEEDBACK_BASE_DIR / "sessions"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_feedback_reports_dir() -> Path:
    path = LIVE_FEEDBACK_BASE_DIR / "reports"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_session_storage_path(session_id: str) -> Path:
    safe_session_id = sanitize_identifier(session_id, fallback="live_test_session")
    return get_feedback_sessions_dir() / f"{safe_session_id}.json"


def load_session_payload(session_id: str) -> dict[str, Any] | None:
    path = get_session_storage_path(session_id)
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else None


def _initial_session_payload(
    *,
    session_id: str,
    tester_role: str,
    runtime_mode: str,
    backend_url: str,
    frontend_url: str,
    scenario_set: str,
) -> dict[str, Any]:
    now = _now_iso()
    return {
        "session_id": sanitize_identifier(session_id, fallback="live_test_session"),
        "started_at_utc": now,
        "ended_at_utc": now,
        "tester_role": str(tester_role or "project_owner"),
        "runtime_mode": str(runtime_mode or "developer_local"),
        "backend_url": str(backend_url or ""),
        "frontend_url": str(frontend_url or ""),
        "scenario_set": str(scenario_set or "guided_live_v1"),
        "turns_total": 0,
        "feedback_count": 0,
        "drift_warning_count": 0,
        "drift_critical_count": 0,
        "notes": [],
        "records": [],
    }


def _recalculate_session_counters(payload: dict[str, Any]) -> None:
    records = [
        item for item in list(payload.get("records", []) or []) if isinstance(item, dict)
    ]
    payload["records"] = records
    payload["feedback_count"] = len(records)
    payload["turns_total"] = len(records)

    warning_count = 0
    critical_count = 0
    for item in records:
        trace_summary = _safe_dict(item.get("trace_summary"))
        drift = _safe_dict(trace_summary.get("planner_drift_guard"))
        status = str(drift.get("status", "") or "")
        if status == "warning":
            warning_count += 1
        elif status == "critical":
            critical_count += 1

    payload["drift_warning_count"] = warning_count
    payload["drift_critical_count"] = critical_count
    payload["ended_at_utc"] = _now_iso()


def append_feedback_record(
    *,
    record: LiveFeedbackRecord,
    tester_role: str = "project_owner",
    runtime_mode: str = "developer_local",
    backend_url: str = "",
    frontend_url: str = "",
    scenario_set: str = "guided_live_v1",
) -> dict[str, Any]:
    payload = load_session_payload(record.session_id)
    if not isinstance(payload, dict):
        payload = _initial_session_payload(
            session_id=record.session_id,
            tester_role=tester_role,
            runtime_mode=runtime_mode,
            backend_url=backend_url,
            frontend_url=frontend_url,
            scenario_set=scenario_set,
        )

    if payload.get("session_id") != record.session_id:
        payload["session_id"] = record.session_id

    records = [
        item for item in list(payload.get("records", []) or []) if isinstance(item, dict)
    ]
    records.append(record.to_dict())
    payload["records"] = records

    _recalculate_session_counters(payload)

    path = get_session_storage_path(record.session_id)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload
