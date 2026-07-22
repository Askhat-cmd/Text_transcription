"""Writer Agent for NEO multi-agent runtime."""

from __future__ import annotations

import logging
import re
import time
from typing import Any, Optional

from ...config import config
from ...feature_flags import feature_flags
from ..active_line import starts_with_mechanical_revoicing
from ..dialogue_policy import (
    DIALOGUE_PROFILE_MVP_FREE,
    detect_examples_request,
    detect_numbered_list_request,
    detect_practice_overview_request,
)
from ..stale_stub_detector import detect_stale_stub
from ..contracts.writer_contract import WriterContract
from .agent_llm_client import create_agent_completion
from .agent_llm_config import get_model_for_agent, get_temperature_for_agent
from .writer_agent_constants import _contains_any
from .writer_agent_enforce_slice1 import _extract_enforce_slice1_prelude
from .writer_agent_enforce_slice2 import _extract_enforce_slice2_second_prelude_and_close_gently
from .writer_agent_fallback_helpers import (
    _build_gentle_close_reply as _fallback_build_gentle_close_reply,
    _build_no_practice_fallback_text as _fallback_build_no_practice_fallback_text,
    _detect_language as _fallback_detect_language,
    _format_diagnostic_summary as _fallback_format_diagnostic_summary,
    _format_hits as _fallback_format_hits,
    _normalize_name as _fallback_normalize_name,
    _static_fallback as _fallback_static_fallback,
    _strip_optional_followup_invitation as _fallback_strip_optional_followup_invitation,
)
from .writer_agent_fallback_state_mixin import WriterAgentFallbackStateMixin
from .writer_agent_lifecycle_mixin import WriterAgentLifecycleMixin
from .writer_agent_call_llm_slice1 import _extract_call_llm_slice1_inputs
from .writer_agent_call_llm_slice2 import _extract_call_llm_slice2_request_detectors
from .writer_agent_call_llm_slice3 import _extract_call_llm_slice3_kb_payload_and_trace
from .writer_agent_call_llm_slice4 import (
    _extract_call_llm_slice4_policy_and_dialogue_state,
)
from .writer_agent_call_llm_slice5 import (
    _extract_call_llm_slice5_kb_payload_and_philosophy,
)
from .writer_agent_call_llm_slice6 import (
    _extract_call_llm_slice6_final_answer_directive_and_legacy,
)
from .writer_agent_call_llm_slice7 import (
    _extract_call_llm_slice7_fresh_chat_and_active_line,
)
from .writer_agent_call_llm_slice8 import (
    _extract_call_llm_slice8_response_planner_and_dialogue_pragmatics,
)
from .writer_agent_call_llm_slice9 import (
    _extract_call_llm_slice9_retrieval_human_like_and_final_shape,
)
from .writer_agent_call_llm_slice10 import (
    _apply_call_llm_slice10_prompt_constraint_and_debug_bookkeeping,
)
from .writer_agent_call_llm_slice11 import (
    _apply_call_llm_slice11_runtime_settings_and_system_prompt,
)
from .writer_agent_call_llm_slice12 import (
    _apply_call_llm_slice12_response_unpack_cost_and_bookkeeping,
)
from .writer_agent_prompts import (
    WRITER_USER_TEMPLATE,
)


logger = logging.getLogger(__name__)
_PRACTICE_MARKERS = (
    "практик",
    "упражн",
    "сделай шаг",
    "сделайте шаг",
    "сделайте один",
    "начни одно простое действие",
    "поставь таймер",
    "таймер",
    "60 секунд",
    "5 минут",
    "10 минут",
    "15 минут",
    "20 минут",
    "открой документ",
    "напиши заголовок",
    "положи руку",
    "ладонь",
    "грудь",
    "живот",
    "вдох",
    "выдох",
    "дыхани",
    "почувствуй тело",
    "почувствуй опору",
    "ступн",
    "опор",
    "сделай вдох",
    "сделай выдох",
)
_KNOWN_CONCEPT_CLARIFICATION_MARKERS = (
    "что ты вкладываешь",
    "что вы вкладываете",
    "о каком варианте",
    "какой вариант",
    "ты имеешь в виду",
    "вы имеете в виду",
)
_EXTERNAL_SURVEILLANCE_MARKERS = (
    "внешнее слежение",
    "биофидбек",
    "ээг",
    "нейроинтерфейс",
    "технический мониторинг",
    "цифровые следы",
    "отслеживание чужих нейроданных",
)
_LOW_RESOURCE_NO_PRACTICE_MARKERS = (
    "без анализа",
    "пару спокойных слов",
    "просто поддержи",
    "без советов",
    "я устал",
    "не нужны практики",
    "побудь со мной коротко",
)


