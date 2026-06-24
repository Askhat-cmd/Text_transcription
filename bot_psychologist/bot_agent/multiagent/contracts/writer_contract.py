"""Writer contract used by multi-agent orchestrator."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any

from ..context_assembly import format_context_for_writer
from ..fresh_chat_context_policy import build_fresh_chat_context_policy_v1
from ..legacy_advisory_sanitizer import sanitize_legacy_advisory_for_writer
from ..writer_context_package import build_writer_context_package_v1
from ..writer_move_compliance import build_writer_move_instructions_v1
from .context_package import ContextAssemblyPackage
from .diagnostic_card import DiagnosticCard
from .memory_bundle import MemoryBundle
from .thread_state import ThreadState


@dataclass
class WriterContract:
    """Stable payload that Writer receives for one response generation."""

    user_message: str
    thread_state: ThreadState
    memory_bundle: MemoryBundle
    context_package: ContextAssemblyPackage | None = None
    diagnostic_card: DiagnosticCard | None = None
    knowledge_answer_guard: dict[str, Any] | None = None
    philosophy_kernel: dict[str, Any] | None = None
    writer_freedom_contract: dict[str, Any] | None = None
    active_line: dict[str, Any] | None = None
    response_planner: dict[str, Any] | None = None
    dialogue_policy: dict[str, Any] | None = None
    dialogue_pragmatics: dict[str, Any] | None = None
    retrieval_decision: dict[str, Any] | None = None
    final_answer_directive: dict[str, Any] | None = None
    response_language: str | None = None

    def to_dict(self) -> dict:
        return {
            "user_message": self.user_message,
            "thread_state": self.thread_state.to_dict(),
            "memory_bundle": self.memory_bundle.to_dict(),
            "context_package": (
                self.context_package.to_dict() if self.context_package is not None else None
            ),
            "diagnostic_card": (
                self.diagnostic_card.to_dict() if self.diagnostic_card is not None else None
            ),
            "knowledge_answer_guard": (
                dict(self.knowledge_answer_guard) if isinstance(self.knowledge_answer_guard, dict) else None
            ),
            "philosophy_kernel": (
                dict(self.philosophy_kernel) if isinstance(self.philosophy_kernel, dict) else None
            ),
            "writer_freedom_contract": (
                dict(self.writer_freedom_contract)
                if isinstance(self.writer_freedom_contract, dict)
                else None
            ),
            "active_line": (
                dict(self.active_line) if isinstance(self.active_line, dict) else None
            ),
            "response_planner": (
                dict(self.response_planner) if isinstance(self.response_planner, dict) else None
            ),
            "dialogue_policy": (
                dict(self.dialogue_policy) if isinstance(self.dialogue_policy, dict) else None
            ),
            "dialogue_pragmatics": (
                dict(self.dialogue_pragmatics)
                if isinstance(self.dialogue_pragmatics, dict)
                else None
            ),
            "retrieval_decision": (
                dict(self.retrieval_decision)
                if isinstance(self.retrieval_decision, dict)
                else None
            ),
            "final_answer_directive": (
                dict(self.final_answer_directive)
                if isinstance(self.final_answer_directive, dict)
                else None
            ),
            "response_language": self.response_language,
        }

    def to_prompt_context(self) -> dict:
        """Serialize context for Writer prompt templates."""
        fresh_chat_context_policy = build_fresh_chat_context_policy_v1(
            user_message=self.user_message,
            recent_turns=list(self.memory_bundle.recent_turns or []),
            knowledge_answer_guard=self.knowledge_answer_guard,
        )
        writer_context_package = build_writer_context_package_v1(
            user_message=self.user_message,
            memory_bundle=self.memory_bundle,
            context_package=self.context_package,
            retrieval_decision=self.retrieval_decision,
            fresh_chat_context_policy=fresh_chat_context_policy,
            latest_turn_constraints=(
                dict(self.final_answer_directive.get("latest_turn_constraints_v1", {}))
                if isinstance(self.final_answer_directive, dict)
                and isinstance(self.final_answer_directive.get("latest_turn_constraints_v1"), dict)
                else {}
            ),
        )
        if self.context_package is not None:
            conversation_context = format_context_for_writer(
                self.context_package,
                include_personal_history=False,
                include_semantic_hits=False,
                include_knowledge_hits=False,
            )
            semantic_hits = [
                str(item.get("content", "") or "")
                for item in list(writer_context_package.get("rag_for_writer", []) or [])
                if isinstance(item, dict) and str(item.get("content", "") or "").strip()
            ]
            if not semantic_hits:
                semantic_hits = [
                    str(item.get("content", "") or "")
                    for item in self.context_package.knowledge_rag_hits
                    if str(item.get("content", "") or "").strip()
                ]
            if not semantic_hits:
                semantic_hits = [
                    str(item.get("content", "") or "")
                    for item in self.context_package.semantic_memory_hits
                    if str(item.get("content", "") or "").strip()
                ]
            context_assembly_trace = self.context_package.trace.to_dict()
        else:
            conversation_context = self.memory_bundle.conversation_context
            semantic_hits = [hit.content for hit in self.memory_bundle.semantic_hits[:2]]
            context_assembly_trace = {}

        diagnostic_card_payload = (
            self.diagnostic_card.to_dict() if self.diagnostic_card is not None else {}
        )
        diagnostic_summary = (
            {
                "present": True,
                "situation_label": self.diagnostic_card.situation_label,
                "current_need": self.diagnostic_card.current_need,
                "suggested_writer_move": self.diagnostic_card.suggested_writer_move,
                "confidence": float(self.diagnostic_card.confidence),
                "risk_flags": list(self.diagnostic_card.risk_flags),
            }
            if self.diagnostic_card is not None
            else {
                "present": False,
                "situation_label": "",
                "current_need": "",
                "suggested_writer_move": "",
                "confidence": 0.0,
                "risk_flags": [],
            }
        )
        writer_move_instructions = build_writer_move_instructions_v1(self.diagnostic_card)
        writer_move_summary = (
            f"move={writer_move_instructions.get('move')}; "
            f"max_sentences={writer_move_instructions.get('max_sentences')}; "
            f"max_questions={writer_move_instructions.get('max_questions')}; "
            f"style={writer_move_instructions.get('style')}"
        )
        knowledge_answer_guard = (
            dict(self.knowledge_answer_guard)
            if isinstance(self.knowledge_answer_guard, dict)
            else {}
        )
        knowledge_answer = (
            dict(knowledge_answer_guard.get("knowledge_answer", {}))
            if isinstance(knowledge_answer_guard.get("knowledge_answer"), dict)
            else {}
        )
        practice_gate = (
            dict(knowledge_answer_guard.get("practice_gate", {}))
            if isinstance(knowledge_answer_guard.get("practice_gate"), dict)
            else {}
        )
        philosophy_kernel = (
            dict(self.philosophy_kernel)
            if isinstance(self.philosophy_kernel, dict)
            else {}
        )
        writer_freedom_contract = (
            dict(self.writer_freedom_contract)
            if isinstance(self.writer_freedom_contract, dict)
            else (
                dict(philosophy_kernel.get("writer_freedom_contract", {}))
                if isinstance(philosophy_kernel.get("writer_freedom_contract"), dict)
                else {}
            )
        )
        active_line = dict(self.active_line) if isinstance(self.active_line, dict) else {}
        response_planner = (
            dict(self.response_planner) if isinstance(self.response_planner, dict) else {}
        )
        dialogue_policy = (
            dict(self.dialogue_policy) if isinstance(self.dialogue_policy, dict) else {}
        )
        dialogue_pragmatics = (
            dict(self.dialogue_pragmatics)
            if isinstance(self.dialogue_pragmatics, dict)
            else (
                dict(dialogue_policy.get("dialogue_pragmatics", {}))
                if isinstance(dialogue_policy.get("dialogue_pragmatics"), dict)
                else {}
            )
        )
        retrieval_decision = (
            dict(self.retrieval_decision)
            if isinstance(self.retrieval_decision, dict)
            else (
                dict(dialogue_policy.get("retrieval_decision", {}))
                if isinstance(dialogue_policy.get("retrieval_decision"), dict)
                else {}
            )
        )
        contextual_retrieval_query_composer = (
            dict(retrieval_decision.get("composer", {}))
            if isinstance(retrieval_decision.get("composer"), dict)
            else (
                dict(retrieval_decision.get("contextual_retrieval_query_composer", {}))
                if isinstance(retrieval_decision.get("contextual_retrieval_query_composer"), dict)
                else {}
            )
        )
        unified_dialogue_policy = (
            dict(dialogue_policy.get("unified_dialogue_profile", {}))
            if isinstance(dialogue_policy.get("unified_dialogue_profile"), dict)
            else {}
        )
        dialogue_act_resolution = (
            dict(dialogue_policy.get("dialogue_act_resolution", {}))
            if isinstance(dialogue_policy.get("dialogue_act_resolution"), dict)
            else {}
        )
        last_assistant_offer = (
            dict(dialogue_policy.get("last_assistant_offer", {}))
            if isinstance(dialogue_policy.get("last_assistant_offer"), dict)
            else {}
        )
        unanswered_question_state = (
            dict(dialogue_policy.get("unanswered_question_state", {}))
            if isinstance(dialogue_policy.get("unanswered_question_state"), dict)
            else {}
        )
        dialogue_style_state = (
            dict(dialogue_policy.get("dialogue_style_state", {}))
            if isinstance(dialogue_policy.get("dialogue_style_state"), dict)
            else {}
        )
        answer_obligation_resolution = (
            dict(dialogue_policy.get("answer_obligation_resolution", {}))
            if isinstance(dialogue_policy.get("answer_obligation_resolution"), dict)
            else {}
        )
        included_writer_hits = [
            str(item.get("content", "") or "")
            for item in list(retrieval_decision.get("rag_included_for_writer", []) or [])
            if isinstance(item, dict) and str(item.get("content", "") or "").strip()
        ]
        writer_grounding_visibility = (
            dict(writer_context_package.get("writer_grounding_visibility_v1", {}))
            if isinstance(writer_context_package.get("writer_grounding_visibility_v1"), dict)
            else {}
        )
        writer_grounding_authority_note = str(
            writer_context_package.get("writer_grounding_authority_note", "") or ""
        )
        semantic_hits_budget = (
            dict(dialogue_policy.get("semantic_hits_budget", {}))
            if isinstance(dialogue_policy.get("semantic_hits_budget"), dict)
            else {}
        )
        semantic_hits_max = int(semantic_hits_budget.get("max_hits", 2) or 2)
        if semantic_hits_max < 1:
            semantic_hits_max = 1
        semantic_hit_chars = int(semantic_hits_budget.get("max_chars_per_hit", 300) or 300)
        if semantic_hit_chars < 120:
            semantic_hit_chars = 120
        has_explicit_retrieval_decision = "rag_included_count" in retrieval_decision
        semantic_source = (
            included_writer_hits
            if has_explicit_retrieval_decision
            else semantic_hits
        )
        if not bool(writer_grounding_visibility.get("kb_visible_to_writer", True)):
            semantic_source = []
        semantic_hits_trimmed = [
            str(item or "")[:semantic_hit_chars]
            for item in semantic_source[:semantic_hits_max]
            if str(item or "").strip()
        ]
        writer_kb_payload = (
            dict(writer_context_package.get("writer_kb_payload", {}))
            if isinstance(writer_context_package.get("writer_kb_payload"), dict)
            else {}
        )
        writer_kb_payload_trace = (
            dict(writer_context_package.get("writer_kb_payload_trace", {}))
            if isinstance(writer_context_package.get("writer_kb_payload_trace"), dict)
            else {}
        )
        runtime_truth_trace = (
            dict(writer_context_package.get("runtime_truth_trace_v1", {}))
            if isinstance(writer_context_package.get("runtime_truth_trace_v1"), dict)
            else {}
        )
        writer_kb_payload_future_graduation_notes = (
            dict(writer_context_package.get("writer_kb_payload_future_graduation_notes", {}))
            if isinstance(writer_context_package.get("writer_kb_payload_future_graduation_notes"), dict)
            else {}
        )
        writer_kb_payload_enabled = bool(writer_context_package.get("writer_kb_payload_enabled", False))
        writer_kb_payload_failed = bool(writer_context_package.get("writer_kb_payload_failed", False))
        writer_kb_payload_failure_reason = str(
            writer_context_package.get("writer_kb_payload_failure_reason", "") or ""
        )
        semantic_cards_pilot = (
            dict(writer_context_package.get("semantic_cards_pilot", {}))
            if isinstance(writer_context_package.get("semantic_cards_pilot"), dict)
            else {}
        )
        profile_for_writer = (
            dict(writer_context_package.get("profile_for_writer", {}))
            if isinstance(writer_context_package.get("profile_for_writer"), dict)
            else {}
        )
        profile_patterns = [
            str(item)
            for item in list(profile_for_writer.get("patterns", []) or [])
            if str(item).strip()
        ]
        profile_values = [
            str(item)
            for item in list(profile_for_writer.get("values", []) or [])
            if str(item).strip()
        ]
        dialogue_profile = str(dialogue_policy.get("profile", "safe_guided") or "safe_guided")
        dialogue_active_concept = str(dialogue_policy.get("active_concept", "") or "")
        final_answer_directive = (
            dict(self.final_answer_directive)
            if isinstance(self.final_answer_directive, dict)
            else {}
        )
        suppressed_legacy_constraints = [
            str(item)
            for item in list(final_answer_directive.get("suppressed_legacy_constraints", []) or [])
            if str(item).strip()
        ]
        writer_first_enabled = bool(final_answer_directive)
        legacy_blocks_source_only = bool(
            unified_dialogue_policy.get("legacy_blocks_source_signals_only", True)
        )
        mode_hint = str(writer_freedom_contract.get("mode_hint", self.thread_state.response_mode) or self.thread_state.response_mode)
        freedom_level = str(writer_freedom_contract.get("freedom_level", "guided") or "guided")
        mode_is_hint_not_cage = bool(writer_freedom_contract.get("mode_is_hint_not_cage", True))
        question_limit = int(writer_freedom_contract.get("question_limit", 1) or 1)
        practice_requires_gate = bool(writer_freedom_contract.get("practice_requires_gate", True))
        freedom_hard_boundaries = [
            str(item)
            for item in list(writer_freedom_contract.get("hard_boundaries", []) or [])
            if str(item).strip()
        ]
        sanitizer_source_signals = {
            "diagnostic_card_summary": diagnostic_summary,
            "writer_move_instructions": writer_move_instructions,
            "active_line": active_line,
            "response_planner": response_planner,
            "knowledge_answer_guard": knowledge_answer_guard,
            "latest_turn_constraints_v1": (
                dict(final_answer_directive.get("latest_turn_constraints_v1", {}))
                if isinstance(final_answer_directive.get("latest_turn_constraints_v1"), dict)
                else {}
            ),
            "writer_grounding_visibility_v1": writer_grounding_visibility,
            "final_answer_directive_version": str(
                final_answer_directive.get("version", "final_answer_directive_v1")
                or "final_answer_directive_v1"
            ),
            "final_answer_diagnostic_center_role": str(
                final_answer_directive.get("diagnostic_center_role", "guided_legacy")
                or "guided_legacy"
            ),
            "final_answer_planner_role": str(
                final_answer_directive.get("planner_role", "guided_legacy")
                or "guided_legacy"
            ),
            "final_answer_active_line_role": str(
                final_answer_directive.get("active_line_role", "guided_legacy")
                or "guided_legacy"
            ),
            "final_answer_diagnostic_card_role": str(
                final_answer_directive.get("diagnostic_card_role", "guided_legacy")
                or "guided_legacy"
            ),
            "answer_obligation": str(
                final_answer_directive.get("answer_obligation", "") or ""
            ),
            "must_answer": str(final_answer_directive.get("must_answer", "") or ""),
            "answer_shape": str(final_answer_directive.get("answer_shape", "") or ""),
            "depth": str(final_answer_directive.get("depth", "") or ""),
            "style": str(final_answer_directive.get("style", "") or ""),
            "question_policy": str(final_answer_directive.get("question_policy", "") or ""),
            "summary_request": bool(final_answer_directive.get("summary_request", False)),
            "summary_scope": str(final_answer_directive.get("summary_scope", "") or ""),
            "no_confirmation_needed": bool(
                final_answer_directive.get("no_confirmation_needed", False)
            ),
            "no_practice_unless_requested": bool(
                final_answer_directive.get("no_practice_unless_requested", False)
            ),
            "writer_autonomy": str(final_answer_directive.get("writer_autonomy", "") or ""),
            "acceptance_gate_feedback": (
                dict(final_answer_directive.get("acceptance_gate_feedback", {}))
                if isinstance(final_answer_directive.get("acceptance_gate_feedback"), dict)
                else {}
            ),
        }
        legacy_advisory_sanitization = sanitize_legacy_advisory_for_writer(
            sanitizer_source_signals
        )

        return {
            "user_message": self.user_message,
            "phase": self.thread_state.phase,
            "response_mode": self.thread_state.response_mode,
            "response_goal": self.thread_state.response_goal,
            "must_avoid": self.thread_state.must_avoid,
            "ok_position": self.thread_state.ok_position,
            "openness": self.thread_state.openness,
            "open_loops": self.thread_state.open_loops,
            "closed_loops": self.thread_state.closed_loops,
            "core_direction": self.thread_state.core_direction,
            "pattern_core": self.thread_state.pattern_core,
            "active_frame": self.thread_state.active_frame,
            "nervous_state": self.thread_state.nervous_state,
            "safety_active": self.thread_state.safety_active,
            "conversation_context": conversation_context,
            "user_profile_patterns": profile_patterns,
            "user_profile_values": profile_values,
            "semantic_hits": semantic_hits_trimmed,
            "has_relevant_knowledge": self.memory_bundle.has_relevant_knowledge,
            "fresh_chat_context_policy": fresh_chat_context_policy,
            "fresh_chat_context_policy_version": str(
                fresh_chat_context_policy.get("version", "fresh_chat_context_policy_v1")
                or "fresh_chat_context_policy_v1"
            ),
            "fresh_chat_is_new_chat": bool(fresh_chat_context_policy.get("is_new_chat", False)),
            "fresh_chat_turn_index": int(fresh_chat_context_policy.get("turn_index", 1) or 1),
            "fresh_chat_is_greeting_or_contact": bool(
                fresh_chat_context_policy.get("is_greeting_or_contact", False)
            ),
            "fresh_chat_cross_session_memory_allowed": bool(
                fresh_chat_context_policy.get("cross_session_memory_allowed", True)
            ),
            "fresh_chat_cross_session_memory_reason": str(
                fresh_chat_context_policy.get("cross_session_memory_reason", "") or ""
            ),
            "fresh_chat_active_context_source": str(
                fresh_chat_context_policy.get("active_context_source", "current_chat_only")
                or "current_chat_only"
            ),
            "writer_context_package": writer_context_package,
            "writer_context_package_version": str(
                writer_context_package.get("version", "writer_context_package_v1")
                or "writer_context_package_v1"
            ),
            "writer_context_recent_turns_count": len(
                list(writer_context_package.get("recent_turns_for_writer", []) or [])
            ),
            "writer_context_profile_present": bool(profile_for_writer),
            "writer_context_rag_candidates_count": len(
                list(writer_context_package.get("rag_candidates_for_trace", []) or [])
            ),
            "writer_context_rag_for_writer_count": len(
                list(writer_context_package.get("rag_for_writer", []) or [])
            ),
            "semantic_hits_budget": {
                "max_hits": semantic_hits_max,
                "max_chars_per_hit": semantic_hit_chars,
            },
            "writer_kb_payload_enabled": writer_kb_payload_enabled,
            "writer_kb_payload_failed": writer_kb_payload_failed,
            "writer_kb_payload_failure_reason": writer_kb_payload_failure_reason,
            "writer_kb_payload": writer_kb_payload,
            "writer_kb_payload_trace": writer_kb_payload_trace,
            "runtime_truth_trace_v1": runtime_truth_trace,
            "writer_kb_payload_trace_version": str(
                writer_kb_payload_trace.get("schema_version", "writer_kb_payload_trace_v1")
                or "writer_kb_payload_trace_v1"
            ),
            "writer_kb_payload_future_graduation_notes": writer_kb_payload_future_graduation_notes,
            "semantic_cards_pilot": semantic_cards_pilot,
            "writer_grounding_visibility_v1": writer_grounding_visibility,
            "writer_grounding_visibility_json": json.dumps(
                writer_grounding_visibility,
                ensure_ascii=False,
                indent=2,
            )
            if writer_grounding_visibility
            else "{}",
            "writer_grounding_authority_note": writer_grounding_authority_note
            or "Safety and the explicit latest user request are mandatory. Grounding is optional support only.",
            "context_assembly_trace": context_assembly_trace,
            "context_package_summary": {
                "present": self.context_package is not None,
                "recent_full_count": (
                    len(self.context_package.recent_turns_full)
                    if self.context_package is not None
                    else 0
                ),
                "recent_summarized_count": (
                    len(self.context_package.recent_turns_summarized)
                    if self.context_package is not None
                    else 0
                ),
            },
            "diagnostic_card": diagnostic_card_payload,
            "diagnostic_card_summary": diagnostic_summary,
            "diagnostic_card_avoid_list": (
                list(self.diagnostic_card.avoid_list)
                if self.diagnostic_card is not None
                else []
            ),
            "diagnostic_card_risk_flags": (
                list(self.diagnostic_card.risk_flags)
                if self.diagnostic_card is not None
                else []
            ),
            "writer_move_instructions": writer_move_instructions,
            "writer_move_instruction_summary": writer_move_summary,
            "writer_move_must_do": list(writer_move_instructions.get("must_do", []) or []),
            "writer_move_must_not_do": list(writer_move_instructions.get("must_not_do", []) or []),
            "legacy_advisory_sanitization": legacy_advisory_sanitization,
            "writer_visible_advisory_summary": str(
                legacy_advisory_sanitization.get("writer_visible_summary", "") or ""
            ),
            "writer_visible_practice_instruction": str(
                legacy_advisory_sanitization.get("writer_visible_practice_instruction", "")
                or ""
            ),
            "writer_visible_practice_note": str(
                legacy_advisory_sanitization.get("writer_visible_practice_note", "") or ""
            ),
            "practice_rewrite_applied": bool(
                legacy_advisory_sanitization.get("practice_rewrite_applied", False)
            ),
            "knowledge_answer_guard": knowledge_answer_guard,
            "knowledge_answer": knowledge_answer,
            "practice_gate": practice_gate,
            "practice_ban_enforced": not bool(practice_gate.get("practice_allowed", True)),
            "known_concept_clarification_ban": bool(knowledge_answer.get("should_answer_directly", False)),
            "external_surveillance_frame_ban": bool(knowledge_answer.get("should_answer_directly", False)),
            "philosophy_kernel": philosophy_kernel,
            "philosophy_kernel_prompt_block": str(philosophy_kernel.get("prompt_block", "") or ""),
            "philosophy_kernel_version": str(philosophy_kernel.get("kernel_version", "") or ""),
            "philosophy_kernel_selected_lenses": list(
                dict(philosophy_kernel.get("selection", {})).get("selected_lenses", [])
                if isinstance(philosophy_kernel.get("selection"), dict)
                else []
            ),
            "philosophy_kernel_quote_policy": str(
                philosophy_kernel.get("quote_policy", "internal_lens_not_citation")
            ),
            "philosophy_kernel_prompt_compactness": (
                dict(philosophy_kernel.get("prompt_compactness", {}))
                if isinstance(philosophy_kernel.get("prompt_compactness"), dict)
                else {}
            ),
            "writer_freedom_contract": writer_freedom_contract,
            "writer_freedom_prompt_block": str(
                philosophy_kernel.get("writer_freedom_prompt_block", "") or ""
            ),
            "writer_freedom_contract_version": str(
                writer_freedom_contract.get("version", "writer_freedom_contract_v1")
            ),
            "writer_freedom_level": freedom_level,
            "writer_mode_hint": mode_hint,
            "mode_is_hint_not_cage": mode_is_hint_not_cage,
            "writer_question_limit": question_limit,
            "practice_requires_gate": practice_requires_gate,
            "writer_freedom_hard_boundaries": freedom_hard_boundaries,
            "active_line": active_line,
            "active_line_version": str(active_line.get("version", "active_line_v1")),
            "active_line_text": str(active_line.get("active_line", "") or ""),
            "active_line_user_intent": str(active_line.get("user_intent", "unknown") or "unknown"),
            "active_line_continuity_mode": str(
                active_line.get("continuity_mode", "continue_existing_line") or "continue_existing_line"
            ),
            "active_line_next_meaningful_move": str(
                active_line.get("next_meaningful_move", "") or ""
            ),
            "active_line_should_continue_line": bool(active_line.get("should_continue_line", True)),
            "active_line_should_ask_question": bool(active_line.get("should_ask_question", False)),
            "active_line_should_offer_practice": bool(active_line.get("should_offer_practice", False)),
            "active_line_revoicing_allowed": bool(active_line.get("revoicing_allowed", False)),
            "active_line_revoicing_style": str(active_line.get("revoicing_style", "suppressed") or "suppressed"),
            "active_line_repair_mode": (
                str(active_line.get("repair_mode"))
                if active_line.get("repair_mode") is not None
                else ""
            ),
            "active_line_practice_suppression_active": bool(
                active_line.get("practice_suppression_active", False)
            ),
            "response_planner": response_planner,
            "response_planner_version": str(
                response_planner.get("version", "response_planner_v1")
            ),
            "response_planner_enabled": bool(response_planner.get("enabled", False)),
            "response_planner_next_move": str(
                response_planner.get("next_move", "continue_active_line") or "continue_active_line"
            ),
            "response_planner_answer_shape": str(
                response_planner.get("answer_shape", "compact_direct") or "compact_direct"
            ),
            "response_planner_response_depth": str(
                response_planner.get("response_depth", "short") or "short"
            ),
            "response_planner_target_micro_shift": str(
                response_planner.get("target_micro_shift", "") or ""
            ),
            "response_planner_should_answer_directly": bool(
                response_planner.get("should_answer_directly", False)
            ),
            "response_planner_question_policy": str(
                response_planner.get("question_policy", "none") or "none"
            ),
            "response_planner_practice_policy": str(
                response_planner.get("practice_policy", "forbidden") or "forbidden"
            ),
            "response_planner_revoicing_policy": str(
                response_planner.get("revoicing_policy", "suppressed") or "suppressed"
            ),
            "response_planner_continuity_policy": str(
                response_planner.get("continuity_policy", "continue_active_line")
                or "continue_active_line"
            ),
            "response_planner_safety_priority": bool(
                response_planner.get("safety_priority", False)
            ),
            "response_planner_confidence": float(
                response_planner.get("confidence", 0.0) or 0.0
            ),
            "response_planner_rationale": str(
                response_planner.get("rationale", "") or ""
            ),
            "response_planner_must_include": list(
                response_planner.get("must_include", []) or []
            ),
            "response_planner_must_avoid": list(
                response_planner.get("must_avoid", []) or []
            ),
            "dialogue_policy": dialogue_policy,
            "dialogue_profile": dialogue_profile,
            "profile_preset": str(
                dialogue_policy.get("profile_preset", unified_dialogue_policy.get("profile_preset", "safe_guided"))
                or unified_dialogue_policy.get("profile_preset", "safe_guided")
            ),
            "unified_dialogue_policy": unified_dialogue_policy,
            "unified_dialogue_policy_version": str(
                unified_dialogue_policy.get("version", "unified_dialogue_policy_v2")
                or "unified_dialogue_policy_v2"
            ),
            "unified_active_profile_alias": str(
                unified_dialogue_policy.get("active_profile_alias", dialogue_profile)
                or dialogue_profile
            ),
            "unified_effective_writer_autonomy": str(
                unified_dialogue_policy.get("effective_writer_autonomy", dialogue_policy.get("writer_autonomy", "medium"))
                or dialogue_policy.get("writer_autonomy", "medium")
            ),
            "unified_effective_safety_floor": str(
                unified_dialogue_policy.get("effective_safety_floor", "minimal_baseline")
                or "minimal_baseline"
            ),
            "unified_legacy_blocks_visible_to_writer": bool(
                unified_dialogue_policy.get("legacy_blocks_visible_to_writer", False)
            ),
            "unified_legacy_blocks_source_signals_only": bool(
                unified_dialogue_policy.get("legacy_blocks_source_signals_only", True)
            ),
            "unified_hard_boundaries_csv": ", ".join(
                [str(item) for item in list(unified_dialogue_policy.get("hard_boundaries", []) or []) if str(item).strip()]
            ) or "none",
            "unified_soft_guidance_csv": ", ".join(
                [str(item) for item in list(unified_dialogue_policy.get("soft_guidance", []) or []) if str(item).strip()]
            ) or "none",
            "dialogue_act_resolution": dialogue_act_resolution,
            "dialogue_act": str(dialogue_act_resolution.get("dialogue_act", "unknown") or "unknown"),
            "dialogue_act_confidence": float(dialogue_act_resolution.get("confidence", 0.0) or 0.0),
            "dialogue_act_evidence": ", ".join(
                [str(item) for item in list(dialogue_act_resolution.get("evidence", []) or []) if str(item).strip()]
            ) or "none",
            "last_assistant_offer": last_assistant_offer,
            "last_assistant_offer_open": bool(last_assistant_offer.get("is_open", False)),
            "last_assistant_offer_type": str(last_assistant_offer.get("offer_type", "none") or "none"),
            "last_assistant_offer_summary": str(last_assistant_offer.get("offer_text_summary", "") or "none"),
            "unanswered_question_state": unanswered_question_state,
            "unanswered_question_answer_required": bool(unanswered_question_state.get("answer_required", False)),
            "unanswered_question_status": str(
                unanswered_question_state.get("answer_status", "answered") or "answered"
            ),
            "unanswered_question_summary": str(
                unanswered_question_state.get("last_direct_user_question", "") or "none"
            ),
            "dialogue_style_state": dialogue_style_state,
            "dialogue_style_tone": str(dialogue_style_state.get("tone", "neutral") or "neutral"),
            "dialogue_style_length_preference": str(
                dialogue_style_state.get("length_preference", "adaptive") or "adaptive"
            ),
            "dialogue_style_complexity_preference": str(
                dialogue_style_state.get("complexity_preference", "normal") or "normal"
            ),
            "dialogue_style_avoid_csv": ", ".join(
                [str(item) for item in list(dialogue_style_state.get("avoid", []) or []) if str(item).strip()]
            ) or "none",
            "answer_obligation_resolution": answer_obligation_resolution,
            "answer_obligation": str(
                answer_obligation_resolution.get("answer_obligation", "continue_thread")
                or "continue_thread"
            ),
            "answer_obligation_shape": str(
                answer_obligation_resolution.get("answer_shape", "structured_explanation")
                or "structured_explanation"
            ),
            "answer_obligation_depth": str(
                answer_obligation_resolution.get("depth", "medium") or "medium"
            ),
            "answer_obligation_question_policy": str(
                answer_obligation_resolution.get("question_policy", "optional_none")
                or "optional_none"
            ),
            "answer_obligation_source": ", ".join(
                [str(item) for item in list(answer_obligation_resolution.get("source", []) or []) if str(item).strip()]
            ) or "none",
            "latest_turn_constraints_v1": (
                dict(final_answer_directive.get("latest_turn_constraints_v1", {}))
                if isinstance(final_answer_directive.get("latest_turn_constraints_v1"), dict)
                else {}
            ),
            "latest_turn_constraint_names": [
                str(item)
                for item in list(
                    dict(final_answer_directive.get("latest_turn_constraints_v1", {})).get(
                        "active_constraints", []
                    )
                    or []
                )
                if str(item).strip()
            ],
            "final_answer_directive": final_answer_directive,
            "final_answer_summary_request": bool(
                final_answer_directive.get("summary_request", False)
            ),
            "final_answer_summary_scope": str(
                final_answer_directive.get("summary_scope", "") or ""
            ),
            "final_answer_no_confirmation_needed": bool(
                final_answer_directive.get("no_confirmation_needed", False)
            ),
            "final_answer_no_practice_unless_requested": bool(
                final_answer_directive.get("no_practice_unless_requested", False)
            ),
            "final_answer_summary_context_anchors": [
                str(item)
                for item in list(final_answer_directive.get("summary_context_anchors", []) or [])
                if str(item).strip()
            ],
            "final_answer_directive_json": json.dumps(
                final_answer_directive,
                ensure_ascii=False,
                indent=2,
            )
            if final_answer_directive
            else "{}",
            "writer_visible_final_answer_directive_json": str(
                legacy_advisory_sanitization.get(
                    "writer_visible_final_answer_directive_json",
                    "{}",
                )
                or "{}"
            ),
            "final_answer_directive_version": str(
                final_answer_directive.get("version", "final_answer_directive_v1")
                or "final_answer_directive_v1"
            ),
            "final_answer_diagnostic_center_role": str(
                final_answer_directive.get("diagnostic_center_role", "guided_legacy")
                or "guided_legacy"
            ),
            "final_answer_planner_role": str(
                final_answer_directive.get("planner_role", "guided_legacy")
                or "guided_legacy"
            ),
            "final_answer_active_line_role": str(
                final_answer_directive.get("active_line_role", "guided_legacy")
                or "guided_legacy"
            ),
            "final_answer_diagnostic_card_role": str(
                final_answer_directive.get("diagnostic_card_role", "guided_legacy")
                or "guided_legacy"
            ),
            "legacy_constraints_suppressed": suppressed_legacy_constraints,
            "legacy_constraints_suppressed_csv": ", ".join(suppressed_legacy_constraints) or "none",
            "writer_first_prompt_assembly_enabled": writer_first_enabled,
            "legacy_blocks_visible_to_writer": bool(
                unified_dialogue_policy.get("legacy_blocks_visible_to_writer", False)
            ),
            "legacy_blocks_source_signals_only": legacy_blocks_source_only,
            "dialogue_expansion_requested": bool(dialogue_policy.get("expansion_requested", False)),
            "dialogue_repair_and_expand_requested": bool(
                dialogue_policy.get("repair_and_expand_requested", False)
            ),
            "dialogue_active_concept": dialogue_active_concept,
            "dialogue_pragmatics": dialogue_pragmatics,
            "dialogue_pragmatics_version": str(
                dialogue_pragmatics.get("version", "dialogue_pragmatics_v1")
            ),
            "dialogue_pragmatics_short_utterance": bool(
                dialogue_pragmatics.get("is_short_utterance", False)
            ),
            "dialogue_pragmatics_short_type": str(
                dialogue_pragmatics.get("short_utterance_type", "not_short") or "not_short"
            ),
            "dialogue_pragmatics_is_contextual_followup": bool(
                dialogue_pragmatics.get("is_contextual_followup", False)
            ),
            "dialogue_pragmatics_offer_type": str(
                dialogue_pragmatics.get("previous_assistant_offer_type", "unknown") or "unknown"
            ),
            "dialogue_pragmatics_inherited_intent": str(
                dialogue_pragmatics.get("inherited_user_intent", "continue_previous_offer")
                or "continue_previous_offer"
            ),
            "dialogue_pragmatics_should_answer_directly": bool(
                dialogue_pragmatics.get("should_answer_directly", False)
            ),
            "dialogue_pragmatics_should_not_ask_confirmation_again": bool(
                dialogue_pragmatics.get("should_not_ask_confirmation_again", False)
            ),
            "dialogue_pragmatics_repair_user_dissatisfaction": bool(
                dialogue_pragmatics.get("repair_user_dissatisfaction", False)
            ),
            "dialogue_pragmatics_reason": str(dialogue_pragmatics.get("reason", "none") or "none"),
            "retrieval_decision": retrieval_decision,
            "contextual_retrieval_query_composer": contextual_retrieval_query_composer,
            "contextual_retrieval_query_composer_version": str(
                contextual_retrieval_query_composer.get(
                    "version",
                    "contextual_retrieval_query_composer_v1",
                )
                or "contextual_retrieval_query_composer_v1"
            ),
            "retrieval_query_source": str(
                contextual_retrieval_query_composer.get("query_source", "") or ""
            ),
            "composed_retrieval_query": str(
                contextual_retrieval_query_composer.get("composed_query", "") or ""
            ),
            "retrieval_need": str(
                contextual_retrieval_query_composer.get("retrieval_need", "") or ""
            ),
            "retrieval_query_composer_action": str(
                contextual_retrieval_query_composer.get("retrieval_action", "") or ""
            ),
            "retrieval_query_composer_writer_can_ignore_rag": bool(
                contextual_retrieval_query_composer.get("writer_can_ignore_rag", True)
            ),
            "retrieval_query_composer_no_user_facing_text_created": bool(
                contextual_retrieval_query_composer.get(
                    "no_user_facing_text_created",
                    True,
                )
            ),
            "hybrid_retrieval_plan": (
                dict(writer_context_package.get("hybrid_retrieval_plan", {}))
                if isinstance(writer_context_package.get("hybrid_retrieval_plan"), dict)
                else {}
            ),
            "hybrid_retrieval_planner_mode": str(
                writer_context_package.get("hybrid_retrieval_planner_mode", "shadow") or "shadow"
            ),
            "retrieval_context": (
                dict(writer_context_package.get("retrieval_context", {}))
                if isinstance(writer_context_package.get("retrieval_context"), dict)
                else {}
            ),
            "retrieval_decision_version": str(
                retrieval_decision.get("retrieval_decision_version", "contextual_retrieval_gating_v1")
                or "contextual_retrieval_gating_v1"
            ),
            "retrieval_action": str(retrieval_decision.get("retrieval_action", "none") or "none"),
            "retrieval_rag_candidates_count": int(retrieval_decision.get("rag_candidates_count", 0) or 0),
            "retrieval_rag_included_count": int(retrieval_decision.get("rag_included_count", 0) or 0),
            "retrieval_rag_included_reason": str(retrieval_decision.get("rag_included_reason", "") or ""),
            "retrieval_rag_suppressed_reason": str(
                retrieval_decision.get("rag_suppressed_reason", "") or ""
            ),
            "retrieval_writer_can_ignore_rag": bool(
                retrieval_decision.get("writer_can_ignore_rag", True)
            ),
            "retrieval_rag_relevance": str(
                retrieval_decision.get("rag_relevance_to_current_turn", "unknown") or "unknown"
            ),
            "retrieval_inherited_topic": str(retrieval_decision.get("inherited_topic", "") or ""),
            "retrieval_inherited_offer_type": str(
                retrieval_decision.get("inherited_offer_type", "unknown") or "unknown"
            ),
        }
