"""State/runtime helper extraction for adaptive orchestration (Wave 2)."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from ..data_loader import Block
from ..state_classifier import StateAnalysis, UserState, state_classifier
from ..user_level_types import UserLevel
from ..working_state import WorkingState

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SDClassificationResult:
    """Neo-compatible SD slot without active SD runtime classification."""

    primary: str = "NONE"
    secondary: Optional[str] = None
    confidence: float = 0.0
    indicator: str = "disabled_by_design"
    method: str = "disabled"
    allowed_blocks: List[str] = field(default_factory=list)


def _fallback_state_analysis() -> StateAnalysis:
    fallback_state = UserState.CURIOUS
    return StateAnalysis(
        primary_state=fallback_state,
        confidence=0.3,
        secondary_states=[],
        indicators=[],
        emotional_tone="neutral",
        depth="intermediate",
        recommendations=state_classifier._get_recommendations_for_state(fallback_state),
    )


def _fallback_sd_result(reason: str = "fallback_on_error") -> SDClassificationResult:
    return SDClassificationResult(
        primary="NONE",
        secondary=None,
        confidence=0.0,
        indicator=reason,
        method="disabled",
        allowed_blocks=[],
    )


def _resolve_path_user_level(_user_level: str) -> UserLevel:
    """Phase 3: path recommendations use neutral level only."""
    return UserLevel.INTERMEDIATE


async def _classify_parallel(
    user_message: str,
    history_state: List[Dict],
) -> Tuple[StateAnalysis, SDClassificationResult]:
    try:
        state_result = await state_classifier.classify(
            user_message,
            conversation_history=history_state,
        )
    except Exception as exc:
        logger.warning(
            "[CLASSIFY_PARALLEL] StateClassifier failed: %s. Using fallback.",
            exc,
        )
        state_result = _fallback_state_analysis()
    return state_result, _fallback_sd_result("disabled_by_flag")


def _build_state_context(
    state_analysis: StateAnalysis,
    mode_prompt: str,
    nervous_system_state: str = "window",
    request_function: str = "understand",
    contradiction_suggestion: str = "",
    cross_session_context: str = "",
) -> str:
    recommendation = (
        state_analysis.recommendations[0]
        if state_analysis and state_analysis.recommendations
        else "РћС‚РІРµС‚СЊ СЏСЃРЅРѕ, СЃРїРѕРєРѕР№РЅРѕ Рё СЃ РѕРїРѕСЂРѕР№ РЅР° РєРѕРЅС‚РµРєСЃС‚ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ."
    )
    contradiction_block = ""
    if contradiction_suggestion:
        contradiction_block = (
            "\nРЎР“РќРђР› Р РђРЎРҐРћР–Р”Р•РќРЇ:\n"
            f"{contradiction_suggestion}\n"
            "РћС‚РјРµС‚СЊ СЌС‚Рѕ РјСЏРіРєРѕ, Р±РµР· РґР°РІР»РµРЅРёСЏ Рё Р±РµР· Р¶С‘СЃС‚РєРёС… РёРЅС‚РµСЂРїСЂРµС‚Р°С†РёР№.\n"
        )

    cross_session_block = ""
    if cross_session_context:
        cross_session_block = (
            "\nРљРћРќРўР•РљРЎРў Р— РџР РћРЁР›Р«РҐ РЎР•РЎРЎР™:\n"
            f"{cross_session_context}\n"
        )

    return f"""
РљРћРќРўР•РљРЎРў РџРћР›Р¬Р—РћР’РђРўР•Р›РЇ:
- nervous_system_state: {nervous_system_state}
- request_function: {request_function}
- Р­РјРѕС†РёРѕРЅР°Р»СЊРЅС‹Р№ С‚РѕРЅ: {state_analysis.emotional_tone}
- Р“Р»СѓР±РёРЅР° РІРѕРІР»РµС‡РµРЅРёСЏ: {state_analysis.depth}

Р Р•РљРћРњР•РќР”РђР¦РЇ РџРћ РћРўР’Р•РўРЈ:
{recommendation}

{contradiction_block}
{cross_session_block}

