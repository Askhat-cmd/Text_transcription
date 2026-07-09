"""Diagnostic Center admin runtime control state and effective payload helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from .config import config


class DiagnosticCenterMode(str, Enum):
    DISABLED = "disabled"
    SHADOW = "shadow"
    DEVELOPER = "developer"
    CREATOR_ONLY = "creator_only"
    ALLOWLIST = "allowlist"
    DEVELOPER_LOCAL_ALL_USERS = "developer_local_all_users"


ALLOWED_MODES = [mode.value for mode in DiagnosticCenterMode]
DEFAULT_MODE = DiagnosticCenterMode.CREATOR_ONLY.value
CONTROL_SCHEMA_VERSION = "diagnostic_center_control_v1"
DIAGNOSTIC_CENTER_CREATOR_USER_ID_DEFAULT = "creator"
DIAGNOSTIC_CENTER_DEVELOPER_USER_IDS_DEFAULT = ""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _repo_root() -> Path:
    # .../Text_transcription/bot_psychologist -> .../Text_transcription
    return Path(config.PROJECT_ROOT).resolve().parent


def _safe_str(value: Any, default: str = "") -> str:
    text = str(value or "").strip()
    return text if text else default


def _safe_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    return default


def _sanitize_allowlist(raw: Any) -> list[str]:
    source: list[Any]
    if isinstance(raw, str):
        source = [item.strip() for item in raw.replace(",", "\n").splitlines() if item.strip()]
    elif isinstance(raw, list):
        source = raw
    else:
        source = []
    result: list[str] = []
    seen: set[str] = set()
    for item in source:
        text = _safe_str(item, "")
        if not text:
            continue
        if text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result[:128]


def _default_creator_user_id() -> str:
    return DIAGNOSTIC_CENTER_CREATOR_USER_ID_DEFAULT


def _default_developer_user_ids() -> list[str]:
    env_value = _safe_str(DIAGNOSTIC_CENTER_DEVELOPER_USER_IDS_DEFAULT, "")
    if not env_value:
        return [_default_creator_user_id()]
    return _sanitize_allowlist(env_value)


@dataclass
class DiagnosticCenterControlState:
    mode: str = DEFAULT_MODE
    force_disabled: bool = False
    allowlist_user_ids: list[str] | None = None
    developer_all_users_enabled: bool = False
    updated_at: str = ""
    updated_by: str = "dev"
    reason: str = "default"

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "force_disabled": self.force_disabled,
            "allowlist_user_ids": list(self.allowlist_user_ids or []),
            "developer_all_users_enabled": self.developer_all_users_enabled,
            "updated_at": self.updated_at or _now_iso(),
            "updated_by": self.updated_by,
            "reason": self.reason,
        }


def _normalize_state(raw: dict[str, Any] | None) -> DiagnosticCenterControlState:
    payload = dict(raw or {})
    mode = _safe_str(payload.get("mode"), DEFAULT_MODE)
    if mode not in ALLOWED_MODES:
        mode = DEFAULT_MODE
    allowlist = _sanitize_allowlist(payload.get("allowlist_user_ids"))
    developer_all_users = _safe_bool(payload.get("developer_all_users_enabled"), mode == DiagnosticCenterMode.DEVELOPER_LOCAL_ALL_USERS.value)
    if mode == DiagnosticCenterMode.DEVELOPER_LOCAL_ALL_USERS.value:
        developer_all_users = True
    return DiagnosticCenterControlState(
        mode=mode,
        force_disabled=_safe_bool(payload.get("force_disabled"), False),
        allowlist_user_ids=allowlist,
        developer_all_users_enabled=developer_all_users,
        updated_at=_safe_str(payload.get("updated_at"), _now_iso()),
        updated_by=_safe_str(payload.get("updated_by"), "dev"),
        reason=_safe_str(payload.get("reason"), "manual_update"),
    )


def _read_control_payload() -> dict[str, Any]:
    data = config._load_overrides()  # noqa: SLF001
    return dict(data) if isinstance(data, dict) else {}


def load_diagnostic_center_control_state() -> DiagnosticCenterControlState:
    payload = _read_control_payload()
    section = payload.get("diagnostic_center")
    if not isinstance(section, dict):
        return DiagnosticCenterControlState(
            mode=DEFAULT_MODE,
            force_disabled=False,
            allowlist_user_ids=[],
            developer_all_users_enabled=False,
            updated_at=_now_iso(),
            updated_by="dev",
            reason="default_bootstrap",
        )
    return _normalize_state(section)


def save_diagnostic_center_control_state(state: DiagnosticCenterControlState) -> DiagnosticCenterControlState:
    payload = _read_control_payload()
    payload["diagnostic_center"] = state.to_dict()
    config._save_overrides(payload)  # noqa: SLF001
    return state


def _latest_evidence() -> dict[str, Any]:
    scorecard_path = _repo_root() / "TO_DO_LIST" / "logs" / "PRD-046.1.37-HF1" / "prd_046_1_37_hf1_scorecard.json"
    if not scorecard_path.exists():
        return {
            "last_prd": "PRD-046.1.37-HF1",
            "diagnostic_center_track_status": "closed_for_current_phase",
            "recommended_runner_timeout_sec": 42,
        }
    try:
        import json

        scorecard = json.loads(scorecard_path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        scorecard = {}
    timeout_sec = int(scorecard.get("recommended_runner_timeout_sec", 42) or 42)
    closed = bool(scorecard.get("diagnostic_center_track_closed", False))
    return {
        "last_prd": "PRD-046.1.37-HF1",
        "diagnostic_center_track_status": "closed_for_current_phase" if closed else "pending",
        "recommended_runner_timeout_sec": timeout_sec,
    }


def build_diagnostic_center_effective_payload(state: DiagnosticCenterControlState | None = None) -> dict[str, Any]:
    active_state = state or load_diagnostic_center_control_state()
    warnings: list[str] = []
    if active_state.mode == DiagnosticCenterMode.DEVELOPER_LOCAL_ALL_USERS.value:
        warnings.append("developer_local_all_users_enabled_not_production_rollout")
    effective_active = (
        not active_state.force_disabled
        and active_state.mode not in {DiagnosticCenterMode.DISABLED.value, DiagnosticCenterMode.SHADOW.value}
    )
    scope_note = (
        "all-users switch is available only as developer-local governed mode"
        if active_state.mode == DiagnosticCenterMode.DEVELOPER_LOCAL_ALL_USERS.value
        else "creator/developer governed mode"
    )
    return {
        "schema_version": CONTROL_SCHEMA_VERSION,
        "status": "completed_for_current_creator_only_phase",
        "current_mode": active_state.mode,
        "effective_active": effective_active,
        "force_disabled": active_state.force_disabled,
        "kill_switch_available": True,
        "single_developer_project": True,
        "developer_identity": {
            "creator_user_id": _default_creator_user_id(),
            "developer_user_ids": _default_developer_user_ids(),
            "allowlist_user_ids": list(active_state.allowlist_user_ids or []),
        },
        "available_modes": list(ALLOWED_MODES),
        "boundary_flags": {
            "broad_rollout_allowed": False,
            "production_ready": False,
            "normal_user_activation_allowed": False,
            "external_users_allowed": False,
        },
        "scope": {
            "runtime_scope": "developer_local",
            "external_rollout_scope": "blocked",
            "note": scope_note,
        },
        "last_evidence": _latest_evidence(),
        "control_state": active_state.to_dict(),
        "warnings": warnings,
    }


def apply_diagnostic_center_control_update(payload: dict[str, Any], updated_by: str = "dev") -> dict[str, Any]:
    current = load_diagnostic_center_control_state()
    mode = _safe_str(payload.get("mode"), current.mode)
    if mode not in ALLOWED_MODES:
        raise ValueError(f"invalid mode: {mode}")
    allowlist = _sanitize_allowlist(payload.get("allowlist_user_ids", current.allowlist_user_ids or []))
    force_disabled = _safe_bool(payload.get("force_disabled"), current.force_disabled)
    reason = _safe_str(payload.get("reason"), "manual_update")
    developer_all_users = mode == DiagnosticCenterMode.DEVELOPER_LOCAL_ALL_USERS.value
    state = DiagnosticCenterControlState(
        mode=mode,
        force_disabled=force_disabled,
        allowlist_user_ids=allowlist,
        developer_all_users_enabled=developer_all_users,
        updated_at=_now_iso(),
        updated_by=_safe_str(updated_by, "dev"),
        reason=reason,
    )
    save_diagnostic_center_control_state(state)
    return build_diagnostic_center_effective_payload(state)


def reset_diagnostic_center_control_state(updated_by: str = "dev") -> dict[str, Any]:
    state = DiagnosticCenterControlState(
        mode=DEFAULT_MODE,
        force_disabled=False,
        allowlist_user_ids=[],
        developer_all_users_enabled=False,
        updated_at=_now_iso(),
        updated_by=_safe_str(updated_by, "dev"),
        reason="reset_to_safe_default",
    )
    save_diagnostic_center_control_state(state)
    return build_diagnostic_center_effective_payload(state)


__all__ = [
    "DiagnosticCenterMode",
    "DiagnosticCenterControlState",
    "ALLOWED_MODES",
    "DEFAULT_MODE",
    "CONTROL_SCHEMA_VERSION",
    "load_diagnostic_center_control_state",
    "save_diagnostic_center_control_state",
    "build_diagnostic_center_effective_payload",
    "apply_diagnostic_center_control_update",
    "reset_diagnostic_center_control_state",
]
