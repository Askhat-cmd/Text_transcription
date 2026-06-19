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
    context_budget_for_profile,
    detect_application_request,
    detect_direct_concrete_request,
    detect_explicit_answer_need,
    detect_examples_request,
    detect_expansion_request,
    detect_numbered_list_request,
    detect_practice_overview_request,
    detect_repair_and_expand_request,
    detect_sarcasm_or_negative_feedback,
    detect_summary_request,
    format_conversation_context_for_writer_with_meta,
    normalize_dialogue_profile,
)
from ..concrete_answer_fit import evaluate_concrete_answer_fit
from ..stale_stub_detector import detect_stale_stub
from ..prompt_constraint_section import format_prompt_constraint_section_v1
from ..contracts.writer_contract import WriterContract
from ..writer_kb_payload import format_writer_kb_payload_for_prompt
from .agent_llm_client import create_agent_completion
from .agent_llm_config import get_model_for_agent, get_temperature_for_agent
from .writer_agent_prompts import (
    WRITER_SYSTEM,
    WRITER_SYSTEM_MVP_FREE_DIALOGUE,
    WRITER_USER_TEMPLATE,
)


logger = logging.getLogger(__name__)

WRITER_MAX_TOKENS_DEFAULT = 600
WRITER_TEMPERATURE_DEFAULT = 0.7
WRITER_TIMEOUT_DEFAULT = 30.0

_SAFE_OVERRIDE_FALLBACKS = {
    "ru": "Я здесь. Ты не один. Сделай медленный вдох — я рядом.",
    "en": "I'm here. You're not alone. Take a slow breath - I'm with you.",
}
_DEFAULT_LANG = "ru"

_COST_PER_1K_TOKENS = {
    "gpt-5-mini": {"input": 0.00025, "output": 0.00200},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.00060},
    "default": {"input": 0.00125, "output": 0.01000},
}

_RU_NAME_PATTERNS = (
    re.compile(r"\bменя\s+зовут\s+([А-ЯЁA-Z][А-ЯЁа-яёA-Za-z\-]{1,30})", re.IGNORECASE),
    re.compile(r"\bмое\s+имя\s+([А-ЯЁA-Z][А-ЯЁа-яёA-Za-z\-]{1,30})", re.IGNORECASE),
)
_EN_NAME_PATTERNS = (
    re.compile(r"\bmy\s+name\s+is\s+([A-Z][A-Za-z\-]{1,30})", re.IGNORECASE),
    re.compile(r"\bi\s+am\s+([A-Z][A-Za-z\-]{1,30})", re.IGNORECASE),
)
_LITERAL_MARKDOWN_ECHO_PATTERNS = (
    re.compile(
        r"(?:верни\s+без\s+объяснений\s+и\s+без\s+изменений\s+следующий\s+markdown(?:-блок)?\s*:)(.+)",
        re.IGNORECASE | re.DOTALL,
    ),
    re.compile(
        r"(?:return\s+the\s+following\s+markdown\s+block\s+without\s+changes\s*:)(.+)",
        re.IGNORECASE | re.DOTALL,
    ),
)
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


def _extract_literal_markdown_echo_request(user_message: str) -> str:
    text = str(user_message or "").strip()
    if not text:
        return ""
    for pattern in _LITERAL_MARKDOWN_ECHO_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        candidate = str(match.group(1) or "").strip()
        if not candidate:
            return ""
        if any(marker in candidate for marker in ("**", "- ", "* ", "1.", "##", "```")):
            return candidate
    return ""


