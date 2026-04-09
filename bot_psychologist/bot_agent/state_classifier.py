# bot_agent/state_classifier.py
"""
State Classifier Module (Phase 4.1)
===================================

РљР»Р°СЃСЃРёС„РёРєР°С†РёСЏ РїСЃРёС…РѕР»РѕРіРёС‡РµСЃРєРѕРіРѕ СЃРѕСЃС‚РѕСЏРЅРёСЏ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ.
10 СЃРѕСЃС‚РѕСЏРЅРёР№ РѕС‚ UNAWARE РґРѕ INTEGRATED.
Keyword + LLM Р°РЅР°Р»РёР· РґР»СЏ С‚РѕС‡РЅРѕСЃС‚Рё РѕРїСЂРµРґРµР»РµРЅРёСЏ.
"""

import asyncio
import logging
import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from .llm_answerer import LLMAnswerer
from .config import config
from .fast_detector import detect_user_state
from .feature_flags import feature_flags

logger = logging.getLogger(__name__)


class UserState(Enum):
    """
    РЎРѕСЃС‚РѕСЏРЅРёСЏ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ РІ РїСЂРѕС†РµСЃСЃРµ С‚СЂР°РЅСЃС„РѕСЂРјР°С†РёРё.
    
    РџСЂРѕРіСЂРµСЃСЃРёСЏ: UNAWARE -> CURIOUS -> ... -> INTEGRATED
    """
    UNAWARE = "unaware"              # РќРµ РѕСЃРѕР·РЅР°РµС‚ РїСЂРѕР±Р»РµРјСѓ
    CURIOUS = "curious"              # Р›СЋР±РѕРїС‹С‚СЃС‚РІРѕ, РёРЅС‚РµСЂРµСЃ
    OVERWHELMED = "overwhelmed"      # РџРµСЂРµРіСЂСѓР¶РµРЅ РёРЅС„РѕСЂРјР°С†РёРµР№
    RESISTANT = "resistant"          # РЎРѕРїСЂРѕС‚РёРІР»РµРЅРёРµ
    CONFUSED = "confused"            # Р—Р°РїСѓС‚Р°РЅРЅРѕСЃС‚СЊ
    COMMITTED = "committed"          # Р“РѕС‚РѕРІ Рє СЂР°Р±РѕС‚Рµ
    PRACTICING = "practicing"        # РџСЂР°РєС‚РёРєСѓРµС‚
    STAGNANT = "stagnant"            # Р—Р°СЃС‚РѕР№, РїР»Р°С‚Рѕ
    BREAKTHROUGH = "breakthrough"    # РџСЂРѕСЂС‹РІ
    INTEGRATED = "integrated"        # РРЅС‚РµРіСЂРёСЂРѕРІР°Р» Р·РЅР°РЅРёРµ


@dataclass
class StateAnalysis:
    """Р РµР·СѓР»СЊС‚Р°С‚ Р°РЅР°Р»РёР·Р° СЃРѕСЃС‚РѕСЏРЅРёСЏ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ"""
    primary_state: UserState
    confidence: float  # 0.0-1.0
    secondary_states: List[UserState]
    indicators: List[str]  # РєРѕРЅРєСЂРµС‚РЅС‹Рµ РёРЅРґРёРєР°С‚РѕСЂС‹ СЃРѕСЃС‚РѕСЏРЅРёСЏ
    emotional_tone: str  # contemplative, frustrated, excited, calm, confused
    depth: str  # surface, intermediate, deep
    recommendations: List[str]  # С‡С‚Рѕ РґРµР»Р°С‚СЊ РІ СЌС‚РѕРј СЃРѕСЃС‚РѕСЏРЅРёРё


@dataclass(frozen=True)
class StateClassifierResult:
    """Runtime-facing Neo output contract for routing/diagnostics."""

    nervous_system_state: str
    request_function: str
    confidence: float
    raw_label: str


VALID_NSS = {"hyper", "window", "hypo"}
VALID_REQUEST_FUNCTIONS = {
    "discharge",
    "understand",
    "solution",
    "validation",
    "explore",
    "contact",
}


