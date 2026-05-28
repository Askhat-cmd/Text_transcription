"""Writer Agent for NEO multi-agent runtime."""

from __future__ import annotations

import logging
import re
import time
from typing import Any, Optional

from ...config import config
from ...feature_flags import feature_flags
from ..active_line import starts_with_mechanical_revoicing
from ..prompt_constraint_section import format_prompt_constraint_section_v1
from ..contracts.writer_contract import WriterContract
from .agent_llm_client import create_agent_completion
from .agent_llm_config import get_model_for_agent, get_temperature_for_agent
from .writer_agent_prompts import WRITER_SYSTEM, WRITER_USER_TEMPLATE


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

    def _resolve_runtime_settings(self) -> dict[str, Any]:
        model = self._resolve_model()
        return {
            "model": model,
            "timeout": _to_float(
                feature_flags.value("MULTIAGENT_LLM_TIMEOUT", str(WRITER_TIMEOUT_DEFAULT)),
                WRITER_TIMEOUT_DEFAULT,
            ),
            "max_tokens": _to_int(
                feature_flags.value(
                    "MULTIAGENT_MAX_TOKENS",
                    feature_flags.value("WRITER_MAX_TOKENS", str(WRITER_MAX_TOKENS_DEFAULT)),
                ),
                WRITER_MAX_TOKENS_DEFAULT,
            ),
            "temperature": get_temperature_for_agent("writer"),
        }

    async def write(
        self,
        contract: WriterContract,
        *,
        prompt_constraint_decision: dict[str, Any] | None = None,
    ) -> str:
        """Write one answer text with safe fallback behavior."""
        runtime_settings = self._resolve_runtime_settings()
        self.last_debug = {
            "model": runtime_settings["model"],
            "api_mode": None,
            "temperature": runtime_settings["temperature"],
            "max_tokens": runtime_settings["max_tokens"],
            "timeout": runtime_settings["timeout"],
            "system_prompt": WRITER_SYSTEM,
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
            "true: no_exercise_no_breathing_no_body_practice_no_microstep_without_explicit_request_or_safety_override"
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
            diagnostic_card_summary=self._format_diagnostic_summary(ctx.get("diagnostic_card_summary")),
            diagnostic_card_avoid=", ".join(ctx.get("diagnostic_card_avoid_list", []) or []) or "нет",
            diagnostic_card_risk_flags=", ".join(ctx.get("diagnostic_card_risk_flags", []) or []) or "нет",
            writer_move_instruction_summary=ctx.get("writer_move_instruction_summary") or "нет",
            writer_move_must_do=", ".join(ctx.get("writer_move_must_do", []) or []) or "нет",
            writer_move_must_not_do=", ".join(ctx.get("writer_move_must_not_do", []) or []) or "нет",
            conversation_context=(ctx["conversation_context"] or "нет")[:2000],
            user_profile_patterns=", ".join(ctx["user_profile_patterns"]) or "нет",
            user_profile_values=", ".join(ctx["user_profile_values"]) or "нет",
            semantic_hits=self._format_hits(ctx["semantic_hits"]),
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

        start_ts = time.perf_counter()
        runtime_settings = self._resolve_runtime_settings()
        result = await create_agent_completion(
            client=client,
            model=runtime_settings["model"],
            messages=[
                {"role": "system", "content": WRITER_SYSTEM},
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
        planner_question_policy = str(response_planner.get("question_policy", "none") or "none")
        planner_practice_policy = str(response_planner.get("practice_policy", "forbidden") or "forbidden")
        planner_safety_priority = bool(response_planner.get("safety_priority", False))
        lowered_text = text.lower()

        has_unsolicited_practice = any(marker in lowered_text for marker in _PRACTICE_MARKERS)
        has_question = "?" in text
        asks_define_known_term = any(marker in lowered_text for marker in _KNOWN_CONCEPT_CLARIFICATION_MARKERS)
        has_external_surveillance_frame = any(marker in lowered_text for marker in _EXTERNAL_SURVEILLANCE_MARKERS)

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

        if planner_question_policy == "none" and has_question:
            return re.sub(r"\s*\?+\s*", ". ", text).strip()

        if planner_practice_policy == "forbidden" and has_unsolicited_practice:
            if active_line_intent == "understand_mechanism":
                return (
                    "Сейчас полезнее удержать фокус на механизме: попытка заранее все проконтролировать "
                    "съедает ресурс еще до старта действия."
                )
            return "Сейчас лучше продолжить смысловую линию без перехода к практике."

        if active_line_practice_suppression and not active_line_should_offer_practice and has_unsolicited_practice:
            if active_line_intent == "correction_of_bot" or active_line_repair_mode:
                return (
                    "Да, ты прав: я слишком рано сдвинулся в действие. "
                    "Тут важнее вернуться к механизму застревания и его разбору."
                )
            if active_line_intent == "understand_mechanism":
                return (
                    "Здесь важнее увидеть механизм: прогнозирование и контроль пытаются снизить риск, "
                    "но забирают ресурс еще до начала действия."
                )
            return "Сейчас лучше остаться в разборе смысла и механизма, без перехода к действиям."

        if not active_line_revoicing_allowed and starts_with_mechanical_revoicing(text):
            if active_line_intent == "correction_of_bot" or active_line_repair_mode:
                return (
                    "Да, здесь я сдвинулся не туда. Вернусь к сути: не к практике, "
                    "а к механизму, из-за которого ты застреваешь."
                )
            if active_line_intent == "understand_mechanism":
                return (
                    "Смысловой узел тут не в пересказе вопроса, а в том, "
                    "как попытка заранее обезопасить старт съедает энергию до действия."
                )
            parts = re.split(r"(?<=[.!?])\s+", text, maxsplit=1)
            if len(parts) == 2 and parts[1].strip():
                return parts[1].strip()

        # Known concept answer-first path: enforce direct internal meaning framing.
        if should_answer_directly and (asks_define_known_term or has_external_surveillance_frame):
            if "самореализац" in lowered_user and ("коррелир" in lowered_user or "связан" in lowered_user):
                return (
                    "Если держаться внутреннего смысла термина, Нейросталкинг связан с самореализацией через "
                    "снятие автопилота. Самореализация требует проявляться и выбирать своё направление, а "
                    "Нейросталкинг помогает заметить паттерны, триггеры и автоматические реакции, которые "
                    "мешают проявляться и действовать из авторства."
                )
            if concept == "нейросталкинг":
                return (
                    "В нашей внутренней рамке Нейросталкинг — это наблюдение за паттернами, триггерами и "
                    "автоматическими реакциями: как включается программа и где запускается страдание, чтобы "
                    "не сливаться с реакцией полностью."
                )
            if concept == "самореализация":
                return (
                    "В нашей внутренней рамке самореализация — это раскрытие потенциала через осознанный выбор "
                    "и авторство, а не повторение автоматических паттернов."
                )
        return text

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
        mode = contract.thread_state.response_mode
        if mode == "safe_override":
            return "Я здесь. Ты не один."
        if mode == "validate":
            return "Я слышу тебя. Расскажи больше, если хочешь."
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