def _to_int(value: str, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _to_float(value: str, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    lowered = str(text or "").lower()
    return any(marker in lowered for marker in markers)


class WriterAgent:
    """Generates final user-facing response from WriterContract."""

    def __init__(self, client: Optional[Any] = None, model: Optional[str] = None):
        self._client = client
        self._model_override = model
        self.last_debug: dict[str, Any] = {}

    def _resolve_model(self) -> str:
        return self._model_override or get_model_for_agent("writer")

    def _resolve_runtime_settings(self, dialogue_profile: str = "safe_guided") -> dict[str, Any]:
        model = self._resolve_model()
        profile = normalize_dialogue_profile(dialogue_profile)
        configured_max_tokens = _to_int(
            feature_flags.value(
                "MULTIAGENT_MAX_TOKENS",
                feature_flags.value("WRITER_MAX_TOKENS", str(WRITER_MAX_TOKENS_DEFAULT)),
            ),
            WRITER_MAX_TOKENS_DEFAULT,
        )
        max_tokens = configured_max_tokens
        if profile == DIALOGUE_PROFILE_MVP_FREE:
            max_tokens = max(configured_max_tokens, 2500)
        return {
            "model": model,
            "timeout": _to_float(
                feature_flags.value("MULTIAGENT_LLM_TIMEOUT", str(WRITER_TIMEOUT_DEFAULT)),
                WRITER_TIMEOUT_DEFAULT,
            ),
            "max_tokens": max_tokens,
            "temperature": get_temperature_for_agent("writer"),
        }

    async def write(
        self,
        contract: WriterContract,
        *,
        prompt_constraint_decision: dict[str, Any] | None = None,
    ) -> str:
        """Write one answer text with safe fallback behavior."""
        dialogue_profile = normalize_dialogue_profile(
            getattr(contract, "dialogue_policy", {}).get("profile", "safe_guided")
            if isinstance(getattr(contract, "dialogue_policy", None), dict)
            else "safe_guided"
        )
        runtime_settings = self._resolve_runtime_settings(dialogue_profile=dialogue_profile)
        system_prompt = (
            WRITER_SYSTEM_MVP_FREE_DIALOGUE
            if dialogue_profile == DIALOGUE_PROFILE_MVP_FREE
            else WRITER_SYSTEM
        )
        self.last_debug = {
            "model": runtime_settings["model"],
            "api_mode": None,
            "temperature": runtime_settings["temperature"],
            "max_tokens": runtime_settings["max_tokens"],
            "timeout": runtime_settings["timeout"],
            "dialogue_profile": dialogue_profile,
            "system_prompt": system_prompt,
            "user_prompt": "",
            "llm_response": "",
            "tokens_prompt": None,
            "tokens_completion": None,
            "tokens_total": None,
            "estimated_cost_usd": None,
            "duration_ms": None,
            "error": None,
            "fallback_used": False,
            "prompt_constraint_pilot_activation_mode": "disabled",
            "prompt_constraint_pilot_applied": False,
            "prompt_constraint_pilot_blocked_reasons": [],
            "prompt_constraint_pilot_prompt_section_chars": 0,
            "context_budget_chars": None,
            "context_truncated": None,
            "preserved_recent_turns_count": None,
            "older_context_omitted_chars": None,
            "writer_kb_payload_trace": {},
            "writer_kb_payload_future_graduation_notes": {},
            "semantic_cards_pilot": {},
            "writer_kb_payload_enabled": None,
            "writer_kb_payload_failed": None,
            "human_like_answer_policy_enabled": None,
            "explicit_answer_need": None,
            "repair_user_dissatisfaction": None,
            "sarcasm_or_negative_feedback": None,
            "overruled_constraints": [],
            "final_answer_shape": None,
            "question_forced": None,
            "practice_forced": None,
            "microstep_forced": None,
        }
        try:
            if contract.thread_state.safety_active:
                lang = contract.response_language or self._detect_language(contract.user_message)
                fallback = _SAFE_OVERRIDE_FALLBACKS.get(lang, _SAFE_OVERRIDE_FALLBACKS[_DEFAULT_LANG])
                try:
                    result = await self._call_llm(
                        contract,
                        prompt_constraint_decision=prompt_constraint_decision,
                    )
                    result = self._enforce_answer_compliance(result, contract)
                    if not result.strip():
                        self.last_debug["fallback_used"] = True
                        return fallback
                    return self._apply_name_continuity(result, contract)
                except Exception as exc:
                    self.last_debug["error"] = str(exc)
                    self.last_debug["fallback_used"] = True
                    return fallback

            result = await self._call_llm(
                contract,
                prompt_constraint_decision=prompt_constraint_decision,
            )
            result = self._enforce_answer_compliance(result, contract)
            if not result.strip():
                self.last_debug["fallback_used"] = True
                return self._static_fallback(contract)
            return self._apply_name_continuity(result, contract)
        except Exception as exc:
            logger.error("[WRITER] write failed: %s", exc, exc_info=True)
            self.last_debug["error"] = str(exc)
            self.last_debug["fallback_used"] = True
            return self._static_fallback(contract)

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
        ctx.setdefault("practice_rewrite_applied", False)
        ctx.setdefault("legacy_advisory_sanitization", {})
        ctx.setdefault("writer_kb_payload_enabled", False)
        ctx.setdefault("writer_kb_payload_failed", False)
        ctx.setdefault("writer_kb_payload_failure_reason", "")
        ctx.setdefault("writer_kb_payload", {})
        ctx.setdefault("writer_kb_payload_trace", {})
        ctx.setdefault("writer_kb_payload_trace_version", "writer_kb_payload_trace_v1")
        ctx.setdefault("writer_kb_payload_future_graduation_notes", {})
        knowledge_answer = (
            dict(ctx.get("knowledge_answer", {}))
            if isinstance(ctx.get("knowledge_answer"), dict)
            else {}
        )
        practice_gate = (
            dict(ctx.get("practice_gate", {}))
            if isinstance(ctx.get("practice_gate"), dict)
            else {}
        )
        knowledge_answer_first = bool(knowledge_answer.get("should_answer_directly", False))
        do_not_ask_definition = bool(knowledge_answer.get("should_answer_directly", False))
        practice_allowed = bool(practice_gate.get("practice_allowed", True))
        practice_ban_instruction = (
            str(ctx.get("writer_visible_practice_instruction", "") or "no_exercise_but_answer_normally")
            if not practice_allowed
            else "false"
        )
        known_concept_clarification_ban = (
            "true: do_not_ask_user_to_define_or_choose_known_concept_variant"
            if do_not_ask_definition
            else "false"
        )
        external_surveillance_frame_ban = (
            "true: avoid_external_surveillance_biofeedback_eeg_frame_for_internal_concept_answer"
            if knowledge_answer_first
            else "false"
        )
        philosophy_kernel = (
            dict(ctx.get("philosophy_kernel", {}))
            if isinstance(ctx.get("philosophy_kernel"), dict)
            else {}
        )
        writer_freedom_contract = (
            dict(ctx.get("writer_freedom_contract", {}))
            if isinstance(ctx.get("writer_freedom_contract"), dict)
            else {}
        )
        selected_lenses = [
            str(item)
            for item in list(ctx.get("philosophy_kernel_selected_lenses", []) or [])
            if str(item).strip()
        ]
        freedom_hard_boundaries = [
            str(item)
            for item in list(ctx.get("writer_freedom_hard_boundaries", []) or [])
            if str(item).strip()
        ]

        dialogue_policy_payload = (
            dict(ctx.get("dialogue_policy", {}))
            if isinstance(ctx.get("dialogue_policy"), dict)
            else {}
        )
        human_like_answer_policy = (
            dict(dialogue_policy_payload.get("human_like_answer_policy", {}))
            if isinstance(dialogue_policy_payload.get("human_like_answer_policy"), dict)
            else {}
        )
        constraint_resolution = (
            dict(dialogue_policy_payload.get("constraint_resolution", {}))
            if isinstance(dialogue_policy_payload.get("constraint_resolution"), dict)
            else {}
        )
        user_message = str(ctx.get("user_message", "") or "")
        dialogue_profile = normalize_dialogue_profile(
            dialogue_policy_payload.get("profile", ctx.get("dialogue_profile", "safe_guided"))
        )
        context_budget_chars = int(
            dialogue_policy_payload.get("context_budget_chars", context_budget_for_profile(dialogue_profile))
            or context_budget_for_profile(dialogue_profile)
        )
        formatted_context, context_meta = format_conversation_context_for_writer_with_meta(
            conversation_context=str(ctx.get("conversation_context", "") or ""),
            profile=dialogue_profile,
            budget_chars=context_budget_chars,
        )

        mvp_overrides_payload = (
            dict(dialogue_policy_payload.get("mvp_overrides", {}))
            if isinstance(dialogue_policy_payload.get("mvp_overrides"), dict)
            else {}
        )
        practice_overview_requested = bool(
            dialogue_policy_payload.get("practice_overview_requested", False)
        ) or detect_practice_overview_request(user_message)
        examples_requested = bool(
            dialogue_policy_payload.get("examples_requested", False)
        ) or detect_examples_request(user_message)
        numbered_list_requested = bool(
            dialogue_policy_payload.get("numbered_list_requested", False)
        ) or detect_numbered_list_request(user_message)
        expansion_requested = bool(
            dialogue_policy_payload.get("expansion_requested", False)
        ) or detect_expansion_request(user_message)
        explicit_answer_need = bool(
            dialogue_policy_payload.get("explicit_answer_need", False)
        ) or detect_explicit_answer_need(user_message)
        direct_concrete_request = bool(
            dialogue_policy_payload.get("direct_concrete_request", False)
        ) or detect_direct_concrete_request(user_message)
        summary_request = bool(
            dialogue_policy_payload.get("summary_request", False)
        ) or detect_summary_request(user_message)
        sarcasm_or_negative_feedback = bool(
            dialogue_policy_payload.get("sarcasm_or_negative_feedback", False)
        ) or detect_sarcasm_or_negative_feedback(user_message)
        application_request = bool(
            dialogue_policy_payload.get("application_request", False)
        ) or detect_application_request(user_message)
        repair_user_dissatisfaction = bool(
            dict(dialogue_policy_payload.get("mvp_overrides", {})).get(
                "repair_user_dissatisfaction",
                False,
            )
            or sarcasm_or_negative_feedback
        )
        overruled_constraints = [
            str(item)
            for item in list(constraint_resolution.get("overruled_constraints", []) or [])
            if str(item).strip()
        ]
        rich_user_request = (
            practice_overview_requested
            or examples_requested
            or numbered_list_requested
            or expansion_requested
            or explicit_answer_need
            or direct_concrete_request
            or summary_request
            or sarcasm_or_negative_feedback
            or application_request
            or bool(dialogue_policy_payload.get("repair_and_expand_requested", False))
        )
        mvp_override_block = "not_applicable_for_safe_guided_profile"
        if dialogue_profile == DIALOGUE_PROFILE_MVP_FREE:
            mvp_override_block = "\n".join(
                [
                    "MVP FREE DIALOGUE OVERRIDES:",
                    f"- explicit_user_request_wins={str(bool(mvp_overrides_payload.get('explicit_user_request_wins', True))).lower()}",
                    f"- old_max_sentence_constraints_softened={str(bool(mvp_overrides_payload.get('old_max_sentence_constraints_softened', True))).lower()}",
                    f"- planner_advisory={str(bool(mvp_overrides_payload.get('planner_advisory', True))).lower()}",
                    f"- overview_questions_allow_lists={str(bool(mvp_overrides_payload.get('overview_questions_allow_lists', practice_overview_requested))).lower()}",
                    f"- target_answer_depth={str(mvp_overrides_payload.get('target_answer_depth', dialogue_policy_payload.get('answer_depth', 'medium')) or 'medium')}",
                    f"- rich_user_request_detected={str(bool(rich_user_request)).lower()}",
                    f"- explicit_answer_need={str(bool(explicit_answer_need)).lower()}",
                    f"- direct_concrete_request={str(bool(direct_concrete_request)).lower()}",
                    f"- summary_request={str(bool(summary_request)).lower()}",
                    f"- sarcasm_or_negative_feedback={str(bool(sarcasm_or_negative_feedback)).lower()}",
                ]
            )

        writer_kb_payload_text = format_writer_kb_payload_for_prompt(
            payload=(
                dict(ctx.get("writer_kb_payload", {}))
                if isinstance(ctx.get("writer_kb_payload"), dict)
                else {}
            ),
            legacy_hits=list(ctx.get("semantic_hits", []) or []),
            fallback_reason=str(
                ctx.get("writer_kb_payload_failure_reason", "")
                or (
                    "writer_kb_payload_disabled"
                    if not bool(ctx.get("writer_kb_payload_enabled", False))
                    else "writer_kb_payload_empty_or_failed"
                )
            ),
        )
        self.last_debug["writer_kb_payload_trace"] = (
            dict(ctx.get("writer_kb_payload_trace", {}))
            if isinstance(ctx.get("writer_kb_payload_trace"), dict)
            else {}
        )
        self.last_debug["writer_kb_payload_future_graduation_notes"] = (
            dict(ctx.get("writer_kb_payload_future_graduation_notes", {}))
            if isinstance(ctx.get("writer_kb_payload_future_graduation_notes"), dict)
            else {}
        )
        self.last_debug["semantic_cards_pilot"] = (
            dict(ctx.get("semantic_cards_pilot", {}))
            if isinstance(ctx.get("semantic_cards_pilot"), dict)
            else {}
        )
        self.last_debug["writer_kb_payload_enabled"] = bool(ctx.get("writer_kb_payload_enabled", False))
        self.last_debug["writer_kb_payload_failed"] = bool(ctx.get("writer_kb_payload_failed", False))

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
            unified_dialogue_policy_version=str(ctx.get("unified_dialogue_policy_version", "unified_dialogue_policy_v2")),
            unified_active_profile_alias=str(ctx.get("unified_active_profile_alias", dialogue_profile)),
            profile_preset=str(ctx.get("profile_preset", "safe_guided")),
            unified_effective_writer_autonomy=str(ctx.get("unified_effective_writer_autonomy", "medium")),
            unified_effective_safety_floor=str(ctx.get("unified_effective_safety_floor", "minimal_baseline")),
            unified_legacy_blocks_visible_to_writer=str(bool(ctx.get("unified_legacy_blocks_visible_to_writer", False))).lower(),
            unified_legacy_blocks_source_signals_only=str(bool(ctx.get("unified_legacy_blocks_source_signals_only", True))).lower(),
            unified_hard_boundaries_csv=str(ctx.get("unified_hard_boundaries_csv", "none") or "none"),
            unified_soft_guidance_csv=str(ctx.get("unified_soft_guidance_csv", "none") or "none"),
            dialogue_act=str(ctx.get("dialogue_act", "unknown") or "unknown"),
            dialogue_act_confidence=float(ctx.get("dialogue_act_confidence", 0.0) or 0.0),
            dialogue_act_evidence=str(ctx.get("dialogue_act_evidence", "none") or "none"),
            last_assistant_offer_open=str(bool(ctx.get("last_assistant_offer_open", False))).lower(),
            last_assistant_offer_type=str(ctx.get("last_assistant_offer_type", "none") or "none"),
            last_assistant_offer_summary=str(ctx.get("last_assistant_offer_summary", "none") or "none"),
            unanswered_question_answer_required=str(bool(ctx.get("unanswered_question_answer_required", False))).lower(),
            unanswered_question_status=str(ctx.get("unanswered_question_status", "answered") or "answered"),
            unanswered_question_summary=str(ctx.get("unanswered_question_summary", "none") or "none"),
            dialogue_style_tone=str(ctx.get("dialogue_style_tone", "neutral") or "neutral"),
            dialogue_style_length_preference=str(ctx.get("dialogue_style_length_preference", "adaptive") or "adaptive"),
            dialogue_style_complexity_preference=str(ctx.get("dialogue_style_complexity_preference", "normal") or "normal"),
            dialogue_style_avoid_csv=str(ctx.get("dialogue_style_avoid_csv", "none") or "none"),
            answer_obligation=str(ctx.get("answer_obligation", "continue_thread") or "continue_thread"),
            answer_obligation_shape=str(ctx.get("answer_obligation_shape", "structured_explanation") or "structured_explanation"),
            answer_obligation_depth=str(ctx.get("answer_obligation_depth", "medium") or "medium"),
            answer_obligation_question_policy=str(ctx.get("answer_obligation_question_policy", "optional_none") or "optional_none"),
            answer_obligation_source=str(ctx.get("answer_obligation_source", "none") or "none"),
            diagnostic_card_summary=self._format_diagnostic_summary(ctx.get("diagnostic_card_summary")),
            diagnostic_card_avoid=", ".join(ctx.get("diagnostic_card_avoid_list", []) or []) or "нет",
            diagnostic_card_risk_flags=", ".join(ctx.get("diagnostic_card_risk_flags", []) or []) or "нет",
            writer_move_instruction_summary=ctx.get("writer_move_instruction_summary") or "нет",
            writer_move_must_do=", ".join(ctx.get("writer_move_must_do", []) or []) or "нет",
            writer_move_must_not_do=", ".join(ctx.get("writer_move_must_not_do", []) or []) or "нет",
            conversation_context=formatted_context,
            context_budget_chars=int(context_meta.get("context_budget_chars", 0) or 0),
            context_truncated=str(bool(context_meta.get("context_truncated", False))).lower(),
            preserved_recent_turns_count=int(context_meta.get("preserved_recent_turns_count", 0) or 0),
            older_context_omitted_chars=int(context_meta.get("older_context_omitted_chars", 0) or 0),
            user_profile_patterns=", ".join(ctx["user_profile_patterns"]) or "нет",
            user_profile_values=", ".join(ctx["user_profile_values"]) or "нет",
            writer_kb_payload_enabled=str(bool(ctx.get("writer_kb_payload_enabled", False))).lower(),
            writer_kb_payload_trace_version=str(
                ctx.get("writer_kb_payload_trace_version", "writer_kb_payload_trace_v1")
                or "writer_kb_payload_trace_v1"
            ),
            writer_kb_payload_failed=str(bool(ctx.get("writer_kb_payload_failed", False))).lower(),
            writer_kb_payload_text=writer_kb_payload_text,
            knowledge_answer_needed=str(bool(knowledge_answer.get("needed", False))).lower(),
            knowledge_answer_concept=str(knowledge_answer.get("concept", "") or "none"),
            knowledge_answer_kb_grounding=str(bool(knowledge_answer.get("kb_grounding_available", False))).lower(),
            knowledge_answer_first=str(knowledge_answer_first).lower(),
            do_not_ask_user_to_define_term_before_answering=str(do_not_ask_definition).lower(),
            practice_allowed=str(practice_allowed).lower(),
            knowledge_answer_writer_instruction=str(
                knowledge_answer.get("writer_instruction", "none") or "none"
            ),
            practice_ban_instruction=practice_ban_instruction,
            known_concept_clarification_ban=known_concept_clarification_ban,
            external_surveillance_frame_ban=external_surveillance_frame_ban,
            philosophy_kernel_version=str(
                ctx.get("philosophy_kernel_version", philosophy_kernel.get("kernel_version", ""))
            ),
            philosophy_kernel_quote_policy=str(
                ctx.get(
                    "philosophy_kernel_quote_policy",
                    philosophy_kernel.get("quote_policy", "internal_lens_not_citation"),
                )
            ),
            philosophy_kernel_selected_lenses=", ".join(selected_lenses) or "none",
            philosophy_kernel_prompt_block=str(ctx.get("philosophy_kernel_prompt_block", "") or "none"),
            philosophy_kernel_prompt_compactness=str(
                ctx.get("philosophy_kernel_prompt_compactness", {}) or {}
            ),
            writer_freedom_prompt_block=str(
                ctx.get("writer_freedom_prompt_block", "") or "none"
            ),
            writer_freedom_contract_version=str(
                ctx.get("writer_freedom_contract_version", writer_freedom_contract.get("version", ""))
            ),
            writer_freedom_level=str(
                ctx.get("writer_freedom_level", writer_freedom_contract.get("freedom_level", "guided"))
            ),
            writer_mode_hint=str(ctx.get("writer_mode_hint", writer_freedom_contract.get("mode_hint", ""))),
            mode_is_hint_not_cage=str(bool(ctx.get("mode_is_hint_not_cage", True))).lower(),
            writer_question_limit=int(ctx.get("writer_question_limit", 1) or 1),
            practice_requires_gate=str(bool(ctx.get("practice_requires_gate", True))).lower(),
            writer_freedom_hard_boundaries=", ".join(freedom_hard_boundaries)
            or "no_diagnosis,no_unsolicited_practice",
            final_answer_directive_json=str(ctx.get("final_answer_directive_json", "{}") or "{}"),
            writer_visible_final_answer_directive_json=str(
                ctx.get("writer_visible_final_answer_directive_json", "{}") or "{}"
            ),
            final_answer_directive_version=str(
                ctx.get("final_answer_directive_version", "final_answer_directive_v1")
                or "final_answer_directive_v1"
            ),
            final_answer_diagnostic_center_role=str(
                ctx.get("final_answer_diagnostic_center_role", "guided_legacy") or "guided_legacy"
            ),
            final_answer_planner_role=str(
                ctx.get("final_answer_planner_role", "guided_legacy") or "guided_legacy"
            ),
            final_answer_active_line_role=str(
                ctx.get("final_answer_active_line_role", "guided_legacy") or "guided_legacy"
            ),
            final_answer_diagnostic_card_role=str(
                ctx.get("final_answer_diagnostic_card_role", "guided_legacy") or "guided_legacy"
            ),
            writer_first_prompt_assembly_enabled=str(
                bool(ctx.get("writer_first_prompt_assembly_enabled", False))
            ).lower(),
            legacy_blocks_visible_to_writer=str(
                bool(ctx.get("legacy_blocks_visible_to_writer", True))
            ).lower(),
            legacy_blocks_source_signals_only=str(
                bool(ctx.get("legacy_blocks_source_signals_only", False))
            ).lower(),
            legacy_constraints_suppressed_csv=str(
                ctx.get("legacy_constraints_suppressed_csv", "none") or "none"
            ),
            writer_visible_advisory_summary=str(
                ctx.get("writer_visible_advisory_summary", "") or "нет"
            ),
            writer_visible_practice_note=str(
                ctx.get("writer_visible_practice_note", "") or "нет"
            ),
            fresh_chat_context_policy_version=str(
                ctx.get("fresh_chat_context_policy_version", "fresh_chat_context_policy_v1")
                or "fresh_chat_context_policy_v1"
            ),
            fresh_chat_is_new_chat=str(bool(ctx.get("fresh_chat_is_new_chat", False))).lower(),
            fresh_chat_turn_index=int(ctx.get("fresh_chat_turn_index", 1) or 1),
            fresh_chat_is_greeting_or_contact=str(
                bool(ctx.get("fresh_chat_is_greeting_or_contact", False))
            ).lower(),
            fresh_chat_cross_session_memory_allowed=str(
                bool(ctx.get("fresh_chat_cross_session_memory_allowed", True))
            ).lower(),
            fresh_chat_cross_session_memory_reason=str(
                ctx.get("fresh_chat_cross_session_memory_reason", "") or ""
            ),
            fresh_chat_active_context_source=str(
                ctx.get("fresh_chat_active_context_source", "current_chat_only")
                or "current_chat_only"
            ),
            writer_context_package_version=str(
                ctx.get("writer_context_package_version", "writer_context_package_v1")
                or "writer_context_package_v1"
            ),
            writer_context_recent_turns_count=int(
                ctx.get("writer_context_recent_turns_count", 0) or 0
            ),
            writer_context_profile_present=str(
                bool(ctx.get("writer_context_profile_present", False))
            ).lower(),
            writer_context_rag_candidates_count=int(
                ctx.get("writer_context_rag_candidates_count", 0) or 0
            ),
            writer_context_rag_for_writer_count=int(
                ctx.get("writer_context_rag_for_writer_count", 0) or 0
            ),
            practice_rewrite_applied=str(bool(ctx.get("practice_rewrite_applied", False))).lower(),
            active_line_version=str(ctx.get("active_line_version", "active_line_v1")),
            active_line_text=str(ctx.get("active_line_text", "") or ""),
            active_line_user_intent=str(ctx.get("active_line_user_intent", "unknown") or "unknown"),
            active_line_continuity_mode=str(
                ctx.get("active_line_continuity_mode", "continue_existing_line")
            ),
            active_line_next_meaningful_move=str(
                ctx.get("active_line_next_meaningful_move", "") or ""
            ),
            active_line_should_continue_line=str(bool(ctx.get("active_line_should_continue_line", True))).lower(),
            active_line_should_ask_question=str(bool(ctx.get("active_line_should_ask_question", False))).lower(),
            active_line_should_offer_practice=str(bool(ctx.get("active_line_should_offer_practice", False))).lower(),
            active_line_revoicing_allowed=str(bool(ctx.get("active_line_revoicing_allowed", False))).lower(),
            active_line_revoicing_style=str(ctx.get("active_line_revoicing_style", "suppressed") or "suppressed"),
            active_line_repair_mode=str(ctx.get("active_line_repair_mode", "") or ""),
            active_line_practice_suppression_active=str(
                bool(ctx.get("active_line_practice_suppression_active", False))
            ).lower(),
            response_planner_version=str(ctx.get("response_planner_version", "response_planner_v1")),
            response_planner_enabled=str(bool(ctx.get("response_planner_enabled", False))).lower(),
            response_planner_next_move=str(
                ctx.get("response_planner_next_move", "continue_active_line") or "continue_active_line"
            ),
            response_planner_answer_shape=str(
                ctx.get("response_planner_answer_shape", "compact_direct") or "compact_direct"
            ),
            response_planner_response_depth=str(
                ctx.get("response_planner_response_depth", "short") or "short"
            ),
            response_planner_target_micro_shift=str(
                ctx.get("response_planner_target_micro_shift", "") or ""
            ),
            response_planner_should_answer_directly=str(
                bool(ctx.get("response_planner_should_answer_directly", False))
            ).lower(),
            response_planner_question_policy=str(
                ctx.get("response_planner_question_policy", "none") or "none"
            ),
            response_planner_practice_policy=str(
                ctx.get("response_planner_practice_policy", "forbidden") or "forbidden"
            ),
            response_planner_revoicing_policy=str(
                ctx.get("response_planner_revoicing_policy", "suppressed") or "suppressed"
            ),
            response_planner_continuity_policy=str(
                ctx.get("response_planner_continuity_policy", "continue_active_line")
                or "continue_active_line"
            ),
            response_planner_safety_priority=str(
                bool(ctx.get("response_planner_safety_priority", False))
            ).lower(),
            response_planner_must_include=", ".join(
                [str(item) for item in list(ctx.get("response_planner_must_include", []) or []) if str(item).strip()]
            )
            or "none",
            response_planner_must_avoid=", ".join(
                [str(item) for item in list(ctx.get("response_planner_must_avoid", []) or []) if str(item).strip()]
            )
            or "none",
            response_planner_confidence=float(ctx.get("response_planner_confidence", 0.0) or 0.0),
            response_planner_rationale=str(ctx.get("response_planner_rationale", "") or ""),
            dialogue_profile=str(ctx.get("dialogue_profile", "safe_guided") or "safe_guided"),
            dialogue_expansion_requested=str(bool(ctx.get("dialogue_expansion_requested", False))).lower(),
            dialogue_repair_and_expand_requested=str(
                bool(ctx.get("dialogue_repair_and_expand_requested", False))
            ).lower(),
            dialogue_active_concept=str(ctx.get("dialogue_active_concept", "") or ""),
            dialogue_pragmatics_version=str(
                ctx.get("dialogue_pragmatics_version", "dialogue_pragmatics_v1")
            ),
            dialogue_pragmatics_short_utterance=str(
                bool(ctx.get("dialogue_pragmatics_short_utterance", False))
            ).lower(),
            dialogue_pragmatics_short_type=str(
                ctx.get("dialogue_pragmatics_short_type", "not_short") or "not_short"
            ),
            dialogue_pragmatics_is_contextual_followup=str(
                bool(ctx.get("dialogue_pragmatics_is_contextual_followup", False))
            ).lower(),
            dialogue_pragmatics_offer_type=str(
                ctx.get("dialogue_pragmatics_offer_type", "unknown") or "unknown"
            ),
            dialogue_pragmatics_inherited_intent=str(
                ctx.get("dialogue_pragmatics_inherited_intent", "continue_previous_offer")
                or "continue_previous_offer"
            ),
            dialogue_pragmatics_should_answer_directly=str(
                bool(ctx.get("dialogue_pragmatics_should_answer_directly", False))
            ).lower(),
            dialogue_pragmatics_should_not_ask_confirmation_again=str(
                bool(ctx.get("dialogue_pragmatics_should_not_ask_confirmation_again", False))
            ).lower(),
            dialogue_pragmatics_repair_user_dissatisfaction=str(
                bool(ctx.get("dialogue_pragmatics_repair_user_dissatisfaction", False))
            ).lower(),
            dialogue_pragmatics_reason=str(ctx.get("dialogue_pragmatics_reason", "none") or "none"),
            retrieval_decision_version=str(
                ctx.get("retrieval_decision_version", "contextual_retrieval_gating_v1")
                or "contextual_retrieval_gating_v1"
            ),
            retrieval_action=str(ctx.get("retrieval_action", "none") or "none"),
            retrieval_rag_candidates_count=int(ctx.get("retrieval_rag_candidates_count", 0) or 0),
            retrieval_rag_included_count=int(ctx.get("retrieval_rag_included_count", 0) or 0),
            retrieval_rag_included_reason=str(
                ctx.get("retrieval_rag_included_reason", "") or ""
            ),
            retrieval_rag_suppressed_reason=str(
                ctx.get("retrieval_rag_suppressed_reason", "") or ""
            ),
            retrieval_writer_can_ignore_rag=str(
                bool(ctx.get("retrieval_writer_can_ignore_rag", True))
            ).lower(),
            retrieval_rag_relevance=str(ctx.get("retrieval_rag_relevance", "unknown") or "unknown"),
            retrieval_inherited_topic=str(ctx.get("retrieval_inherited_topic", "") or ""),
            retrieval_inherited_offer_type=str(
                ctx.get("retrieval_inherited_offer_type", "unknown") or "unknown"
            ),
            human_like_enabled=str(bool(human_like_answer_policy.get("enabled", False))).lower(),
            human_like_answer_style=str(
                human_like_answer_policy.get("answer_style", "guided_compact") or "guided_compact"
            ),
            human_like_default_depth=str(
                human_like_answer_policy.get("default_depth", "short_to_medium") or "short_to_medium"
            ),
            human_like_question_is_optional=str(
                bool(human_like_answer_policy.get("question_is_optional", False))
            ).lower(),
            human_like_do_not_force_question=str(
                bool(human_like_answer_policy.get("do_not_force_question_at_end", False))
            ).lower(),
            human_like_do_not_force_practice=str(
                bool(human_like_answer_policy.get("do_not_force_practice_frame", False))
            ).lower(),
            human_like_flexible_length_allowed=str(
                bool(human_like_answer_policy.get("do_not_force_max_sentences", False))
            ).lower(),
            human_like_respect_user_requested_format=str(
                bool(human_like_answer_policy.get("respect_user_requested_format", False))
            ).lower(),
            human_like_repair_user_dissatisfaction=str(bool(repair_user_dissatisfaction)).lower(),
            human_like_direct_answer_repair=str(
                bool(human_like_answer_policy.get("direct_answer_repair_when_user_complains", False))
            ).lower(),
            constraint_resolution_profile=str(
                constraint_resolution.get("profile", dialogue_profile) or dialogue_profile
            ),
            constraint_resolution_planner_authority=str(
                constraint_resolution.get("planner_authority", "guided") or "guided"
            ),
            constraint_resolution_overruled=", ".join(overruled_constraints) or "none",
            constraint_resolution_reason=str(
                constraint_resolution.get("overrule_reason", "none") or "none"
            ),
            mvp_free_dialogue_overrides=mvp_override_block,
        )
        prompt_section = (
            format_prompt_constraint_section_v1(prompt_constraint_decision)
            if prompt_constraint_decision is not None
            else ""
        )
        activation_mode = (
            str(prompt_constraint_decision.get("activation_mode", "disabled"))
            if isinstance(prompt_constraint_decision, dict)
            else "disabled"
        )
        blocked_reasons = (
            list(prompt_constraint_decision.get("blocked_reasons", []))
            if isinstance(prompt_constraint_decision, dict)
            and isinstance(prompt_constraint_decision.get("blocked_reasons", []), list)
            else []
        )
        if prompt_section:
            user_prompt = f"{user_prompt}\n\n{prompt_section}"
        self.last_debug["user_prompt"] = user_prompt
        self.last_debug["prompt_constraint_pilot_activation_mode"] = activation_mode
        self.last_debug["prompt_constraint_pilot_applied"] = bool(prompt_section)
        self.last_debug["prompt_constraint_pilot_blocked_reasons"] = blocked_reasons
        self.last_debug["prompt_constraint_pilot_prompt_section_chars"] = len(prompt_section)
        self.last_debug["context_budget_chars"] = int(context_meta.get("context_budget_chars", 0) or 0)
        self.last_debug["context_truncated"] = bool(context_meta.get("context_truncated", False))
        self.last_debug["preserved_recent_turns_count"] = int(
            context_meta.get("preserved_recent_turns_count", 0) or 0
        )
        self.last_debug["older_context_omitted_chars"] = int(
            context_meta.get("older_context_omitted_chars", 0) or 0
        )
        self.last_debug["human_like_answer_policy_enabled"] = bool(
            human_like_answer_policy.get("enabled", False)
        )
        self.last_debug["explicit_answer_need"] = bool(explicit_answer_need)
        self.last_debug["repair_user_dissatisfaction"] = bool(repair_user_dissatisfaction)
        self.last_debug["sarcasm_or_negative_feedback"] = bool(sarcasm_or_negative_feedback)
        self.last_debug["overruled_constraints"] = overruled_constraints
        self.last_debug["dialogue_pragmatics_contextual_followup"] = bool(
            ctx.get("dialogue_pragmatics_is_contextual_followup", False)
        )
        self.last_debug["dialogue_pragmatics_offer_type"] = str(
            ctx.get("dialogue_pragmatics_offer_type", "unknown") or "unknown"
        )
        self.last_debug["retrieval_action"] = str(ctx.get("retrieval_action", "none") or "none")
        self.last_debug["retrieval_rag_included_count"] = int(
            ctx.get("retrieval_rag_included_count", 0) or 0
        )

        start_ts = time.perf_counter()
        dialogue_profile = normalize_dialogue_profile(ctx.get("dialogue_profile", dialogue_profile))
        runtime_settings = self._resolve_runtime_settings(dialogue_profile=dialogue_profile)
        system_prompt = (
            WRITER_SYSTEM_MVP_FREE_DIALOGUE
            if dialogue_profile == DIALOGUE_PROFILE_MVP_FREE
            else WRITER_SYSTEM
        )
        self.last_debug["system_prompt"] = system_prompt
        self.last_debug["dialogue_profile"] = dialogue_profile
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
        llm_response = result.text
        tokens_prompt, tokens_completion, tokens_total = (
            result.tokens_prompt,
            result.tokens_completion,
            result.tokens_total,
        )
        estimated_cost = self._estimate_cost(tokens_prompt=tokens_prompt, tokens_completion=tokens_completion)
        duration_ms = int((time.perf_counter() - start_ts) * 1000)
        self.last_debug.update(
            {
                "model": runtime_settings["model"],
                "api_mode": result.api_mode,
                "temperature": runtime_settings["temperature"],
                "max_tokens": runtime_settings["max_tokens"],
                "timeout": runtime_settings["timeout"],
                "llm_response": llm_response,
                "tokens_prompt": tokens_prompt,
                "tokens_completion": tokens_completion,
                "tokens_total": tokens_total,
                "estimated_cost_usd": estimated_cost,
                "duration_ms": duration_ms,
                "error": None,
                "fallback_used": False,
            }
        )
        return llm_response

    def _enforce_answer_compliance(self, response_text: str, contract: WriterContract) -> str:
        text = str(response_text or "").strip()
        if not text:
            return text

        ctx = contract.to_prompt_context()
        user_message = str(ctx.get("user_message", "") or "")
        lowered_user = user_message.lower()
        literal_markdown_echo = _extract_literal_markdown_echo_request(user_message)
        dialogue_profile = normalize_dialogue_profile(ctx.get("dialogue_profile", "safe_guided"))
        expansion_requested = bool(ctx.get("dialogue_expansion_requested", False)) or detect_expansion_request(user_message)
        repair_and_expand_requested = bool(
            ctx.get("dialogue_repair_and_expand_requested", False)
        ) or detect_repair_and_expand_request(user_message)
        knowledge_answer = dict(ctx.get("knowledge_answer", {})) if isinstance(ctx.get("knowledge_answer"), dict) else {}
        practice_gate = dict(ctx.get("practice_gate", {})) if isinstance(ctx.get("practice_gate"), dict) else {}
        practice_allowed = bool(practice_gate.get("practice_allowed", True))
        should_answer_directly = bool(knowledge_answer.get("should_answer_directly", False))
        is_greeting = bool(practice_gate.get("is_greeting", False))
        concept = str(knowledge_answer.get("concept", "") or "").strip().lower()
        active_line = dict(ctx.get("active_line", {})) if isinstance(ctx.get("active_line"), dict) else {}
        active_line_intent = str(active_line.get("user_intent", "unknown") or "unknown")
        active_line_repair_mode = str(active_line.get("repair_mode", "") or "")
        active_line_revoicing_allowed = bool(active_line.get("revoicing_allowed", True))
        active_line_should_offer_practice = bool(active_line.get("should_offer_practice", practice_allowed))
        active_line_practice_suppression = bool(active_line.get("practice_suppression_active", False))
        response_planner = dict(ctx.get("response_planner", {})) if isinstance(ctx.get("response_planner"), dict) else {}
        planner_next_move = str(response_planner.get("next_move", "continue_active_line") or "continue_active_line")
        planner_answer_shape = str(response_planner.get("answer_shape", "compact_direct") or "compact_direct")
        planner_question_policy = str(response_planner.get("question_policy", "none") or "none")
        planner_practice_policy = str(response_planner.get("practice_policy", "forbidden") or "forbidden")
        planner_safety_priority = bool(response_planner.get("safety_priority", False))
        dialogue_policy_payload = dict(ctx.get("dialogue_policy", {})) if isinstance(ctx.get("dialogue_policy"), dict) else {}
        dialogue_pragmatics_payload = (
            dict(ctx.get("dialogue_pragmatics", {}))
            if isinstance(ctx.get("dialogue_pragmatics"), dict)
            else {}
        )
        explicit_answer_need = bool(
            dialogue_policy_payload.get("explicit_answer_need", False)
        ) or detect_explicit_answer_need(user_message)
        direct_concrete_request = bool(
            dialogue_policy_payload.get("direct_concrete_request", False)
        ) or detect_direct_concrete_request(user_message)
        summary_request = bool(
            dialogue_policy_payload.get("summary_request", False)
        ) or detect_summary_request(user_message)
        sarcasm_or_negative_feedback = bool(
            dialogue_policy_payload.get("sarcasm_or_negative_feedback", False)
        ) or detect_sarcasm_or_negative_feedback(user_message)
        application_request = bool(
            dialogue_policy_payload.get("application_request", False)
        ) or detect_application_request(user_message)
        human_like_answer_policy = (
            dict(dialogue_policy_payload.get("human_like_answer_policy", {}))
            if isinstance(dialogue_policy_payload.get("human_like_answer_policy"), dict)
            else {}
        )
        constraint_resolution = (
            dict(dialogue_policy_payload.get("constraint_resolution", {}))
            if isinstance(dialogue_policy_payload.get("constraint_resolution"), dict)
            else {}
        )
        practice_overview_requested = bool(
            dialogue_policy_payload.get("practice_overview_requested", False)
            or planner_next_move == "answer_practice_overview"
            or planner_answer_shape == "practice_catalog_explanation"
        )
        pragmatics_contextual_followup = bool(
            dialogue_pragmatics_payload.get("is_contextual_followup", False)
        )
        pragmatics_offer_type = str(
            dialogue_pragmatics_payload.get("previous_assistant_offer_type", "unknown") or "unknown"
        )
        pragmatics_should_not_reconfirm = bool(
            dialogue_pragmatics_payload.get("should_not_ask_confirmation_again", False)
        )
        pragmatics_repair_dissatisfaction = bool(
            dialogue_pragmatics_payload.get("repair_user_dissatisfaction", False)
        )
        lowered_text = text.lower()
        self.last_debug["compliance_planner_next_move"] = planner_next_move
        self.last_debug["compliance_planner_answer_shape"] = planner_answer_shape
        self.last_debug["compliance_planner_question_policy"] = planner_question_policy
        self.last_debug["compliance_response_planner_present"] = bool(response_planner)
        self.last_debug["human_like_answer_policy_enabled"] = bool(
            human_like_answer_policy.get("enabled", False)
        )
        self.last_debug["explicit_answer_need"] = bool(explicit_answer_need)
        self.last_debug["repair_user_dissatisfaction"] = bool(
            sarcasm_or_negative_feedback
            or bool(
                dict(dialogue_policy_payload.get("mvp_overrides", {})).get(
                    "repair_user_dissatisfaction",
                    False,
                )
            )
        )
        self.last_debug["sarcasm_or_negative_feedback"] = bool(sarcasm_or_negative_feedback)
        self.last_debug["overruled_constraints"] = [
            str(item)
            for item in list(constraint_resolution.get("overruled_constraints", []) or [])
            if str(item).strip()
        ]
        final_answer_directive = (
            dict(ctx.get("final_answer_directive", {}))
            if isinstance(ctx.get("final_answer_directive"), dict)
            else {}
        )
        self.last_debug["final_answer_directive"] = final_answer_directive
        gate_feedback = (
            dict(final_answer_directive.get("acceptance_gate_feedback", {}))
            if isinstance(final_answer_directive.get("acceptance_gate_feedback"), dict)
            else {}
        )
        gate_failed_checks = {
            str(item)
            for item in list(gate_feedback.get("failed_checks", []) or [])
            if str(item).strip()
        }
        if (
            "greeting_answered_with_mechanism_explanation" in gate_failed_checks
            and _contains_any(lowered_user, ("здравств", "привет", "добрый день", "добрый вечер"))
        ):
            return self._defer_no_stub_repair(
                signal="acceptance_gate_greeting_repair",
                text=text,
                must_answer="greeting_without_mechanism_lecture",
            )
        self.last_debug["legacy_constraints_suppressed"] = [
            str(item)
            for item in list(ctx.get("legacy_constraints_suppressed", []) or [])
            if str(item).strip()
        ]
        self.last_debug["question_forced"] = bool(
            planner_question_policy not in {"none", "optional_none"}
        )
        self.last_debug["practice_forced"] = bool(
            planner_practice_policy in {"required", "one_step_required"}
        )
        self.last_debug["microstep_forced"] = False
        answer_obligation = str(
            ctx.get("answer_obligation")
            or dict(ctx.get("final_answer_directive", {})).get("answer_obligation", "")
            or ""
        )
        last_direct_question = str(ctx.get("unanswered_question_summary", "") or "")
        last_offer_summary = str(ctx.get("last_assistant_offer_summary", "") or "")
        offer_repair_context = f"{last_offer_summary} {last_direct_question}".lower()
        concept_question = "нейросталкинг" in lowered_user

        has_unsolicited_practice = any(marker in lowered_text for marker in _PRACTICE_MARKERS)
        has_question = "?" in text
        asks_define_known_term = any(marker in lowered_text for marker in _KNOWN_CONCEPT_CLARIFICATION_MARKERS)
        has_external_surveillance_frame = any(marker in lowered_text for marker in _EXTERNAL_SURVEILLANCE_MARKERS)
        user_requests_no_question = _contains_any(
            lowered_user, ("без вопросов", "не задавай вопросов", "ответь без вопроса", "без вопроса")
        )
        user_requests_no_practice = _contains_any(
            lowered_user, ("без практик", "без перехода в практик", "не давай практик", "без упражн")
        )
        user_repair_signal = _contains_any(
            lowered_user, ("ушел не туда", "вернись к сути", "снова предлагаешь практику", "я просил разбор механизма")
        )
        user_step_request = _contains_any(
            lowered_user, ("один шаг", "что сделать прямо сейчас", "что делать прямо сейчас", "дай шаг", "хочу действие")
        )
        self.last_debug["microstep_forced"] = bool(
            planner_answer_shape == "one_step" and not user_step_request
        )
        user_mechanism_request = _contains_any(
            lowered_user, ("механизм", "почему застреваю", "как это работает", "разбор")
        )
        answer_fit = evaluate_concrete_answer_fit(
            user_message=user_message,
            answer_text=text,
            direct_concrete_request=direct_concrete_request,
            application_request=application_request,
            explicit_answer_need=explicit_answer_need,
        )
        self.last_debug["answer_fit_evaluator"] = dict(answer_fit)

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
                return "Сделай один шаг прямо сейчас: открой задачу и выполни первый минимальный фрагмент в течение 5 минут."
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
                return "Сделай один шаг прямо сейчас: открой задачу и выполни первый минимальный фрагмент в течение 5 минут."
            if planner_next_move == "give_short_support":
                return "Я рядом. Сейчас не нужно ничего разбирать. Можно просто немного снизить внутреннее давление."
            if planner_next_move == "stabilize_safety":
                return "Я рядом. Сейчас важнее чуть стабилизироваться и снизить внутреннюю перегрузку. Без разбора, только опора здесь-и-сейчас."
            if planner_next_move == "close_gently":
                return "Пожалуйста. Рад, что стало чуть яснее."
            return "Я рядом. Продолжим спокойно и без лишней нагрузки."
        if planner_question_policy == "none":
            if planner_next_move == "give_direct_step" or planner_answer_shape == "one_step":
                return "Сделай один шаг прямо сейчас: открой задачу и выполни первый минимальный фрагмент в течение 5 минут."
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
            return "Сделай один шаг прямо сейчас: открой задачу и выполни первый минимальный фрагмент в течение 5 минут."

        if planner_answer_shape == "one_step" or user_step_request or active_line_intent == "ask_for_direct_step":
            list_like = bool(re.search(r"(^|\n)\s*(?:[-*•]|\d+[.)])\s+", text))
            if list_like:
                first_item = re.search(r"(?:[-*•]|\d+[.)])\s+(.+)", text)
                if first_item:
                    return first_item.group(1).strip()
            sentence_parts = [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]
            if len(sentence_parts) > 2:
                return "Сделай один шаг прямо сейчас: открой задачу и выполни первый минимальный фрагмент в течение 5 минут."
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
                return "Сделай один шаг прямо сейчас: открой задачу и выполни первый минимальный фрагмент в течение 5 минут."
            has_step_marker = _contains_any(lowered_text, ("сделай", "начни", "открой", "выбери", "напиши", "шаг"))
            if not has_step_marker:
                return "Сделай один шаг прямо сейчас: открой задачу и выполни первый минимальный фрагмент в течение 5 минут."

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

        if planner_answer_shape == "one_step" or user_step_request:
            self._set_final_answer_shape_debug("one_step")
            return "Сделай один шаг прямо сейчас: открой задачу и выполни первый минимальный фрагмент в течение 5 минут."

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

    def _set_final_answer_shape_debug(self, shape: str) -> None:
        self.last_debug["final_answer_shape"] = str(shape or "compact_direct")

    def _defer_no_stub_repair(self, *, signal: str, text: str, must_answer: str = "") -> str:
        """Signal the existing acceptance gate/retry path instead of writing a canned answer."""

        shape = str(signal or "no_stub_repair").strip() or "no_stub_repair"
        self._set_final_answer_shape_debug(f"{shape}_deferred_to_gate")
        failed_checks = [
            str(item)
            for item in list(self.last_debug.get("compliance_failed_checks", []) or [])
            if str(item).strip()
        ]
        if "no_stub_repair_signal" not in failed_checks:
            failed_checks.append("no_stub_repair_signal")
        payload = {
            "version": "no_stub_repair_signal_v1",
            "reason": shape,
            "recommended_action": "writer_retry",
            "must_answer": str(must_answer or "").strip(),
            "user_facing_replacement_created": False,
        }
        self.last_debug["compliance_failed_checks"] = failed_checks
        self.last_debug["no_stub_repair_signal"] = payload
        self.last_debug["retry_recommended"] = True
        return self._strip_optional_followup_invitation(text) or text

    @staticmethod
    def _strip_optional_followup_invitation(text: str) -> str:
        return re.sub(
            r"\n{2,}(?:Если хочешь|Если хотите|Хочешь|Хотите|Могу дальше|Могу сразу|Если нужно).*$",
            "",
            text.strip(),
            flags=re.IGNORECASE | re.DOTALL,
        ).strip()

    def _get_client(self):
        if self._client is not None:
            return self._client
        try:
            from openai import AsyncOpenAI

            api_key = getattr(config, "OPENAI_API_KEY", None)
            if not api_key:
                return None
            self._client = AsyncOpenAI(api_key=api_key)
            return self._client
        except Exception:
            return None

    @staticmethod
    def _detect_language(text: str) -> str:
        cyrillic = sum(1 for ch in text if ("а" <= ch.lower() <= "я") or ch.lower() == "ё")
        return "ru" if cyrillic > len(text) * 0.2 else "en"

    @staticmethod
    def _format_hits(hits: list[str]) -> str:
        if not hits:
            return "нет релевантных знаний"
        return "\n---\n".join(f"- {h[:300]}" for h in hits[:2])

    @staticmethod
    def _format_diagnostic_summary(summary: Any) -> str:
        if not isinstance(summary, dict) or not summary.get("present"):
            return "нет"
        return (
            f"situation_label={summary.get('situation_label')}; "
            f"current_need={summary.get('current_need')}; "
            f"suggested_writer_move={summary.get('suggested_writer_move')}; "
            f"confidence={summary.get('confidence')}"
        )

    def _estimate_cost(self, *, tokens_prompt: Optional[int], tokens_completion: Optional[int]) -> Optional[float]:
        if tokens_prompt is None and tokens_completion is None:
            return None
        model = str(self.last_debug.get("model") or self._resolve_model()).lower()
        rates = _COST_PER_1K_TOKENS.get(model, _COST_PER_1K_TOKENS["default"])
        prompt = float(tokens_prompt or 0)
        completion = float(tokens_completion or 0)
        cost = (prompt / 1000.0) * float(rates["input"]) + (completion / 1000.0) * float(rates["output"])
        return round(cost, 6)

    @staticmethod
    def _static_fallback(contract: WriterContract) -> str:
        response_planner = (
            dict(contract.response_planner) if isinstance(getattr(contract, "response_planner", None), dict) else {}
        )
        planner_next_move = str(response_planner.get("next_move", "") or "")
        planner_answer_shape = str(response_planner.get("answer_shape", "") or "")
        planner_question_policy = str(response_planner.get("question_policy", "") or "")
        planner_practice_policy = str(response_planner.get("practice_policy", "") or "")

        if planner_next_move == "stabilize_safety" or planner_answer_shape == "safety_grounding":
            return "Я рядом. Сейчас важнее чуть стабилизироваться и снизить внутреннюю перегрузку. Без разбора, только опора здесь-и-сейчас."
        if planner_next_move == "give_short_support" or planner_answer_shape == "short_support":
            return "Я рядом. Сейчас не нужно ничего разбирать. Можно просто немного снизить внутреннее давление."
        if planner_next_move == "give_direct_step" or planner_answer_shape == "one_step":
            return "Сделай один шаг прямо сейчас: открой задачу и выполни первый минимальный фрагмент в течение 5 минут."
        if planner_next_move == "close_gently" or planner_answer_shape == "gentle_close":
            return "Пожалуйста. Рад, что стало чуть яснее."
        if planner_next_move == "clarify_one_point" or planner_answer_shape == "one_question":
            return "Если выбрать один узел прямо сейчас, что больше всего сжимает тебя в этой ситуации?"
        if planner_question_policy == "none":
            if planner_practice_policy == "forbidden":
                return "Я рядом. Давай продолжим спокойно, без лишней нагрузки."
            return "Я рядом. Продолжим спокойно."

        mode = contract.thread_state.response_mode
        if mode == "safe_override":
            return "Я здесь. Ты не один."
        if mode == "validate":
            return "Я слышу тебя. Я рядом."
        if mode == "regulate":
            return "Сделай медленный вдох. Я рядом."
        return "Я слышу тебя."

    def _apply_name_continuity(self, response_text: str, contract: WriterContract) -> str:
        """Добавляет обращение по имени, если имя найдено в контексте и отсутствует в ответе."""
        name = self._extract_user_name(contract)
        if not name:
            return response_text
        if name.lower() in response_text.lower():
            return response_text
        return f"{name}, {response_text}"

    def _extract_user_name(self, contract: WriterContract) -> Optional[str]:
        memory_bundle = getattr(contract, "memory_bundle", None)
        conversation_context = ""
        if memory_bundle is not None:
            conversation_context = str(getattr(memory_bundle, "conversation_context", "") or "")
        context = " ".join(
            (
                str(contract.user_message or ""),
                conversation_context,
            )
        )
        if not context.strip():
            return None

        for pattern in _RU_NAME_PATTERNS:
            match = pattern.search(context)
            if match:
                return self._normalize_name(match.group(1))

        for pattern in _EN_NAME_PATTERNS:
            match = pattern.search(context)
            if match:
                return self._normalize_name(match.group(1))

        return None

    @staticmethod
    def _normalize_name(raw_name: str) -> Optional[str]:
        name = (raw_name or "").strip(" .,:;!?\"'()[]{}")
        if len(name) < 2 or len(name) > 31:
            return None
        return name[0].upper() + name[1:]


writer_agent = WriterAgent()


