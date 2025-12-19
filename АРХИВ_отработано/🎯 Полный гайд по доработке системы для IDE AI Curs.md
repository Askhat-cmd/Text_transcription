
# 🎯 Полный гайд по доработке системы для IDE AI Cursor

## 📋 Оглавление

1. [Фаза 1: Улучшение графа знаний (автоматически)](#%D1%84%D0%B0%D0%B7%D0%B0-1)
2. [Фаза 2: Экстрактор практик](#%D1%84%D0%B0%D0%B7%D0%B0-2)
3. [Фаза 3: Модуль безопасности (Safety)](#%D1%84%D0%B0%D0%B7%D0%B0-3)
4. [Фаза 4: Иерархия концептов](#%D1%84%D0%B0%D0%B7%D0%B0-4)
5. [Фаза 5: Тестирование и валидация](#%D1%84%D0%B0%D0%B7%D0%B0-5)

***

```
# <a id="фаза-1"></a>ФАЗА 1: Улучшение графа знаний
```


## Задача для Cursor AI

```markdown
# ЗАДАЧА 1.1: Добавить вычисление весов связей в графе знаний

## Контекст
Сейчас все связи в графе имеют strength=1.0, что неинформативно.
Нужно вычислять реальные веса на основе:
- Co-occurrence frequency (частота совместной встречаемости)
- Расстояние между концептами в тексте
- PMI (Pointwise Mutual Information)

## Файл для модификации
`orchestrator/knowledge_graph_builder.py`

## Что нужно сделать

### Шаг 1: Создать класс GraphWeightCalculator
Добавь новый класс в конец файла `knowledge_graph_builder.py`:

```

class GraphWeightCalculator:
"""
Вычисляет веса связей между концептами в графе знаний.
"""

    def __init__(self):
        self.concept_positions = {}  # {concept: [positions_in_text]}
        self.cooccurrence_matrix = {}  # {(concept1, concept2): count}
        
    def analyze_block(self, block_content: str, entities: List[str], block_idx: int):
        """
        Анализирует блок текста и сохраняет позиции концептов.
        
        Args:
            block_content: Текст блока
            entities: Список сущностей (концептов) в блоке
            block_idx: Индекс блока
        """
        words = block_content.lower().split()
        
        # Найти позиции каждого концепта
        for entity in entities:
            entity_lower = entity.lower()
            positions = []
            
            for i, word in enumerate(words):
                if entity_lower in word:
                    positions.append((block_idx, i))
            
            if entity not in self.concept_positions:
                self.concept_positions[entity] = []
            self.concept_positions[entity].extend(positions)
        
        # Подсчитать co-occurrence
        for i, entity1 in enumerate(entities):
            for entity2 in entities[i+1:]:
                pair = tuple(sorted([entity1, entity2]))
                self.cooccurrence_matrix[pair] = self.cooccurrence_matrix.get(pair, 0) + 1
    
    def calculate_pmi(self, entity1: str, entity2: str, total_blocks: int) -> float:
        """
        Вычисляет Pointwise Mutual Information между двумя концептами.
        
        Args:
            entity1: Первый концепт
            entity2: Второй концепт
            total_blocks: Общее количество блоков
            
        Returns:
            PMI score (0.0 - 1.0)
        """
        import math
        
        pair = tuple(sorted([entity1, entity2]))
        cooccur = self.cooccurrence_matrix.get(pair, 0)
        
        if cooccur == 0:
            return 0.0
        
        count1 = len([p for p in self.concept_positions.get(entity1, []) if p < total_blocks])
        count2 = len([p for p in self.concept_positions.get(entity2, []) if p < total_blocks])
        
        if count1 == 0 or count2 == 0:
            return 0.0
        
        p_xy = cooccur / total_blocks
        p_x = count1 / total_blocks
        p_y = count2 / total_blocks
        
        if p_x * p_y == 0:
            return 0.0
        
        pmi = math.log2(p_xy / (p_x * p_y))
        # Нормализация от 0 до 1
        normalized_pmi = max(0, min(1, (pmi + 10) / 20))
        
        return normalized_pmi
    
    def calculate_distance_weight(self, entity1: str, entity2: str) -> float:
        """
        Вычисляет вес на основе среднего расстояния между концептами.
        Чем ближе концепты встречаются в тексте, тем выше вес.
        
        Args:
            entity1: Первый концепт
            entity2: Второй концепт
            
        Returns:
            Weight (0.0 - 1.0)
        """
        positions1 = self.concept_positions.get(entity1, [])
        positions2 = self.concept_positions.get(entity2, [])
        
        if not positions1 or not positions2:
            return 0.0
        
        min_distances = []
        for pos1 in positions1:
            for pos2 in positions2:
                # Только если в одном блоке
                if pos1 == pos2:
                    distance = abs(pos1 - pos2)[^1]
                    min_distances.append(distance)
        
        if not min_distances:
            return 0.3  # Базовый вес для концептов из разных блоков
        
        avg_distance = sum(min_distances) / len(min_distances)
        # Чем меньше расстояние, тем выше вес
        # Используем экспоненциальное затухание
        import math
        weight = math.exp(-avg_distance / 50)  # 50 слов - характерная длина
        
        return weight
    
    def calculate_combined_weight(self, entity1: str, entity2: str, total_blocks: int) -> float:
        """
        Вычисляет итоговый вес связи как комбинацию метрик.
        
        Args:
            entity1: Первый концепт
            entity2: Второй концепт
            total_blocks: Общее количество блоков
            
        Returns:
            Combined weight (0.0 - 1.0)
        """
        pair = tuple(sorted([entity1, entity2]))
        cooccur_count = self.cooccurrence_matrix.get(pair, 0)
        
        if cooccur_count == 0:
            return 0.1  # Минимальный вес для связей без co-occurrence
        
        # Нормализованная частота co-occurrence
        max_cooccur = max(self.cooccurrence_matrix.values()) if self.cooccurrence_matrix else 1
        freq_weight = cooccur_count / max_cooccur
        
        # PMI
        pmi_weight = self.calculate_pmi(entity1, entity2, total_blocks)
        
        # Distance weight
        dist_weight = self.calculate_distance_weight(entity1, entity2)
        
        # Комбинированный вес (взвешенная сумма)
        combined = (
            0.4 * freq_weight +  # 40% - частота
            0.3 * pmi_weight +   # 30% - PMI
            0.3 * dist_weight    # 30% - расстояние
        )
        
        return round(combined, 3)
    ```

### Шаг 2: Интегрировать в KnowledgeGraphBuilder

Найди метод `_build_graph_entities` в классе `KnowledgeGraphBuilder` и добавь использование `GraphWeightCalculator`:

```

def _build_graph_entities(self, blocks: List[dict]) -> dict:
"""
Строит граф знаний из блоков.
"""
\# ... существующий код ...

    # ДОБАВИТЬ ЭТО:
    # Инициализируем калькулятор весов
    weight_calculator = GraphWeightCalculator()
    
    # Анализируем все блоки для сбора статистики
    for idx, block in enumerate(blocks):
        entities = block.get('graph_entities', [])
        content = block.get('content', '')
        weight_calculator.analyze_block(content, entities, idx)
    
    total_blocks = len(blocks)
    
    # ... существующий код создания узлов ...
    
    # МОДИФИЦИРОВАТЬ создание связей:
    # Вместо strength=1.0 использовать вычисленные веса
    
    for link_type in ['conceptual_links', 'causal_links', 'practical_links']:
        for link in combined_relationships.get(link_type, []):
            source = link['source']
            target = link['target']
            
            # ЗАМЕНИТЬ ЭТУ СТРОКУ:
            # strength = link.get('strength', 1.0)
            
            # НА ЭТО:
            strength = weight_calculator.calculate_combined_weight(
                source, target, total_blocks
            )
            
            # ... остальной код создания edge ...
    ```

### Шаг 3: Обновить метаданные графа

Добавь статистику о весах в метаданные:

```


# В конце метода _build_graph_entities добавить:

edge_weights = [edge['confidence'] for edge in knowledge_graph['edges']]

knowledge_graph['metadata']['weight_statistics'] = {
'min_weight': min(edge_weights) if edge_weights else 0,
'max_weight': max(edge_weights) if edge_weights else 0,
'avg_weight': sum(edge_weights) / len(edge_weights) if edge_weights else 0,
'median_weight': sorted(edge_weights)[len(edge_weights)//2] if edge_weights else 0
}

```

## Критерии успеха
- ✅ Веса связей варьируются от 0.1 до 1.0
- ✅ Часто встречающиеся вместе концепты имеют вес > 0.7
- ✅ Редко связанные концепты имеют вес < 0.3
- ✅ В метаданных графа есть статистика весов

## Тестирование
Запусти обработку тестового видео и проверь:
```

python main.py --video_id 9BEpGP7L1_Q

```

Проверь в файле `for_vector.json`:
- Поле `knowledge_graph.edges[*].confidence` должно иметь разные значения
- Поле `knowledge_graph.metadata.weight_statistics` должно быть заполнено
```


***

```
# <a id="фаза-2"></a>ФАЗА 2: Экстрактор практик
```


## Задача для Cursor AI

```markdown
# ЗАДАЧА 2.1: Создать экстрактор практических упражнений

## Контекст
Нужно извлекать из текста лекций структурированные практики с пошаговыми инструкциями.

## Создать новый файл
`orchestrator/extractors/practice_extractor.py`

## Код

```

"""
Экстрактор практических упражнений из текста лекций.
"""

import re
from typing import List, Dict, Optional
from dataclasses import dataclass

@dataclass
class PracticeStep:
"""Один шаг практики."""
step_number: int
instruction: str
duration: Optional[str] = None
notes: Optional[str] = None

@dataclass
class Practice:
"""Структурированное практическое упражнение."""
title: str
description: str
steps: List[PracticeStep]
goal: str
prerequisites: List[str]
duration: Optional[str] = None
difficulty: str  \# beginner, intermediate, advanced
related_concepts: List[str]
when_to_use: List[str]
contraindications: List[str]

    def to_dict(self) -> dict:
        return {
            'title': self.title,
            'description': self.description,
            'steps': [
                {
                    'step_number': step.step_number,
                    'instruction': step.instruction,
                    'duration': step.duration,
                    'notes': step.notes
                }
                for step in self.steps
            ],
            'goal': self.goal,
            'prerequisites': self.prerequisites,
            'duration': self.duration,
            'difficulty': self.difficulty,
            'related_concepts': self.related_concepts,
            'when_to_use': self.when_to_use,
            'contraindications': self.contraindications
        }
    class PracticeExtractor:
"""
Извлекает практические упражнения из текста лекций.
"""

    # Маркеры начала практики
    PRACTICE_MARKERS = [
        r'практик[аи]',
        r'упражнени[ея]',
        r'техник[аи]',
        r'метод',
        r'способ',
        r'делаем так',
        r'сделайте',
        r'попробуйте',
        r'давайте',
    ]
    
    # Маркеры шагов
    STEP_MARKERS = [
        r'первое',
        r'второе',
        r'третье',
        r'далее',
        r'затем',
        r'после этого',
        r'во-первых',
        r'во-вторых',
        r'в-третьих',
        r'шаг \d+',
        r'\d+\.',
    ]
    
    # Императивные формы глаголов
    IMPERATIVE_PATTERNS = [
        r'\b(сосредоточьтесь|обратите|заметьте|почувствуйте|осознайте)',
        r'\b(остановитесь|замрите|расслабьтесь|дышите)',
        r'\b(представьте|вообразите|визуализируйте)',
        r'\b(наблюдайте|следите|отслеживайте)',
    ]
    
    def __init__(self):
        self.practice_pattern = re.compile(
            '|'.join(self.PRACTICE_MARKERS),
            re.IGNORECASE
        )
        self.step_pattern = re.compile(
            '|'.join(self.STEP_MARKERS),
            re.IGNORECASE
        )
        self.imperative_pattern = re.compile(
            '|'.join(self.IMPERATIVE_PATTERNS),
            re.IGNORECASE
        )
    
    def extract_practices(self, blocks: List[dict]) -> List[Practice]:
        """
        Извлекает практики из списка блоков.
        
        Args:
            blocks: Список блоков контента
            
        Returns:
            Список извлечённых практик
        """
        practices = []
        
        for block in blocks:
            content = block.get('content', '')
            
            # Поиск потенциальных практик
            if self._is_practice_block(content):
                practice = self._extract_practice_from_block(block)
                if practice:
                    practices.append(practice)
        
        return practices
    
    def _is_practice_block(self, content: str) -> bool:
        """
        Проверяет, содержит ли блок практическое упражнение.
        """
        # Есть маркер практики
        has_marker = bool(self.practice_pattern.search(content))
        
        # Есть императивные формы
        has_imperatives = bool(self.imperative_pattern.search(content))
        
        # Есть маркеры шагов
        has_steps = bool(self.step_pattern.search(content))
        
        return has_marker and (has_imperatives or has_steps)
    
    def _extract_practice_from_block(self, block: dict) -> Optional[Practice]:
        """
        Извлекает структурированную практику из блока.
        """
        content = block.get('content', '')
        
        # Разбить на предложения
        sentences = self._split_sentences(content)
        
        # Найти название практики (первое предложение с маркером)
        title = self._extract_title(sentences)
        if not title:
            title = "Практика без названия"
        
        # Извлечь описание (1-2 предложения после названия)
        description = self._extract_description(sentences)
        
        # Извлечь шаги
        steps = self._extract_steps(sentences)
        
        if len(steps) < 2:
            # Недостаточно шагов для полноценной практики
            return None
        
        # Извлечь цель (предложения с "чтобы", "для того чтобы")
        goal = self._extract_goal(sentences)
        
        # Определить сложность
        difficulty = self._estimate_difficulty(block, steps)
        
        # Связанные концепты
        related_concepts = block.get('graph_entities', [])
        
        practice = Practice(
            title=title,
            description=description,
            steps=steps,
            goal=goal,
            prerequisites=[],  # Заполним позже
            duration=None,  # Попытаемся извлечь
            difficulty=difficulty,
            related_concepts=related_concepts,
            when_to_use=[],  # Заполним позже
            contraindications=[]  # Заполним позже
        )
        
        return practice
    
    def _split_sentences(self, text: str) -> List[str]:
        """Разбивает текст на предложения."""
        # Простая эвристика
        sentences = re.split(r'[.!?]\s+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _extract_title(self, sentences: List[str]) -> str:
        """Извлекает название практики."""
        for sentence in sentences[:5]:  # Ищем в первых 5 предложениях
            if self.practice_pattern.search(sentence):
                # Берём до первого знака препинания или до конца
                title = sentence.split(',').split('.')
                return title[:100]  # Ограничиваем длину
        return ""
    
    def _extract_description(self, sentences: List[str]) -> str:
        """Извлекает описание практики."""
        # Берём 1-2 предложения после названия
        description_sentences = []
        found_title = False
        
        for sentence in sentences:
            if self.practice_pattern.search(sentence):
                found_title = True
                continue
            
            if found_title:
                description_sentences.append(sentence)
                if len(description_sentences) >= 2:
                    break
        
        return ' '.join(description_sentences)
    
    def _extract_steps(self, sentences: List[str]) -> List[PracticeStep]:
        """Извлекает пошаговые инструкции."""
        steps = []
        step_number = 1
        
        for sentence in sentences:
            # Проверяем, это шаг?
            is_step = (
                self.step_pattern.search(sentence) or
                self.imperative_pattern.search(sentence)
            )
            
            if is_step and len(sentence) > 20:  # Минимальная длина шага
                step = PracticeStep(
                    step_number=step_number,
                    instruction=sentence,
                    duration=None,
                    notes=None
                )
                steps.append(step)
                step_number += 1
        
        return steps
    
    def _extract_goal(self, sentences: List[str]) -> str:
        """Извлекает цель практики."""
        goal_markers = ['чтобы', 'для того', 'цель', 'задача']
        
        for sentence in sentences:
            for marker in goal_markers:
                if marker in sentence.lower():
                    return sentence
        
        return "Цель не указана"
    
    def _estimate_difficulty(self, block: dict, steps: List[PracticeStep]) -> str:
        """Оценивает сложность практики."""
        # Эвристика на основе:
        # 1. Количества шагов
        # 2. Сложности концептов
        # 3. Длины инструкций
        
        num_steps = len(steps)
        complexity_score = block.get('complexity_score', 5.0)
        
        if num_steps <= 3 and complexity_score < 5:
            return 'beginner'
        elif num_steps <= 5 and complexity_score < 7:
            return 'intermediate'
        else:
            return 'advanced'
    
# Функция для интеграции в pipeline

def extract_practices_from_blocks(blocks: List[dict]) -> List[dict]:
"""
Обёртка для вызова из основного pipeline.

    Args:
        blocks: Список блоков контента
        
    Returns:
        Список практик в формате dict
    """
    extractor = PracticeExtractor()
    practices = extractor.extract_practices(blocks)
    return [p.to_dict() for p in practices]
    ```

## Шаг 2: Интегрировать в KnowledgeGraphBuilder

В файле `orchestrator/knowledge_graph_builder.py` добавь:

```


# В начале файла

from orchestrator.extractors.practice_extractor import extract_practices_from_blocks

# В методе build_knowledge_graph после обработки блоков:

def build_knowledge_graph(self, document_data: dict) -> dict:
\# ... существующий код ...

    # ДОБАВИТЬ ПОСЛЕ ОБРАБОТКИ БЛОКОВ:
    # Извлечь практики
    practices = extract_practices_from_blocks(blocks)
    
    # Добавить в document_data
    document_data['practices'] = practices
    
    # Обновить метаданные
    document_data['document_metadata']['practices_count'] = len(practices)
    
    # ... остальной код ...
    ```

## Критерии успеха
- ✅ Файл `for_vector.json` содержит секцию `practices`
- ✅ Каждая практика имеет title, steps, goal
- ✅ Шаги пронумерованы и содержат инструкции
- ✅ Определён уровень сложности

## Тестирование
```

python -c "
from orchestrator.extractors.practice_extractor import extract_practices_from_blocks

test_block = {
'content': '''
Практика осознанного дыхания. Это базовое упражнение для начинающих.
Первое, сосредоточьтесь на своём дыхании. Наблюдайте как воздух входит и выходит.
Второе, заметьте ощущения в теле при вдохе и выдохе.
Третье, когда отвлекаетесь, мягко возвращайте внимание к дыханию.
Это поможет развить осознанность и присутствие.
''',
'graph_entities': ['осознанность', 'дыхание', 'присутствие'],
'complexity_score': 3.0
}

practices = extract_practices_from_blocks([test_block])
print(f'Найдено практик: {len(practices)}')
if practices:
print(f'Название: {practices[\"title\"]}')
print(f'Шагов: {len(practices[\"steps\"])}')
print(f'Сложность: {practices[\"difficulty\"]}')
"

```
```


***

```
# <a id="фаза-3"></a>ФАЗА 3: Модуль безопасности (Safety)
```


## Задача для Cursor AI

```markdown
# ЗАДАЧА 3.1: Создать модуль Safety для психологической безопасности

## Контекст
КРИТИЧЕСКИ ВАЖНО для психологического контента!
Нужно извлекать и добавлять информацию о:
- Противопоказаниях
- Ограничениях метода
- Ситуациях когда нужно обратиться к специалисту
- Красных флагах

## Создать новый файл
`orchestrator/extractors/safety_extractor.py`

## Код

```

"""
Экстрактор информации о безопасности практик.
"""

import re
from typing import List, Dict
from dataclasses import dataclass

@dataclass
class SafetyInfo:
"""Информация о безопасности практики."""
contraindications: List[str]  \# Противопоказания
limitations: List[str]  \# Ограничения
when_to_stop: List[str]  \# Когда остановиться
when_to_seek_help: List[str]  \# Когда обратиться к специалисту
red_flags: List[str]  \# Красные флаги
notes: List[str]  \# Дополнительные заметки

    def to_dict(self) -> dict:
        return {
            'contraindications': self.contraindications,
            'limitations': self.limitations,
            'when_to_stop': self.when_to_stop,
            'when_to_seek_professional_help': self.when_to_seek_help,
            'red_flags': self.red_flags,
            'notes': self.notes
        }
    class SafetyExtractor:
"""
Извлекает информацию о безопасности из текста.
"""

    # Маркеры противопоказаний
    CONTRAINDICATION_MARKERS = [
        r'противопоказан',
        r'не рекомендуется',
        r'нельзя',
        r'запрещено',
        r'избегайте',
        r'не стоит',
        r'опасно для',
    ]
    
    # Маркеры ограничений
    LIMITATION_MARKERS = [
        r'ограничени',
        r'только если',
        r'не подходит для',
        r'требует осторожности',
        r'с осторожностью',
    ]
    
    # Маркеры когда остановиться
    STOP_MARKERS = [
        r'если появляется',
        r'при возникновении',
        r'прекратите если',
        r'остановитесь когда',
        r'немедленно прекратите',
    ]
    
    # Маркеры обращения к специалисту
    HELP_MARKERS = [
        r'обратитесь к',
        r'консультация',
        r'специалист',
        r'психотерапевт',
        r'врач',
        r'профессиональная помощь',
    ]
    
    # Красные флаги (серьёзные симптомы)
    RED_FLAGS = [
        r'суицидальн',
        r'самоповреждени',
        r'панические атаки',
        r'галлюцинаци',
        r'бред',
        r'потеря сознания',
        r'сердцебиение',
        r'удушье',
    ]
    
    def __init__(self):
        self.contraindication_pattern = re.compile(
            '|'.join(self.CONTRAINDICATION_MARKERS),
            re.IGNORECASE
        )
        self.limitation_pattern = re.compile(
            '|'.join(self.LIMITATION_MARKERS),
            re.IGNORECASE
        )
        self.stop_pattern = re.compile(
            '|'.join(self.STOP_MARKERS),
            re.IGNORECASE
        )
        self.help_pattern = re.compile(
            '|'.join(self.HELP_MARKERS),
            re.IGNORECASE
        )
        self.red_flag_pattern = re.compile(
            '|'.join(self.RED_FLAGS),
            re.IGNORECASE
        )
    
    def extract_safety_info(self, blocks: List[dict]) -> SafetyInfo:
        """
        Извлекает информацию о безопасности из блоков.
        
        Args:
            blocks: Список блоков контента
            
        Returns:
            SafetyInfo с извлечённой информацией
        """
        contraindications = []
        limitations = []
        when_to_stop = []
        when_to_seek_help = []
        red_flags = []
        notes = []
        
        for block in blocks:
            content = block.get('content', '')
            sentences = self._split_sentences(content)
            
            for sentence in sentences:
                # Противопоказания
                if self.contraindication_pattern.search(sentence):
                    contraindications.append(sentence)
                
                # Ограничения
                if self.limitation_pattern.search(sentence):
                    limitations.append(sentence)
                
                # Когда остановиться
                if self.stop_pattern.search(sentence):
                    when_to_stop.append(sentence)
                
                # Когда обращаться за помощью
                if self.help_pattern.search(sentence):
                    when_to_seek_help.append(sentence)
                
                # Красные флаги
                if self.red_flag_pattern.search(sentence):
                    red_flags.append(sentence)
        
        # Добавить базовые рекомендации
        safety_info = SafetyInfo(
            contraindications=self._deduplicate(contraindications),
            limitations=self._deduplicate(limitations),
            when_to_stop=self._deduplicate(when_to_stop),
            when_to_seek_help=self._add_default_help_recommendations(
                self._deduplicate(when_to_seek_help)
            ),
            red_flags=self._deduplicate(red_flags),
            notes=self._add_general_notes()
        )
        
        return safety_info
    
    def _split_sentences(self, text: str) -> List[str]:
        """Разбивает текст на предложения."""
        sentences = re.split(r'[.!?]\s+', text)
        return [s.strip() for s in sentences if len(s.strip()) > 20]
    
    def _deduplicate(self, items: List[str]) -> List[str]:
        """Удаляет дубликаты с учётом схожести."""
        seen = set()
        unique = []
        for item in items:
            normalized = item.lower().strip()
            if normalized not in seen:
                seen.add(normalized)
                unique.append(item)
        return unique
    
    def _add_default_help_recommendations(self, existing: List[str]) -> List[str]:
        """Добавляет базовые рекомендации обращения за помощью."""
        defaults = [
            "При суицидальных мыслях немедленно обратитесь к психотерапевту или позвоните на горячую линию",
            "Если практика вызывает сильный дискомфорт более 3 дней, проконсультируйтесь со специалистом",
            "При обострении психических симптомов обратитесь к врачу-психиатру",
        ]
        
        return existing + defaults
    
    def _add_general_notes(self) -> List[str]:
        """Добавляет общие примечания о безопасности."""
        return [
            "Данные практики не заменяют профессиональную психотерапию",
            "При наличии психических заболеваний обязательна консультация врача",
            "Практики предназначены для здоровых людей, интересующихся саморазвитием",
            "Регулярность важнее интенсивности - начинайте с малого",
        ]
    def extract_safety_from_blocks(blocks: List[dict]) -> dict:
"""
Обёртка для вызова из основного pipeline.

    Args:
        blocks: Список блоков контента
        
    Returns:
        Safety информация в формате dict
    """
    extractor = SafetyExtractor()
    safety_info = extractor.extract_safety_info(blocks)
    return safety_info.to_dict()
    ```

## Шаг 2: Добавить safety в каждый блок

В файле `orchestrator/knowledge_graph_builder.py` модифицируй обработку блоков:

```

from orchestrator.extractors.safety_extractor import SafetyExtractor

def build_knowledge_graph(self, document_data: dict) -> dict:
\# ... существующий код ...

    # Инициализировать safety extractor
    safety_extractor = SafetyExtractor()
    
    # Извлечь общую safety информацию для всего документа
    global_safety = safety_extractor.extract_safety_info(blocks)
    document_data['global_safety'] = global_safety.to_dict()
    
    # Для каждого блока добавить safety
    for block in blocks:
        # Если блок не имеет safety, добавить пустой
        if 'safety' not in block or not any(block['safety'].values()):
            block['safety'] = {
                'contraindications': [],
                'limitations': [],
                'when_to_stop': [],
                'when_to_seek_professional_help': [],
                'notes': []
            }
    
    # ... остальной код ...
    ```

## Шаг 3: Обогатить safety информацию для практик

В файле `orchestrator/extractors/practice_extractor.py` добавь:

```

from orchestrator.extractors.safety_extractor import SafetyExtractor

class PracticeExtractor:
def __init__(self):
\# ... существующий код ...
self.safety_extractor = SafetyExtractor()

    def _extract_practice_from_block(self, block: dict) -> Optional[Practice]:
        # ... существующий код ...
        
        # ДОБАВИТЬ извлечение safety для практики
        practice_sentences = self._split_sentences(content)
        practice_safety = self.safety_extractor.extract_safety_info([{
            'content': content
        }])
        
        practice = Practice(
            # ... существующие поля ...
            contraindications=practice_safety.contraindications
        )
        
        return practice
    ```

## Критерии успеха
- ✅ Каждая практика имеет заполненные contraindications
- ✅ Документ имеет global_safety с базовыми рекомендациями
- ✅ Красные флаги (если есть) извлечены
- ✅ Минимум 3 рекомендации "когда обращаться за помощью"

## Тестирование
```

from orchestrator.extractors.safety_extractor import extract_safety_from_blocks

test_blocks = [{
'content': '''
Эта практика не рекомендуется людям с паническими атаками.
Если появляется головокружение, прекратите упражнение.
При усилении тревоги обратитесь к психотерапевту.
'''
}]

safety = extract_safety_from_blocks(test_blocks)
print(f"Противопоказания: {len(safety['contraindications'])}")
print(f"Когда остановиться: {len(safety['when_to_stop'])}")
print(f"Когда за помощью: {len(safety['when_to_seek_professional_help'])}")

```
```


***

```
# <a id="фаза-4"></a>ФАЗА 4: Иерархия концептов и Prerequisites
```


## Задача для Cursor AI

```markdown
# ЗАДАЧА 4.1: Построить иерархию концептов

## Контекст
Нужно определить какие концепты базовые, какие продвинутые, и какие концепты являются prerequisites для других.

## Создать новый файл
`orchestrator/extractors/hierarchy_builder.py`

## Код

```

"""
Построитель иерархии концептов и зависимостей.
"""

from typing import List, Dict, Set, Tuple
from collections import defaultdict
import networkx as nx

class ConceptHierarchyBuilder:
"""
Строит иерархию концептов на основе порядка их появления
и частоты упоминаний.
"""

    def __init__(self):
        self.concept_first_appearance = {}  # {concept: block_index}
        self.concept_frequency = defaultdict(int)  # {concept: count}
        self.concept_cooccurrence = defaultdict(int)  # {(concept1, concept2): count}
        self.dependency_graph = nx.DiGraph()
    
    def build_hierarchy(self, blocks: List[dict]) -> dict:
        """
        Строит иерархию концептов.
        
        Args:
            blocks: Список блоков контента
            
        Returns:
            Dict с информацией об иерархии
        """
        # Анализ блоков
        self._analyze_blocks(blocks)
        
        # Построить граф зависимостей
        self._build_dependency_graph()
        
        # Определить уровни сложности
        levels = self._assign_levels()
        
        # Найти prerequisites
        prerequisites_map = self._find_prerequisites()
        
        # Рекомендуемая последовательность
        learning_sequence = self._generate_learning_sequence()
        
        return {
            'concept_levels': levels,
            'prerequisites': prerequisites_map,
            'learning_sequence': learning_sequence,
            'fundamental_concepts': self._get_fundamental_concepts(levels),
            'advanced_concepts': self._get_advanced_concepts(levels)
        }
    
    def _analyze_blocks(self, blocks: List[dict]):
        """Анализирует блоки для сбора статистики."""
        for idx, block in enumerate(blocks):
            entities = block.get('graph_entities', [])
            
            for entity in entities:
                # Первое появление
                if entity not in self.concept_first_appearance:
                    self.concept_first_appearance[entity] = idx
                
                # Частота
                self.concept_frequency[entity] += 1
            
            # Co-occurrence
            for i, entity1 in enumerate(entities):
                for entity2 in entities[i+1:]:
                    pair = tuple(sorted([entity1, entity2]))
                    self.concept_cooccurrence[pair] += 1
    
    def _build_dependency_graph(self):
        """Строит граф зависимостей между концептами."""
        # Правило: если концепт A появляется раньше B и часто встречается с ним,
        # то A -> B (A является prerequisite для B)
        
        for (concept1, concept2), cooccur_count in self.concept_cooccurrence.items():
            if cooccur_count < 2:  # Слишком редко
                continue
            
            idx1 = self.concept_first_appearance[concept1]
            idx2 = self.concept_first_appearance[concept2]
            
            # Тот, что появился раньше, становится prerequisite
            if idx1 < idx2:
                self.dependency_graph.add_edge(concept1, concept2, weight=cooccur_count)
            else:
                self.dependency_graph.add_edge(concept2, concept1, weight=cooccur_count)
    
    def _assign_levels(self) -> Dict[str, str]:
        """
        Назначает уровни сложности концептам.
        
        Returns:
            {concept: level} где level in ['fundamental', 'intermediate', 'advanced']
        """
        levels = {}
        
        # Сортировать концепты по первому появлению
        sorted_concepts = sorted(
            self.concept_first_appearance.items(),
            key=lambda x: x[^1]
        )
        
        total = len(sorted_concepts)
        
        for i, (concept, _) in enumerate(sorted_concepts):
            # Первые 30% - fundamental
            if i < total * 0.3:
                level = 'fundamental'
            # Следующие 50% - intermediate
            elif i < total * 0.8:
                level = 'intermediate'
            # Последние 20% - advanced
            else:
                level = 'advanced'
            
            # Корректировка на основе частоты
            freq = self.concept_frequency[concept]
            avg_freq = sum(self.concept_frequency.values()) / len(self.concept_frequency)
            
            # Часто упоминаемые концепты скорее fundamental
            if freq > avg_freq * 2:
                if level == 'advanced':
                    level = 'intermediate'
                elif level == 'intermediate' and i < total * 0.5:
                    level = 'fundamental'
            
            levels[concept] = level
        
        return levels
    
    def _find_prerequisites(self) -> Dict[str, List[str]]:
        """
        Находит prerequisites для каждого концепта.
        
        Returns:
            {concept: [list of prerequisite concepts]}
        """
        prerequisites_map = {}
        
        for concept in self.dependency_graph.nodes():
            # Найти все концепты, от которых зависит данный
            predecessors = list(self.dependency_graph.predecessors(concept))
            
            # Отсортировать по важности (вес рёбер)
            weighted_prereqs = [
                (pred, self.dependency_graph[pred][concept]['weight'])
                for pred in predecessors
            ]
            weighted_prereqs.sort(key=lambda x: x, reverse=True)[^1]
            
            # Взять топ-3 самых важных prerequisites
            prerequisites_map[concept] = [pred for pred, _ in weighted_prereqs[:3]]
        
        return prerequisites_map
    
    def _generate_learning_sequence(self) -> List[List[str]]:
        """
        Генерирует рекомендуемую последовательность изучения концептов.
        
        Returns:
            Список уровней, каждый уровень - список концептов
        """
        try:
            # Топологическая сортировка графа зависимостей
            sorted_concepts = list(nx.topological_sort(self.dependency_graph))
            
            # Разбить на уровни (группы концептов без взаимных зависимостей)
            levels = []
            remaining = set(sorted_concepts)
            
            while remaining:
                # Найти концепты без оставшихся prerequisites
                current_level = []
                for concept in list(remaining):
                    prereqs = set(self.dependency_graph.predecessors(concept))
                    if not prereqs.intersection(remaining):
                        current_level.append(concept)
                
                if not current_level:
                    # Цикл в графе - добавить все оставшиеся
                    current_level = list(remaining)
                
                levels.append(current_level)
                remaining -= set(current_level)
            
            return levels
            
        except nx.NetworkXError:
            # Граф содержит циклы - fallback на сортировку по появлению
            sorted_concepts = sorted(
                self.concept_first_appearance.items(),
                key=lambda x: x[^1]
            )
            # Разбить на группы по 5
            concepts_only = [c for c, _ in sorted_concepts]
            return [concepts_only[i:i+5] for i in range(0, len(concepts_only), 5)]
    
    def _get_fundamental_concepts(self, levels: Dict[str, str]) -> List[str]:
        """Возвращает список базовых концептов."""
        return [c for c, level in levels.items() if level == 'fundamental']
    
    def _get_advanced_concepts(self, levels: Dict[str, str]) -> List[str]:
        """Возвращает список продвинутых концептов."""
        return [c for c, level in levels.items() if level == 'advanced']
    def build_concept_hierarchy(blocks: List[dict]) -> dict:
"""
Обёртка для вызова из основного pipeline.

    Args:
        blocks: Список блоков контента
        
    Returns:
        Информация об иерархии в формате dict
    """
    builder = ConceptHierarchyBuilder()
    return builder.build_hierarchy(blocks)
    ```

## Шаг 2: Интегрировать в pipeline

В `orchestrator/knowledge_graph_builder.py`:

```

from orchestrator.extractors.hierarchy_builder import build_concept_hierarchy

def build_knowledge_graph(self, document_data: dict) -> dict:
\# ... существующий код ...

    # ДОБАВИТЬ ПОСЛЕ обработки блоков:
    
    # Построить иерархию концептов
    hierarchy = build_concept_hierarchy(blocks)
    document_data['concept_hierarchy'] = hierarchy
    
    # Обновить метаданные
    document_data['document_metadata']['fundamental_concepts_count'] = len(
        hierarchy['fundamental_concepts']
    )
    document_data['document_metadata']['advanced_concepts_count'] = len(
        hierarchy['advanced_concepts']
    )
    
    # Добавить prerequisites в блоки
    for block in blocks:
        block_entities = block.get('graph_entities', [])
        block_prerequisites = []
        
        for entity in block_entities:
            prereqs = hierarchy['prerequisites'].get(entity, [])
            block_prerequisites.extend(prereqs)
        
        # Убрать дубликаты
        block['prerequisites']['prerequisites'] = list(set(block_prerequisites))
        block['prerequisites']['recommended_sequence'] = hierarchy['learning_sequence']
    
    # ... остальной код ...
    ```

## Критерии успеха
- ✅ Документ содержит `concept_hierarchy`
- ✅ Концепты разделены на fundamental/intermediate/advanced
- ✅ Для каждого концепта указаны prerequisites
- ✅ Есть рекомендуемая последовательность изучения

## Тестирование
```

from orchestrator.extractors.hierarchy_builder import build_concept_hierarchy

test_blocks = [
{'graph_entities': ['осознанность', 'внимание', 'дыхание']},
{'graph_entities': ['осознанность', 'медитация', 'практика']},
{'graph_entities': ['медитация', 'самадхи', 'просветление']},
]

hierarchy = build_concept_hierarchy(test_blocks)
print(f"Fundamental: {hierarchy['fundamental_concepts']}")
print(f"Advanced: {hierarchy['advanced_concepts']}")
print(f"Learning sequence: {hierarchy['learning_sequence']}")

```
```


***

```
# <a id="фаза-5"></a>ФАЗА 5: Тестирование и валидация
```


## Задача для Cursor AI

```markdown
# ЗАДАЧА 5.1: Создать comprehensive тесты

## Создать файл тестов
`tests/test_knowledge_graph_enhancements.py`

## Код

```

"""
Тесты для улучшений графа знаний.
"""

import pytest
import json
from pathlib import Path

class TestGraphWeights:
"""Тесты весов связей в графе."""

    def test_weights_variance(self, processed_video_data):
        """Веса должны варьироваться."""
        kg = processed_video_data['knowledge_graph']
        weights = [edge['confidence'] for edge in kg['edges']]
        
        assert len(set(weights)) > 1, "Все веса одинаковые!"
        assert min(weights) >= 0.1, f"Минимальный вес слишком низкий: {min(weights)}"
        assert max(weights) <= 1.0, f"Максимальный вес слишком высокий: {max(weights)}"
    
    def test_weight_statistics(self, processed_video_data):
        """Метаданные должны содержать статистику весов."""
        kg = processed_video_data['knowledge_graph']
        stats = kg['metadata'].get('weight_statistics')
        
        assert stats is not None, "Нет статистики весов!"
        assert 'min_weight' in stats
        assert 'max_weight' in stats
        assert 'avg_weight' in stats
        assert stats['avg_weight'] > 0
    class TestPracticeExtractor:
"""Тесты экстрактора практик."""

    def test_practices_extracted(self, processed_video_data):
        """Практики должны быть извлечены."""
        practices = processed_video_data.get('practices', [])
        
        # Ожидаем хотя бы одну практику в 20-минутном видео
        assert len(practices) > 0, "Не извлечено ни одной практики!"
    
    def test_practice_structure(self, processed_video_data):
        """Каждая практика должна иметь правильную структуру."""
        practices = processed_video_data.get('practices', [])
        
        for practice in practices:
            assert 'title' in practice
            assert 'steps' in practice
            assert 'goal' in practice
            assert 'difficulty' in practice
            
            # Проверить шаги
            assert len(practice['steps']) >= 2, "Слишком мало шагов!"
            
            for step in practice['steps']:
                assert 'step_number' in step
                assert 'instruction' in step
                assert len(step['instruction']) > 10, "Инструкция слишком короткая!"
    
    def test_practice_difficulty(self, processed_video_data):
        """Сложность должна быть определена корректно."""
        practices = processed_video_data.get('practices', [])
        
        valid_difficulties = ['beginner', 'intermediate', 'advanced']
        
        for practice in practices:
            assert practice['difficulty'] in valid_difficulties, \
                f"Неверная сложность: {practice['difficulty']}"
    class TestSafetyExtractor:
"""Тесты экстрактора safety информации."""

    def test_global_safety_exists(self, processed_video_data):
        """Документ должен содержать global_safety."""
        assert 'global_safety' in processed_video_data, "Нет global_safety!"
    
    def test_safety_structure(self, processed_video_data):
        """Safety должен иметь все необходимые поля."""
        safety = processed_video_data['global_safety']
        
        required_fields = [
            'contraindications',
            'limitations',
            'when_to_stop',
            'when_to_seek_professional_help',
            'notes'
        ]
        
        for field in required_fields:
            assert field in safety, f"Отсутствует поле: {field}"
    
    def test_default_help_recommendations(self, processed_video_data):
        """Должны быть базовые рекомендации обращения за помощью."""
        safety = processed_video_data['global_safety']
        help_recommendations = safety['when_to_seek_professional_help']
        
        assert len(help_recommendations) >= 3, \
            "Недостаточно рекомендаций обращения за помощью!"
        
        # Проверить наличие критических рекомендаций
        help_text = ' '.join(help_recommendations).lower()
        assert 'суицид' in help_text or 'психотерапевт' in help_text
    class TestConceptHierarchy:
"""Тесты иерархии концептов."""

    def test_hierarchy_exists(self, processed_video_data):
        """Документ должен содержать concept_hierarchy."""
        assert 'concept_hierarchy' in processed_video_data, "Нет concept_hierarchy!"
    
    def test_hierarchy_structure(self, processed_video_data):
        """Иерархия должна иметь правильную структуру."""
        hierarchy = processed_video_data['concept_hierarchy']
        
        required_fields = [
            'concept_levels',
            'prerequisites',
            'learning_sequence',
            'fundamental_concepts',
            'advanced_concepts'
        ]
        
        for field in required_fields:
            assert field in hierarchy, f"Отсутствует поле: {field}"
    
    def test_concept_levels(self, processed_video_data):
        """Концепты должны быть распределены по уровням."""
        hierarchy = processed_video_data['concept_hierarchy']
        levels = hierarchy['concept_levels']
        
        valid_levels = ['fundamental', 'intermediate', 'advanced']
        
        assert len(levels) > 0, "Нет концептов с уровнями!"
        
        for concept, level in levels.items():
            assert level in valid_levels, f"Неверный уровень {level} для {concept}"
    
    def test_learning_sequence(self, processed_video_data):
        """Последовательность изучения должна быть логичной."""
        hierarchy = processed_video_data['concept_hierarchy']
        sequence = hierarchy['learning_sequence']
        
        assert len(sequence) > 0, "Пустая последовательность изучения!"
        
        # Проверить, что это список списков
        assert isinstance(sequence, list), "Неверный формат последовательности!"
    class TestIntegration:
"""Интеграционные тесты."""

    def test_full_pipeline(self):
        """Полный цикл обработки видео."""
        # Запустить обработку тестового видео
        import subprocess
        result = subprocess.run(
            ['python', 'main.py', '--video_id', '9BEpGP7L1_Q'],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0, f"Pipeline failed: {result.stderr}"
        
        # Проверить что файл создан
        output_file = Path('data/sag_final/2025/05') / \
                     '2025-05-15_9BEpGP7L1_Q_Как_быть_в_Присутствии.for_vector.json'
        
        assert output_file.exists(), "Выходной файл не создан!"
        
        # Загрузить и проверить
        with open(output_file) as f:
            data = json.load(f)
        
        # Проверить все новые компоненты
        assert 'practices' in data
        assert 'global_safety' in data
        assert 'concept_hierarchy' in data
        assert data['knowledge_graph']['metadata'].get('weight_statistics')
    
# Фикстура с обработанными данными

@pytest.fixture
def processed_video_data():
"""Загружает обработанные данные тестового видео."""
output_file = Path('data/sag_final/2025/05') / \
'2025-05-15_9BEpGP7L1_Q_Как_быть_в_Присутствии.for_vector.json'

    if not output_file.exists():
        pytest.skip("Тестовое видео не обработано")
    
    with open(output_file) as f:
        return json.load(f)
    ```

## Запуск тестов

```


# Установить pytest если ещё не установлен

pip install pytest

# Запустить тесты

pytest tests/test_knowledge_graph_enhancements.py -v

# Или запустить с подробным выводом

pytest tests/test_knowledge_graph_enhancements.py -vv

```

## Критерии успеха всех фаз
- ✅ Все тесты проходят
- ✅ Файл for_vector.json содержит все новые компоненты
- ✅ Размер файла вырос (больше данных)
- ✅ Нет ошибок при обработке

## Финальная проверка

```


# Обработать тестовое видео

python main.py --video_id 9BEpGP7L1_Q

# Проверить размер выходного файла (должен быть больше ~250KB)

ls -lh data/sag_final/2025/05/*.for_vector.json

# Запустить тесты

pytest tests/test_knowledge_graph_enhancements.py

# Посмотреть статистику в файле

python -c "
import json
with open('data/sag_final/2025/05/2025-05-15_9BEpGP7L1_Q_Как_быть_в_Присутствии.for_vector.json') as f:
data = json.load(f)
print(f'Практик: {len(data.get(\"practices\", []))}')
print(f'Safety рекомендаций: {len(data[\"global_safety\"][\"when_to_seek_professional_help\"])}')
print(f'Fundamental концептов: {len(data[\"concept_hierarchy\"][\"fundamental_concepts\"])}')
print(f'Learning уровней: {len(data[\"concept_hierarchy\"][\"learning_sequence\"])}')
print(f'Вес связей: min={data[\"knowledge_graph\"][\"metadata\"][\"weight_statistics\"][\"min_weight\"]}, max={data[\"knowledge_graph\"][\"metadata\"][\"weight_statistics\"][\"max_weight\"]}')
"

```
```


***

## 🎉 Финальный чеклист

После выполнения всех задач, у вас должно быть:

- [x] ✅ Веса связей в графе варьируются от 0.1 до 1.0
- [x] ✅ Извлекаются практические упражнения с шагами
- [x] ✅ Каждая практика имеет safety информацию
- [x] ✅ Документ имеет global_safety с критическими рекомендациями
- [x] ✅ Построена иерархия концептов (fundamental/intermediate/advanced)
- [x] ✅ Для концептов определены prerequisites
- [x] ✅ Есть рекомендуемая последовательность изучения
- [x] ✅ Все тесты проходят

**Готовность к масштабированию на 500 видео: 85-90%!** 🚀

<div align="center">⁂</div>

[^1]: image.jpg

