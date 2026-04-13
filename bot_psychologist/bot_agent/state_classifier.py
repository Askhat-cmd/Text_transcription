# bot_agent/state_classifier.py
"""
State Classifier Module (Phase 4.1)
===================================

Классификация психологического состояния пользователя.
10 состояний от UNAWARE до INTEGRATED.
Keyword + LLM анализ для точности определения.
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
    Состояния пользователя в процессе трансформации.
    
    Прогрессия: UNAWARE -> CURIOUS -> ... -> INTEGRATED
    """
    UNAWARE = "unaware"              # Не осознает проблему
    CURIOUS = "curious"              # Любопытство, интерес
    OVERWHELMED = "overwhelmed"      # Перегружен информацией
    RESISTANT = "resistant"          # Сопротивление
    CONFUSED = "confused"            # Запутанность
    COMMITTED = "committed"          # Готов к работе
    PRACTICING = "practicing"        # Практикует
    STAGNANT = "stagnant"            # Застой, плато
    BREAKTHROUGH = "breakthrough"    # Прорыв
    INTEGRATED = "integrated"        # нтегрировал знание


@dataclass
class StateAnalysis:
    """Результат анализа состояния пользователя"""
    primary_state: UserState
    confidence: float  # 0.0-1.0
    secondary_states: List[UserState]
    indicators: List[str]  # конкретные индикаторы состояния
    emotional_tone: str  # contemplative, frustrated, excited, calm, confused
    depth: str  # surface, intermediate, deep
    recommendations: List[str]  # что делать в этом состоянии


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
    Классифицирует состояние пользователя на основе:
    1. Содержания вопроса
    2. стории диалога
    3. Лингвистических сигналов
    4. Явно указанной обратной связи
    """
    
    def __init__(self):
        self.llm = LLMAnswerer()
        self.state_indicators = self._init_state_indicators()
    
    def _init_state_indicators(self) -> Dict[UserState, List[str]]:
        """нициализировать индикаторы для каждого состояния"""
        return {
            UserState.UNAWARE: [
                "что такое", "какой смысл", "зачем", "не понимаю",
                "в чем суть", "объясни", "это важно?", "что это",
                "для чего", "не слышал", "первый раз"
            ],
            UserState.CURIOUS: [
                "интересно", "хочу узнать", "расскажи подробнее",
                "а как", "почему", "связь между", "как это работает",
                "расскажи больше", "любопытно", "хотелось бы понять"
            ],
            UserState.OVERWHELMED: [
                "слишком много", "не могу понять", "запутался", "сложно",
                "помощь", "как начать", "откуда начинать", "где начало",
                "не знаю с чего", "теряюсь", "много всего", "голова кругом"
            ],
            UserState.RESISTANT: [
                "не верю", "не согласен", "но ведь", "однако",
                "это невозможно", "у меня не получится", "это для других",
                "сомневаюсь", "не уверен что", "скептически", "ерунда"
            ],
            UserState.CONFUSED: [
                "не понял", "путаюсь", "противоречит", "несовместимо",
                "противоречиво", "дополнительно", "уточни", "еще раз",
                "как это связано", "не вижу связи", "одно противоречит"
            ],
            UserState.COMMITTED: [
                "готов", "хочу", "начинаю", "буду", "согласен",
                "понял", "пойду", "попробую", "решил", "приступаю",
                "давай начнем", "с чего начать", "готов действовать"
            ],
            UserState.PRACTICING: [
                "пробую", "делаю", "практикую", "занимаюсь", "работаю",
                "получается", "не получается", "замечаю", "вижу", "чувствую",
                "заметил что", "когда делаю", "в процессе практики"
            ],
            UserState.STAGNANT: [
                "ничего не меняется", "застрял", "плато", "одно и то же",
                "скучно", "не вижу результата", "зачем дальше", "сомневаюсь",
                "топчусь на месте", "нет прогресса", "устал", "надоело"
            ],
            UserState.BREAKTHROUGH: [
                "понял", "прорыв", "внезапно", "озарение", "инсайт",
                "все встало на место", "вау", "ахмомент", "теперь я вижу",
                "дошло", "осенило", "наконец понял", "ага-момент"
            ],
            UserState.INTEGRATED: [
                "применяю", "использую", "уже не думаю", "естественно",
                "это часть меня", "просто делаю", "помню всегда",
                "автоматически", "без усилий", "само собой", "живу этим"
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
        if any(
            token in lowered
            for token in (
                "страшно",
                "паника",
                "тревога",
                "не могу",
                "боюсь",
                "злость",
                "бесит",
                "плохо",
                "overwhelmed",
            )
        ):
            return "discharge"
        if any(
            token in lowered
            for token in (
                "что делать",
                "дай шаг",
                "план",
                "как начать",
                "конкретный шаг",
                "пошаг",
                "инструкц",
                "как применить",
                "next step",
                "what should i do",
            )
        ):
            return "solution"
        if any(
            token in lowered
            for token in (
                "правильно ли",
                "нормально ли",
                "это ок",
                "это нормально",
                "я слаб",
                "я виноват",
                "со мной что-то не так",
                "стыдно",
                "is this normal",
                "am i wrong",
            )
        ):
            return "validation"
        if any(
            token in lowered
            for token in (
                "я чувствую",
                "мне важно",
                "про меня",
                "со мной",
                "поддерж",
                "мне сейчас",
                "i feel",
                "support me",
            )
        ):
            return "contact"
        if any(
            token in lowered
            for token in (
                "почему",
                "как это работает",
                "в чем смысл",
                "разобраться",
                "исследовать",
                "что означает",
                "how does it work",
                "why",
                "explain",
            )
        ):
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
        Анализирует состояние пользователя по сообщению и истории.
        
        Args:
            user_message: Последнее сообщение пользователя
            conversation_history: стория диалога [{"role": "user", "content": ...}, ...]
        
        Returns:
            StateAnalysis с детальной информацией
        """
        logger.info(f"🎯 Анализирую состояние пользователя...")

        # ===  0: fast detector    ===
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
        
        # === ЭТАП 1: Анализ текущего сообщения по ключевым словам ===
        primary_state, confidence = self._classify_by_keywords(user_message)
        logger.debug(f"   Первичное состояние: {primary_state.value} (уверенность: {confidence:.2f})")
        
        # === ЭТАП 2: Анализ через LLM для уточнения ===
        llm_analysis = self._classify_by_llm(user_message, conversation_history)
        logger.debug(f"   LLM анализ: {llm_analysis}")
        
        # === ЭТАП 3: Объединение результатов ===
        final_analysis = self._merge_classifications(
            primary_state, confidence, llm_analysis
        )
        
        # === ЭТАП 4: Определение рекомендаций ===
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
        Простая классификация по ключевым словам.
        Возвращает (состояние, уверенность).
        """
        message_lower = message.lower()
        state_scores: Dict[UserState, int] = {}
        
        for state, keywords in self.state_indicators.items():
            score = sum(1 for kw in keywords if kw in message_lower)
            if score > 0:
                state_scores[state] = score
        
        if not state_scores:
            return UserState.CURIOUS, 0.3  # дефолт
        
        # Находим состояние с максимальным score
        primary_state = max(state_scores, key=lambda s: state_scores[s])
        max_score = state_scores[primary_state]
        
        # Уверенность = (кол-во совпадений) / (макс возможно)
        confidence = min(max_score / len(self.state_indicators[primary_state]), 1.0)
        
        return primary_state, confidence
    
    def _classify_by_llm(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict]]
    ) -> Dict:
        """
        Анализирует состояние через LLM для большей точности.
        """
        if not self.llm.client:
            logger.warning("⚠️ LLM недоступен, пропускаю LLM-классификацию")
            return {}
        
        # Формируем контекст истории
        history_context = ""
        if conversation_history:
            for turn in conversation_history[-3:]:  # последние 3 хода
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
            
            #     GPT-5   None
            raw_content = response.choices[0].message.content
            content = (raw_content or "").strip()

            #  markdown- (```json ... ```  ``` ... ```)
            if "```" in content:
                import re
                content = re.sub(r"```(?:json)?\s*", "", content).strip()

            #      GPT-5 mini    
            if not content:
                logger.warning(" LLM      ")
                return {}

            result = json.loads(content)
            return result

        except json.JSONDecodeError as e:
            logger.debug(f" JSON parse miss (   ): {e}")
            return {}
        except Exception as e:
            logger.warning(f"⚠️ LLM классификация не удалась: {e}")
            return {}
    
    def _merge_classifications(
        self,
        keyword_state: UserState,
        keyword_confidence: float,
        llm_analysis: Dict
    ) -> StateAnalysis:
        """
        Объединяет результаты keyword и LLM классификации.
        """
        # Если LLM вернул результат
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
        
        # Вторичные состояния
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
            .
        """
        recommendations = {
            UserState.UNAWARE: [
                "   ",
                "  ",
                "   ",
                "  "
            ],
            UserState.CURIOUS: [
                "   ",
                "    ",
                "    ",
                "  "
            ],
            UserState.OVERWHELMED: [
                "    ",
                "   ",
                "    ",
                "   "
            ],
            UserState.RESISTANT: [
                "   ",
                "    ",
                "   ",
                "  "
            ],
            UserState.CONFUSED: [
                "    ",
                "    ",
                " ",
                "  "
            ],
            UserState.COMMITTED: [
                "   ",
                "   ",
                " ",
                "  "
            ],
            UserState.PRACTICING: [
                "  ",
                "  ",
                "   ",
                "  "
            ],
            UserState.STAGNANT: [
                "   ",
                "   ",
                "  ",
                "    "
            ],
            UserState.BREAKTHROUGH: [
                " ",
                "    ",
                "    ",
                "   "
            ],
            UserState.INTEGRATED: [
                "   ",
                "  ",
                "   ",
                "  "
            ]
        }
        
        return recommendations.get(state, ["  "])


#  
state_classifier = StateClassifier()


