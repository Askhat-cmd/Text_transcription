"""Diagnostic Center v1 runtime shadow adapter (trace-only, non-blocking)."""

from __future__ import annotations

import time
from typing import Any

from .contracts.context_package import ContextAssemblyPackage
from .contracts.diagnostic_card import DiagnosticCard
from .contracts.diagnostic_center_v1 import DiagnosticCenterInput, DiagnosticCenterOutput
from .contracts.memory_bundle import MemoryBundle
from .contracts.state_snapshot import StateSnapshot
from .contracts.thread_state import ThreadState
from .diagnostic_center_v1_builder import build_diagnostic_center_output_v1


FORBIDDEN_KB_FIELDS = {
    "content_full",
    "raw_text",
    "full_text",
    "text",
    "source_text",
    "page_content",
}

_DC_INTENTS = {
    "contact",
    "vent",
    "clarify",
    "validation",
    "directive",
    "explore",
    "practical_step",
    "crisis",
    "unknown",
}
_DC_OPENNESS = {"open", "mixed", "defensive", "collapsed", "unknown"}
_DC_OK_POSITION = {"I+W+", "I-W+", "I+W-", "I-W-", "unknown"}
_DC_RELATION = {"continue", "branch", "new_thread", "return_to_old", "unknown"}
_DC_PHASE = {"stabilize", "clarify", "explore", "integrate", "unknown"}


def _safe_text(value: Any, *, limit: int = 220) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _safe_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _safe_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _norm_enum(value: str, allowed: set[str]) -> str:
    text = str(value or "").strip()
    return text if text in allowed else "unknown"


def _map_intent(state_snapshot: StateSnapshot, thread_state: ThreadState) -> str:
    state_intent = str(getattr(state_snapshot, "intent", "") or "").strip()
    thread_goal = str(getattr(thread_state, "response_goal", "") or "").strip().lower()
    if state_intent == "solution":
        return "practical_step"
    if state_intent in _DC_INTENTS:
        return state_intent
    if "криз" in thread_goal or "safety" in thread_goal:
        return "crisis"
    return "unknown"


