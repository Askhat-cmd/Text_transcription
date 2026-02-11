# bot_agent/state_classifier.py
"""
State Classifier Module (Phase 4.1)
===================================

РљР»Р°СЃСЃРёС„РёРєР°С†РёСЏ РїСЃРёС…РѕР»РѕРіРёС‡РµСЃРєРѕРіРѕ СЃРѕСЃС‚РѕСЏРЅРёСЏ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ.
10 СЃРѕСЃС‚РѕСЏРЅРёР№ РѕС‚ UNAWARE РґРѕ INTEGRATED.
Keyword + LLM Р°РЅР°Р»РёР· РґР»СЏ С‚РѕС‡РЅРѕСЃС‚Рё РѕРїСЂРµРґРµР»РµРЅРёСЏ.
"""

import logging
import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from .llm_answerer import LLMAnswerer
from .config import config

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
        
        logger.info(f"вњ… РЎРѕСЃС‚РѕСЏРЅРёРµ РѕРїСЂРµРґРµР»РµРЅРѕ: {final_analysis.primary_state.value} "
                   f"(СѓРІРµСЂРµРЅРЅРѕСЃС‚СЊ: {final_analysis.confidence:.2f})")
        
        return final_analysis
    
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
            response = self.llm.client.chat.completions.create(
                model=config.LLM_MODEL,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                **self.llm._temperature_kwargs(config.LLM_MODEL, 0.3),  # РЅРёР·РєР°СЏ С‚РµРјРїРµСЂР°С‚СѓСЂР° РґР»СЏ РєР»Р°СЃСЃРёС„РёРєР°С†РёРё
                **self.llm._token_limit_kwargs(config.LLM_MODEL, 500)
            )
            
            content = response.choices[0].message.content.strip()
            
            # РћС‡РёСЃС‚РєР° РѕС‚ markdown РµСЃР»Рё РµСЃС‚СЊ
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            
            result = json.loads(content)
            return result
        
        except json.JSONDecodeError as e:
            logger.warning(f"вљ пёЏ РћС€РёР±РєР° РїР°СЂСЃРёРЅРіР° JSON: {e}")
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




