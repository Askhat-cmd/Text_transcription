"""Runtime decision builder for prompt-constraint pilot (default-off, allowlisted)."""

from __future__ import annotations

from typing import Any

from ..feature_flags import feature_flags
from .contracts.prompt_constraint_pilot_runtime_v1 import (
    PromptConstraintPilotRuntimeDecision,
    PromptConstraintPilotRuntimeInput,
    PromptConstraintPilotRuntimeTrace,
)
from .contracts.state_snapshot import StateSnapshot
from .contracts.thread_state import ThreadState


_ALLOWED_MODE = {"shadow", "test_apply"}
_DEPTH_ORDER = {"none": 0, "low": 1, "low_to_medium": 2, "medium": 3, "high": 4}


def _safe_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _safe_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def _as_bool(value: Any, default: bool = False) -> bool:
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


def _as_str(value: Any, default: str = "") -> str:
    text = str(value or "").strip()
    return text if text else default


def _as_int(value: Any, default: int, minimum: int = 0) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, parsed)


def _as_float(value: Any, default: float, minimum: float = 0.0) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, parsed)


def _dedupe(values: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for item in values:
        value = str(item or "").strip()
        if not value or value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def _parse_allowed_ids(value: str) -> set[str]:
    return {item.strip() for item in str(value or "").split(",") if item.strip()}


def _feature_snapshot_from_env() -> dict[str, Any]:
    return {
        "PROMPT_CONSTRAINT_PILOT_ENABLED": feature_flags.enabled("PROMPT_CONSTRAINT_PILOT_ENABLED"),
        "PROMPT_CONSTRAINT_PILOT_FORCE_DISABLED": feature_flags.enabled("PROMPT_CONSTRAINT_PILOT_FORCE_DISABLED"),
        "PROMPT_CONSTRAINT_PILOT_MODE": feature_flags.value("PROMPT_CONSTRAINT_PILOT_MODE", "shadow"),
        "PROMPT_CONSTRAINT_PILOT_ALLOWED_USER_IDS": feature_flags.value("PROMPT_CONSTRAINT_PILOT_ALLOWED_USER_IDS", ""),
        "PROMPT_CONSTRAINT_PILOT_TEST_USER_PREFIX": feature_flags.value("PROMPT_CONSTRAINT_PILOT_TEST_USER_PREFIX", "pilot_"),
        "PROMPT_CONSTRAINT_PILOT_MAX_PROMPT_DELTA_CHARS": feature_flags.value("PROMPT_CONSTRAINT_PILOT_MAX_PROMPT_DELTA_CHARS", "2500"),
        "PROMPT_CONSTRAINT_PILOT_MAX_PROMPT_DELTA_RATIO": feature_flags.value("PROMPT_CONSTRAINT_PILOT_MAX_PROMPT_DELTA_RATIO", "0.35"),
    }


def _eligible_user(*, user_id: str, allowed_user_ids: set[str], test_user_prefix: str) -> bool:
    if not user_id:
        return False
    if user_id in allowed_user_ids:
        return True
    if test_user_prefix and user_id.startswith(test_user_prefix):
        return True
    return False


def _safety_gate_ok(
    *,
    candidate_constraints: dict[str, Any],
    state_snapshot: StateSnapshot,
    thread_state: ThreadState,
) -> bool:
    safety_case = bool(
        state_snapshot.safety_flag
        or thread_state.safety_active
        or state_snapshot.nervous_state in {"hyper", "hypo"}
    )
    if not safety_case:
        return True
    depth = _as_str(candidate_constraints.get("depth_limit"), "none")
    max_questions = _as_int(candidate_constraints.get("max_questions"), 0)
    max_concepts = _as_int(candidate_constraints.get("max_concepts"), 1, minimum=1)
    return _DEPTH_ORDER.get(depth, 2) <= _DEPTH_ORDER["low"] and max_questions <= 0 and max_concepts <= 1


def build_prompt_constraint_pilot_runtime_decision_v1(
    *,
    user_id: str,
    writer_prompt_replay_result: dict[str, Any],
    writer_contract_pilot: dict[str, Any],
    state_snapshot: StateSnapshot,
    thread_state: ThreadState,
    feature_flags_snapshot: dict[str, Any] | None = None,
) -> PromptConstraintPilotRuntimeDecision:
    snapshot = _safe_dict(feature_flags_snapshot) if feature_flags_snapshot is not None else _feature_snapshot_from_env()

    _ = PromptConstraintPilotRuntimeInput(
        user_id=user_id,
        writer_prompt_replay_result=writer_prompt_replay_result,
        writer_contract_pilot=writer_contract_pilot,
        state_snapshot=state_snapshot.to_dict(),
        thread_state=thread_state.to_dict(),
        feature_flag_snapshot=snapshot,
    )

    enabled = _as_bool(snapshot.get("PROMPT_CONSTRAINT_PILOT_ENABLED"), False)
    force_disabled = _as_bool(snapshot.get("PROMPT_CONSTRAINT_PILOT_FORCE_DISABLED"), True)
    mode = _as_str(snapshot.get("PROMPT_CONSTRAINT_PILOT_MODE"), "shadow")
    if mode not in _ALLOWED_MODE:
        mode = "shadow"
    allowed_user_ids = _parse_allowed_ids(_as_str(snapshot.get("PROMPT_CONSTRAINT_PILOT_ALLOWED_USER_IDS"), ""))
    test_user_prefix = _as_str(snapshot.get("PROMPT_CONSTRAINT_PILOT_TEST_USER_PREFIX"), "pilot_")
    max_delta_chars = _as_int(snapshot.get("PROMPT_CONSTRAINT_PILOT_MAX_PROMPT_DELTA_CHARS"), 2500, minimum=100)
    max_delta_ratio = _as_float(snapshot.get("PROMPT_CONSTRAINT_PILOT_MAX_PROMPT_DELTA_RATIO"), 0.35, minimum=0.05)

    replay = _safe_dict(writer_prompt_replay_result)
    replay_quality = _safe_dict(replay.get("quality"))
    replay_comparison = _safe_dict(replay.get("comparison"))
    replay_blocked = _safe_list(replay.get("blocked_reasons"))

    pilot_overlay = _safe_dict(_safe_dict(writer_contract_pilot).get("overlay"))
    candidate_constraints = _safe_dict(pilot_overlay.get("candidate_constraints"))

    rules: list[str] = ["default_off_guardrail", "force_disabled_guardrail", "allowlist_guardrail"]
    blocked_reasons: list[str] = []
    warnings: list[str] = []

    eligible = _eligible_user(
        user_id=user_id,
        allowed_user_ids=allowed_user_ids,
        test_user_prefix=test_user_prefix,
    )

    if force_disabled:
        blocked_reasons.append("force_disabled_active")
        rules.append("rollback_priority")
        return PromptConstraintPilotRuntimeDecision(
            activation_mode="disabled",
            apply_to_writer_prompt=False,
            rollback_active=True,
            eligible_user=eligible,
            feature_flag_snapshot=snapshot,
            candidate_constraints=candidate_constraints,
            blocked_reasons=_dedupe(blocked_reasons),
            warnings=_dedupe(warnings),
            trace=PromptConstraintPilotRuntimeTrace(
                rules_applied=_dedupe(rules),
                warnings=_dedupe(warnings),
            ),
        )

    if not enabled:
        blocked_reasons.append("feature_flag_disabled")
        return PromptConstraintPilotRuntimeDecision(
            activation_mode="disabled",
            apply_to_writer_prompt=False,
            rollback_active=False,
            eligible_user=eligible,
            feature_flag_snapshot=snapshot,
            candidate_constraints=candidate_constraints,
            blocked_reasons=_dedupe(blocked_reasons),
            warnings=_dedupe(warnings),
            trace=PromptConstraintPilotRuntimeTrace(
                rules_applied=_dedupe(rules),
                warnings=_dedupe(warnings),
            ),
        )

    # shadow mode never applies to prompt
    if mode == "shadow":
        rules.append("shadow_mode_no_apply")
        return PromptConstraintPilotRuntimeDecision(
            activation_mode="shadow_only",
            apply_to_writer_prompt=False,
            rollback_active=False,
            eligible_user=eligible,
            feature_flag_snapshot=snapshot,
            candidate_constraints=candidate_constraints,
            blocked_reasons=_dedupe(blocked_reasons),
            warnings=_dedupe(warnings),
            trace=PromptConstraintPilotRuntimeTrace(
                rules_applied=_dedupe(rules),
                warnings=_dedupe(warnings),
            ),
        )

    # test_apply path
    if not eligible:
        blocked_reasons.append("user_not_allowlisted")
        return PromptConstraintPilotRuntimeDecision(
            activation_mode="disabled",
            apply_to_writer_prompt=False,
            rollback_active=False,
            eligible_user=False,
            feature_flag_snapshot=snapshot,
            candidate_constraints=candidate_constraints,
            blocked_reasons=_dedupe(blocked_reasons),
            warnings=_dedupe(warnings),
            trace=PromptConstraintPilotRuntimeTrace(
                rules_applied=_dedupe(rules + ["allowlist_blocked"]),
                warnings=_dedupe(warnings),
            ),
        )

    quality_status = _as_str(replay_quality.get("quality_status"), "blocked")
    if quality_status != "passed":
        blocked_reasons.append(f"replay_quality_{quality_status}")

    if not _as_bool(replay_quality.get("safety_ok"), False):
        blocked_reasons.append("replay_safety_not_ok")
    if not _as_bool(replay_quality.get("kb_boundary_ok"), False):
        blocked_reasons.append("replay_kb_boundary_not_ok")
    if not _as_bool(replay_quality.get("constraint_conflict_ok"), False):
        blocked_reasons.append("replay_conflict_not_ok")
    if not _as_bool(replay_quality.get("prompt_bloat_ok"), False):
        blocked_reasons.append("replay_prompt_bloat_not_ok")
    if not _as_bool(replay_quality.get("non_mutating_ok"), False):
        blocked_reasons.append("replay_non_mutating_not_ok")

    if any(item in replay_blocked for item in {"prompt_bloat_blocker", "constraint_conflict", "kb_boundary_violation"}):
        blocked_reasons.extend([item for item in replay_blocked if item in {"prompt_bloat_blocker", "constraint_conflict", "kb_boundary_violation"}])

    forbidden_hits = _safe_list(replay_comparison.get("forbidden_field_hits"))
    if forbidden_hits:
        blocked_reasons.append("forbidden_kb_fields_detected")

    conflict_rules = _safe_list(replay_comparison.get("conflict_rules"))
    if conflict_rules:
        blocked_reasons.append("constraint_conflict_rules_detected")

    delta_chars = _as_int(replay_comparison.get("size_delta_chars"), 0)
    delta_ratio = _as_float(replay_comparison.get("size_delta_ratio"), 0.0)
    if delta_chars > max_delta_chars or delta_ratio > max_delta_ratio:
        blocked_reasons.append("prompt_delta_limit_exceeded")

    if not _safety_gate_ok(
        candidate_constraints=candidate_constraints,
        state_snapshot=state_snapshot,
        thread_state=thread_state,
    ):
        blocked_reasons.append("unsafe_constraints_for_current_state")

    activation_mode = "test_apply"
    apply_to_writer_prompt = True
    if blocked_reasons:
        activation_mode = "shadow_only"
        apply_to_writer_prompt = False
        warnings.append("downgraded_to_shadow_due_to_gates")

    rules.append("test_apply_eligibility_checked")
    rules.append("replay_quality_gate_checked")
    rules.append("safety_kb_conflict_bloat_gates_checked")

    return PromptConstraintPilotRuntimeDecision(
        activation_mode=activation_mode,
        apply_to_writer_prompt=apply_to_writer_prompt,
        rollback_active=False,
        eligible_user=True,
        feature_flag_snapshot=snapshot,
        candidate_constraints=candidate_constraints,
        blocked_reasons=_dedupe(blocked_reasons),
        warnings=_dedupe(warnings),
        trace=PromptConstraintPilotRuntimeTrace(
            rules_applied=_dedupe(rules),
            warnings=_dedupe(warnings),
        ),
    )