def _safe_float(value: Any, *, fallback: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _sanitize_knowledge_hits(
    *,
    context_package: ContextAssemblyPackage,
    memory_bundle: MemoryBundle,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    source_hits: list[dict[str, Any]] = []
    source_hits.extend(
        [dict(item) for item in context_package.knowledge_rag_hits if isinstance(item, dict)]
    )
    source_hits.extend(
        [dict(item) for item in memory_bundle.knowledge_rag_hits if isinstance(item, dict)]
    )
    stripped_fields = 0
    sanitized_hits: list[dict[str, Any]] = []
    for item in source_hits:
        for key in list(item.keys()):
            if key in FORBIDDEN_KB_FIELDS:
                stripped_fields += 1
                item.pop(key, None)

        governance = _safe_dict(item.get("governance_summary"))
        lens_family = _safe_text(item.get("lens_family")) or _safe_text(governance.get("lens_family")) or "unknown"
        score = _safe_float(item.get("score"), fallback=0.0)
        allowed_use = _safe_list(item.get("allowed_use")) or _safe_list(governance.get("allowed_use"))
        safety_flags = _safe_list(item.get("safety_flags")) or _safe_list(governance.get("safety_flags"))
        safe_summary = _safe_text(item.get("content") or item.get("summary") or item.get("safe_preview"))
        sanitized_hits.append(
            {
                "lens_family": lens_family,
                "score": max(0.0, min(1.0, score)),
                "source_id": _safe_text(item.get("source_id") or item.get("source")),
                "block_id": _safe_text(item.get("block_id") or item.get("chunk_id")),
                "allowed_use": allowed_use,
                "safety_flags": safety_flags,
                "summary": safe_summary,
            }
        )
    return sanitized_hits[:8], {
        "source_hits_count": len(source_hits),
        "sanitized_hits_count": len(sanitized_hits[:8]),
        "forbidden_fields_stripped": stripped_fields,
        "raw_kb_text_exposed": False,
    }


def build_diagnostic_center_shadow_divergence_v1(
    *,
    diagnostic_card: DiagnosticCard,
    diagnostic_center_output: DiagnosticCenterOutput,
    thread_state: ThreadState,
    state_snapshot: StateSnapshot,
    kb_sanitization: dict[str, Any] | None = None,
) -> dict[str, Any]:
    expected_safety = bool(state_snapshot.safety_flag or thread_state.safety_active) or (
        state_snapshot.nervous_state in {"hyper", "hypo"}
    )
    depth_allowed = diagnostic_center_output.next_micro_shift.depth_allowed
    safety_priority_match = (
        diagnostic_center_output.status == "safety_first"
        if expected_safety
        else diagnostic_center_output.status in {"ok", "safety_first"}
    )
    depth_compatible = True
    if expected_safety:
        depth_compatible = depth_allowed in {"none", "low"}

    move = diagnostic_card.suggested_writer_move
    goal = diagnostic_center_output.next_micro_shift.response_goal
    writer_move_compatible = True
    if move in {"safe_override", "regulate_first"}:
        writer_move_compatible = goal in {"safety_redirect", "ground_and_reduce_load"}
    elif move == "offer_one_micro_step":
        writer_move_compatible = goal in {"clarify_before_action", "clarify"}
    elif move in {"clarify_one_point", "reflect_pattern_once"}:
        writer_move_compatible = goal in {
            "stabilize_authorship",
            "clarify",
            "deepen_and_integrate",
            "decenter_without_shaming",
        }

    response_mode_compatible = True
    if thread_state.response_mode == "safe_override":
        response_mode_compatible = diagnostic_center_output.next_micro_shift.response_mode in {
            "ground_then_one_step",
            "minimal_support",
        }
    relation_to_thread_match = diagnostic_center_output.relation_to_thread == thread_state.relation_to_thread
    phase_match = diagnostic_center_output.phase == thread_state.phase
    pattern_core_present = bool(str(thread_state.pattern_core or "").strip())
    kb_usage_mode = diagnostic_center_output.trace.kb_usage_mode
    must_not_quote_source = bool(diagnostic_center_output.trace.must_not_quote_source)
    raw_kb_text_exposed = bool(_safe_dict(kb_sanitization).get("raw_kb_text_exposed", False))
    kb_boundary_ok = kb_usage_mode in {"internal_lens_only", "disabled"} and must_not_quote_source and not raw_kb_text_exposed
    thread_risk = "none"

    warnings: list[str] = []
    if not writer_move_compatible:
        warnings.append("writer_move_compatible_false")
    if not response_mode_compatible:
        warnings.append("response_mode_compatible_false")
    if not phase_match:
        warnings.append("phase_match_false")
    if not pattern_core_present:
        warnings.append("pattern_core_missing")

    return {
        "safety_priority_match": bool(safety_priority_match),
        "depth_compatible": bool(depth_compatible),
        "writer_move_compatible": bool(writer_move_compatible),
        "response_mode_compatible": bool(response_mode_compatible),
        "relation_to_thread_match": bool(relation_to_thread_match),
        "phase_match": bool(phase_match),
        "pattern_core_present": bool(pattern_core_present),
        "kb_boundary_ok": bool(kb_boundary_ok),
        "raw_kb_text_exposed": bool(raw_kb_text_exposed),
        "thread_risk": thread_risk,
        "warnings": warnings,
        "diagnostic_card_alignment": {
            "safety_priority_match": bool(safety_priority_match),
            "low_resource_depth_match": bool(depth_compatible),
            "writer_move_compatible": bool(writer_move_compatible),
            "response_mode_compatible": bool(response_mode_compatible),
        },
        "thread_alignment": {
            "relation_to_thread_match": bool(relation_to_thread_match),
            "phase_match": bool(phase_match),
            "pattern_core_present": bool(pattern_core_present),
            "continuity_risk": thread_risk,
        },
        "kb_boundary": {
            "kb_usage_mode": kb_usage_mode,
            "must_not_quote_source": must_not_quote_source,
            "raw_kb_text_exposed": bool(raw_kb_text_exposed),
        },
        "user_path": {
            "writer_contract_changed": False,
            "writer_prompt_changed_by_shadow": False,
            "final_answer_changed_by_shadow": False,
            "diagnostic_center_output_passed_to_writer": False,
        },
    }


def build_diagnostic_center_shadow_v1(
    *,
    user_message: str,
    state_snapshot: StateSnapshot,
    thread_state: ThreadState,
    context_package: ContextAssemblyPackage,
    memory_bundle: MemoryBundle,
    diagnostic_card: DiagnosticCard,
    thread_debug: dict[str, Any] | None = None,
    enabled: bool = True,
) -> dict[str, Any]:
    if not enabled:
        return {
            "enabled": False,
            "status": "disabled",
            "runtime_mode": "shadow_only",
            "user_path_effect": "none",
        }

    started_at = time.perf_counter()
    try:
        knowledge_hits, kb_sanitization = _sanitize_knowledge_hits(
            context_package=context_package,
            memory_bundle=memory_bundle,
        )
        thread_action = _safe_text(_safe_dict(thread_debug).get("action", {}).get("thread_action"))
        context_signals = {
            "state_confidence": _safe_float(state_snapshot.confidence, fallback=0.0),
            "active_frame": _safe_dict(thread_state.active_frame),
            "open_loops": list(thread_state.open_loops or []),
            "closed_loops": list(thread_state.closed_loops or []),
            "continuity_score": _safe_float(thread_state.continuity_score, fallback=0.0),
            "context_trace_flags": list(context_package.trace.reasons or []),
            "recent_turns_count": int(len(context_package.recent_turns_full) + len(context_package.recent_turns_summarized)),
        }
        payload = DiagnosticCenterInput(
            user_message=user_message,
            nervous_state=_norm_enum(getattr(state_snapshot, "nervous_state", "unknown"), {"hyper", "window", "hypo", "unknown"}),
            intent=_map_intent(state_snapshot, thread_state),
            openness=_norm_enum(getattr(state_snapshot, "openness", "unknown"), _DC_OPENNESS),
            ok_position=_norm_enum(getattr(state_snapshot, "ok_position", "unknown"), _DC_OK_POSITION),
            relation_to_thread=_norm_enum(getattr(thread_state, "relation_to_thread", "unknown"), _DC_RELATION),
            phase=_norm_enum(getattr(thread_state, "phase", "unknown"), _DC_PHASE),
            safety_flag=bool(state_snapshot.safety_flag or thread_state.safety_active),
            response_mode=_safe_text(getattr(thread_state, "response_mode", "reflect"), limit=80) or "reflect",
            pattern_core=_safe_text(getattr(thread_state, "pattern_core", "")),
            thread_action=thread_action,
            knowledge_hits=knowledge_hits,
            context_signals=context_signals,
        )
        output = build_diagnostic_center_output_v1(payload)
        divergence = build_diagnostic_center_shadow_divergence_v1(
            diagnostic_card=diagnostic_card,
            diagnostic_center_output=output,
            thread_state=thread_state,
            state_snapshot=state_snapshot,
            kb_sanitization=kb_sanitization,
        )
        timing_ms = int((time.perf_counter() - started_at) * 1000)
        return {
            "enabled": True,
            "status": "ok",
            "schema_version": output.schema_version,
            "runtime_mode": "shadow_only",
            "user_path_effect": "none",
            "output": output.to_dict(),
            "divergence": divergence,
            "kb_sanitization": kb_sanitization,
            "timing_ms": timing_ms,
            "error": None,
        }
    except Exception as exc:  # noqa: BLE001
        timing_ms = int((time.perf_counter() - started_at) * 1000)
        return {
            "enabled": True,
            "status": "error",
            "runtime_mode": "shadow_only",
            "user_path_effect": "none",
            "output": None,
            "divergence": {"shadow_failed_non_blocking": True},
            "timing_ms": timing_ms,
            "error": f"diagnostic_center_shadow_failed:{exc.__class__.__name__}",
        }
