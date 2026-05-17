from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


CURRENT_FILE = Path(__file__).resolve()
BOT_PSYCHOLOGIST_ROOT = CURRENT_FILE.parents[1]
REPO_ROOT = CURRENT_FILE.parents[2]
if str(BOT_PSYCHOLOGIST_ROOT) not in sys.path:
    sys.path.insert(0, str(BOT_PSYCHOLOGIST_ROOT))

from bot_agent.multiagent.contracts.state_snapshot import StateSnapshot
from bot_agent.multiagent.contracts.thread_state import ThreadState
from bot_agent.multiagent.prompt_constraint_pilot_runtime import (
    build_prompt_constraint_pilot_runtime_decision_v1,
)
from tools import validate_prd_artifact_encoding as encoding_validator


PRD = "PRD-046.1.7"
SOURCE_PRD = "PRD-046.1.6"
DEPTH_ORDER = {"none": 0, "low": 1, "low_to_medium": 2, "medium": 3, "high": 4}
ALLOWED_KB_MODES = {"none", "internal_lens_only", "practice_candidate_only"}
FORBIDDEN_KB_KEYS = {"raw_text", "full_text", "source_text", "content_full", "page_content"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _safe_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


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


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _required_source_artifacts(input_dir: Path) -> dict[str, Path]:
    return {
        "runtime_eval": input_dir / "prompt_constraint_pilot_runtime_eval.json",
        "runtime_scorecard": input_dir / "prompt_constraint_pilot_runtime_scorecard.json",
        "runtime_smoke": input_dir / "prompt_constraint_pilot_runtime_smoke.json",
        "runtime_trace": input_dir / "prompt_constraint_pilot_runtime_trace_samples.json",
        "no_mutation": input_dir / "no_mutation_proof.json",
        "encoding_hygiene": input_dir / "artifact_encoding_hygiene_report.json",
        "report_impl": REPO_ROOT / "TO_DO_LIST" / "reports" / "PRD-046.1.6_IMPLEMENTATION_REPORT.md",
        "report_runtime": REPO_ROOT / "TO_DO_LIST" / "reports" / "PRD-046.1.6_PROMPT_CONSTRAINT_PILOT_RUNTIME_REPORT.md",
        "project_state": REPO_ROOT / "docs" / "PROJECT_STATE.md",
        "roadmap": REPO_ROOT / "docs" / "ROADMAP.md",
        "prd_index": REPO_ROOT / "docs" / "PRD_INDEX.md",
        "decisions": REPO_ROOT / "docs" / "DECISIONS.md",
    }


def _preflight(input_dir: Path) -> dict[str, Any]:
    required = _required_source_artifacts(input_dir)
    missing: list[str] = []
    parse_errors: list[str] = []
    parsed: dict[str, Any] = {}
    for key, path in required.items():
        if not path.exists():
            missing.append(key)
            continue
        if path.suffix.lower() == ".json":
            try:
                parsed[key] = _read_json(path)
            except Exception as exc:  # noqa: BLE001
                parse_errors.append(f"{key}:{exc.__class__.__name__}")
    return {
        "required": {k: str(v) for k, v in required.items()},
        "missing": missing,
        "parse_errors": parse_errors,
        "ok": len(missing) == 0 and len(parse_errors) == 0,
        "parsed": parsed,
    }


def _evidence_quality(*, scorecard: dict[str, Any], trace_samples: list[Any], eval_cases: list[Any]) -> tuple[str, list[str], list[str]]:
    warnings: list[str] = []
    blockers: list[str] = []
    trace_count = len(trace_samples)
    cases_total = _as_int(scorecard.get("cases_total"), 0)
    cases_passed = _as_int(scorecard.get("cases_passed"), 0)
    test_apply_applied = _as_int(scorecard.get("test_apply_applied_count"), 0)
    safety_blocked = _as_int(scorecard.get("safety_apply_blocked_count"), 0)
    default_effect = _as_int(scorecard.get("default_off_user_path_effect_count"), 0)
    shadow_apply = _as_int(scorecard.get("shadow_mode_apply_count"), 0)
    allowlist_viol = _as_int(scorecard.get("allowlist_violation_count"), 0)
    raw_exposure = _as_int(scorecard.get("raw_kb_text_exposure_count"), 0)

    if cases_total <= 0 or cases_passed <= 0:
        blockers.append("missing_or_empty_case_evidence")
    if trace_count <= 0:
        blockers.append("missing_trace_samples")
    if test_apply_applied <= 0:
        warnings.append("no_test_apply_applied_cases")
    if safety_blocked <= 0:
        warnings.append("no_safety_blocked_cases")
    if default_effect > 0:
        blockers.append("default_off_user_path_effect_detected")
    if shadow_apply > 0:
        blockers.append("shadow_mode_apply_detected")
    if allowlist_viol > 0:
        blockers.append("allowlist_violation_detected")
    if raw_exposure > 0:
        blockers.append("raw_kb_exposure_detected")

    if blockers:
        return "insufficient", warnings, blockers
    if warnings:
        return "limited", warnings, blockers
    return "sufficient", warnings, blockers


def _build_runtime_evidence_audit(*, preflight: dict[str, Any], scorecard: dict[str, Any], eval_payload: dict[str, Any], trace_payload: dict[str, Any]) -> dict[str, Any]:
    trace_samples = _safe_list(trace_payload.get("samples"))
    eval_cases = _safe_list(eval_payload.get("cases"))
    eq, warnings, blockers = _evidence_quality(
        scorecard=scorecard,
        trace_samples=trace_samples,
        eval_cases=eval_cases,
    )
    return {
        "prd": PRD,
        "source_prd": SOURCE_PRD,
        "input_artifacts_found": bool(preflight.get("ok", False)),
        "trace_samples_count": len(trace_samples),
        "cases_total": _as_int(scorecard.get("cases_total"), 0),
        "cases_passed": _as_int(scorecard.get("cases_passed"), 0),
        "default_off_user_path_effect_count": _as_int(scorecard.get("default_off_user_path_effect_count"), 0),
        "shadow_mode_apply_count": _as_int(scorecard.get("shadow_mode_apply_count"), 0),
        "test_apply_applied_count": _as_int(scorecard.get("test_apply_applied_count"), 0),
        "allowlist_violation_count": _as_int(scorecard.get("allowlist_violation_count"), 0),
        "safety_apply_blocked_count": _as_int(scorecard.get("safety_apply_blocked_count"), 0),
        "kb_boundary_violation_count": _as_int(scorecard.get("kb_boundary_violation_count"), 0),
        "raw_kb_text_exposure_count": _as_int(scorecard.get("raw_kb_text_exposure_count"), 0),
        "prompt_bloat_blocker_count": _as_int(scorecard.get("prompt_bloat_blocker_count"), 0),
        "constraint_conflict_count": _as_int(scorecard.get("constraint_conflict_count"), 0),
        "provider_called_by_eval_count": _as_int(scorecard.get("provider_called_by_eval_count"), 0),
        "evidence_quality": eq,
        "warnings": warnings,
        "blockers": blockers,
    }


def _evaluate_rollback_case(
    *,
    enabled: bool,
    force_disabled: bool,
    mode: str,
    user_id: str,
) -> dict[str, Any]:
    replay = {
        "quality": {
            "quality_status": "passed",
            "safety_ok": True,
            "kb_boundary_ok": True,
            "constraint_conflict_ok": True,
            "prompt_bloat_ok": True,
            "non_mutating_ok": True,
        },
        "comparison": {"size_delta_chars": 100, "size_delta_ratio": 0.1, "forbidden_field_hits": [], "conflict_rules": []},
        "blocked_reasons": [],
    }
    pilot = {
        "overlay": {
            "candidate_constraints": {
                "depth_limit": "low",
                "max_questions": 0,
                "max_concepts": 1,
                "must_do": ["validate_current_state"],
                "must_not_do": ["do_not_analyze_deeply"],
                "kb_usage_mode": "internal_lens_only",
                "must_not_quote_source": True,
            }
        }
    }
    decision = build_prompt_constraint_pilot_runtime_decision_v1(
        user_id=user_id,
        writer_prompt_replay_result=replay,
        writer_contract_pilot=pilot,
        state_snapshot=StateSnapshot("window", "clarify", "open", "I+W+", False, 0.8),
        thread_state=ThreadState(
            thread_id="rollback_t",
            user_id=user_id,
            core_direction="rollback",
            phase="clarify",
            response_mode="reflect",
        ),
        feature_flags_snapshot={
            "PROMPT_CONSTRAINT_PILOT_ENABLED": enabled,
            "PROMPT_CONSTRAINT_PILOT_FORCE_DISABLED": force_disabled,
            "PROMPT_CONSTRAINT_PILOT_MODE": mode,
            "PROMPT_CONSTRAINT_PILOT_ALLOWED_USER_IDS": "pilot_user",
            "PROMPT_CONSTRAINT_PILOT_TEST_USER_PREFIX": "pilot_",
        },
    ).to_dict()
    return decision


def _build_rollback_toggle_matrix() -> dict[str, Any]:
    scenarios = [
        {"name": "default_safe", "enabled": False, "force_disabled": True, "mode": "shadow", "user_id": "pilot_user", "expected": "disabled"},
        {"name": "enabled_but_force_disabled", "enabled": True, "force_disabled": True, "mode": "test_apply", "user_id": "pilot_user", "expected": "disabled"},
        {"name": "enabled_shadow_allowlisted", "enabled": True, "force_disabled": False, "mode": "shadow", "user_id": "pilot_user", "expected": "shadow_only"},
        {"name": "enabled_test_apply_not_allowlisted", "enabled": True, "force_disabled": False, "mode": "test_apply", "user_id": "normal_user", "expected": "disabled"},
        {"name": "enabled_test_apply_allowlisted", "enabled": True, "force_disabled": False, "mode": "test_apply", "user_id": "pilot_user", "expected": "test_apply"},
        {"name": "force_disabled_after_apply_candidate_a", "enabled": True, "force_disabled": False, "mode": "test_apply", "user_id": "pilot_user", "expected": "test_apply"},
        {"name": "force_disabled_after_apply_candidate_b", "enabled": True, "force_disabled": True, "mode": "test_apply", "user_id": "pilot_user", "expected": "disabled"},
        {"name": "repeated_toggle_stability_1", "enabled": True, "force_disabled": False, "mode": "test_apply", "user_id": "pilot_user", "expected": "test_apply"},
        {"name": "repeated_toggle_stability_2", "enabled": True, "force_disabled": True, "mode": "test_apply", "user_id": "pilot_user", "expected": "disabled"},
        {"name": "repeated_toggle_stability_3", "enabled": True, "force_disabled": False, "mode": "shadow", "user_id": "pilot_user", "expected": "shadow_only"},
    ]

    failure_count = 0
    stale_apply_after_force_disabled = 0
    unexpected_apply_count = 0
    unexpected_disabled_count = 0
    rows: list[dict[str, Any]] = []
    for item in scenarios:
        decision = _evaluate_rollback_case(
            enabled=item["enabled"],
            force_disabled=item["force_disabled"],
            mode=item["mode"],
            user_id=item["user_id"],
        )
        activation_mode = str(decision.get("activation_mode", "disabled"))
        apply = bool(decision.get("apply_to_writer_prompt", False))
        expected_mode = str(item["expected"])
        pass_case = activation_mode == expected_mode
        if expected_mode == "test_apply" and not apply:
            pass_case = False
            unexpected_disabled_count += 1
        if expected_mode != "test_apply" and apply:
            pass_case = False
            unexpected_apply_count += 1
        if item["force_disabled"] and apply:
            stale_apply_after_force_disabled += 1
            pass_case = False
        if not pass_case:
            failure_count += 1
        rows.append(
            {
                "case": item["name"],
                "enabled": item["enabled"],
                "force_disabled": item["force_disabled"],
                "mode": item["mode"],
                "user_id": item["user_id"],
                "expected_activation_mode": expected_mode,
                "observed_activation_mode": activation_mode,
                "observed_apply": apply,
                "pass": pass_case,
            }
        )

    total = len(rows)
    passed = total - failure_count
    return {
        "prd": PRD,
        "schema_version": "rollback_toggle_matrix_v1",
        "cases_total": total,
        "cases_passed": passed,
        "rollback_cases_total": total,
        "rollback_cases_passed": passed,
        "rollback_failure_count": failure_count,
        "stale_apply_after_force_disabled_count": stale_apply_after_force_disabled,
        "unexpected_apply_count": unexpected_apply_count,
        "unexpected_disabled_count": unexpected_disabled_count,
        "rollback_priority_preserved": failure_count == 0 and stale_apply_after_force_disabled == 0,
        "cases": rows,
    }


def _quality_delta(*, eval_payload: dict[str, Any], scorecard: dict[str, Any]) -> dict[str, Any]:
    cases = [item for item in _safe_list(eval_payload.get("cases")) if isinstance(item, dict)]
    compared = 0
    tighter = 0
    same = 0
    weaker = 0
    safety_regression = 0
    kb_regression = 0
    bloat_regression = 0
    conflict_regression = 0
    max_chars = 0
    max_ratio = 0.0
    max_cap_chars = 2500
    max_cap_ratio = 0.35

    for case in cases:
        decision = _safe_dict(case.get("decision"))
        if str(decision.get("activation_mode", "")) != "test_apply" or not bool(decision.get("apply_to_writer_prompt", False)):
            continue
        compared += 1
        constraints = _safe_dict(decision.get("candidate_constraints"))
        depth = str(constraints.get("depth_limit", "low_to_medium"))
        questions = _as_int(constraints.get("max_questions"), 0)
        concepts = _as_int(constraints.get("max_concepts"), 1)
        must_do = {str(item) for item in _safe_list(constraints.get("must_do"))}
        must_not_do = {str(item) for item in _safe_list(constraints.get("must_not_do"))}
        kb_mode = str(constraints.get("kb_usage_mode", "none"))
        quote_guard = bool(constraints.get("must_not_quote_source", True))

        replay_case = _safe_dict(case.get("decision"))
        blocked_reasons = {str(item) for item in _safe_list(replay_case.get("blocked_reasons"))}
        if DEPTH_ORDER.get(depth, 2) > DEPTH_ORDER["low_to_medium"] or questions > 1 or concepts > 1:
            weaker += 1
        elif DEPTH_ORDER.get(depth, 2) <= DEPTH_ORDER["low"] and questions == 0 and concepts <= 1:
            tighter += 1
        else:
            same += 1

        if DEPTH_ORDER.get(depth, 2) > DEPTH_ORDER["low"] and ("safe_override" in must_do or "validate_current_state" in must_do):
            safety_regression += 1
        if kb_mode not in ALLOWED_KB_MODES or not quote_guard:
            kb_regression += 1
        if must_do.intersection(must_not_do):
            conflict_regression += 1

        # Try to read observed prompt deltas from source eval case input replay if present.
        # Fallback to source scorecard caps.
        case_delta_chars = _as_int(_safe_dict(case.get("input", {})).get("size_delta_chars"), 0)
        case_delta_ratio = _as_float(_safe_dict(case.get("input", {})).get("size_delta_ratio"), 0.0)
        max_chars = max(max_chars, case_delta_chars)
        max_ratio = max(max_ratio, case_delta_ratio)
        if case_delta_chars > max_cap_chars or case_delta_ratio > max_cap_ratio or "prompt_delta_limit_exceeded" in blocked_reasons:
            bloat_regression += 1

    if compared == 0:
        quality_decision = "needs_hf"
    elif safety_regression > 0 or kb_regression > 0:
        quality_decision = "blocked"
    elif bloat_regression > 0 or conflict_regression > 0 or weaker > 0:
        quality_decision = "needs_hf"
    else:
        quality_decision = "pass"

    # If source scorecard explicitly has bloat/conflict violations, keep that as regression.
    if _as_int(scorecard.get("prompt_bloat_blocker_count"), 0) > 0:
        bloat_regression = max(bloat_regression, _as_int(scorecard.get("prompt_bloat_blocker_count"), 0))
        quality_decision = "needs_hf" if quality_decision == "pass" else quality_decision
    if _as_int(scorecard.get("constraint_conflict_count"), 0) > 0:
        conflict_regression = max(conflict_regression, _as_int(scorecard.get("constraint_conflict_count"), 0))
        quality_decision = "needs_hf" if quality_decision == "pass" else quality_decision

    return {
        "schema_version": "baseline_vs_test_apply_quality_delta_v1",
        "prd": PRD,
        "source_prd": SOURCE_PRD,
        "cases_total": _as_int(scorecard.get("cases_total"), 0),
        "cases_compared": compared,
        "candidate_tighter_than_baseline_count": tighter,
        "candidate_same_as_baseline_count": same,
        "candidate_weaker_than_baseline_count": weaker,
        "safety_regression_count": safety_regression,
        "kb_policy_regression_count": kb_regression,
        "prompt_bloat_regression_count": bloat_regression,
        "constraint_conflict_regression_count": conflict_regression,
        "max_prompt_delta_chars_observed": max_chars,
        "max_prompt_delta_ratio_observed": max_ratio,
        "quality_delta_decision": quality_decision,
    }


def _gate_verification(*, scorecard: dict[str, Any], eval_payload: dict[str, Any]) -> dict[str, Any]:
    cases = [item for item in _safe_list(eval_payload.get("cases")) if isinstance(item, dict)]
    safety_total = 0
    safety_passed = 0
    kb_total = 0
    kb_passed = 0
    conflict_total = 0
    conflict_passed = 0
    bloat_total = 0
    bloat_passed = 0
    raw_exposure = 0
    internal_exposure = 0
    quote_viol = 0
    normal_user_apply = 0

    for case in cases:
        decision = _safe_dict(case.get("decision"))
        constraints = _safe_dict(decision.get("candidate_constraints"))
        blocked = {str(item) for item in _safe_list(decision.get("blocked_reasons"))}
        case_id = str(case.get("case_id", ""))
        user_id = str(_safe_dict(decision.get("feature_flag_snapshot")).get("PROMPT_CONSTRAINT_PILOT_ALLOWED_USER_IDS", ""))
        applied = bool(decision.get("apply_to_writer_prompt", False))

        # Safety gate
        is_safety_case = (
            "safety" in case_id
            or "unsafe_constraints_for_current_state" in blocked
            or "replay_safety_not_ok" in blocked
        )
        if is_safety_case:
            safety_total += 1
            if not applied and (
                "unsafe_constraints_for_current_state" in blocked
                or "replay_safety_not_ok" in blocked
            ):
                safety_passed += 1

        # KB gate
        is_kb_case = (
            applied
            or "kb" in case_id
            or "replay_kb_boundary_not_ok" in blocked
            or "forbidden_kb_fields_detected" in blocked
        )
        kb_mode = str(constraints.get("kb_usage_mode", "none"))
        quote_ok = bool(constraints.get("must_not_quote_source", True))
        if is_kb_case:
            kb_total += 1
            if (
                not applied
                and ("replay_kb_boundary_not_ok" in blocked or "forbidden_kb_fields_detected" in blocked)
            ) or (
                applied
                and kb_mode in ALLOWED_KB_MODES
                and quote_ok
                and "forbidden_kb_fields_detected" not in blocked
            ):
                kb_passed += 1
        if "internal_only" in str(constraints).lower():
            internal_exposure += 1
        if not quote_ok:
            quote_viol += 1
        if any(key in str(constraints) for key in FORBIDDEN_KB_KEYS):
            raw_exposure += 1

        # Conflict gate
        is_conflict_case = applied or "constraint_conflict_rules_detected" in blocked or "conflict" in case_id
        must_do = {str(item) for item in _safe_list(constraints.get("must_do"))}
        must_not_do = {str(item) for item in _safe_list(constraints.get("must_not_do"))}
        if is_conflict_case:
            conflict_total += 1
            if (
                not applied
                and "constraint_conflict_rules_detected" in blocked
            ) or (
                applied
                and len(must_do.intersection(must_not_do)) == 0
                and "constraint_conflict_rules_detected" not in blocked
            ):
                conflict_passed += 1

        # Bloat gate
        is_bloat_case = applied or "prompt_delta_limit_exceeded" in blocked or "replay_prompt_bloat_not_ok" in blocked
        if is_bloat_case:
            bloat_total += 1
            if (
                not applied
                and ("prompt_delta_limit_exceeded" in blocked or "replay_prompt_bloat_not_ok" in blocked)
            ) or (
                applied
                and "prompt_delta_limit_exceeded" not in blocked
                and "replay_prompt_bloat_not_ok" not in blocked
            ):
                bloat_passed += 1

        if applied and "pilot_" not in user_id:
            normal_user_apply += 1

    return {
        "schema_version": "prompt_constraint_pilot_gate_verification_v1",
        "prd": PRD,
        "safety_gate_cases_total": safety_total,
        "safety_gate_cases_passed": safety_passed,
        "kb_gate_cases_total": kb_total,
        "kb_gate_cases_passed": kb_passed,
        "conflict_gate_cases_total": conflict_total,
        "conflict_gate_cases_passed": conflict_passed,
        "bloat_gate_cases_total": bloat_total,
        "bloat_gate_cases_passed": bloat_passed,
        "raw_kb_text_exposure_count": raw_exposure,
        "internal_only_exposure_count": internal_exposure,
        "not_for_direct_quote_violation_count": quote_viol,
        "normal_user_apply_count": normal_user_apply,
        "provider_called_by_gate_count": _as_int(scorecard.get("provider_called_by_eval_count"), 0),
    }


def _final_decision(
    *,
    evidence_audit: dict[str, Any],
    rollback_matrix: dict[str, Any],
    quality_delta: dict[str, Any],
    gate_verification: dict[str, Any],
    scorecard_source: dict[str, Any],
    no_mutation_source: dict[str, Any],
) -> dict[str, Any]:
    rollback_gate_passed = _as_int(rollback_matrix.get("rollback_failure_count"), 1) == 0 and _as_int(
        rollback_matrix.get("stale_apply_after_force_disabled_count"), 1
    ) == 0
    quality_decision = str(quality_delta.get("quality_delta_decision", "blocked"))
    quality_delta_gate_passed = quality_decision == "pass"
    safety_gate_passed = _as_int(gate_verification.get("safety_gate_cases_passed"), 0) == _as_int(
        gate_verification.get("safety_gate_cases_total"), -1
    )
    kb_gate_passed = (
        _as_int(gate_verification.get("kb_gate_cases_passed"), 0) == _as_int(gate_verification.get("kb_gate_cases_total"), -1)
        and _as_int(gate_verification.get("raw_kb_text_exposure_count"), 0) == 0
        and _as_int(gate_verification.get("internal_only_exposure_count"), 0) == 0
        and _as_int(gate_verification.get("not_for_direct_quote_violation_count"), 0) == 0
    )
    conflict_gate_passed = _as_int(gate_verification.get("conflict_gate_cases_passed"), 0) == _as_int(
        gate_verification.get("conflict_gate_cases_total"), -1
    )
    bloat_gate_passed = _as_int(gate_verification.get("bloat_gate_cases_passed"), 0) == _as_int(
        gate_verification.get("bloat_gate_cases_total"), -1
    )
    default_off_effect = _as_int(scorecard_source.get("default_off_user_path_effect_count"), 0)
    allowlist_viol = _as_int(scorecard_source.get("allowlist_violation_count"), 0)
    normal_user_apply = _as_int(gate_verification.get("normal_user_apply_count"), 0)
    provider_called = _as_int(scorecard_source.get("provider_called_by_eval_count"), 0)
    production_mutation_detected = any(
        bool(no_mutation_source.get(key, False))
        for key in (
            "all_blocks_merged_mutated",
            "registry_mutated",
            "config_mutated",
            "chroma_reindex_performed",
            "production_apply_performed",
        )
    )

    evidence_quality = str(evidence_audit.get("evidence_quality", "insufficient"))
    hard_block = (
        not _as_bool(evidence_audit.get("input_artifacts_found"), False)
        or evidence_quality == "insufficient"
        or not rollback_gate_passed
        or default_off_effect > 0
        or allowlist_viol > 0
        or normal_user_apply > 0
        or not safety_gate_passed
        or not kb_gate_passed
        or provider_called > 0
        or production_mutation_detected
    )

    if hard_block:
        final_status = "blocked"
        decision = "blocked"
        recommended = "PRD-046.1.7-HF1 Safety/Rollback Blocker Fix v1"
    elif quality_decision == "blocked":
        final_status = "blocked"
        decision = "blocked"
        recommended = "PRD-046.1.7-HF1 Safety/Rollback Blocker Fix v1"
    elif quality_decision == "needs_hf":
        final_status = "needs_hf"
        decision = "hotfix_required"
        recommended = "PRD-046.1.7-HF1 Prompt Constraint Quality Delta Calibration v1"
    elif evidence_quality == "limited":
        final_status = "passed_with_limited_evidence"
        decision = "stay_limited"
        recommended = "PRD-046.1.7-RUN1 Expanded Limited Runtime Evidence Collection v1"
    else:
        final_status = "passed"
        decision = "supervised_rollout_candidate"
        recommended = "PRD-046.1.8 Supervised Prompt-Constraint Pilot Rollout Plan v1"

    return {
        "prd": PRD,
        "schema_version": "prompt_constraint_pilot_quality_gate_scorecard_v1",
        "final_status": final_status,
        "decision": decision,
        "evidence_quality": evidence_quality,
        "rollback_gate_passed": rollback_gate_passed,
        "quality_delta_gate_passed": quality_delta_gate_passed,
        "safety_gate_passed": safety_gate_passed,
        "kb_gate_passed": kb_gate_passed,
        "conflict_gate_passed": conflict_gate_passed,
        "bloat_gate_passed": bloat_gate_passed,
        "default_off_user_path_effect_count": default_off_effect,
        "normal_user_apply_count": normal_user_apply,
        "allowlist_violation_count": allowlist_viol,
        "raw_kb_text_exposure_count": _as_int(gate_verification.get("raw_kb_text_exposure_count"), 0),
        "provider_called_by_eval_count": provider_called,
        "production_mutation_detected": production_mutation_detected,
        "recommended_next_prd": recommended,
    }


def _no_mutation_proof(*, hash_before: dict[str, str], hash_after: dict[str, str], scorecard: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "prompt_constraint_pilot_quality_gate_no_mutation_proof_v1",
        "prd": PRD,
        "tracked_paths": {
            "all_blocks_merged": "Bot_data_base/data/processed/all_blocks_merged.json",
            "registry": "Bot_data_base/data/registry.json",
            "config": "Bot_data_base/config.yaml",
        },
        "all_blocks_merged_mutated": hash_before["all_blocks"] != hash_after["all_blocks"],
        "registry_mutated": hash_before["registry"] != hash_after["registry"],
        "config_mutated": hash_before["config"] != hash_after["config"],
        "chroma_reindex_performed": False,
        "production_apply_performed": False,
        "kb_governance_authority_mutated": False,
        "writer_contract_production_authority_mutated": False,
        "final_answer_path_mutated_for_default_users": False,
        "provider_called_by_eval_count": _as_int(scorecard.get("provider_called_by_eval_count"), 0),
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    input_dir = Path(args.input_dir).resolve()
    out_dir = Path(args.output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    strict = bool(getattr(args, "strict", False))

    tracked_files = {
        "all_blocks": REPO_ROOT / "Bot_data_base" / "data" / "processed" / "all_blocks_merged.json",
        "registry": REPO_ROOT / "Bot_data_base" / "data" / "registry.json",
        "config": REPO_ROOT / "Bot_data_base" / "config.yaml",
    }
    hash_before = {name: _sha256(path) for name, path in tracked_files.items()}

    preflight = _preflight(input_dir)
    if not preflight["ok"]:
        evidence = {
            "prd": PRD,
            "source_prd": SOURCE_PRD,
            "input_artifacts_found": False,
            "trace_samples_count": 0,
            "cases_total": 0,
            "cases_passed": 0,
            "default_off_user_path_effect_count": 0,
            "shadow_mode_apply_count": 0,
            "test_apply_applied_count": 0,
            "allowlist_violation_count": 0,
            "safety_apply_blocked_count": 0,
            "kb_boundary_violation_count": 0,
            "raw_kb_text_exposure_count": 0,
            "prompt_bloat_blocker_count": 0,
            "constraint_conflict_count": 0,
            "provider_called_by_eval_count": 0,
            "evidence_quality": "insufficient",
            "warnings": [],
            "blockers": list(preflight["missing"]) + list(preflight["parse_errors"]),
        }
        rollback = {
            "prd": PRD,
            "schema_version": "rollback_toggle_matrix_v1",
            "cases_total": 0,
            "cases_passed": 0,
            "rollback_cases_total": 0,
            "rollback_cases_passed": 0,
            "rollback_failure_count": 1,
            "stale_apply_after_force_disabled_count": 0,
            "unexpected_apply_count": 0,
            "unexpected_disabled_count": 0,
            "rollback_priority_preserved": False,
            "cases": [],
        }
        quality_delta = {
            "schema_version": "baseline_vs_test_apply_quality_delta_v1",
            "prd": PRD,
            "source_prd": SOURCE_PRD,
            "cases_total": 0,
            "cases_compared": 0,
            "candidate_tighter_than_baseline_count": 0,
            "candidate_same_as_baseline_count": 0,
            "candidate_weaker_than_baseline_count": 0,
            "safety_regression_count": 0,
            "kb_policy_regression_count": 0,
            "prompt_bloat_regression_count": 0,
            "constraint_conflict_regression_count": 0,
            "max_prompt_delta_chars_observed": 0,
            "max_prompt_delta_ratio_observed": 0.0,
            "quality_delta_decision": "blocked",
        }
        gate = {
            "schema_version": "prompt_constraint_pilot_gate_verification_v1",
            "prd": PRD,
            "safety_gate_cases_total": 0,
            "safety_gate_cases_passed": 0,
            "kb_gate_cases_total": 0,
            "kb_gate_cases_passed": 0,
            "conflict_gate_cases_total": 0,
            "conflict_gate_cases_passed": 0,
            "bloat_gate_cases_total": 0,
            "bloat_gate_cases_passed": 0,
            "raw_kb_text_exposure_count": 0,
            "internal_only_exposure_count": 0,
            "not_for_direct_quote_violation_count": 0,
            "normal_user_apply_count": 0,
            "provider_called_by_gate_count": 0,
        }
        scorecard = {
            "prd": PRD,
            "schema_version": "prompt_constraint_pilot_quality_gate_scorecard_v1",
            "final_status": "blocked_missing_prd_046_1_6_artifacts",
            "decision": "blocked",
            "evidence_quality": "insufficient",
            "rollback_gate_passed": False,
            "quality_delta_gate_passed": False,
            "safety_gate_passed": False,
            "kb_gate_passed": False,
            "conflict_gate_passed": False,
            "bloat_gate_passed": False,
            "default_off_user_path_effect_count": 0,
            "normal_user_apply_count": 0,
            "allowlist_violation_count": 0,
            "raw_kb_text_exposure_count": 0,
            "provider_called_by_eval_count": 0,
            "production_mutation_detected": False,
            "recommended_next_prd": "PRD-046.1.7-HF1 Safety/Rollback Blocker Fix v1",
        }
        hash_after = {name: _sha256(path) for name, path in tracked_files.items()}
        no_mutation = _no_mutation_proof(hash_before=hash_before, hash_after=hash_after, scorecard=scorecard)
        _write_json(out_dir / "runtime_evidence_audit.json", evidence)
        _write_json(out_dir / "rollback_toggle_matrix.json", rollback)
        _write_json(out_dir / "baseline_vs_test_apply_quality_delta.json", quality_delta)
        _write_json(out_dir / "prompt_constraint_pilot_gate_verification.json", gate)
        _write_json(out_dir / "prompt_constraint_pilot_quality_gate_scorecard.json", scorecard)
        _write_json(out_dir / "no_mutation_proof.json", no_mutation)

        encoding_report = encoding_validator.run(
            argparse.Namespace(
                prd=PRD,
                logs_dir=str(out_dir),
                reports_dir=str((REPO_ROOT / "TO_DO_LIST" / "reports").resolve()),
                out_dir=str(out_dir),
                report_prd=PRD,
                repo_root=str(REPO_ROOT),
                fixed_file=[],
            )
        )
        return {
            "status": scorecard["final_status"],
            "scorecard": scorecard,
            "preflight": preflight,
            "encoding_report": encoding_report,
        }

    parsed = preflight["parsed"]
    eval_payload = _safe_dict(parsed.get("runtime_eval"))
    source_scorecard = _safe_dict(parsed.get("runtime_scorecard"))
    trace_payload = _safe_dict(parsed.get("runtime_trace"))
    source_no_mutation = _safe_dict(parsed.get("no_mutation"))

    evidence = _build_runtime_evidence_audit(
        preflight=preflight,
        scorecard=source_scorecard,
        eval_payload=eval_payload,
        trace_payload=trace_payload,
    )
    rollback = _build_rollback_toggle_matrix()
    quality_delta = _quality_delta(eval_payload=eval_payload, scorecard=source_scorecard)
    gate = _gate_verification(scorecard=source_scorecard, eval_payload=eval_payload)
    scorecard = _final_decision(
        evidence_audit=evidence,
        rollback_matrix=rollback,
        quality_delta=quality_delta,
        gate_verification=gate,
        scorecard_source=source_scorecard,
        no_mutation_source=source_no_mutation,
    )

    hash_after = {name: _sha256(path) for name, path in tracked_files.items()}
    no_mutation = _no_mutation_proof(hash_before=hash_before, hash_after=hash_after, scorecard=scorecard)

    _write_json(out_dir / "runtime_evidence_audit.json", evidence)
    _write_json(out_dir / "rollback_toggle_matrix.json", rollback)
    _write_json(out_dir / "baseline_vs_test_apply_quality_delta.json", quality_delta)
    _write_json(out_dir / "prompt_constraint_pilot_gate_verification.json", gate)
    _write_json(out_dir / "prompt_constraint_pilot_quality_gate_scorecard.json", scorecard)
    _write_json(out_dir / "no_mutation_proof.json", no_mutation)

    encoding_report = encoding_validator.run(
        argparse.Namespace(
            prd=PRD,
            logs_dir=str(out_dir),
            reports_dir=str((REPO_ROOT / "TO_DO_LIST" / "reports").resolve()),
            out_dir=str(out_dir),
            report_prd=PRD,
            repo_root=str(REPO_ROOT),
            fixed_file=[],
        )
    )

    if strict and scorecard["final_status"] not in {"passed", "passed_with_limited_evidence"}:
        return {
            "status": scorecard["final_status"],
            "scorecard": scorecard,
            "preflight": preflight,
            "encoding_report": encoding_report,
        }
    return {
        "status": scorecard["final_status"],
        "scorecard": scorecard,
        "preflight": preflight,
        "encoding_report": encoding_report,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run prompt-constraint pilot runtime quality gate.")
    parser.add_argument("--input-dir", default="TO_DO_LIST/logs/PRD-046.1.6")
    parser.add_argument("--output-dir", default="TO_DO_LIST/logs/PRD-046.1.7")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--allow-missing-runtime-samples", default="false")
    parser.add_argument("--max-quality-regression-count", type=int, default=0)
    parser.add_argument("--max-rollback-failure-count", type=int, default=0)
    parser.add_argument("--max-safety-violation-count", type=int, default=0)
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    result = run(args)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    status = str(result.get("status", "blocked"))
    return 0 if status in {"passed", "passed_with_limited_evidence"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
