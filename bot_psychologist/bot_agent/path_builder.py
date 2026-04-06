# bot_agent/path_builder.py
"""
Path Builder Module (Phase 4.3)
===============================

Построение персональных путей трансформации.
Интеграция с Knowledge Graph, состояниями пользователя, историей диалога.
"""

import logging
from typing import List, Dict, Optional
from dataclasses import dataclass, field

from .state_classifier import UserState, StateAnalysis
from .conversation_memory import ConversationMemory
from .graph_client import graph_client
from .user_level_types import UserLevel
from .config import config

logger = logging.getLogger(__name__)


@dataclass
class TransformationPathStep:
    """Один шаг в пути трансформации"""
    step_number: int
    title: str
    description: str
    duration_weeks: int
    practices: List[str] = field(default_factory=list)
    key_concepts: List[str] = field(default_factory=list)
    expected_outcomes: List[str] = field(default_factory=list)
    focus_areas: List[str] = field(default_factory=list)
    warning_signs: List[str] = field(default_factory=list)


@dataclass
class PersonalTransformationPath:
    """Персональный путь трансформации"""
    user_id: str
    current_state: UserState
    target_state: UserState
    current_level: UserLevel
    path_steps: List[TransformationPathStep]
    total_duration_weeks: int
    key_focus: str
    challenges_identified: List[str] = field(default_factory=list)
    adaptation_notes: List[str] = field(default_factory=list)


