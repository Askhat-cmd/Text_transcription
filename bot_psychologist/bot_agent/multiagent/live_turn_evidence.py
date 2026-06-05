"""Live turn evidence helpers for reproducible multiagent diagnostics."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from .stale_stub_detector import detect_stale_stub


LIVE_TURN_EVIDENCE_VERSION = "live_turn_evidence_v1"


def _safe_text(value: Any, *, limit: int = 1200) -> str:
    text = str(value or "").replace("\r\n", "\n").strip()
    if len(text) <= limit:
        return text
    return f"{text[:limit]}...[truncated:{len(text) - limit}]"


def _sha256(text: str) -> str:
    if not text:
        return ""
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _safe_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def build_live_turn_evidence_v1(
    *,
    query: str,
    user_id: str,
    session_id: str | None,
    turn_index: int | None,
    orchestrator_result: dict,
    writer_contract: Any,
    writer_debug: dict,
    memory_bundle: Any,
    state_snapshot: Any,
    thread_state: Any,
    thread_debug: dict,
    diagnostic_card: Any,
    active_line_state: dict,
    response_planner_state: dict,
    dialogue_policy: dict,
    dialogue_pragmatics: dict,
    contextual_retrieval_decision: dict,
    unified_dialogue_profile: dict,
    dialogue_act_resolution: dict,
    last_assistant_offer: dict,
    unanswered_question_state: dict,
    dialogue_style_state: dict,
    answer_obligation_resolution: dict,
    validation_result: Any,
) -> dict:
    contract_context = writer_contract.to_prompt_context() if hasattr(writer_contract, "to_prompt_context") else {}
    conversation_context = _safe_text(
        getattr(memory_bundle, "conversation_context", ""),
        limit=1800,
    )
    user_prompt = _safe_text(writer_debug.get("user_prompt", ""), limit=2200)
    system_prompt = _safe_text(writer_debug.get("system_prompt", ""), limit=1800)
    writer_answer = _safe_text(orchestrator_result.get("answer", ""), limit=2200)
    stale_stub_result = detect_stale_stub(str(orchestrator_result.get("answer", "") or ""))
    final_answer_directive = _safe_dict(contract_context.get("final_answer_directive", {}))
    suppressed_legacy_constraints = [
        str(item)
        for item in list(contract_context.get("legacy_constraints_suppressed", []) or [])
        if str(item).strip()
    ]

    semantic_hits = []
    for hit in list(getattr(memory_bundle, "semantic_hits", []) or []):
        chunk_id = str(getattr(hit, "chunk_id", "") or "")
        semantic_hits.append(
            {
                "chunk_id_hash": _sha256(chunk_id),
                "source": str(getattr(hit, "source", "unknown") or "unknown"),
                "score": float(getattr(hit, "score", 0.0) or 0.0),
                "content_preview": _safe_text(getattr(hit, "content", ""), limit=240),
            }
        )

    card_dict = diagnostic_card.to_dict() if hasattr(diagnostic_card, "to_dict") else {}
    validation_payload = {
        "is_blocked": bool(getattr(validation_result, "is_blocked", False)),
        "block_reason": str(getattr(validation_result, "block_reason", "") or ""),
        "quality_flags": [
            str(item)
            for item in list(getattr(validation_result, "quality_flags", []) or [])
            if str(item).strip()
        ],
    }

    return {
        "version": LIVE_TURN_EVIDENCE_VERSION,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "turn_identity": {
            "user_id": str(user_id or ""),
            "session_id": str(session_id or ""),
            "turn_index": int(turn_index) if isinstance(turn_index, int) else None,
        },
        "input": {
            "query": _safe_text(query, limit=500),
            "query_chars": len(str(query or "")),
        },
        "state_thread": {
            "nervous_state": str(getattr(state_snapshot, "nervous_state", "") or ""),
            "intent": str(getattr(state_snapshot, "intent", "") or ""),
            "safety_flag": bool(getattr(state_snapshot, "safety_flag", False)),
            "thread_id": str(getattr(thread_state, "thread_id", "") or ""),
            "phase": str(getattr(thread_state, "phase", "") or ""),
            "relation_to_thread": str(getattr(thread_state, "relation_to_thread", "") or ""),
            "response_mode": str(getattr(thread_state, "response_mode", "") or ""),
        },
        "dialogue": {
            "policy": _safe_dict(dialogue_policy),
            "unified_dialogue_policy": _safe_dict(unified_dialogue_profile),
            "pragmatics": _safe_dict(dialogue_pragmatics),
            "dialogue_act_resolution": _safe_dict(dialogue_act_resolution),
            "last_assistant_offer": _safe_dict(last_assistant_offer),
            "unanswered_question_state": _safe_dict(unanswered_question_state),
            "dialogue_style_state": _safe_dict(dialogue_style_state),
            "answer_obligation_resolution": _safe_dict(answer_obligation_resolution),
            "fresh_chat_context_policy": _safe_dict(
                contract_context.get("fresh_chat_context_policy", {})
            ),
            "retrieval": _safe_dict(contextual_retrieval_decision),
            "active_line": _safe_dict(active_line_state),
            "response_planner": _safe_dict(response_planner_state),
            "thread_debug": _safe_dict(thread_debug),
        },
        "memory": {
            "conversation_context": conversation_context,
            "conversation_context_chars": len(str(getattr(memory_bundle, "conversation_context", "") or "")),
            "semantic_hits_count": len(semantic_hits),
            "semantic_hits": semantic_hits,
        },
        "writer": {
            "contract_excerpt": {
                "response_mode": str(contract_context.get("response_mode", "") or ""),
                "response_goal": str(contract_context.get("response_goal", "") or ""),
                "must_avoid": list(contract_context.get("must_avoid", []) or []),
                "dialogue_profile": str(contract_context.get("dialogue_profile", "") or ""),
                "retrieval_action": str(contract_context.get("retrieval_action", "") or ""),
                "dialogue_pragmatics_short_type": str(
                    contract_context.get("dialogue_pragmatics_short_type", "") or ""
                ),
            },
            "final_answer_directive": final_answer_directive,
            "prompt_assembly": {
                "writer_first_enabled": bool(
                    contract_context.get("writer_first_prompt_assembly_enabled", False)
                ),
                "fresh_chat_context_policy": _safe_dict(
                    contract_context.get("fresh_chat_context_policy", {})
                ),
                "writer_context_package": _safe_dict(
                    contract_context.get("writer_context_package", {})
                ),
                "legacy_blocks_visible_to_writer": bool(
                    contract_context.get("legacy_blocks_visible_to_writer", True)
                ),
                "legacy_blocks_source_signals_only": bool(
                    contract_context.get("legacy_blocks_source_signals_only", False)
                ),
                "suppressed_legacy_constraints": suppressed_legacy_constraints,
                "diagnostic_center_role": str(
                    contract_context.get("final_answer_diagnostic_center_role", "guided_legacy")
                    or "guided_legacy"
                ),
                "planner_role": str(
                    contract_context.get("final_answer_planner_role", "guided_legacy")
                    or "guided_legacy"
                ),
                "active_line_role": str(
                    contract_context.get("final_answer_active_line_role", "guided_legacy")
                    or "guided_legacy"
                ),
                "diagnostic_card_role": str(
                    contract_context.get("final_answer_diagnostic_card_role", "guided_legacy")
                    or "guided_legacy"
                ),
                "legacy_advisory_sanitization": _safe_dict(
                    contract_context.get("legacy_advisory_sanitization", {})
                ),
                "writer_visible_practice_instruction": str(
                    contract_context.get("writer_visible_practice_instruction", "") or ""
                ),
                "practice_rewrite_applied": bool(
                    contract_context.get("practice_rewrite_applied", False)
                ),
            },
            "prompt_canvas": {
                "system_prompt_sha256": _sha256(system_prompt),
                "system_prompt_preview": system_prompt,
                "system_prompt_chars": len(str(writer_debug.get("system_prompt", "") or "")),
                "user_prompt_sha256": _sha256(user_prompt),
                "user_prompt_preview": user_prompt,
                "user_prompt_chars": len(str(writer_debug.get("user_prompt", "") or "")),
            },
            "writer_debug": {
                "model": str(writer_debug.get("model", "") or ""),
                "api_mode": writer_debug.get("api_mode"),
                "temperature": writer_debug.get("temperature"),
                "max_tokens": writer_debug.get("max_tokens"),
                "fallback_used": bool(writer_debug.get("fallback_used", False)),
                "overruled_constraints": list(writer_debug.get("overruled_constraints", []) or []),
                "final_answer_shape": writer_debug.get("final_answer_shape"),
                "retrieval_action": writer_debug.get("retrieval_action"),
                "dialogue_pragmatics_offer_type": writer_debug.get("dialogue_pragmatics_offer_type"),
                "answer_fit_evaluator": _safe_dict(writer_debug.get("answer_fit_evaluator")),
                "answer_fit_repair_applied": bool(writer_debug.get("answer_fit_repair_applied", False)),
            },
            "answer": writer_answer,
            "answer_chars": len(str(orchestrator_result.get("answer", "") or "")),
            "stale_stub_detected": bool(stale_stub_result.get("detected", False)),
            "stale_stub_match": str(stale_stub_result.get("matched_phrase", "") or ""),
        },
        "validator": validation_payload,
        "diagnostic_card": {
            "present": bool(card_dict),
            "summary": {
                "situation_label": str(card_dict.get("situation_label", "") or ""),
                "current_need": str(card_dict.get("current_need", "") or ""),
                "suggested_writer_move": str(card_dict.get("suggested_writer_move", "") or ""),
                "confidence": float(card_dict.get("confidence", 0.0) or 0.0),
            },
            "trace": _safe_dict(card_dict.get("trace", {})),
        },
    }


__all__ = ["LIVE_TURN_EVIDENCE_VERSION", "build_live_turn_evidence_v1"]
