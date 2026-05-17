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
from .diagnostic_center_divergence import evaluate_diagnostic_center_divergence_v1
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
    return evaluate_diagnostic_center_divergence_v1(
        diagnostic_card=diagnostic_card,
        diagnostic_center_output=diagnostic_center_output,
        thread_state=thread_state,
        state_snapshot=state_snapshot,
        kb_sanitization=kb_sanitization,
    )


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