class PathBuilder:
    """
    Строит персональные пути трансформации на основе:
    1. Текущего состояния пользователя
    2. Его истории (интересы, вызовы)
    3. Уровня развития
    4. Knowledge Graph
    """
    
    # Прогрессия состояний (упорядоченная)
    STATE_PROGRESSION = [
        UserState.UNAWARE,
        UserState.CURIOUS,
        UserState.CONFUSED,
        UserState.OVERWHELMED,
        UserState.RESISTANT,
        UserState.COMMITTED,
        UserState.PRACTICING,
        UserState.STAGNANT,
        UserState.BREAKTHROUGH,
        UserState.INTEGRATED
    ]
    
    def __init__(self):
        self._graphs_loaded = False
    
    def _ensure_graphs_loaded(self):
        """Загрузить графы если ещё не загружены"""
        if not config.ENABLE_KNOWLEDGE_GRAPH:
            if not self._graphs_loaded:
                logger.debug("[PATH] graph_client skipped — ENABLE_KNOWLEDGE_GRAPH=false")
                self._graphs_loaded = True
            return
        if not self._graphs_loaded:
            graph_client.load_graphs_from_all_documents()
            self._graphs_loaded = True
    
    def build_path(
        self,
        user_id: str,
        state_analysis: StateAnalysis,
        user_level: UserLevel,
        memory: ConversationMemory,
        target_state: UserState = UserState.INTEGRATED
    ) -> PersonalTransformationPath:
        """
        Построить персональный путь трансформации.
        
        Args:
            user_id: ID пользователя
            state_analysis: Анализ текущего состояния
            user_level: Уровень пользователя
            memory: История диалога
            target_state: Целевое состояние (по умолчанию INTEGRATED)
        
        Returns:
            PersonalTransformationPath со всеми деталями
        """
        logger.info(f"🛤️ Строю путь трансформации для {user_id}...")
        
        self._ensure_graphs_loaded()
        
        current_state = state_analysis.primary_state
        
        # === ЭТАП 1: Получить интересы и вызовы ===
        logger.debug("📊 Этап 1: Анализ интересов и вызовов...")
        
        interests = memory.get_primary_interests()
        challenges = memory.get_challenges()
        
        # === ЭТАП 2: Построить промежуточные состояния ===
        logger.debug("🌉 Этап 2: Определение промежуточных состояний...")
        
        intermediate_states = self._get_intermediate_states(
            current_state,
            target_state
        )
        
        # === ЭТАП 3: Построить шаги пути ===
        logger.debug("👣 Этап 3: Построение шагов пути...")
        
        path_steps = []
        for i, state_transition in enumerate(intermediate_states, 1):
            step = self._build_step(
                step_number=i,
                from_state=state_transition["from"],
                to_state=state_transition["to"],
                user_level=user_level,
                interests=interests
            )
            path_steps.append(step)
        
        # === ЭТАП 4: Персонализация по истории ===
        logger.debug("🎯 Этап 4: Персонализация по истории пользователя...")
        
        adaptation_notes = self._personalize_path(
            path_steps,
            interests,
            challenges,
            user_level
        )
        
        # === ЭТАП 5: Определить основной фокус ===
        key_focus = self._determine_key_focus(
            current_state,
            interests,
            challenges
        )
        
        total_duration = sum(step.duration_weeks for step in path_steps)
        
        path = PersonalTransformationPath(
            user_id=user_id,
            current_state=current_state,
            target_state=target_state,
            current_level=user_level,
            path_steps=path_steps,
            total_duration_weeks=total_duration,
            key_focus=key_focus,
            challenges_identified=[c.get("turn", "") for c in challenges],
            adaptation_notes=adaptation_notes
        )
        
        logger.info(f"✅ Путь построен: {len(path_steps)} шагов, "
                   f"{total_duration} недель, фокус: {key_focus}")
        
        return path
    
    def _get_intermediate_states(
        self,
        from_state: UserState,
        to_state: UserState
    ) -> List[Dict]:
        """
        Определить промежуточные состояния между текущим и целевым.
        
        Returns:
            Список переходов [{"from": state1, "to": state2}, ...]
        """
        try:
            from_idx = self.STATE_PROGRESSION.index(from_state)
            to_idx = self.STATE_PROGRESSION.index(to_state)
        except ValueError:
            # Если состояние не в прогрессии, просто один переход
            return [{"from": from_state, "to": to_state}]
        
        # Если уже в целевом состоянии или дальше
        if from_idx >= to_idx:
            return [{"from": from_state, "to": to_state}]
        
        # Построить цепочку переходов
        transitions = []
        for i in range(from_idx, to_idx):
            transitions.append({
                "from": self.STATE_PROGRESSION[i],
                "to": self.STATE_PROGRESSION[i + 1]
            })
        
        return transitions
    
    def _build_step(
        self,
        step_number: int,
        from_state: UserState,
        to_state: UserState,
        user_level: UserLevel,
        interests: List[str]
    ) -> TransformationPathStep:
        """
        Построить один шаг пути.
        """
        # Определить концепты для этого перехода
        key_concepts = self._get_concepts_for_transition(
            from_state,
            to_state,
            interests
        )
        
        # Получить практики из графа
        practices = []
        graph_enabled = config.ENABLE_KNOWLEDGE_GRAPH and graph_client.has_data()
        for concept in key_concepts[:2]:  # берем макс 2 концепта
            concept_practices = (
                graph_client.get_practices_for_concept(concept) if graph_enabled else []
            )
            practices.extend([p["practice_name"] for p in concept_practices[:2]])
        
        # Убрать дубликаты
        practices = list(dict.fromkeys(practices))[:4]
        
        # Определить ожидаемые результаты
        expected_outcomes = self._get_expected_outcomes(to_state)
        
        # Длительность зависит от уровня пользователя
        duration_multiplier = {
            UserLevel.BEGINNER: 1.5,
            UserLevel.INTERMEDIATE: 1.0,
            UserLevel.ADVANCED: 0.7
        }
        
        base_duration = 2  # недели
        duration = max(1, int(base_duration * duration_multiplier.get(user_level, 1.0)))
        
        return TransformationPathStep(
            step_number=step_number,
            title=f"Переход из {from_state.value} в {to_state.value}",
            description=self._get_step_description(from_state, to_state),
            duration_weeks=duration,
            practices=practices,
            key_concepts=key_concepts,
            expected_outcomes=expected_outcomes,
            focus_areas=self._get_focus_areas(to_state),
            warning_signs=self._get_warning_signs(to_state)
        )
    
    def _get_concepts_for_transition(
        self,
        from_state: UserState,
        to_state: UserState,
        interests: List[str]
    ) -> List[str]:
        """
        Получить ключевые концепты для переходного периода.
        """
        transition_concepts = {
            (UserState.UNAWARE, UserState.CURIOUS): [
                "осознавание", "восприятие", "наблюдение"
            ],
            (UserState.CURIOUS, UserState.CONFUSED): [
                "система знания", "многоуровневость", "парадоксы"
            ],
            (UserState.CONFUSED, UserState.OVERWHELMED): [
                "структурирование", "приоритеты", "фокус"
            ],
            (UserState.OVERWHELMED, UserState.RESISTANT): [
                "принятие", "доверие", "открытость"
            ],
            (UserState.RESISTANT, UserState.COMMITTED): [
                "решение", "намерение", "мотивация"
            ],
            (UserState.COMMITTED, UserState.PRACTICING): [
                "практика", "упражнение", "применение"
            ],
            (UserState.PRACTICING, UserState.STAGNANT): [
                "терпение", "глубина", "вариации"
            ],
            (UserState.STAGNANT, UserState.BREAKTHROUGH): [
                "новый взгляд", "отпускание", "доверие процессу"
            ],
            (UserState.BREAKTHROUGH, UserState.INTEGRATED): [
                "интеграция", "целостность", "естественное состояние"
            ],
            # Прямые переходы
            (UserState.CONFUSED, UserState.COMMITTED): [
                "интеграция", "синтез", "понимание"
            ],
            (UserState.PRACTICING, UserState.BREAKTHROUGH): [
                "инсайт", "прорыв", "озарение"
            ]
        }
        
        key = (from_state, to_state)
        concepts = transition_concepts.get(key, ["трансформация", "развитие"])
        
        # Добавить интересы пользователя если есть
        if interests:
            concepts = concepts + interests[:2]
        
        return concepts[:5]  # макс 5 концептов
    
    def _get_expected_outcomes(self, state: UserState) -> List[str]:
        """
        Ожидаемые результаты для каждого состояния.
        """
        outcomes = {
            UserState.UNAWARE: [
                "Осознание существования проблемы",
                "Первое понимание учения",
                "Интерес к дальнейшему исследованию"
            ],
            UserState.CURIOUS: [
                "Углубленное понимание концепций",
                "Связь между идеями",
                "Готовность к практике"
            ],
            UserState.CONFUSED: [
                "Прояснение противоречий",
                "Интеграция знаний",
                "Путь вперед"
            ],
            UserState.OVERWHELMED: [
                "Структурированный подход",
                "Приоритеты действий",
                "Спокойствие"
            ],
            UserState.RESISTANT: [
                "Открытость новому",
                "Снижение сопротивления",
                "Готовность попробовать"
            ],
            UserState.COMMITTED: [
                "Четкий план действий",
                "Начало практики",
                "Первые результаты"
            ],
            UserState.PRACTICING: [
                "Стабильная практика",
                "Видимые изменения",
                "Углубление опыта"
            ],
            UserState.STAGNANT: [
                "Новый угол зрения",
                "Обновление подхода",
                "Возобновление прогресса"
            ],
            UserState.BREAKTHROUGH: [
                "Глубокий инсайт",
                "Трансформация восприятия",
                "Готовность к интеграции"
            ],
            UserState.INTEGRATED: [
                "Знание как часть жизни",
                "Спонтанное применение",
                "Помощь другим"
            ]
        }
        
        return outcomes.get(state, ["Продолжение развития"])
    
    def _get_focus_areas(self, state: UserState) -> List[str]:
        """
        Области фокуса для каждого состояния.
        """
        focus = {
            UserState.UNAWARE: ["Основы", "Понимание"],
            UserState.CURIOUS: ["Глубина", "Связи"],
            UserState.CONFUSED: ["Ясность", "Интеграция"],
            UserState.OVERWHELMED: ["Простота", "Шаг за шагом"],
            UserState.RESISTANT: ["Открытость", "Доверие"],
            UserState.COMMITTED: ["Дисциплина", "Практика"],
            UserState.PRACTICING: ["Глубина", "Опыт"],
            UserState.STAGNANT: ["Вариации", "Новизна"],
            UserState.BREAKTHROUGH: ["Интеграция", "Применение"],
            UserState.INTEGRATED: ["Мастерство", "Передача знания"]
        }
        
        return focus.get(state, ["Развитие"])
    
    def _get_warning_signs(self, state: UserState) -> List[str]:
        """
        Признаки застоя на каждом этапе.
        """
        warnings = {
            UserState.OVERWHELMED: [
                "Паника от объёма информации",
                "Прокрастинация",
                "Желание бросить"
            ],
            UserState.PRACTICING: [
                "Механическое выполнение без осознания",
                "Отсутствие видимых изменений",
                "Потеря интереса"
            ],
            UserState.STAGNANT: [
                "Все больше одного и того же",
                "Нет новых инсайтов",
                "Скука и сомнения"
            ]
        }
        
        return warnings.get(state, [])
    
    def _get_step_description(
        self,
        from_state: UserState,
        to_state: UserState
    ) -> str:
        """
        Описание шага перехода.
        """
        descriptions = {
            (UserState.UNAWARE, UserState.CURIOUS):
                "Пробуждение интереса к учению и первые вопросы",
            (UserState.CURIOUS, UserState.CONFUSED):
                "Углубленное изучение выявляет парадоксы и противоречия",
            (UserState.CONFUSED, UserState.OVERWHELMED):
                "Осознание масштаба изменений может вызвать перегрузку",
            (UserState.OVERWHELMED, UserState.RESISTANT):
                "Перегрузка может перейти в сопротивление изменениям",
            (UserState.RESISTANT, UserState.COMMITTED):
                "Преодоление сопротивления ведет к принятию решения",
            (UserState.CONFUSED, UserState.COMMITTED):
                "Синтез понимания и готовность к действию",
            (UserState.COMMITTED, UserState.PRACTICING):
                "Начало регулярной практики и опыта",
            (UserState.PRACTICING, UserState.STAGNANT):
                "Плато — естественная часть любого развития",
            (UserState.PRACTICING, UserState.BREAKTHROUGH):
                "Внезапное озарение и трансформация восприятия",
            (UserState.STAGNANT, UserState.BREAKTHROUGH):
                "Выход из плато через новый угол зрения",
            (UserState.BREAKTHROUGH, UserState.INTEGRATED):
                "Интеграция инсайта в повседневную жизнь"
        }
        
        return descriptions.get(
            (from_state, to_state),
            f"Переход от {from_state.value} к {to_state.value}"
        )
    
    def _personalize_path(
        self,
        path_steps: List[TransformationPathStep],
        interests: List[str],
        challenges: List[Dict],
        user_level: UserLevel
    ) -> List[str]:
        """
        Персонализировать путь на основе истории пользователя.
        """
        notes = []
        
        if interests:
            notes.append(f"🎯 Основные интересы: {', '.join(interests[:3])}")
        
        if challenges:
            notes.append(f"⚠️ Выявленные вызовы: {len(challenges)} областей затруднения")
        
        if user_level == UserLevel.BEGINNER:
            notes.append("📚 Рекомендуется идти медленнее, углубляя основы")
        elif user_level == UserLevel.ADVANCED:
            notes.append("🚀 Можно ускорить темп и добавить сложности")
        
        return notes
    
    def _determine_key_focus(
        self,
        current_state: UserState,
        interests: List[str],
        challenges: List[Dict]
    ) -> str:
        """
        Определить основной фокус пути.
        """
        if current_state == UserState.PRACTICING:
            return "Углубление практики и преодоление застоя"
        elif current_state == UserState.STAGNANT:
            return "Выход из плато и обновление подхода"
        elif current_state == UserState.RESISTANT:
            return "Преодоление сопротивления и открытость"
        elif current_state == UserState.OVERWHELMED:
            return "Структурирование и упрощение"
        elif current_state == UserState.CONFUSED:
            return "Прояснение и интеграция понимания"
        elif interests:
            return f"Исследование: {interests[0]}"
        else:
            return "Целостное развитие"


# Глобальный инстанс
path_builder = PathBuilder()