class WriterAgent(WriterAgentLifecycleMixin, WriterAgentFallbackStateMixin):
    """Generates final user-facing response from WriterContract."""

    _PRACTICE_MARKERS = _PRACTICE_MARKERS

    def __init__(self, client: Optional[Any] = None, model: Optional[str] = None):
        self._client = client
        self._model_override = model
        self.last_debug: dict[str, Any] = {}

    def _resolve_model(self) -> str:
        return self._model_override or get_model_for_agent("writer")

    @staticmethod
    def _get_temperature_for_agent(agent_name: str) -> float:
        return get_temperature_for_agent(agent_name)

    async def _call_llm(
        self,
        contract: WriterContract,
        *,
        prompt_constraint_decision: dict[str, Any] | None = None,
    ) -> str:
        client = self._get_client()
        if client is None:
            raise RuntimeError("No LLM client available")

        ctx = contract.to_prompt_context()
        ctx.setdefault("active_line_version", "active_line_v1")
        ctx.setdefault("active_line_text", "")
        ctx.setdefault("active_line_user_intent", "unknown")
        ctx.setdefault("active_line_continuity_mode", "continue_existing_line")
        ctx.setdefault("active_line_next_meaningful_move", "")
        ctx.setdefault("active_line_should_continue_line", True)
        ctx.setdefault("active_line_should_ask_question", False)
        ctx.setdefault("active_line_should_offer_practice", False)
        ctx.setdefault("active_line_revoicing_allowed", False)
        ctx.setdefault("active_line_revoicing_style", "suppressed")
        ctx.setdefault("active_line_repair_mode", "")
        ctx.setdefault("active_line_practice_suppression_active", False)
        ctx.setdefault("response_planner_version", "response_planner_v1")
        ctx.setdefault("response_planner_enabled", False)
        ctx.setdefault("response_planner_next_move", "continue_active_line")
        ctx.setdefault("response_planner_answer_shape", "compact_direct")
        ctx.setdefault("response_planner_response_depth", "short")
        ctx.setdefault("response_planner_target_micro_shift", "")
        ctx.setdefault("response_planner_should_answer_directly", False)
        ctx.setdefault("response_planner_question_policy", "none")
        ctx.setdefault("response_planner_practice_policy", "forbidden")
        ctx.setdefault("response_planner_revoicing_policy", "suppressed")
        ctx.setdefault("response_planner_continuity_policy", "continue_active_line")
        ctx.setdefault("response_planner_safety_priority", False)
        ctx.setdefault("response_planner_confidence", 0.0)
        ctx.setdefault("response_planner_rationale", "")
        ctx.setdefault("response_planner_must_include", [])
        ctx.setdefault("response_planner_must_avoid", [])
        ctx.setdefault("dialogue_profile", "safe_guided")
        ctx.setdefault("profile_preset", "safe_guided")
        ctx.setdefault("unified_dialogue_policy_version", "unified_dialogue_policy_v2")
        ctx.setdefault("unified_active_profile_alias", "safe_guided")
        ctx.setdefault("unified_effective_writer_autonomy", "medium")
        ctx.setdefault("unified_effective_safety_floor", "minimal_baseline")
        ctx.setdefault("unified_legacy_blocks_visible_to_writer", False)
        ctx.setdefault("unified_legacy_blocks_source_signals_only", True)
        ctx.setdefault("unified_hard_boundaries_csv", "safety, crisis_routing")
        ctx.setdefault("unified_soft_guidance_csv", "state, thread, planner")
        ctx.setdefault("dialogue_act", "unknown")
        ctx.setdefault("dialogue_act_confidence", 0.0)
        ctx.setdefault("dialogue_act_evidence", "none")
        ctx.setdefault("last_assistant_offer_open", False)
        ctx.setdefault("last_assistant_offer_type", "none")
        ctx.setdefault("last_assistant_offer_summary", "none")
        ctx.setdefault("unanswered_question_answer_required", False)
        ctx.setdefault("unanswered_question_status", "answered")
        ctx.setdefault("unanswered_question_summary", "none")
        ctx.setdefault("dialogue_style_tone", "neutral")
        ctx.setdefault("dialogue_style_length_preference", "adaptive")
        ctx.setdefault("dialogue_style_complexity_preference", "normal")
        ctx.setdefault("dialogue_style_avoid_csv", "none")
        ctx.setdefault("answer_obligation", "continue_thread")
        ctx.setdefault("answer_obligation_shape", "structured_explanation")
        ctx.setdefault("answer_obligation_depth", "medium")
        ctx.setdefault("answer_obligation_question_policy", "optional_none")
        ctx.setdefault("answer_obligation_source", "none")
        ctx.setdefault("dialogue_expansion_requested", False)
        ctx.setdefault("dialogue_repair_and_expand_requested", False)
        ctx.setdefault("dialogue_active_concept", "")
        ctx.setdefault("dialogue_pragmatics", {})
        ctx.setdefault("dialogue_pragmatics_version", "dialogue_pragmatics_v1")
        ctx.setdefault("dialogue_pragmatics_short_utterance", False)
        ctx.setdefault("dialogue_pragmatics_short_type", "not_short")
        ctx.setdefault("dialogue_pragmatics_is_contextual_followup", False)
        ctx.setdefault("dialogue_pragmatics_offer_type", "unknown")
        ctx.setdefault("dialogue_pragmatics_inherited_intent", "continue_previous_offer")
        ctx.setdefault("dialogue_pragmatics_should_answer_directly", False)
        ctx.setdefault("dialogue_pragmatics_should_not_ask_confirmation_again", False)
        ctx.setdefault("dialogue_pragmatics_repair_user_dissatisfaction", False)
        ctx.setdefault("dialogue_pragmatics_reason", "none")
        ctx.setdefault("retrieval_decision", {})
        ctx.setdefault("retrieval_decision_version", "contextual_retrieval_gating_v1")
        ctx.setdefault("retrieval_action", "none")
        ctx.setdefault("retrieval_rag_candidates_count", 0)
        ctx.setdefault("retrieval_rag_included_count", 0)
        ctx.setdefault("retrieval_rag_included_reason", "")
        ctx.setdefault("retrieval_rag_suppressed_reason", "")
        ctx.setdefault("retrieval_writer_can_ignore_rag", True)
        ctx.setdefault("retrieval_rag_relevance", "unknown")
        ctx.setdefault("retrieval_inherited_topic", "")
        ctx.setdefault("retrieval_inherited_offer_type", "unknown")
        ctx.setdefault("final_answer_directive", {})
        ctx.setdefault("final_answer_directive_json", "{}")
        ctx.setdefault("writer_visible_final_answer_directive_json", "{}")
        ctx.setdefault("final_answer_directive_version", "final_answer_directive_v1")
        ctx.setdefault("final_answer_diagnostic_center_role", "guided_legacy")
        ctx.setdefault("final_answer_planner_role", "guided_legacy")
        ctx.setdefault("final_answer_active_line_role", "guided_legacy")
        ctx.setdefault("final_answer_diagnostic_card_role", "guided_legacy")
        ctx.setdefault("legacy_constraints_suppressed", [])
        ctx.setdefault("legacy_constraints_suppressed_csv", "none")
        ctx.setdefault("writer_first_prompt_assembly_enabled", False)
        ctx.setdefault("legacy_blocks_visible_to_writer", True)
        ctx.setdefault("legacy_blocks_source_signals_only", False)
        ctx.setdefault("writer_visible_advisory_summary", "")
        ctx.setdefault("writer_visible_practice_instruction", "")
        ctx.setdefault("writer_visible_practice_note", "")
        ctx.setdefault("writer_grounding_visibility_v1", {})
        ctx.setdefault("writer_grounding_visibility_json", "{}")
        ctx.setdefault("writer_grounding_authority_note", "")
        ctx.setdefault("practice_rewrite_applied", False)
        ctx.setdefault("legacy_advisory_sanitization", {})
        ctx.setdefault("writer_kb_payload_enabled", False)
        ctx.setdefault("writer_kb_payload_failed", False)
        ctx.setdefault("writer_kb_payload_failure_reason", "")
        ctx.setdefault("writer_kb_payload", {})
        ctx.setdefault("writer_kb_payload_trace", {})
        ctx.setdefault("writer_kb_payload_trace_version", "writer_kb_payload_trace_v1")
        ctx.setdefault("writer_kb_payload_future_graduation_notes", {})
        slice1_inputs = _extract_call_llm_slice1_inputs(ctx)
        knowledge_answer = slice1_inputs.knowledge_answer
        knowledge_answer_first = slice1_inputs.knowledge_answer_first
        do_not_ask_definition = slice1_inputs.do_not_ask_definition
        practice_allowed = slice1_inputs.practice_allowed
        practice_ban_instruction = slice1_inputs.practice_ban_instruction
        known_concept_clarification_ban = slice1_inputs.known_concept_clarification_ban
        external_surveillance_frame_ban = slice1_inputs.external_surveillance_frame_ban
        philosophy_kernel = slice1_inputs.philosophy_kernel
        writer_freedom_contract = slice1_inputs.writer_freedom_contract
        selected_lenses = slice1_inputs.selected_lenses
        freedom_hard_boundaries = slice1_inputs.freedom_hard_boundaries
        dialogue_policy_payload = slice1_inputs.dialogue_policy_payload
        human_like_answer_policy = slice1_inputs.human_like_answer_policy
        constraint_resolution = slice1_inputs.constraint_resolution
        user_message = slice1_inputs.user_message
        dialogue_profile = slice1_inputs.dialogue_profile
        context_budget_chars = slice1_inputs.context_budget_chars
        formatted_context = slice1_inputs.formatted_context
        context_meta = slice1_inputs.context_meta

        slice2_inputs = _extract_call_llm_slice2_request_detectors(
            dialogue_policy_payload=dialogue_policy_payload,
            user_message=user_message,
            constraint_resolution=constraint_resolution,
            dialogue_profile=dialogue_profile,
        )
        explicit_answer_need = slice2_inputs.explicit_answer_need
        sarcasm_or_negative_feedback = slice2_inputs.sarcasm_or_negative_feedback
        repair_user_dissatisfaction = slice2_inputs.repair_user_dissatisfaction
        overruled_constraints = slice2_inputs.overruled_constraints
        mvp_override_block = slice2_inputs.mvp_override_block

        slice3_inputs = _extract_call_llm_slice3_kb_payload_and_trace(ctx)
        writer_kb_payload_text = slice3_inputs.writer_kb_payload_text
        self.last_debug.update(slice3_inputs.last_debug_patch)
        slice4_inputs = _extract_call_llm_slice4_policy_and_dialogue_state(
            ctx,
            context_meta,
            dialogue_profile,
        )
        slice5_inputs = _extract_call_llm_slice5_kb_payload_and_philosophy(
            ctx,
            knowledge_answer,
            knowledge_answer_first,
            do_not_ask_definition,
            practice_allowed,
            philosophy_kernel,
            writer_freedom_contract,
            selected_lenses,
            freedom_hard_boundaries,
        )
        slice6_inputs = _extract_call_llm_slice6_final_answer_directive_and_legacy(
            ctx
        )
        slice7_inputs = _extract_call_llm_slice7_fresh_chat_and_active_line(ctx)
        slice8_inputs = (
            _extract_call_llm_slice8_response_planner_and_dialogue_pragmatics(ctx)
        )
        slice9_inputs = _extract_call_llm_slice9_retrieval_human_like_and_final_shape(
            ctx,
            human_like_answer_policy=human_like_answer_policy,
            repair_user_dissatisfaction=repair_user_dissatisfaction,
            constraint_resolution=constraint_resolution,
            dialogue_profile=dialogue_profile,
            overruled_constraints=overruled_constraints,
        )

        user_prompt = WRITER_USER_TEMPLATE.format(
            user_message=ctx["user_message"],
            response_mode=ctx["response_mode"],
            response_goal=ctx["response_goal"] or "нет",
            phase=ctx["phase"],
            nervous_state=ctx["nervous_state"],
            ok_position=ctx["ok_position"],
            openness=ctx["openness"],
            safety_active=ctx["safety_active"],
            open_loops=", ".join(ctx["open_loops"]) or "нет",
            must_avoid=", ".join(ctx["must_avoid"]) or "нет",
            unified_dialogue_policy_version=slice4_inputs.unified_dialogue_policy_version,
            unified_active_profile_alias=slice4_inputs.unified_active_profile_alias,
            profile_preset=slice4_inputs.profile_preset,
            unified_effective_writer_autonomy=slice4_inputs.unified_effective_writer_autonomy,
            unified_effective_safety_floor=slice4_inputs.unified_effective_safety_floor,
            unified_legacy_blocks_visible_to_writer=slice4_inputs.unified_legacy_blocks_visible_to_writer,
            unified_legacy_blocks_source_signals_only=slice4_inputs.unified_legacy_blocks_source_signals_only,
            unified_hard_boundaries_csv=slice4_inputs.unified_hard_boundaries_csv,
            unified_soft_guidance_csv=slice4_inputs.unified_soft_guidance_csv,
            dialogue_act=slice4_inputs.dialogue_act,
            dialogue_act_confidence=slice4_inputs.dialogue_act_confidence,
            dialogue_act_evidence=slice4_inputs.dialogue_act_evidence,
            last_assistant_offer_open=slice4_inputs.last_assistant_offer_open,
            last_assistant_offer_type=slice4_inputs.last_assistant_offer_type,
            last_assistant_offer_summary=slice4_inputs.last_assistant_offer_summary,
            unanswered_question_answer_required=slice4_inputs.unanswered_question_answer_required,
            unanswered_question_status=slice4_inputs.unanswered_question_status,
            unanswered_question_summary=slice4_inputs.unanswered_question_summary,
            dialogue_style_tone=slice4_inputs.dialogue_style_tone,
            dialogue_style_length_preference=slice4_inputs.dialogue_style_length_preference,
            dialogue_style_complexity_preference=slice4_inputs.dialogue_style_complexity_preference,
            dialogue_style_avoid_csv=slice4_inputs.dialogue_style_avoid_csv,
            answer_obligation=slice4_inputs.answer_obligation,
            answer_obligation_shape=slice4_inputs.answer_obligation_shape,
            answer_obligation_depth=slice4_inputs.answer_obligation_depth,
            answer_obligation_question_policy=slice4_inputs.answer_obligation_question_policy,
            answer_obligation_source=slice4_inputs.answer_obligation_source,
            diagnostic_card_summary=slice4_inputs.diagnostic_card_summary,
            diagnostic_card_avoid=slice4_inputs.diagnostic_card_avoid,
            diagnostic_card_risk_flags=slice4_inputs.diagnostic_card_risk_flags,
            writer_move_instruction_summary=slice4_inputs.writer_move_instruction_summary,
            writer_move_must_do=slice4_inputs.writer_move_must_do,
            writer_move_must_not_do=slice4_inputs.writer_move_must_not_do,
            conversation_context=formatted_context,
            context_budget_chars=slice4_inputs.context_budget_chars,
            context_truncated=slice4_inputs.context_truncated,
            preserved_recent_turns_count=slice4_inputs.preserved_recent_turns_count,
            older_context_omitted_chars=slice4_inputs.older_context_omitted_chars,
            user_profile_patterns=slice4_inputs.user_profile_patterns,
            user_profile_values=slice4_inputs.user_profile_values,
            writer_kb_payload_enabled=slice5_inputs.writer_kb_payload_enabled,
            writer_kb_payload_trace_version=slice5_inputs.writer_kb_payload_trace_version,
            writer_kb_payload_failed=slice5_inputs.writer_kb_payload_failed,
            writer_kb_payload_text=writer_kb_payload_text,
            knowledge_answer_needed=slice5_inputs.knowledge_answer_needed,
            knowledge_answer_concept=slice5_inputs.knowledge_answer_concept,
            knowledge_answer_kb_grounding=slice5_inputs.knowledge_answer_kb_grounding,
            knowledge_answer_first=slice5_inputs.knowledge_answer_first,
            do_not_ask_user_to_define_term_before_answering=slice5_inputs.do_not_ask_user_to_define_term_before_answering,
            practice_allowed=slice5_inputs.practice_allowed,
            knowledge_answer_writer_instruction=slice5_inputs.knowledge_answer_writer_instruction,
            practice_ban_instruction=practice_ban_instruction,
            known_concept_clarification_ban=known_concept_clarification_ban,
            external_surveillance_frame_ban=external_surveillance_frame_ban,
            philosophy_kernel_version=slice5_inputs.philosophy_kernel_version,
            philosophy_kernel_quote_policy=slice5_inputs.philosophy_kernel_quote_policy,
            philosophy_kernel_selected_lenses=slice5_inputs.philosophy_kernel_selected_lenses,
            philosophy_kernel_prompt_block=slice5_inputs.philosophy_kernel_prompt_block,
            philosophy_kernel_prompt_compactness=slice5_inputs.philosophy_kernel_prompt_compactness,
            writer_freedom_prompt_block=slice5_inputs.writer_freedom_prompt_block,
            writer_freedom_contract_version=slice5_inputs.writer_freedom_contract_version,
            writer_freedom_level=slice5_inputs.writer_freedom_level,
            writer_mode_hint=slice5_inputs.writer_mode_hint,
            mode_is_hint_not_cage=slice5_inputs.mode_is_hint_not_cage,
            writer_question_limit=slice5_inputs.writer_question_limit,
            practice_requires_gate=slice5_inputs.practice_requires_gate,
            writer_freedom_hard_boundaries=slice5_inputs.writer_freedom_hard_boundaries,
            final_answer_directive_json=slice6_inputs.final_answer_directive_json,
            writer_visible_final_answer_directive_json=slice6_inputs.writer_visible_final_answer_directive_json,
            final_answer_directive_version=slice6_inputs.final_answer_directive_version,
            final_answer_current_user_request=slice6_inputs.final_answer_current_user_request,
            final_answer_must_answer_source=slice6_inputs.final_answer_must_answer_source,
            final_answer_previous_must_answer_demoted=slice6_inputs.final_answer_previous_must_answer_demoted,
            final_answer_previous_must_answer=slice6_inputs.final_answer_previous_must_answer,
            final_answer_explicit_continue_previous_detected=slice6_inputs.final_answer_explicit_continue_previous_detected,
            final_answer_answer_target=slice6_inputs.final_answer_answer_target,
            final_answer_writer_contact_mode=slice6_inputs.final_answer_writer_contact_mode,
            final_answer_diagnostic_center_role=slice6_inputs.final_answer_diagnostic_center_role,
            final_answer_planner_role=slice6_inputs.final_answer_planner_role,
            final_answer_active_line_role=slice6_inputs.final_answer_active_line_role,
            final_answer_diagnostic_card_role=slice6_inputs.final_answer_diagnostic_card_role,
            writer_first_prompt_assembly_enabled=slice6_inputs.writer_first_prompt_assembly_enabled,
            legacy_blocks_visible_to_writer=slice6_inputs.legacy_blocks_visible_to_writer,
            legacy_blocks_source_signals_only=slice6_inputs.legacy_blocks_source_signals_only,
            legacy_constraints_suppressed_csv=slice6_inputs.legacy_constraints_suppressed_csv,
            writer_visible_advisory_summary=slice6_inputs.writer_visible_advisory_summary,
            writer_visible_practice_note=slice6_inputs.writer_visible_practice_note,
            writer_grounding_authority_note=slice6_inputs.writer_grounding_authority_note,
            writer_grounding_visibility_json=slice6_inputs.writer_grounding_visibility_json,
            fresh_chat_context_policy_version=slice7_inputs.fresh_chat_context_policy_version,
            fresh_chat_is_new_chat=slice7_inputs.fresh_chat_is_new_chat,
            fresh_chat_turn_index=slice7_inputs.fresh_chat_turn_index,
            fresh_chat_is_greeting_or_contact=slice7_inputs.fresh_chat_is_greeting_or_contact,
            fresh_chat_cross_session_memory_allowed=slice7_inputs.fresh_chat_cross_session_memory_allowed,
            fresh_chat_cross_session_memory_reason=slice7_inputs.fresh_chat_cross_session_memory_reason,
            fresh_chat_active_context_source=slice7_inputs.fresh_chat_active_context_source,
            writer_context_package_version=slice7_inputs.writer_context_package_version,
            writer_context_recent_turns_count=slice7_inputs.writer_context_recent_turns_count,
            writer_context_profile_present=slice7_inputs.writer_context_profile_present,
            writer_context_rag_candidates_count=slice7_inputs.writer_context_rag_candidates_count,
            writer_context_rag_for_writer_count=slice7_inputs.writer_context_rag_for_writer_count,
            practice_rewrite_applied=slice7_inputs.practice_rewrite_applied,
            active_line_version=slice7_inputs.active_line_version,
            active_line_text=slice7_inputs.active_line_text,
            active_line_user_intent=slice7_inputs.active_line_user_intent,
            active_line_continuity_mode=slice7_inputs.active_line_continuity_mode,
            active_line_next_meaningful_move=slice7_inputs.active_line_next_meaningful_move,
            active_line_should_continue_line=slice7_inputs.active_line_should_continue_line,
            active_line_should_ask_question=slice7_inputs.active_line_should_ask_question,
            active_line_should_offer_practice=slice7_inputs.active_line_should_offer_practice,
            active_line_revoicing_allowed=slice7_inputs.active_line_revoicing_allowed,
            active_line_revoicing_style=slice7_inputs.active_line_revoicing_style,
            active_line_repair_mode=slice7_inputs.active_line_repair_mode,
            active_line_practice_suppression_active=slice7_inputs.active_line_practice_suppression_active,
            response_planner_version=slice8_inputs.response_planner_version,
            response_planner_enabled=slice8_inputs.response_planner_enabled,
            response_planner_next_move=slice8_inputs.response_planner_next_move,
            response_planner_answer_shape=slice8_inputs.response_planner_answer_shape,
            response_planner_response_depth=slice8_inputs.response_planner_response_depth,
            response_planner_target_micro_shift=slice8_inputs.response_planner_target_micro_shift,
            response_planner_should_answer_directly=slice8_inputs.response_planner_should_answer_directly,
            response_planner_question_policy=slice8_inputs.response_planner_question_policy,
            response_planner_practice_policy=slice8_inputs.response_planner_practice_policy,
            response_planner_revoicing_policy=slice8_inputs.response_planner_revoicing_policy,
            response_planner_continuity_policy=slice8_inputs.response_planner_continuity_policy,
            response_planner_safety_priority=slice8_inputs.response_planner_safety_priority,
            response_planner_must_include=slice8_inputs.response_planner_must_include,
            response_planner_must_avoid=slice8_inputs.response_planner_must_avoid,
            response_planner_confidence=slice8_inputs.response_planner_confidence,
            response_planner_rationale=slice8_inputs.response_planner_rationale,
            dialogue_profile=slice8_inputs.dialogue_profile,
            dialogue_expansion_requested=slice8_inputs.dialogue_expansion_requested,
            dialogue_repair_and_expand_requested=slice8_inputs.dialogue_repair_and_expand_requested,
            dialogue_active_concept=slice8_inputs.dialogue_active_concept,
            dialogue_pragmatics_version=slice8_inputs.dialogue_pragmatics_version,
            dialogue_pragmatics_short_utterance=slice8_inputs.dialogue_pragmatics_short_utterance,
            dialogue_pragmatics_short_type=slice8_inputs.dialogue_pragmatics_short_type,
            dialogue_pragmatics_is_contextual_followup=slice8_inputs.dialogue_pragmatics_is_contextual_followup,
            dialogue_pragmatics_offer_type=slice8_inputs.dialogue_pragmatics_offer_type,
            dialogue_pragmatics_inherited_intent=slice8_inputs.dialogue_pragmatics_inherited_intent,
            dialogue_pragmatics_should_answer_directly=slice8_inputs.dialogue_pragmatics_should_answer_directly,
            dialogue_pragmatics_should_not_ask_confirmation_again=slice8_inputs.dialogue_pragmatics_should_not_ask_confirmation_again,
            dialogue_pragmatics_repair_user_dissatisfaction=slice8_inputs.dialogue_pragmatics_repair_user_dissatisfaction,
            dialogue_pragmatics_reason=slice8_inputs.dialogue_pragmatics_reason,
            retrieval_decision_version=slice9_inputs.retrieval_decision_version,
            retrieval_action=slice9_inputs.retrieval_action,
            retrieval_rag_candidates_count=slice9_inputs.retrieval_rag_candidates_count,
            retrieval_rag_included_count=slice9_inputs.retrieval_rag_included_count,
            retrieval_rag_included_reason=slice9_inputs.retrieval_rag_included_reason,
            retrieval_rag_suppressed_reason=slice9_inputs.retrieval_rag_suppressed_reason,
            retrieval_writer_can_ignore_rag=slice9_inputs.retrieval_writer_can_ignore_rag,
            retrieval_rag_relevance=slice9_inputs.retrieval_rag_relevance,
            retrieval_inherited_topic=slice9_inputs.retrieval_inherited_topic,
            retrieval_inherited_offer_type=slice9_inputs.retrieval_inherited_offer_type,
            human_like_enabled=slice9_inputs.human_like_enabled,
            human_like_answer_style=slice9_inputs.human_like_answer_style,
            human_like_default_depth=slice9_inputs.human_like_default_depth,
            human_like_question_is_optional=slice9_inputs.human_like_question_is_optional,
            human_like_do_not_force_question=slice9_inputs.human_like_do_not_force_question,
            human_like_do_not_force_practice=slice9_inputs.human_like_do_not_force_practice,
            human_like_flexible_length_allowed=slice9_inputs.human_like_flexible_length_allowed,
            human_like_respect_user_requested_format=slice9_inputs.human_like_respect_user_requested_format,
            human_like_repair_user_dissatisfaction=slice9_inputs.human_like_repair_user_dissatisfaction,
            human_like_direct_answer_repair=slice9_inputs.human_like_direct_answer_repair,
            human_like_support_answer_compactness=slice9_inputs.human_like_support_answer_compactness,
            human_like_preferred_shape=slice9_inputs.human_like_preferred_shape,
            human_like_target_length_chars=slice9_inputs.human_like_target_length_chars,
            human_like_avoid_mechanism_heavy_default=slice9_inputs.human_like_avoid_mechanism_heavy_default,
            human_like_prefer_direct_answer_first=slice9_inputs.human_like_prefer_direct_answer_first,
            human_like_prefer_single_main_mechanism=slice9_inputs.human_like_prefer_single_main_mechanism,
            human_like_max_list_items=slice9_inputs.human_like_max_list_items,
            final_answer_shape_profile=slice9_inputs.final_answer_shape_profile,
            final_answer_shape_profile_notes_block=slice9_inputs.final_answer_shape_profile_notes_block,
            constraint_resolution_profile=slice9_inputs.constraint_resolution_profile,
            constraint_resolution_planner_authority=slice9_inputs.constraint_resolution_planner_authority,
            constraint_resolution_overruled=slice9_inputs.constraint_resolution_overruled,
            constraint_resolution_reason=slice9_inputs.constraint_resolution_reason,
            mvp_free_dialogue_overrides=mvp_override_block,
        )
        slice10_result = _apply_call_llm_slice10_prompt_constraint_and_debug_bookkeeping(
            ctx,
            user_prompt=user_prompt,
            prompt_constraint_decision=prompt_constraint_decision,
            context_meta=context_meta,
            human_like_answer_policy=human_like_answer_policy,
            explicit_answer_need=explicit_answer_need,
            repair_user_dissatisfaction=repair_user_dissatisfaction,
            sarcasm_or_negative_feedback=sarcasm_or_negative_feedback,
            overruled_constraints=overruled_constraints,
        )
        user_prompt = slice10_result.user_prompt
        self.last_debug.update(slice10_result.last_debug_patch)

        start_ts = time.perf_counter()
        slice11_result = _apply_call_llm_slice11_runtime_settings_and_system_prompt(
            ctx,
            dialogue_profile=dialogue_profile,
            resolve_runtime_settings=self._resolve_runtime_settings,
        )
        dialogue_profile = slice11_result.dialogue_profile
        runtime_settings = slice11_result.runtime_settings
        system_prompt = slice11_result.system_prompt
        self.last_debug.update(slice11_result.last_debug_patch)
        result = await create_agent_completion(
            client=client,
            model=runtime_settings["model"],
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=runtime_settings["temperature"],
            max_tokens=runtime_settings["max_tokens"],
            timeout=runtime_settings["timeout"],
        )
        slice12_result = _apply_call_llm_slice12_response_unpack_cost_and_bookkeeping(
            result=result,
            runtime_settings=runtime_settings,
            start_ts=start_ts,
            estimate_cost=self._estimate_cost,
        )
        llm_response = slice12_result.llm_response
        self.last_debug.update(slice12_result.last_debug_patch)
        return llm_response

    def _enforce_answer_compliance(self, response_text: str, contract: WriterContract) -> str:
        text = str(response_text or "").strip()
        if not text:
            return text

        slice1_prelude = _extract_enforce_slice1_prelude(contract, text=text)
        ctx = slice1_prelude.ctx
        user_message = slice1_prelude.user_message
        lowered_user = slice1_prelude.lowered_user
        literal_markdown_echo = slice1_prelude.literal_markdown_echo
        dialogue_profile = slice1_prelude.dialogue_profile
        expansion_requested = slice1_prelude.expansion_requested
        repair_and_expand_requested = slice1_prelude.repair_and_expand_requested
        knowledge_answer = slice1_prelude.knowledge_answer
        practice_gate = slice1_prelude.practice_gate
        practice_allowed = slice1_prelude.practice_allowed
        should_answer_directly = slice1_prelude.should_answer_directly
        is_greeting = slice1_prelude.is_greeting
        concept = slice1_prelude.concept
        active_line = slice1_prelude.active_line
        active_line_intent = slice1_prelude.active_line_intent
        active_line_repair_mode = slice1_prelude.active_line_repair_mode
        active_line_revoicing_allowed = slice1_prelude.active_line_revoicing_allowed
        active_line_should_offer_practice = slice1_prelude.active_line_should_offer_practice
        active_line_practice_suppression = slice1_prelude.active_line_practice_suppression
        response_planner = slice1_prelude.response_planner
        planner_next_move = slice1_prelude.planner_next_move
        planner_answer_shape = slice1_prelude.planner_answer_shape
        planner_question_policy = slice1_prelude.planner_question_policy
        planner_practice_policy = slice1_prelude.planner_practice_policy
        planner_safety_priority = slice1_prelude.planner_safety_priority
        dialogue_policy_payload = slice1_prelude.dialogue_policy_payload
        dialogue_pragmatics_payload = slice1_prelude.dialogue_pragmatics_payload
        explicit_answer_need = slice1_prelude.explicit_answer_need
        direct_concrete_request = slice1_prelude.direct_concrete_request
        summary_request = slice1_prelude.summary_request
        sarcasm_or_negative_feedback = slice1_prelude.sarcasm_or_negative_feedback
        application_request = slice1_prelude.application_request
        human_like_answer_policy = slice1_prelude.human_like_answer_policy
        constraint_resolution = slice1_prelude.constraint_resolution
        practice_overview_requested = slice1_prelude.practice_overview_requested
        pragmatics_contextual_followup = slice1_prelude.pragmatics_contextual_followup
        pragmatics_offer_type = slice1_prelude.pragmatics_offer_type
        pragmatics_should_not_reconfirm = slice1_prelude.pragmatics_should_not_reconfirm
        pragmatics_repair_dissatisfaction = slice1_prelude.pragmatics_repair_dissatisfaction
        lowered_text = slice1_prelude.lowered_text
        final_answer_directive = slice1_prelude.final_answer_directive
        writer_contact_mode = slice1_prelude.writer_contact_mode
        gate_feedback = slice1_prelude.gate_feedback
        gate_failed_checks = slice1_prelude.gate_failed_checks
        self.last_debug.update(slice1_prelude.last_debug_patch)
        if (
            "greeting_answered_with_mechanism_explanation" in gate_failed_checks
            and _contains_any(lowered_user, ("здравств", "привет", "добрый день", "добрый вечер"))
        ):
            return self._repair_greeting_without_mechanism_lecture(user_message=user_message)
        slice2_result = _extract_enforce_slice2_second_prelude_and_close_gently(
            ctx,
            text=text,
            lowered_user=lowered_user,
            lowered_text=lowered_text,
            planner_question_policy=planner_question_policy,
            planner_practice_policy=planner_practice_policy,
            planner_answer_shape=planner_answer_shape,
            writer_contact_mode=writer_contact_mode,
            direct_concrete_request=direct_concrete_request,
            application_request=application_request,
            explicit_answer_need=explicit_answer_need,
            user_message=user_message,
            practice_markers=_PRACTICE_MARKERS,
            known_concept_clarification_markers=_KNOWN_CONCEPT_CLARIFICATION_MARKERS,
            external_surveillance_markers=_EXTERNAL_SURVEILLANCE_MARKERS,
        )
        self.last_debug.update(slice2_result.last_debug_patch)
        if slice2_result.close_gently_triggered:
            self._set_final_answer_shape_debug("gentle_close")
            return self._build_gentle_close_reply()
        answer_obligation = slice2_result.answer_obligation
        last_direct_question = slice2_result.last_direct_question
        last_offer_summary = slice2_result.last_offer_summary
        offer_repair_context = slice2_result.offer_repair_context
        concept_question = slice2_result.concept_question
        has_unsolicited_practice = slice2_result.has_unsolicited_practice
        has_question = slice2_result.has_question
        asks_define_known_term = slice2_result.asks_define_known_term
        has_external_surveillance_frame = slice2_result.has_external_surveillance_frame
        user_requests_no_question = slice2_result.user_requests_no_question
        user_requests_no_practice = slice2_result.user_requests_no_practice
        user_repair_signal = slice2_result.user_repair_signal
        user_step_request = slice2_result.user_step_request
        canned_step_disallowed = slice2_result.canned_step_disallowed
        user_mechanism_request = slice2_result.user_mechanism_request
        answer_fit = slice2_result.answer_fit

        if answer_obligation == "provide_one_bounded_practice":
            practice_anchor_present = _contains_any(
                lowered_text,
                ("будь сильным", "драйвер", "сильн", "напряж", "сдерж"),
            )
            practice_step_present = _contains_any(
                lowered_text,
                ("сделай", "заметь", "отметь", "поймай", "назови", "остановись", "выдох"),
            )
            practice_multistep = len(re.findall(r"(?m)^\s*(?:[-*•]|\d+[.)])\s+", text)) > 1
            if (
                "?" in text
                or len(text.strip()) > 900
                or practice_multistep
                or not practice_step_present
                or not practice_anchor_present
            ):
                if "будь сильным" in lowered_user:
                    self._set_final_answer_shape_debug("one_short_practice")
                    return (
                        "Одна короткая практика: в момент, когда включается «Будь сильным», "
                        "заметь, где тело напрягается, и тихо назови про себя: "
                        "«сейчас я снова держусь через силу». На этом остановись, ничего не исправляя."
                    )
                return self._defer_no_stub_repair(
                    signal="bounded_practice_repair",
                    text=text,
                    must_answer=user_message,
                )
            self._set_final_answer_shape_debug("one_short_practice")
            return self._strip_optional_followup_invitation(text) or text

        if literal_markdown_echo:
            normalized_requested = literal_markdown_echo.strip()
            normalized_response = text.strip()
            if normalized_response != normalized_requested:
                self.last_debug["format_request_repair_applied"] = True
                self.last_debug["final_answer_shape"] = "literal_markdown_echo"
                return normalized_requested

        if answer_obligation == "acknowledge_style_preference_then_answer" and (
            "расскажи больше" in lowered_text or len(text) < 140
        ):
            if concept_question:
                return self._defer_no_stub_repair(
                    signal="style_preference_direct_answer_repair",
                    text=text,
                    must_answer="known_concept_question",
                )

        if answer_obligation == "repair_and_answer_last_question" and (
            "сейчас полезнее прямое объяснение механизма" in lowered_text or len(text) < 180
        ):
            target = last_direct_question or user_message
            if "нейросталкинг" in target.lower():
                return self._defer_no_stub_repair(
                    signal="repair_answer_last_question_repair",
                    text=text,
                    must_answer=target,
                )

        if answer_obligation == "answer_last_offer" and (
            any(marker in lowered_text for marker in ("подтверди", "если хочешь", "могу так сделать"))
            or any(marker in lowered_text for marker in ("предлагаю такой план", "хотите, чтобы", "сначала"))
            or "после подтверждения" in lowered_text
            or ("могу так сделать" in last_offer_summary.lower() and len(text) < 500)
            or (
                any(color in offer_repair_context for color in ("красн", "оранж", "зелен"))
                and not all(color in lowered_text for color in ("красн", "оранж", "зелен"))
            )
        ):
            if any(color in offer_repair_context for color in ("красн", "оранж", "зелен")):
                return self._defer_no_stub_repair(
                    signal="answer_last_offer_repair",
                    text=text,
                    must_answer=last_offer_summary or last_direct_question or "last_assistant_offer",
                )

        if answer_obligation in {"answer_knowledge_question", "answer_direct_question"} and (
            "сейчас полезнее прямое объяснение механизма" in lowered_text or len(text) < 140
        ):
            if concept_question:
                return self._defer_no_stub_repair(
                    signal="knowledge_direct_answer_repair",
                    text=text,
                    must_answer="known_concept_question",
                )

        if dialogue_profile == DIALOGUE_PROFILE_MVP_FREE:
            return self._enforce_mvp_free_dialogue_compliance(
                text=text,
                user_message=user_message,
                lowered_text=lowered_text,
                lowered_user=lowered_user,
                concept=concept,
                should_answer_directly=should_answer_directly,
                planner_next_move=planner_next_move,
                planner_answer_shape=planner_answer_shape,
                planner_question_policy=planner_question_policy,
                planner_practice_policy=planner_practice_policy,
                planner_safety_priority=planner_safety_priority,
                has_unsolicited_practice=has_unsolicited_practice,
                has_question=has_question,
                asks_define_known_term=asks_define_known_term,
                has_external_surveillance_frame=has_external_surveillance_frame,
                user_step_request=user_step_request,
                expansion_requested=expansion_requested,
                repair_and_expand_requested=repair_and_expand_requested,
                user_repair_signal=user_repair_signal,
                active_line_intent=active_line_intent,
                practice_overview_requested=practice_overview_requested,
                explicit_answer_need=explicit_answer_need,
                direct_concrete_request=direct_concrete_request,
                summary_request=summary_request,
                sarcasm_or_negative_feedback=sarcasm_or_negative_feedback,
                application_request=application_request,
                pragmatics_contextual_followup=pragmatics_contextual_followup,
                pragmatics_offer_type=pragmatics_offer_type,
                pragmatics_should_not_reconfirm=pragmatics_should_not_reconfirm,
                pragmatics_repair_dissatisfaction=pragmatics_repair_dissatisfaction,
                answer_obligation=answer_obligation,
                last_offer_summary=last_offer_summary,
                last_direct_question=last_direct_question,
                answer_fit=answer_fit,
                canned_step_disallowed=canned_step_disallowed,
            )

        # Greeting path: remove unsolicited practice when gate forbids it.
        if not practice_allowed and not should_answer_directly and (is_greeting or has_unsolicited_practice):
            return (
                "Привет. Рад знакомству. "
                "Можем спокойно начать: принеси любой вопрос или тему, которую хочешь разобрать."
            )

        # Low-resource contact: keep response short and do not insert practice instructions.
        if _contains_any(lowered_user, _LOW_RESOURCE_NO_PRACTICE_MARKERS):
            if has_unsolicited_practice or len(text) > 280 or "?" in text:
                return "Я рядом. Сейчас не нужно ничего разбирать. Можно просто немного снизить внутреннее давление."

        if active_line_intent == "thanks_close" and (
            has_unsolicited_practice
            or _contains_any(lowered_text, ("шаг", "давай сделаем", "предложу еще"))
        ):
            return "Пожалуйста. Рад, что стало чуть яснее."

        if planner_safety_priority and has_question:
            return "Я рядом. Сейчас важнее чуть стабилизироваться и снизить внутреннюю перегрузку."

        if planner_next_move == "give_short_support" or planner_answer_shape == "short_support":
            return "Я рядом. Сейчас не нужно ничего разбирать. Можно просто немного снизить внутреннее давление."

        if planner_next_move == "give_short_support" and (len(text) > 260 or has_question or has_unsolicited_practice):
            return "Я рядом. Сейчас не нужно всё разбирать. Можно просто немного снизить внутреннее давление."

        if planner_next_move == "stabilize_safety" and (len(text) > 320 or has_question):
            return "Я рядом. Сейчас важнее короткая опора здесь-и-сейчас, без перегруза."

        if planner_next_move == "stabilize_safety" and _contains_any(
            lowered_text,
            ("механизм", "прогнозирован", "контрол", "паттерн", "драйвер", "до начала действия"),
        ):
            return "Я рядом. Сейчас важнее чуть стабилизироваться и снизить внутреннюю перегрузку. Без разбора, только опора здесь-и-сейчас."

        if planner_next_move == "close_gently" and (
            has_question
            or has_unsolicited_practice
            or _contains_any(lowered_text, ("новый шаг", "давай продолжим", "в следующий раз разберем"))
        ):
            return "Пожалуйста. Рад, что стало чуть яснее."

        if planner_next_move == "give_short_support" and _contains_any(
            lowered_text,
            ("механизм", "теория", "стратегия", "прогнозирован", "контрол", "паттерн"),
        ):
            return "Я рядом. Сейчас не нужно ничего разбирать. Можно просто немного снизить внутреннее давление."

        if planner_next_move == "clarify_one_point":
            question_count = text.count("?")
            if question_count == 0:
                return "Если выбрать один узел прямо сейчас, что больше всего сжимает тебя в этой ситуации?"
            if question_count > 1:
                first = text.split("?")[0].strip()
                return (first + "?").strip()
            if len(text) > 320:
                return "Похоже, это сильно выматывает. Если взять один конкретный эпизод, где это ощущается острее всего?"

        if user_repair_signal:
            return self._defer_no_stub_repair(
                signal="user_repair_signal",
                text=text,
                must_answer=user_message,
            )

        # Known concept answer-first path: enforce direct internal meaning framing
        # before generic question-policy rewrites.
        if should_answer_directly and (asks_define_known_term or has_external_surveillance_frame):
            if "самореализац" in lowered_user and ("коррелир" in lowered_user or "связан" in lowered_user):
                return self._defer_no_stub_repair(
                    signal="known_concept_correlation_repair",
                    text=text,
                    must_answer=user_message,
                )
            if concept == "нейросталкинг":
                return self._defer_no_stub_repair(
                    signal="known_concept_neurostalking_repair",
                    text=text,
                    must_answer=user_message,
                )
            if concept == "самореализация":
                return self._defer_no_stub_repair(
                    signal="known_concept_self_realization_repair",
                    text=text,
                    must_answer=user_message,
                )

        if planner_question_policy == "none" and has_question:
            if planner_next_move == "give_direct_step" or planner_answer_shape == "one_step":
                return self._resolve_one_step_or_no_practice_fallback(
                    text=text,
                    user_message=user_message,
                    lowered_user=lowered_user,
                    canned_step_disallowed=canned_step_disallowed,
                )
            if planner_next_move == "give_short_support" or planner_answer_shape == "short_support":
                return "Я рядом. Сейчас не нужно ничего разбирать. Можно просто немного снизить внутреннее давление."
            if planner_next_move == "stabilize_safety" or planner_answer_shape == "safety_grounding":
                return "Я рядом. Сейчас важнее чуть стабилизироваться и снизить внутреннюю перегрузку. Без разбора, только опора здесь-и-сейчас."
            if planner_next_move == "answer_known_concept":
                if "самореализац" in lowered_user and "нейросталкинг" in lowered_user:
                    return self._defer_no_stub_repair(
                        signal="known_concept_correlation_repair",
                        text=text,
                        must_answer=user_message,
                    )
                if "нейросталкинг" in lowered_user:
                    return self._defer_no_stub_repair(
                        signal="known_concept_neurostalking_repair",
                        text=text,
                        must_answer=user_message,
                    )
            return re.sub(r"\s*\?+\s*", ". ", text).strip()
        if planner_question_policy == "none" and _contains_any(
            lowered_text, ("что именно", "почему", "как ты", "можешь ли", "хочешь")
        ):
            if planner_next_move == "give_direct_step" or planner_answer_shape == "one_step":
                return self._resolve_one_step_or_no_practice_fallback(
                    text=text,
                    user_message=user_message,
                    lowered_user=lowered_user,
                    canned_step_disallowed=canned_step_disallowed,
                )
            if planner_next_move == "give_short_support":
                return "Я рядом. Сейчас не нужно ничего разбирать. Можно просто немного снизить внутреннее давление."
            if planner_next_move == "stabilize_safety":
                return "Я рядом. Сейчас важнее чуть стабилизироваться и снизить внутреннюю перегрузку. Без разбора, только опора здесь-и-сейчас."
            if planner_next_move == "close_gently":
                return "Пожалуйста. Рад, что стало чуть яснее."
            return "Я рядом. Продолжим спокойно и без лишней нагрузки."
        if planner_question_policy == "none":
            if planner_next_move == "give_direct_step" or planner_answer_shape == "one_step":
                return self._resolve_one_step_or_no_practice_fallback(
                    text=text,
                    user_message=user_message,
                    lowered_user=lowered_user,
                    canned_step_disallowed=canned_step_disallowed,
                )
            if planner_next_move == "deepen_mechanism" or planner_answer_shape == "mechanism_explanation":
                return self._defer_no_stub_repair(
                    signal="mechanism_explanation_repair",
                    text=text,
                    must_answer=user_message,
                )

        if planner_next_move == "repair_misalignment":
            has_repair_forbidden = _contains_any(lowered_text, ("практик", "упражн", "таймер", "шаг"))
            if has_question or has_repair_forbidden or len(text) > 480:
                return self._defer_no_stub_repair(
                    signal="repair_misalignment",
                    text=text,
                    must_answer=user_message,
                )

        if planner_practice_policy == "forbidden" and has_unsolicited_practice:
            self.last_debug["template_leakage_repair_deferred_to_gate"] = True
            self._set_final_answer_shape_debug("template_repair_deferred_to_gate")
            return self._strip_optional_followup_invitation(text) or text

        if (
            (planner_next_move == "deepen_mechanism" or user_mechanism_request)
            and (planner_question_policy == "none" or user_requests_no_question)
            and (len(text) > 700 or has_question or has_unsolicited_practice or user_requests_no_practice)
        ):
            return self._defer_no_stub_repair(
                signal="mechanism_explanation_repair",
                text=text,
                must_answer=user_message,
            )

        if planner_answer_shape == "one_step" or planner_next_move == "give_direct_step":
            return self._resolve_one_step_or_no_practice_fallback(
                text=text,
                user_message=user_message,
                lowered_user=lowered_user,
                canned_step_disallowed=canned_step_disallowed,
            )

        if planner_answer_shape == "one_step" or user_step_request or active_line_intent == "ask_for_direct_step":
            list_like = bool(re.search(r"(^|\n)\s*(?:[-*•]|\d+[.)])\s+", text))
            if list_like:
                first_item = re.search(r"(?:[-*•]|\d+[.)])\s+(.+)", text)
                if first_item:
                    return first_item.group(1).strip()
            sentence_parts = [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]
            if len(sentence_parts) > 2:
                return self._resolve_one_step_or_no_practice_fallback(
                    text=text,
                    user_message=user_message,
                    lowered_user=lowered_user,
                    canned_step_disallowed=canned_step_disallowed,
                )
            if planner_question_policy == "none" and _contains_any(
                lowered_text,
                (
                    "хочешь",
                    "хочется",
                    "можешь",
                    "уточни",
                    "попробу",
                    "какой",
                    "что выбрать",
                ),
            ):
                return self._resolve_one_step_or_no_practice_fallback(
                    text=text,
                    user_message=user_message,
                    lowered_user=lowered_user,
                    canned_step_disallowed=canned_step_disallowed,
                )
            has_step_marker = _contains_any(lowered_text, ("сделай", "начни", "открой", "выбери", "напиши", "шаг"))
            if not has_step_marker:
                return self._resolve_one_step_or_no_practice_fallback(
                    text=text,
                    user_message=user_message,
                    lowered_user=lowered_user,
                    canned_step_disallowed=canned_step_disallowed,
                )

        if active_line_practice_suppression and not active_line_should_offer_practice and has_unsolicited_practice:
            if planner_next_move == "stabilize_safety" or planner_answer_shape == "safety_grounding":
                return "Я рядом. Сейчас важнее чуть стабилизироваться и снизить внутреннюю перегрузку. Без разбора, только опора здесь-и-сейчас."
            if active_line_intent == "correction_of_bot" or active_line_repair_mode:
                return self._defer_no_stub_repair(
                    signal="active_line_correction_repair",
                    text=text,
                    must_answer=user_message,
                )
            if active_line_intent == "understand_mechanism":
                return self._defer_no_stub_repair(
                    signal="active_line_mechanism_repair",
                    text=text,
                    must_answer=user_message,
                )
            return self._defer_no_stub_repair(
                signal="practice_suppression_meaning_repair",
                text=text,
                must_answer=user_message,
            )

        if not active_line_revoicing_allowed and starts_with_mechanical_revoicing(text):
            if active_line_intent == "correction_of_bot" or active_line_repair_mode:
                return self._defer_no_stub_repair(
                    signal="active_line_revoicing_correction_repair",
                    text=text,
                    must_answer=user_message,
                )
            if active_line_intent == "understand_mechanism":
                return self._defer_no_stub_repair(
                    signal="active_line_revoicing_mechanism_repair",
                    text=text,
                    must_answer=user_message,
                )
            parts = re.split(r"(?<=[.!?])\s+", text, maxsplit=1)
            if len(parts) == 2 and parts[1].strip():
                return parts[1].strip()

        if planner_next_move == "answer_known_concept" and planner_practice_policy == "forbidden":
            if "самореализац" in lowered_user and "нейросталкинг" in lowered_user:
                return self._defer_no_stub_repair(
                    signal="known_concept_correlation_repair",
                    text=text,
                    must_answer=user_message,
                )
            if "нейросталкинг" in lowered_user:
                return self._defer_no_stub_repair(
                    signal="known_concept_neurostalking_repair",
                    text=text,
                    must_answer=user_message,
                )
            if "самореализац" in lowered_user:
                return self._defer_no_stub_repair(
                    signal="known_concept_self_realization_repair",
                    text=text,
                    must_answer=user_message,
                )
        return text

    def _enforce_mvp_free_dialogue_compliance(
        self,
        *,
        text: str,
        user_message: str,
        lowered_text: str,
        lowered_user: str,
        concept: str,
        should_answer_directly: bool,
        planner_next_move: str,
        planner_answer_shape: str,
        planner_question_policy: str,
        planner_practice_policy: str,
        planner_safety_priority: bool,
        has_unsolicited_practice: bool,
        has_question: bool,
        asks_define_known_term: bool,
        has_external_surveillance_frame: bool,
        user_step_request: bool,
        expansion_requested: bool,
        repair_and_expand_requested: bool,
        user_repair_signal: bool,
        active_line_intent: str,
        practice_overview_requested: bool,
        explicit_answer_need: bool,
        direct_concrete_request: bool,
        summary_request: bool,
        sarcasm_or_negative_feedback: bool,
        application_request: bool,
        pragmatics_contextual_followup: bool,
        pragmatics_offer_type: str,
        pragmatics_should_not_reconfirm: bool,
        pragmatics_repair_dissatisfaction: bool,
        answer_obligation: str,
        last_offer_summary: str,
        last_direct_question: str,
        answer_fit: dict[str, Any],
        canned_step_disallowed: bool,
    ) -> str:
        offer_repair_context = f"{last_offer_summary} {last_direct_question}".lower()
        if pragmatics_repair_dissatisfaction:
            target = (last_direct_question or user_message).strip()
            target_lower = target.lower()
            if answer_obligation == "repair_and_answer_last_question" and "нейросталкинг" in target_lower:
                return self._defer_no_stub_repair(
                    signal="mvp_repair_answer_last_question",
                    text=text,
                    must_answer=target,
                )
            return self._defer_no_stub_repair(
                signal="mvp_repair_user_dissatisfaction",
                text=text,
                must_answer=target or user_message,
            )

        if pragmatics_contextual_followup and pragmatics_should_not_reconfirm:
            if "хочешь" in lowered_text and "?" in text:
                text = re.sub(r"\s*\?+\s*", ". ", text).strip()
                lowered_text = text.lower()
            if "сфокусируюсь на разборе" in lowered_text or "без практик по умолчанию" in lowered_text:
                if pragmatics_offer_type in {"short_phrase", "one_step", "practice_observation"}:
                    return self._defer_no_stub_repair(
                        signal="mvp_contextual_followup_short_phrase",
                        text=text,
                        must_answer=last_offer_summary or user_message,
                    )
                if pragmatics_offer_type in {"example", "application", "explanation"}:
                    return self._defer_no_stub_repair(
                        signal="mvp_contextual_followup_example",
                        text=text,
                        must_answer=last_offer_summary or user_message,
                    )
                return self._defer_no_stub_repair(
                    signal="mvp_contextual_followup_direct",
                    text=text,
                    must_answer=last_offer_summary or user_message,
                )

        if planner_safety_priority or planner_next_move == "stabilize_safety" or planner_answer_shape == "safety_grounding":
            if has_question or len(text) > 380:
                self._set_final_answer_shape_debug("safety_grounding")
                return "Я рядом. Сейчас важнее немного стабилизироваться и снизить перегруз, без лишнего давления."
            self._set_final_answer_shape_debug("safety_grounding")
            return text

        if canned_step_disallowed and (planner_answer_shape == "one_step" or planner_next_move == "give_direct_step"):
            self._set_final_answer_shape_debug("sanitized_direct_no_forced_practice")
            return self._strip_optional_followup_invitation(text) or text

        if planner_answer_shape == "one_step" or user_step_request:
            return self._resolve_one_step_or_no_practice_fallback(
                text=text,
                user_message=user_message,
                lowered_user=lowered_user,
                canned_step_disallowed=canned_step_disallowed,
            )

        if summary_request:
            self._set_final_answer_shape_debug("structured_summary")
            return self._strip_optional_followup_invitation(text) or text

        if sarcasm_or_negative_feedback:
            return self._defer_no_stub_repair(
                signal="mvp_sarcasm_negative_feedback_repair",
                text=text,
                must_answer=user_message,
            )

        if direct_concrete_request:
            return self._defer_no_stub_repair(
                signal="mvp_direct_concrete_request_repair",
                text=text,
                must_answer=user_message,
            )

        if explicit_answer_need and has_question and planner_question_policy in {"none", "optional_none"}:
            self._set_final_answer_shape_debug("direct_no_forced_question")
            return re.sub(r"\s*\?+\s*", ". ", text).strip()

        if planner_practice_policy == "forbidden" and has_unsolicited_practice and not user_step_request:
            stale_stub = detect_stale_stub(text)
            preserve_direct_answer = (
                answer_obligation
                in {
                    "acknowledge_style_preference_then_answer",
                    "answer_direct_question",
                    "answer_knowledge_question",
                    "provide_one_bounded_practice",
                    "answer_last_offer",
                    "repair_and_answer_last_question",
                }
                or application_request
                or practice_overview_requested
            )
            if preserve_direct_answer and not bool(stale_stub.get("detected", False)) and len(text.strip()) >= 220:
                sanitized_text = self._strip_optional_followup_invitation(text)
                if sanitized_text:
                    self._set_final_answer_shape_debug("sanitized_direct_no_forced_practice")
                    return sanitized_text
            if bool(answer_fit.get("needs_repair", False)) or bool(answer_fit.get("concrete_need", False)) or application_request:
                self.last_debug["answer_fit_repair_applied"] = True
                self.last_debug["template_leakage_repair_deferred_to_gate"] = True
                self._set_final_answer_shape_debug("template_repair_deferred_to_gate")
                return self._strip_optional_followup_invitation(text) or text
            self.last_debug["answer_fit_repair_applied"] = True
            self.last_debug["template_leakage_repair_deferred_to_gate"] = True
            self._set_final_answer_shape_debug("template_repair_deferred_to_gate")
            return self._strip_optional_followup_invitation(text) or text

        if practice_overview_requested or planner_answer_shape == "practice_catalog_explanation":
            list_items = re.findall(r"(?m)^\s*(?:[-*•]|\d+[.)])\s+", text)
            if len(list_items) < 3 or len(text) < 420:
                return self._defer_no_stub_repair(
                    signal="mvp_practice_catalog_repair",
                    text=text,
                    must_answer="practice_catalog_explanation",
                )

        if planner_question_policy == "none" and has_question and not expansion_requested:
            self._set_final_answer_shape_debug("direct_no_forced_question")
            return re.sub(r"\s*\?+\s*", ". ", text).strip()

        if repair_and_expand_requested or user_repair_signal:
            return self._defer_no_stub_repair(
                signal="mvp_repair_and_expand",
                text=text,
                must_answer=user_message,
            )

        if should_answer_directly and (asks_define_known_term or has_external_surveillance_frame):
            return self._defer_no_stub_repair(
                signal="mvp_concept_explanation_repair",
                text=text,
                must_answer=user_message,
            )

        if (expansion_requested or application_request) and len(text) < 260:
            if answer_obligation in {
                "answer_direct_question",
                "answer_knowledge_question",
                "provide_one_bounded_practice",
                "answer_last_offer",
                "repair_and_answer_last_question",
            }:
                preserved_text = self._strip_optional_followup_invitation(text)
                preserved_lower = preserved_text.lower()
                if (
                    len(preserved_text) >= 120
                    or any(color in preserved_lower for color in ("красн", "оранж", "зелен"))
                    or "нейросталкинг" in preserved_lower
                ):
                    self._set_final_answer_shape_debug("preserved_application_answer")
                    return preserved_text
            if concept == "нейросталкинг" or "нейросталкинг" in lowered_user or active_line_intent == "known_concept_question":
                return self._defer_no_stub_repair(
                    signal="mvp_concept_expansion_repair",
                    text=text,
                    must_answer=user_message,
                )
            return self._defer_no_stub_repair(
                signal="mvp_expanded_explanation_repair",
                text=text,
                must_answer=user_message,
            )

        stale_stub = detect_stale_stub(text)
        if bool(stale_stub.get("detected", False)):
            self.last_debug["answer_fit_repair_applied"] = bool(answer_fit.get("concrete_need", False))
            self.last_debug["template_leakage_repair_deferred_to_gate"] = True
            self._set_final_answer_shape_debug("stale_stub_retry_deferred_to_gate")
            return text

        sanitized_final = text
        if answer_obligation in {
            "answer_direct_question",
            "answer_knowledge_question",
            "provide_one_bounded_practice",
            "answer_last_offer",
            "repair_and_answer_last_question",
        }:
            sanitized_final = self._strip_optional_followup_invitation(text) or text
        self._set_final_answer_shape_debug(planner_answer_shape or "compact_direct")
        return sanitized_final

    @staticmethod
    def _build_gentle_close_reply() -> str:
        return _fallback_build_gentle_close_reply()

    @staticmethod
    def _build_no_practice_fallback_text(user_message: str) -> str:
        return _fallback_build_no_practice_fallback_text(user_message)

    @staticmethod
    def _strip_optional_followup_invitation(text: str) -> str:
        return _fallback_strip_optional_followup_invitation(text)

    @staticmethod
    def _detect_language(text: str) -> str:
        return _fallback_detect_language(text)

    @staticmethod
    def _format_hits(hits: list[str]) -> str:
        return _fallback_format_hits(hits)

    @staticmethod
    def _format_diagnostic_summary(summary: Any) -> str:
        return _fallback_format_diagnostic_summary(summary)

    @staticmethod
    def _static_fallback(contract: WriterContract) -> str:
        return _fallback_static_fallback(contract)

    @staticmethod
    def _normalize_name(raw_name: str) -> Optional[str]:
        return _fallback_normalize_name(raw_name)


writer_agent = WriterAgent()