class StateClassifier:
    """
    РљР»Р°СЃСЃРёС„РёС†РёСЂСѓРµС‚ СЃРѕСЃС‚РѕСЏРЅРёРµ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ РЅР° РѕСЃРЅРѕРІРµ:
    1. РЎРѕРґРµСЂР¶Р°РЅРёСЏ РІРѕРїСЂРѕСЃР°
    2. РСЃС‚РѕСЂРёРё РґРёР°Р»РѕРіР°
    3. Р›РёРЅРіРІРёСЃС‚РёС‡РµСЃРєРёС… СЃРёРіРЅР°Р»РѕРІ
    4. РЇРІРЅРѕ СѓРєР°Р·Р°РЅРЅРѕР№ РѕР±СЂР°С‚РЅРѕР№ СЃРІСЏР·Рё
    """
    
    def __init__(self):
        self.llm = LLMAnswerer()
        self.state_indicators = self._init_state_indicators()
    
    def _init_state_indicators(self) -> Dict[UserState, List[str]]:
        """РРЅРёС†РёР°Р»РёР·РёСЂРѕРІР°С‚СЊ РёРЅРґРёРєР°С‚РѕСЂС‹ РґР»СЏ РєР°Р¶РґРѕРіРѕ СЃРѕСЃС‚РѕСЏРЅРёСЏ"""
        return {
            UserState.UNAWARE: [
                "С‡С‚Рѕ С‚Р°РєРѕРµ", "РєР°РєРѕР№ СЃРјС‹СЃР»", "Р·Р°С‡РµРј", "РЅРµ РїРѕРЅРёРјР°СЋ",
                "РІ С‡РµРј СЃСѓС‚СЊ", "РѕР±СЉСЏСЃРЅРё", "СЌС‚Рѕ РІР°Р¶РЅРѕ?", "С‡С‚Рѕ СЌС‚Рѕ",
                "РґР»СЏ С‡РµРіРѕ", "РЅРµ СЃР»С‹С€Р°Р»", "РїРµСЂРІС‹Р№ СЂР°Р·"
            ],
            UserState.CURIOUS: [
                "РёРЅС‚РµСЂРµСЃРЅРѕ", "С…РѕС‡Сѓ СѓР·РЅР°С‚СЊ", "СЂР°СЃСЃРєР°Р¶Рё РїРѕРґСЂРѕР±РЅРµРµ",
                "Р° РєР°Рє", "РїРѕС‡РµРјСѓ", "СЃРІСЏР·СЊ РјРµР¶РґСѓ", "РєР°Рє СЌС‚Рѕ СЂР°Р±РѕС‚Р°РµС‚",
                "СЂР°СЃСЃРєР°Р¶Рё Р±РѕР»СЊС€Рµ", "Р»СЋР±РѕРїС‹С‚РЅРѕ", "С…РѕС‚РµР»РѕСЃСЊ Р±С‹ РїРѕРЅСЏС‚СЊ"
            ],
            UserState.OVERWHELMED: [
                "СЃР»РёС€РєРѕРј РјРЅРѕРіРѕ", "РЅРµ РјРѕРіСѓ РїРѕРЅСЏС‚СЊ", "Р·Р°РїСѓС‚Р°Р»СЃСЏ", "СЃР»РѕР¶РЅРѕ",
                "РїРѕРјРѕС‰СЊ", "РєР°Рє РЅР°С‡Р°С‚СЊ", "РѕС‚РєСѓРґР° РЅР°С‡РёРЅР°С‚СЊ", "РіРґРµ РЅР°С‡Р°Р»Рѕ",
                "РЅРµ Р·РЅР°СЋ СЃ С‡РµРіРѕ", "С‚РµСЂСЏСЋСЃСЊ", "РјРЅРѕРіРѕ РІСЃРµРіРѕ", "РіРѕР»РѕРІР° РєСЂСѓРіРѕРј"
            ],
            UserState.RESISTANT: [
                "РЅРµ РІРµСЂСЋ", "РЅРµ СЃРѕРіР»Р°СЃРµРЅ", "РЅРѕ РІРµРґСЊ", "РѕРґРЅР°РєРѕ",
                "СЌС‚Рѕ РЅРµРІРѕР·РјРѕР¶РЅРѕ", "Сѓ РјРµРЅСЏ РЅРµ РїРѕР»СѓС‡РёС‚СЃСЏ", "СЌС‚Рѕ РґР»СЏ РґСЂСѓРіРёС…",
                "СЃРѕРјРЅРµРІР°СЋСЃСЊ", "РЅРµ СѓРІРµСЂРµРЅ С‡С‚Рѕ", "СЃРєРµРїС‚РёС‡РµСЃРєРё", "РµСЂСѓРЅРґР°"
            ],
            UserState.CONFUSED: [
                "РЅРµ РїРѕРЅСЏР»", "РїСѓС‚Р°СЋСЃСЊ", "РїСЂРѕС‚РёРІРѕСЂРµС‡РёС‚", "РЅРµСЃРѕРІРјРµСЃС‚РёРјРѕ",
                "РїСЂРѕС‚РёРІРѕСЂРµС‡РёРІРѕ", "РґРѕРїРѕР»РЅРёС‚РµР»СЊРЅРѕ", "СѓС‚РѕС‡РЅРё", "РµС‰Рµ СЂР°Р·",
                "РєР°Рє СЌС‚Рѕ СЃРІСЏР·Р°РЅРѕ", "РЅРµ РІРёР¶Сѓ СЃРІСЏР·Рё", "РѕРґРЅРѕ РїСЂРѕС‚РёРІРѕСЂРµС‡РёС‚"
            ],
            UserState.COMMITTED: [
                "РіРѕС‚РѕРІ", "С…РѕС‡Сѓ", "РЅР°С‡РёРЅР°СЋ", "Р±СѓРґСѓ", "СЃРѕРіР»Р°СЃРµРЅ",
                "РїРѕРЅСЏР»", "РїРѕР№РґСѓ", "РїРѕРїСЂРѕР±СѓСЋ", "СЂРµС€РёР»", "РїСЂРёСЃС‚СѓРїР°СЋ",
                "РґР°РІР°Р№ РЅР°С‡РЅРµРј", "СЃ С‡РµРіРѕ РЅР°С‡Р°С‚СЊ", "РіРѕС‚РѕРІ РґРµР№СЃС‚РІРѕРІР°С‚СЊ"
            ],
            UserState.PRACTICING: [
                "РїСЂРѕР±СѓСЋ", "РґРµР»Р°СЋ", "РїСЂР°РєС‚РёРєСѓСЋ", "Р·Р°РЅРёРјР°СЋСЃСЊ", "СЂР°Р±РѕС‚Р°СЋ",
                "РїРѕР»СѓС‡Р°РµС‚СЃСЏ", "РЅРµ РїРѕР»СѓС‡Р°РµС‚СЃСЏ", "Р·Р°РјРµС‡Р°СЋ", "РІРёР¶Сѓ", "С‡СѓРІСЃС‚РІСѓСЋ",
                "Р·Р°РјРµС‚РёР» С‡С‚Рѕ", "РєРѕРіРґР° РґРµР»Р°СЋ", "РІ РїСЂРѕС†РµСЃСЃРµ РїСЂР°РєС‚РёРєРё"
            ],
            UserState.STAGNANT: [
                "РЅРёС‡РµРіРѕ РЅРµ РјРµРЅСЏРµС‚СЃСЏ", "Р·Р°СЃС‚СЂСЏР»", "РїР»Р°С‚Рѕ", "РѕРґРЅРѕ Рё С‚Рѕ Р¶Рµ",
                "СЃРєСѓС‡РЅРѕ", "РЅРµ РІРёР¶Сѓ СЂРµР·СѓР»СЊС‚Р°С‚Р°", "Р·Р°С‡РµРј РґР°Р»СЊС€Рµ", "СЃРѕРјРЅРµРІР°СЋСЃСЊ",
                "С‚РѕРїС‡СѓСЃСЊ РЅР° РјРµСЃС‚Рµ", "РЅРµС‚ РїСЂРѕРіСЂРµСЃСЃР°", "СѓСЃС‚Р°Р»", "РЅР°РґРѕРµР»Рѕ"
            ],
            UserState.BREAKTHROUGH: [
                "РїРѕРЅСЏР»", "РїСЂРѕСЂС‹РІ", "РІРЅРµР·Р°РїРЅРѕ", "РѕР·Р°СЂРµРЅРёРµ", "РёРЅСЃР°Р№С‚",
                "РІСЃРµ РІСЃС‚Р°Р»Рѕ РЅР° РјРµСЃС‚Рѕ", "РІР°Сѓ", "Р°С…РјРѕРјРµРЅС‚", "С‚РµРїРµСЂСЊ СЏ РІРёР¶Сѓ",
                "РґРѕС€Р»Рѕ", "РѕСЃРµРЅРёР»Рѕ", "РЅР°РєРѕРЅРµС† РїРѕРЅСЏР»", "Р°РіР°-РјРѕРјРµРЅС‚"
            ],
            UserState.INTEGRATED: [
                "РїСЂРёРјРµРЅСЏСЋ", "РёСЃРїРѕР»СЊР·СѓСЋ", "СѓР¶Рµ РЅРµ РґСѓРјР°СЋ", "РµСЃС‚РµСЃС‚РІРµРЅРЅРѕ",
                "СЌС‚Рѕ С‡Р°СЃС‚СЊ РјРµРЅСЏ", "РїСЂРѕСЃС‚Рѕ РґРµР»Р°СЋ", "РїРѕРјРЅСЋ РІСЃРµРіРґР°",
                "Р°РІС‚РѕРјР°С‚РёС‡РµСЃРєРё", "Р±РµР· СѓСЃРёР»РёР№", "СЃР°РјРѕ СЃРѕР±РѕР№", "Р¶РёРІСѓ СЌС‚РёРј"
            ]
        }

    def _map_state_to_nss(self, state: UserState, tone: str = "") -> str:
        state_value = str(getattr(state, "value", "") or "").lower()
        tone_value = str(tone or "").lower()
        if state_value in {"overwhelmed", "resistant"}:
            return "hyper"
        if state_value in {"stagnant"}:
            return "hypo"
        if any(token in tone_value for token in ("panic", "anxiety", "frustrat", "urgent")):
            return "hyper"
        if any(token in tone_value for token in ("numb", "shutdown", "flat", "apathy")):
            return "hypo"
        return "window"

    def _detect_request_function(self, text: str) -> str:
        lowered = (text or "").lower()
        if any(token in lowered for token in ("выговориться", "выплеснуть", "просто сказать")):
            return "discharge"
        if any(token in lowered for token in ("что делать", "как поступить", "дай шаги", "план")):
            return "solution"
        if any(token in lowered for token in ("я прав", "подтверди", "нормально ли")):
            return "validation"
        if any(token in lowered for token in ("побудь со мной", "ты рядом", "нужна поддержка")):
            return "contact"
        if any(token in lowered for token in ("почему", "что со мной", "как это связано")):
            return "explore"
        return "understand"

    def _to_runtime_result(self, analysis: StateAnalysis, text: str) -> StateClassifierResult:
        nss = self._map_state_to_nss(analysis.primary_state, analysis.emotional_tone)
        request_function = self._detect_request_function(text)
        if nss not in VALID_NSS:
            nss = "window"
        if request_function not in VALID_REQUEST_FUNCTIONS:
            request_function = "understand"
        return StateClassifierResult(
            nervous_system_state=nss,
            request_function=request_function,
            confidence=max(0.0, min(1.0, float(analysis.confidence))),
            raw_label=analysis.primary_state.value,
        )
    
    def analyze_message(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict]] = None
    ) -> StateAnalysis:
        """
        РђРЅР°Р»РёР·РёСЂСѓРµС‚ СЃРѕСЃС‚РѕСЏРЅРёРµ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ РїРѕ СЃРѕРѕР±С‰РµРЅРёСЋ Рё РёСЃС‚РѕСЂРёРё.
        
        Args:
            user_message: РџРѕСЃР»РµРґРЅРµРµ СЃРѕРѕР±С‰РµРЅРёРµ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ
            conversation_history: РСЃС‚РѕСЂРёСЏ РґРёР°Р»РѕРіР° [{"role": "user", "content": ...}, ...]
        
        Returns:
            StateAnalysis СЃ РґРµС‚Р°Р»СЊРЅРѕР№ РёРЅС„РѕСЂРјР°С†РёРµР№
        """
        logger.info(f"рџЋЇ РђРЅР°Р»РёР·РёСЂСѓСЋ СЃРѕСЃС‚РѕСЏРЅРёРµ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ...")

        # === ЭТАП 0: fast detector для очевидных случаев ===
        fast = detect_user_state(user_message) if feature_flags.enabled("ENABLE_FAST_STATE_DETECTOR") else None
        if fast and fast.confidence >= 0.85:
            try:
                fast_state = UserState(fast.label.lower())
            except ValueError:
                fast_state = UserState.CURIOUS
            fast_analysis = StateAnalysis(
                primary_state=fast_state,
                confidence=float(fast.confidence),
                secondary_states=[],
                indicators=[fast.indicator],
                emotional_tone="neutral",
                depth="surface",
                recommendations=self._get_recommendations_for_state(fast_state),
            )
            fast_runtime = self._to_runtime_result(fast_analysis, user_message)
            logger.info(
                "STATE nss=%s fn=%s conf=%.2f",
                fast_runtime.nervous_system_state,
                fast_runtime.request_function,
                fast_runtime.confidence,
            )
            return fast_analysis
        
        # === Р­РўРђРџ 1: РђРЅР°Р»РёР· С‚РµРєСѓС‰РµРіРѕ СЃРѕРѕР±С‰РµРЅРёСЏ РїРѕ РєР»СЋС‡РµРІС‹Рј СЃР»РѕРІР°Рј ===
        primary_state, confidence = self._classify_by_keywords(user_message)
        logger.debug(f"   РџРµСЂРІРёС‡РЅРѕРµ СЃРѕСЃС‚РѕСЏРЅРёРµ: {primary_state.value} (СѓРІРµСЂРµРЅРЅРѕСЃС‚СЊ: {confidence:.2f})")
        
        # === Р­РўРђРџ 2: РђРЅР°Р»РёР· С‡РµСЂРµР· LLM РґР»СЏ СѓС‚РѕС‡РЅРµРЅРёСЏ ===
        llm_analysis = self._classify_by_llm(user_message, conversation_history)
        logger.debug(f"   LLM Р°РЅР°Р»РёР·: {llm_analysis}")
        
        # === Р­РўРђРџ 3: РћР±СЉРµРґРёРЅРµРЅРёРµ СЂРµР·СѓР»СЊС‚Р°С‚РѕРІ ===
        final_analysis = self._merge_classifications(
            primary_state, confidence, llm_analysis
        )
        
        # === Р­РўРђРџ 4: РћРїСЂРµРґРµР»РµРЅРёРµ СЂРµРєРѕРјРµРЅРґР°С†РёР№ ===
        final_analysis.recommendations = self._get_recommendations_for_state(
            final_analysis.primary_state
        )

        runtime_result = self._to_runtime_result(final_analysis, user_message)
        logger.info(
            "STATE nss=%s fn=%s conf=%.2f",
            runtime_result.nervous_system_state,
            runtime_result.request_function,
            runtime_result.confidence,
        )
        
        return final_analysis

    async def classify(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict]] = None,
    ) -> StateAnalysis:
        """Async wrapper for parallel classification."""
        return await asyncio.to_thread(
            self.analyze_message,
            user_message,
            conversation_history,
        )

    async def classify_runtime(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict]] = None,
    ) -> StateClassifierResult:
        analysis = await self.classify(
            user_message=user_message,
            conversation_history=conversation_history,
        )
        return self._to_runtime_result(analysis, user_message)
    
    def _classify_by_keywords(
        self,
        message: str
    ) -> Tuple[UserState, float]:
        """
        РџСЂРѕСЃС‚Р°СЏ РєР»Р°СЃСЃРёС„РёРєР°С†РёСЏ РїРѕ РєР»СЋС‡РµРІС‹Рј СЃР»РѕРІР°Рј.
        Р’РѕР·РІСЂР°С‰Р°РµС‚ (СЃРѕСЃС‚РѕСЏРЅРёРµ, СѓРІРµСЂРµРЅРЅРѕСЃС‚СЊ).
        """
        message_lower = message.lower()
        state_scores: Dict[UserState, int] = {}
        
        for state, keywords in self.state_indicators.items():
            score = sum(1 for kw in keywords if kw in message_lower)
            if score > 0:
                state_scores[state] = score
        
        if not state_scores:
            return UserState.CURIOUS, 0.3  # РґРµС„РѕР»С‚
        
        # РќР°С…РѕРґРёРј СЃРѕСЃС‚РѕСЏРЅРёРµ СЃ РјР°РєСЃРёРјР°Р»СЊРЅС‹Рј score
        primary_state = max(state_scores, key=lambda s: state_scores[s])
        max_score = state_scores[primary_state]
        
        # РЈРІРµСЂРµРЅРЅРѕСЃС‚СЊ = (РєРѕР»-РІРѕ СЃРѕРІРїР°РґРµРЅРёР№) / (РјР°РєСЃ РІРѕР·РјРѕР¶РЅРѕ)
        confidence = min(max_score / len(self.state_indicators[primary_state]), 1.0)
        
        return primary_state, confidence
    
    def _classify_by_llm(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict]]
    ) -> Dict:
        """
        РђРЅР°Р»РёР·РёСЂСѓРµС‚ СЃРѕСЃС‚РѕСЏРЅРёРµ С‡РµСЂРµР· LLM РґР»СЏ Р±РѕР»СЊС€РµР№ С‚РѕС‡РЅРѕСЃС‚Рё.
        """
        if not self.llm.client:
            logger.warning("вљ пёЏ LLM РЅРµРґРѕСЃС‚СѓРїРµРЅ, РїСЂРѕРїСѓСЃРєР°СЋ LLM-РєР»Р°СЃСЃРёС„РёРєР°С†РёСЋ")
            return {}
        
        # Р¤РѕСЂРјРёСЂСѓРµРј РєРѕРЅС‚РµРєСЃС‚ РёСЃС‚РѕСЂРёРё
        history_context = ""
        if conversation_history:
            for turn in conversation_history[-3:]:  # РїРѕСЃР»РµРґРЅРёРµ 3 С…РѕРґР°
                role = turn.get("role", "user")
                content = turn.get("content", "")[:200]
                history_context += f"{role}: {content}\n"
        
        prompt = f"""Analyze the user's psychological/emotional state in the context of consciousness transformation and neurostalking practice.

{f"Recent conversation history:\\n{history_context}" if history_context else ""}

Current user message: "{user_message}"

Determine:
1. Primary state (unaware, curious, overwhelmed, resistant, confused, committed, practicing, stagnant, breakthrough, integrated)
2. Confidence (0.0-1.0)
3. Secondary states (list up to 2)
4. Emotional tone (contemplative, frustrated, excited, calm, confused, hopeful, skeptical)
5. Depth of engagement (surface, intermediate, deep)
6. Specific indicators in the text that suggest this state

Respond ONLY in valid JSON format (no markdown, no explanations):
{{
  "primary_state": "...",
  "confidence": 0.85,
  "secondary_states": ["...", "..."],
  "emotional_tone": "...",
  "depth": "...",
  "indicators": ["indicator1", "indicator2"]
}}"""
        
        try:
            token_param = config.get_token_param_name(config.CLASSIFIER_MODEL)
            request_params = {
                "model": config.CLASSIFIER_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                token_param: 4000,
                "response_format": {"type": "json_object"},
            }
            if config.supports_custom_temperature(config.CLASSIFIER_MODEL):
                request_params["temperature"] = 0.3
            response = self.llm.client.chat.completions.create(**request_params)
            
            # Безопасное извлечение контента — GPT-5 может вернуть None
            raw_content = response.choices[0].message.content
            content = (raw_content or "").strip()

            # Очистка markdown-обёртки (```json ... ``` или ``` ... ```)
            if "```" in content:
                import re
                content = re.sub(r"```(?:json)?\s*", "", content).strip()

            # Защита от пустого ответа — GPT-5 mini иногда возвращает пустую строку
            if not content:
                logger.warning("⚠️ LLM вернул пустой ответ при классификации состояния")
                return {}

            result = json.loads(content)
            return result

        except json.JSONDecodeError as e:
            logger.debug(f"🔍 JSON parse miss (нормально для коротких сообщений): {e}")
            return {}
        except Exception as e:
            logger.warning(f"вљ пёЏ LLM РєР»Р°СЃСЃРёС„РёРєР°С†РёСЏ РЅРµ СѓРґР°Р»Р°СЃСЊ: {e}")
            return {}
    
    def _merge_classifications(
        self,
        keyword_state: UserState,
        keyword_confidence: float,
        llm_analysis: Dict
    ) -> StateAnalysis:
        """
        РћР±СЉРµРґРёРЅСЏРµС‚ СЂРµР·СѓР»СЊС‚Р°С‚С‹ keyword Рё LLM РєР»Р°СЃСЃРёС„РёРєР°С†РёРё.
        """
        # Р•СЃР»Рё LLM РІРµСЂРЅСѓР» СЂРµР·СѓР»СЊС‚Р°С‚
        if llm_analysis.get("primary_state"):
            try:
                primary_state = UserState(llm_analysis["primary_state"])
                confidence = float(llm_analysis.get("confidence", 0.7))
            except (ValueError, KeyError):
                primary_state = keyword_state
                confidence = keyword_confidence
        else:
            primary_state = keyword_state
            confidence = keyword_confidence
        
        # Р’С‚РѕСЂРёС‡РЅС‹Рµ СЃРѕСЃС‚РѕСЏРЅРёСЏ
        secondary_states: List[UserState] = []
        if llm_analysis.get("secondary_states"):
            for state_name in llm_analysis["secondary_states"]:
                try:
                    secondary_states.append(UserState(state_name))
                except ValueError:
                    pass
        
        return StateAnalysis(
            primary_state=primary_state,
            confidence=confidence,
            secondary_states=secondary_states,
            indicators=llm_analysis.get("indicators", []),
            emotional_tone=llm_analysis.get("emotional_tone", "neutral"),
            depth=llm_analysis.get("depth", "intermediate"),
            recommendations=[]
        )
    
    def _get_recommendations_for_state(self, state: UserState) -> List[str]:
        """
        Р’РѕР·РІСЂР°С‰Р°РµС‚ СЂРµРєРѕРјРµРЅРґР°С†РёРё РґР»СЏ РєРѕРЅРєСЂРµС‚РЅРѕРіРѕ СЃРѕСЃС‚РѕСЏРЅРёСЏ.
        """
        recommendations = {
            UserState.UNAWARE: [
                "РћР±СЉСЏСЃРЅРё СЃ РїСЂРѕСЃС‚С‹С… РїСЂРёРјРµСЂРѕРІ",
                "РџРѕРєР°Р¶Рё РїСЂР°РєС‚РёС‡РµСЃРєРѕРµ РїСЂРёРјРµРЅРµРЅРёРµ",
                "РџСЂРµРґР»РѕР¶Рё РїРµСЂРІС‹Р№ С€Р°Рі",
                "РќРµ РїРµСЂРµРіСЂСѓР¶Р°Р№ РёРЅС„РѕСЂРјР°С†РёРµР№"
            ],
            UserState.CURIOUS: [
                "Р Р°Р·РІРёРІР°Р№ РёРЅС‚РµСЂРµСЃ",
                "РџРѕРєР°Р¶Рё РіР»СѓР±РёРЅСѓ С‚РµРјС‹",
                "РџСЂРµРґР»РѕР¶Рё РґР°Р»СЊРЅРµР№С€РµРµ РёСЃСЃР»РµРґРѕРІР°РЅРёРµ",
                "Р РµРєРѕРјРµРЅРґСѓР№ РїСЂР°РєС‚РёРєРё"
            ],
            UserState.OVERWHELMED: [
                "РЈРїСЂРѕСЃС‚Рё РѕР±СЉСЏСЃРЅРµРЅРёРµ",
                "Р Р°Р·Р±РµР№ РЅР° РјР°Р»РµРЅСЊРєРёРµ С€Р°РіРё",
                "РЎРѕСЃСЂРµРґРѕС‚РѕС‡СЊСЃСЏ РЅР° РѕРґРЅРѕРј",
                "РџСЂРµРґР»РѕР¶Рё СЂРµСЃСѓСЂСЃС‹ РґР»СЏ СЃР°РјРѕСѓСЃРїРѕРєРѕРµРЅРёСЏ"
            ],
            UserState.RESISTANT: [
                "РЎР»СѓС€Р°Р№ Р±РµР· СЃСѓР¶РґРµРЅРёР№",
                "РџРѕРєР°Р¶Рё РґРѕРєР°Р·Р°С‚РµР»СЊСЃС‚РІР°",
                "РџСЂРµРґР»РѕР¶Рё Р°Р»СЊС‚РµСЂРЅР°С‚РёРІРЅС‹Рµ РїРѕРґС…РѕРґС‹",
                "РСЃРїРѕР»СЊР·СѓР№ РµРіРѕ СЏР·С‹Рє"
            ],
            UserState.CONFUSED: [
                "РЈС‚РѕС‡РЅРё РѕСЃРЅРѕРІРЅС‹Рµ РєРѕРЅС†РµРїС‚С‹",
                "Р”Р°Р№ РїСЂР°РєС‚РёС‡РµСЃРєРёРµ РїСЂРёРјРµСЂС‹",
                "РџРµСЂРµСЃРєР°Р·Р°С‚СЊ РїРѕ-РґСЂСѓРіРѕРјСѓ",
                "РќР°Р№РґРё РёСЃС‚РѕС‡РЅРёРє РїСѓС‚Р°РЅРёС†С‹"
            ],
            UserState.COMMITTED: [
                "Р”Р°Р№ С‡РµС‚РєРёР№ РїР»Р°РЅ РґРµР№СЃС‚РІРёР№",
                "РџСЂРµРґР»РѕР¶Рё РїСЂР°РєС‚РёРєРё",
                "РџРѕРґРґРµСЂР¶Рё СЌРЅС‚СѓР·РёР°Р·Рј",
                "РЈСЃС‚Р°РЅРѕРІРё РІРµС…Рё РїСЂРѕРіСЂРµСЃСЃР°"
            ],
            UserState.PRACTICING: [
                "РџРѕРјРѕРіР°Р№ РїСЂРё СЃР»РѕР¶РЅРѕСЃС‚СЏС…",
                "РџСЂРёР·РЅР°РІР°Р№ РїСЂРѕРіСЂРµСЃСЃ",
                "РџСЂРµРґР»РѕР¶Рё СѓРіР»СѓР±Р»РµРЅРёРµ",
                "РџРѕРґРґРµСЂР¶РёРІР°Р№ РјРѕС‚РёРІР°С†РёСЋ"
            ],
            UserState.STAGNANT: [
                "РџСЂРёР·РЅР°Р№ РїР»Р°С‚Рѕ РєР°Рє РЅРѕСЂРјР°Р»СЊРЅРѕРµ",
                "РџСЂРµРґР»РѕР¶Рё РЅРѕРІС‹Р№ СѓРіРѕР» Р·СЂРµРЅРёСЏ",
                "РР·РјРµРЅРё РїСЂР°РєС‚РёРєСѓ",
                "РќР°РїРѕРјРЅРё Рѕ С†РµР»СЏС…"
            ],
            UserState.BREAKTHROUGH: [
                "РџСЂРёР·РЅР°Р№ РёРЅСЃР°Р№С‚",
                "РџРѕРјРѕРіР°Р№ РёРЅС‚РµРіСЂРёСЂРѕРІР°С‚СЊ",
                "РџСЂРµРґР»РѕР¶Рё РїСЂРёРјРµРЅРµРЅРёРµ",
                "Р”РІРёРіР°Р№СЃСЏ Рє СЃР»РµРґСѓСЋС‰РµРјСѓ СѓСЂРѕРІРЅСЋ"
            ],
            UserState.INTEGRATED: [
                "РџРѕРјРѕРіР°Р№ СЃ РїСЂРёРјРµРЅРµРЅРёРµРј",
                "РџСЂРµРґР»РѕР¶Рё РЅРѕРІС‹Рµ СѓСЂРѕРІРЅРё",
                "РЎС‚Р°РЅСЊС‚Рµ РїР°СЂС‚РЅРµСЂР°РјРё РІ РёСЃСЃР»РµРґРѕРІР°РЅРёРё",
                "РџРѕРґРґРµСЂР¶РёРІР°Р№ РЅРµРїСЂРµСЂС‹РІРЅРѕРµ СЂР°Р·РІРёС‚РёРµ"
            ]
        }
        
        return recommendations.get(state, ["РџСЂРѕРґРѕР»Р¶Р°Р№ С‚РµРєСѓС‰РёР№ РїСѓС‚СЊ"])


# Р“Р»РѕР±Р°Р»СЊРЅС‹Р№ РёРЅСЃС‚Р°РЅСЃ
state_classifier = StateClassifier()



