"""Offline writer prompt replay builder (quality eval, non-mutating)."""

from __future__ import annotations

import copy
import hashlib
import json
from typing import Any

from .contracts.diagnostic_card import DiagnosticCard
from .contracts.planner_bridge_writer_contract_pilot_v1 import PlannerBridgeWriterContractPilotResult
from .contracts.state_snapshot import StateSnapshot
from .contracts.thread_state import ThreadState
from .contracts.writer_contract import WriterContract
from .contracts.writer_prompt_replay_v1 import (
    WriterPromptReplayCandidateContext,
    WriterPromptReplayComparison,
    WriterPromptReplayInput,
    WriterPromptReplayQuality,
    WriterPromptReplayResult,
    WriterPromptReplayTrace,
    normalize_kb_usage_mode,
)


_DEPTH_ORDER = {"none": 0, "low": 1, "low_to_medium": 2, "medium": 3, "high": 4}
_FORBIDDEN_KB_FIELDS = {"raw_text", "full_text", "content_full", "page_content", "source_text"}


def _safe_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _safe_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


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


def _stable_payload(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): _stable_payload(val)
            for key, val in sorted(value.items(), key=lambda kv: str(kv[0]))
        }
    if isinstance(value, list):
        return [_stable_payload(item) for item in value]
    if isinstance(value, tuple):
        return [_stable_payload(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:  # noqa: BLE001
            return str(value)
    return str(value)


def _stable_json(value: Any) -> str:
    return json.dumps(_stable_payload(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _hash_dict(value: dict[str, Any]) -> str:
    return hashlib.sha256(_stable_json(value).encode("utf-8")).hexdigest()


def _hash_writer_contract(writer_contract: WriterContract) -> str:
    return _hash_dict(writer_contract.to_dict())


def _extract_forbidden_keys(payload: Any, prefix: str = "") -> list[str]:
    hits: list[str] = []
    if isinstance(payload, dict):
        for key, val in payload.items():
            key_str = str(key)
            path = f"{prefix}.{key_str}" if prefix else key_str
            if key_str in _FORBIDDEN_KB_FIELDS:
                hits.append(path)
            hits.extend(_extract_forbidden_keys(val, path))
    elif isinstance(payload, list):
        for idx, item in enumerate(payload):
            path = f"{prefix}[{idx}]" if prefix else f"[{idx}]"
            hits.extend(_extract_forbidden_keys(item, path))
    return hits


def _top_level_diff_counts(
    baseline: dict[str, Any],
    candidate: dict[str, Any],
) -> tuple[int, int, int]:
    baseline_keys = set(baseline.keys())
    candidate_keys = set(candidate.keys())
    added = len(candidate_keys - baseline_keys)
    removed = len(baseline_keys - candidate_keys)
    changed = 0
    for key in sorted(baseline_keys.intersection(candidate_keys)):
        if _stable_json(baseline.get(key)) != _stable_json(candidate.get(key)):
            changed += 1
    return added, removed, changed


def _summary(payload: dict[str, Any]) -> dict[str, Any]:
    writer_move = _safe_dict(payload.get("writer_move_instructions"))
    pilot_constraints = _safe_dict(payload.get("pilot_writer_constraints"))
    must_do = _safe_list(pilot_constraints.get("must_do"))
    must_not_do = _safe_list(pilot_constraints.get("must_not_do"))
    return {
        "top_level_keys": sorted(list(payload.keys())),
        "top_level_key_count": len(payload.keys()),
        "writer_move_max_questions": int(writer_move.get("max_questions", 0) or 0),
        "writer_move_max_sentences": int(writer_move.get("max_sentences", 0) or 0),
        "pilot_constraints_present": bool(pilot_constraints),
        "pilot_must_do_count": len(must_do),
        "pilot_must_not_do_count": len(must_not_do),
        "has_forbidden_kb_fields": len(_extract_forbidden_keys(payload)) > 0,
    }


def _sanitize_constraint_list(value: Any, limit: int) -> list[str]:
    return _dedupe(_safe_list(value))[:limit]


def _build_candidate_constraints(pilot_overlay: dict[str, Any]) -> dict[str, Any]:
    candidate_constraints = _safe_dict(pilot_overlay.get("candidate_constraints"))
    depth_limit = str(candidate_constraints.get("depth_limit", "low_to_medium") or "low_to_medium")
    if depth_limit not in _DEPTH_ORDER:
        depth_limit = "low_to_medium"

    return {
        "source": "planner_bridge_writer_contract_pilot",
        "activation_mode": "offline_replay_only",
        "response_goal": str(candidate_constraints.get("response_goal", "") or ""),
        "response_mode": str(candidate_constraints.get("response_mode", "reflect") or "reflect"),
        "depth_limit": depth_limit,
        "max_questions": max(0, int(candidate_constraints.get("max_questions", 0) or 0)),
        "max_concepts": max(1, int(candidate_constraints.get("max_concepts", 1) or 1)),
        "must_do": _sanitize_constraint_list(candidate_constraints.get("must_do"), limit=8),
        "must_not_do": _sanitize_constraint_list(candidate_constraints.get("must_not_do"), limit=12),
        "kb_usage_mode": normalize_kb_usage_mode(str(candidate_constraints.get("kb_usage_mode", "none") or "none")),
        "must_not_quote_source": True,
    }


def _build_quality(
    *,
    writer_move: dict[str, Any],
    constraints: dict[str, Any],
    comparison: WriterPromptReplayComparison,
    non_mutating_ok: bool,
    safety_context: bool,
    pilot_activation_readiness: str,
) -> tuple[WriterPromptReplayQuality, list[str], list[str]]:
    blocked_reasons: list[str] = []
    warnings: list[str] = []

    baseline_max_questions = max(0, int(writer_move.get("max_questions", 0) or 0))
    candidate_max_questions = max(0, int(constraints.get("max_questions", 0) or 0))

    safety_ok = True
    if safety_context:
        candidate_depth = str(constraints.get("depth_limit", "low"))
        safety_ok = (
            _DEPTH_ORDER.get(candidate_depth, 2) <= _DEPTH_ORDER["low"]
            and candidate_max_questions <= 0
            and int(constraints.get("max_concepts", 1) or 1) <= 1
        )
        if not safety_ok:
            blocked_reasons.append("safety_depth_or_question_violation")

    kb_boundary_ok = (
        len(comparison.forbidden_field_hits) == 0
        and str(constraints.get("kb_usage_mode", "none")) in {"none", "internal_lens_only", "practice_candidate_only"}
        and bool(constraints.get("must_not_quote_source", True))
    )
    if not kb_boundary_ok:
        blocked_reasons.append("kb_boundary_violation")

    must_do = set(_safe_list(constraints.get("must_do")))
    must_not_do = set(_safe_list(constraints.get("must_not_do")))
    conflict_rules = sorted(list(must_do.intersection(must_not_do)))
    constraint_conflict_ok = len(conflict_rules) == 0 and len(comparison.conflict_rules) == 0
    if not constraint_conflict_ok:
        blocked_reasons.append("constraint_conflict")

    if candidate_max_questions > baseline_max_questions:
        warnings.append("candidate_questions_increased_vs_baseline")

    delta_chars = comparison.size_delta_chars
    delta_ratio = comparison.size_delta_ratio
    prompt_bloat_ok = delta_chars <= 2500 and delta_ratio <= 0.35
    if not prompt_bloat_ok:
        if delta_chars > 5000 or delta_ratio > 0.75:
            blocked_reasons.append("prompt_bloat_blocker")
        else:
            warnings.append("prompt_bloat_warning")

    candidate_improves_constraints = (
        candidate_max_questions < baseline_max_questions
        or _DEPTH_ORDER.get(str(constraints.get("depth_limit", "low_to_medium")), 2)
        <= _DEPTH_ORDER.get("low_to_medium", 2)
        or len(_safe_list(constraints.get("must_not_do"))) > len(_safe_list(writer_move.get("must_not_do")))
    )

    if pilot_activation_readiness == "blocked":
        warnings.append("pilot_activation_readiness_blocked")
    elif pilot_activation_readiness == "not_ready":
        warnings.append("pilot_activation_readiness_not_ready")

    if not non_mutating_ok:
        blocked_reasons.append("non_mutating_violation")

    quality_status = "passed"
    if blocked_reasons:
        quality_status = "blocked"
    elif warnings:
        quality_status = "needs_review"

    quality = WriterPromptReplayQuality(
        schema_version="writer_prompt_replay_quality_v1",
        safety_ok=safety_ok,
        kb_boundary_ok=kb_boundary_ok,
        constraint_conflict_ok=constraint_conflict_ok,
        prompt_bloat_ok=prompt_bloat_ok,
        non_mutating_ok=non_mutating_ok,
        candidate_improves_constraints=candidate_improves_constraints,
        quality_status=quality_status,
    )
    return quality, _dedupe(blocked_reasons), _dedupe(warnings)


def build_writer_prompt_replay_v1(
    *,
    writer_contract: WriterContract,
    writer_contract_pilot: dict[str, Any] | PlannerBridgeWriterContractPilotResult,
    diagnostic_card: DiagnosticCard,
    thread_state: ThreadState,
    state_snapshot: StateSnapshot,
) -> WriterPromptReplayResult:
    pilot_payload = (
        writer_contract_pilot.to_dict()
        if isinstance(writer_contract_pilot, PlannerBridgeWriterContractPilotResult)
        else _safe_dict(writer_contract_pilot)
    )

    baseline = writer_contract.to_prompt_context()
    baseline_copy = copy.deepcopy(baseline)

    _ = WriterPromptReplayInput(
        baseline_prompt_context=baseline,
        writer_contract_pilot=pilot_payload,
        diagnostic_card=diagnostic_card.to_dict(),
        thread_state=thread_state.to_dict(),
        state_snapshot=state_snapshot.to_dict(),
    )

    writer_contract_hash_before = _hash_writer_contract(writer_contract)
    baseline_hash_before = _hash_dict(baseline)

    pilot_overlay = _safe_dict(pilot_payload.get("overlay"))
    candidate_constraints = _build_candidate_constraints(pilot_overlay)

    candidate = copy.deepcopy(baseline)
    candidate["pilot_writer_constraints"] = candidate_constraints

    candidate_contract = WriterPromptReplayCandidateContext(
        schema_version="writer_prompt_replay_candidate_context_v1",
        activation_mode="offline_replay_only",
        payload=candidate,
    )

    writer_contract_hash_after = _hash_writer_contract(writer_contract)
    baseline_hash_after = _hash_dict(baseline)

    forbidden_field_hits = _extract_forbidden_keys(candidate_contract.payload)
    top_added, top_removed, top_changed = _top_level_diff_counts(baseline_copy, candidate_contract.payload)

    baseline_text = _stable_json(baseline_copy)
    candidate_text = _stable_json(candidate_contract.payload)
    baseline_chars = len(baseline_text)
    candidate_chars = len(candidate_text)
    delta_chars = max(0, candidate_chars - baseline_chars)
    delta_ratio = (delta_chars / baseline_chars) if baseline_chars > 0 else 0.0

    conflict_rules = []
    must_do = set(_safe_list(candidate_constraints.get("must_do")))
    must_not_do = set(_safe_list(candidate_constraints.get("must_not_do")))
    if must_do.intersection(must_not_do):
        conflict_rules = sorted(list(must_do.intersection(must_not_do)))

    comparison = WriterPromptReplayComparison(
        schema_version="writer_prompt_replay_comparison_v1",
        added_fields_count=top_added,
        removed_fields_count=top_removed,
        changed_fields_count=top_changed,
        baseline_serialized_chars=baseline_chars,
        candidate_serialized_chars=candidate_chars,
        size_delta_chars=delta_chars,
        size_delta_ratio=delta_ratio,
        forbidden_field_hits=forbidden_field_hits,
        conflict_rules=conflict_rules,
    )

    safety_context = bool(
        state_snapshot.safety_flag
        or thread_state.safety_active
        or state_snapshot.nervous_state in {"hyper", "hypo"}
    )
    writer_move = _safe_dict(baseline_copy.get("writer_move_instructions"))
    activation_readiness = str(
        _safe_dict(pilot_overlay.get("risk_assessment")).get("activation_readiness", "pilot_ready")
    )

    non_mutating_ok = (
        writer_contract_hash_before == writer_contract_hash_after
        and baseline_hash_before == baseline_hash_after
        and _stable_json(baseline_copy) == _stable_json(baseline)
    )

    quality, blocked_reasons, warnings = _build_quality(
        writer_move=writer_move,
        constraints=candidate_constraints,
        comparison=comparison,
        non_mutating_ok=non_mutating_ok,
        safety_context=safety_context,
        pilot_activation_readiness=activation_readiness,
    )

    trace_rules = [
        "offline_replay_only_guardrail",
        "non_mutating_hash_proof",
        "pilot_constraints_namespace_injection",
        "quality_rules_v1",
    ]
    if safety_context:
        trace_rules.append("safety_context_checked")

    result = WriterPromptReplayResult(
        schema_version="writer_prompt_replay_result_v1",
        activation_mode="offline_replay_only",
        baseline_prompt_context_hash=_hash_dict(baseline_copy),
        candidate_prompt_context_hash=_hash_dict(candidate_contract.payload),
        baseline_summary=_summary(baseline_copy),
        candidate_summary=_summary(candidate_contract.payload),
        comparison=comparison,
        quality=quality,
        apply_to_writer_contract=False,
        apply_to_writer_prompt=False,
        apply_to_final_answer=False,
        provider_called=False,
        blocked_reasons=blocked_reasons,
        warnings=warnings,
        trace=WriterPromptReplayTrace(
            schema_version="writer_prompt_replay_trace_v1",
            builder="writer_prompt_replay_v1",
            rules_applied=trace_rules,
            warnings=warnings,
        ),
    )
    return result


def build_writer_prompt_replay_runtime_shadow_v1(
    *,
    writer_contract: WriterContract,
    writer_contract_pilot: dict[str, Any] | PlannerBridgeWriterContractPilotResult,
    diagnostic_card: DiagnosticCard,
    thread_state: ThreadState,
    state_snapshot: StateSnapshot,
) -> dict[str, Any]:
    """Build replay payload for runtime debug only; never mutates writer path."""
    try:
        return build_writer_prompt_replay_v1(
            writer_contract=writer_contract,
            writer_contract_pilot=writer_contract_pilot,
            diagnostic_card=diagnostic_card,
            thread_state=thread_state,
            state_snapshot=state_snapshot,
        ).to_dict()
    except Exception as exc:  # noqa: BLE001
        return {
            "schema_version": "writer_prompt_replay_result_v1",
            "activation_mode": "offline_replay_only",
            "baseline_prompt_context_hash": "",
            "candidate_prompt_context_hash": "",
            "baseline_summary": {},
            "candidate_summary": {},
            "comparison": {
                "schema_version": "writer_prompt_replay_comparison_v1",
                "added_fields_count": 0,
                "removed_fields_count": 0,
                "changed_fields_count": 0,
                "baseline_serialized_chars": 0,
                "candidate_serialized_chars": 0,
                "size_delta_chars": 0,
                "size_delta_ratio": 0.0,
                "forbidden_field_hits": [],
                "conflict_rules": [],
            },
            "quality": {
                "schema_version": "writer_prompt_replay_quality_v1",
                "safety_ok": False,
                "kb_boundary_ok": False,
                "constraint_conflict_ok": False,
                "prompt_bloat_ok": False,
                "non_mutating_ok": False,
                "candidate_improves_constraints": False,
                "quality_status": "blocked",
            },
            "apply_to_writer_contract": False,
            "apply_to_writer_prompt": False,
            "apply_to_final_answer": False,
            "provider_called": False,
            "blocked_reasons": [f"writer_prompt_replay_failed:{exc.__class__.__name__}"],
            "warnings": [],
            "trace": {
                "schema_version": "writer_prompt_replay_trace_v1",
                "builder": "writer_prompt_replay_v1",
                "rules_applied": ["offline_replay_only_guardrail", "runtime_exception_fallback"],
                "warnings": [],
            },
        }
