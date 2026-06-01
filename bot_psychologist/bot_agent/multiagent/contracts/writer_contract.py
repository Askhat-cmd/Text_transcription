"""Writer contract used by multi-agent orchestrator."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any

from ..context_assembly import format_context_for_writer
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
        if self.context_package is not None:
            conversation_context = format_context_for_writer(self.context_package)
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
        included_writer_hits = [
            str(item.get("content", "") or "")
            for item in list(retrieval_decision.get("rag_included_for_writer", []) or [])
            if isinstance(item, dict) and str(item.get("content", "") or "").strip()
        ]
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
        semantic_hits_trimmed = [
            str(item or "")[:semantic_hit_chars]
            for item in semantic_source[:semantic_hits_max]
            if str(item or "").strip()
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
        legacy_blocks_source_only = bool(dialogue_profile == "mvp_free_dialogue")
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
            "user_profile_patterns": self.memory_bundle.user_profile.patterns,
            "user_profile_values": self.memory_bundle.user_profile.values,
            "semantic_hits": semantic_hits_trimmed,
            "has_relevant_knowledge": self.memory_bundle.has_relevant_knowledge,
            "semantic_hits_budget": {
                "max_hits": semantic_hits_max,
                "max_chars_per_hit": semantic_hit_chars,
            },
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
            "final_answer_directive": final_answer_directive,
            "final_answer_directive_json": json.dumps(
                final_answer_directive,
                ensure_ascii=False,
                indent=2,
            )
            if final_answer_directive
            else "{}",
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
            "legacy_blocks_visible_to_writer": not legacy_blocks_source_only,
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
