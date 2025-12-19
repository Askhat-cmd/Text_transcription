# bot_agent/state_classifier.py
"""
State Classifier Module (Phase 4.1)
===================================

Классификация психологического состояния пользователя.
10 состояний от UNAWARE до INTEGRATED.
Keyword + LLM анализ для точности определения.
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
    INTEGRATED = "integrated"        # Интегрировал знание


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


class StateClassifier:
    """
    Классифицирует состояние пользователя на основе:
    1. Содержания вопроса
    2. Истории диалога
    3. Лингвистических сигналов
    4. Явно указанной обратной связи
    """
    
    def __init__(self):
        self.llm = LLMAnswerer()
        self.state_indicators = self._init_state_indicators()
    
    def _init_state_indicators(self) -> Dict[UserState, List[str]]:
        """Инициализировать индикаторы для каждого состояния"""
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
    
    def analyze_message(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict]] = None
    ) -> StateAnalysis:
        """
        Анализирует состояние пользователя по сообщению и истории.
        
        Args:
            user_message: Последнее сообщение пользователя
            conversation_history: История диалога [{"role": "user", "content": ...}, ...]
        
        Returns:
            StateAnalysis с детальной информацией
        """
        logger.info(f"🎯 Анализирую состояние пользователя...")
        
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
        
        logger.info(f"✅ Состояние определено: {final_analysis.primary_state.value} "
                   f"(уверенность: {final_analysis.confidence:.2f})")
        
        return final_analysis
    
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
            response = self.llm.client.chat.completions.create(
                model=config.LLM_MODEL,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,  # низкая температура для классификации
                max_tokens=500
            )
            
            content = response.choices[0].message.content.strip()
            
            # Очистка от markdown если есть
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            
            result = json.loads(content)
            return result
        
        except json.JSONDecodeError as e:
            logger.warning(f"⚠️ Ошибка парсинга JSON: {e}")
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
        Возвращает рекомендации для конкретного состояния.
        """
        recommendations = {
            UserState.UNAWARE: [
                "Объясни с простых примеров",
                "Покажи практическое применение",
                "Предложи первый шаг",
                "Не перегружай информацией"
            ],
            UserState.CURIOUS: [
                "Развивай интерес",
                "Покажи глубину темы",
                "Предложи дальнейшее исследование",
                "Рекомендуй практики"
            ],
            UserState.OVERWHELMED: [
                "Упрости объяснение",
                "Разбей на маленькие шаги",
                "Сосредоточься на одном",
                "Предложи ресурсы для самоуспокоения"
            ],
            UserState.RESISTANT: [
                "Слушай без суждений",
                "Покажи доказательства",
                "Предложи альтернативные подходы",
                "Используй его язык"
            ],
            UserState.CONFUSED: [
                "Уточни основные концепты",
                "Дай практические примеры",
                "Пересказать по-другому",
                "Найди источник путаницы"
            ],
            UserState.COMMITTED: [
                "Дай четкий план действий",
                "Предложи практики",
                "Поддержи энтузиазм",
                "Установи вехи прогресса"
            ],
            UserState.PRACTICING: [
                "Помогай при сложностях",
                "Признавай прогресс",
                "Предложи углубление",
                "Поддерживай мотивацию"
            ],
            UserState.STAGNANT: [
                "Признай плато как нормальное",
                "Предложи новый угол зрения",
                "Измени практику",
                "Напомни о целях"
            ],
            UserState.BREAKTHROUGH: [
                "Признай инсайт",
                "Помогай интегрировать",
                "Предложи применение",
                "Двигайся к следующему уровню"
            ],
            UserState.INTEGRATED: [
                "Помогай с применением",
                "Предложи новые уровни",
                "Станьте партнерами в исследовании",
                "Поддерживай непрерывное развитие"
            ]
        }
        
        return recommendations.get(state, ["Продолжай текущий путь"])


# Глобальный инстанс
state_classifier = StateClassifier()