Р Р•Р–РњРќРђРЇ Р”Р Р•РљРўР’Рђ:
{mode_prompt}
"""


def _depth_to_phase(depth: str) -> str:
    normalized = (depth or "").lower()
    if "deep" in normalized:
        return "СЂР°Р±РѕС‚Р°"
    if "intermediate" in normalized or "medium" in normalized:
        return "РѕСЃРјС‹СЃР»РµРЅРёРµ"
    return "РЅР°С‡Р°Р»Рѕ РєРѕРЅС‚Р°РєС‚Р°"


def _mode_to_direction(mode: str) -> str:
    mapping = {
        "CLARIFICATION": "СѓС‚РѕС‡РЅРµРЅРёРµ",
        "VALIDATION": "РїРѕРґРґРµСЂР¶РєР°",
        "THINKING": "СЂРµС„Р»РµРєСЃРёСЏ",
        "INTERVENTION": "РґРµР№СЃС‚РІРёРµ",
        "INTEGRATION": "РёРЅС‚РµРіСЂР°С†РёСЏ",
        "PRESENCE": "РґРёР°РіРЅРѕСЃС‚РёРєР°",
    }
    return mapping.get((mode or "PRESENCE").upper(), "РґРёР°РіРЅРѕСЃС‚РёРєР°")


def _derive_defense(state_value: str) -> Optional[str]:
    state = (state_value or "").lower()
    if state == "resistant":
        return "СЃРѕРїСЂРѕС‚РёРІР»РµРЅРёРµ"
    if state == "overwhelmed":
        return "РїРµСЂРµРіСЂСѓР·РєР°"
    if state == "confused":
        return "РЅРµСЏСЃРЅРѕСЃС‚СЊ"
    return None


def _build_working_state(
    *,
    state_analysis: StateAnalysis,
    routing_result,
    memory,
) -> WorkingState:
    return WorkingState(
        dominant_state=state_analysis.primary_state.value,
        emotion=state_analysis.emotional_tone or "neutral",
        defense=_derive_defense(state_analysis.primary_state.value),
        phase=_depth_to_phase(state_analysis.depth),
        direction=_mode_to_direction(routing_result.mode),
        last_updated_turn=len(memory.turns) + 1,
        confidence_level=routing_result.confidence_level,
    )


def _set_working_state_best_effort(
    *,
    memory,
    state_analysis: StateAnalysis,
    routing_result,
    build_working_state_fn,
    logger,
    log_prefix: str,
) -> None:
    try:
        memory.set_working_state(
            build_working_state_fn(
                state_analysis=state_analysis,
                routing_result=routing_result,
                memory=memory,
            )
        )
    except Exception as exc:
        logger.warning("%s %s", log_prefix, exc)


def _looks_like_greeting(query: str) -> bool:
    q = (query or "").strip().lower()
    greetings = {
        "РїСЂРёРІРµС‚",
        "Р·РґСЂР°РІСЃС‚РІСѓР№",
        "Р·РґСЂР°РІСЃС‚РІСѓР№С‚Рµ",
        "РґРѕР±СЂС‹Р№ РґРµРЅСЊ",
        "РґРѕР±СЂС‹Р№ РІРµС‡РµСЂ",
        "РґРѕР±СЂРѕРµ СѓС‚СЂРѕ",
        "hi",
        "hello",
    }
    return q in greetings


def _looks_like_name_intro(query: str) -> bool:
    q = (query or "").strip().lower()
    return bool(re.search(r"\b(РјРµРЅСЏ Р·РѕРІСѓС‚|my name is)\b", q))


def _should_use_fast_path(query: str, routing_result) -> bool:
    if _looks_like_greeting(query) or _looks_like_name_intro(query):
        return True
    tokens = [token for token in re.split(r"\s+", query.strip()) if token]
    if len(tokens) <= 3 and routing_result.mode in {"PRESENCE", "CLARIFICATION"}:
        return True
    return False


def _detect_fast_path_reason(query: str, routing_result) -> str:
    if _looks_like_greeting(query):
        return "greeting"
    if _looks_like_name_intro(query):
        return "name_intro"
    tokens = [token for token in re.split(r"\s+", query.strip()) if token]
    if len(tokens) <= 3 and routing_result.mode in {"PRESENCE", "CLARIFICATION"}:
        return "short_query"
    return "other"


def _build_fast_path_block(
    *,
    query: str,
    conversation_context: str,
    state_analysis: StateAnalysis,
) -> Block:
    return Block(
        block_id="fast-path-runtime-context",
        video_id="runtime",
        start="00:00:00",
        end="00:00:00",
        title="Runtime conversational context",
        summary="Use dialogue context and user message only. No lecture citation required.",
        content=(
            "FAST PATH CONTEXT\n"
            "This user turn should be handled without lecture retrieval.\n\n"
            f"USER MESSAGE:\n{query}\n\n"
            f"DIALOGUE CONTEXT:\n{conversation_context[:1500]}\n\n"
            f"USER STATE:\n{state_analysis.primary_state.value}, "
            f"{state_analysis.emotional_tone}, depth={state_analysis.depth}\n"
        ),
        keywords=["fast-path", "context"],
        youtube_link="",
        document_title="Runtime",
        block_type="dialogue",
        emotional_tone=state_analysis.emotional_tone or "neutral",
        conceptual_depth="low",
        complexity_score=0.1,
        graph_entities=[],
    )
