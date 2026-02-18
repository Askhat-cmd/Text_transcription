

***

# 📋 PRD v3.0 — Интеллектуальный Бот-Психолог

### Адаптация по Спиральной Динамике Клэра Грейвза

**Исполнитель:** Cursor AI Agent (CODEX) | **Приоритет:** Качество | **Дедлайн:** нет

***

## 0. ПРОЧИТАЙ ПЕРЕД СТАРТОМ

Существует **два репозитория**. Твоя задача затрагивает оба.

**Репозиторий 1** — `voice_bot_pipeline` (подготовка данных, офлайн-пайплайн)
**Репозиторий 2** — `Text_transcription` → папка `bot_psychologist/` (сам бот, онлайн-диалог)

Перед началом работы **обязательно прочитай** эти файлы целиком:

- `bot_psychologist/bot_agent/answer_adaptive.py` — главный оркестратор бота
- `bot_psychologist/bot_agent/conversation_memory.py` — структура памяти
- `bot_psychologist/bot_agent/state_classifier.py` — классификатор состояний
- `bot_psychologist/bot_agent/retrieval/` — текущий поиск блоков
- `bot_psychologist/bot_agent/response/` — генерация ответа
- `voice_bot_pipeline/pipeline_orchestrator.py` — пайплайн данных
- `voice_bot_pipeline/text_processor/` — нарезка блоков

**Правило:** не переписывай то, что работает. Только добавляй и расширяй. Исключение — `answer_adaptive.py` требует точечного рефакторинга (описано в Части 2).

***

## 1. ФИЛОСОФИЯ И ЦЕЛЬ

Бот не лечит, не даёт советы и не учит жить. Он **слышит** человека на том уровне, на котором тот находится, и отвечает **на его языке**.

Спиральная Динамика — это не метка и не диагноз. Это **фильтр безопасности**: ответ на уровень выше готовности пользователя может причинить вред его психике. Ответ на уровень ниже — просто бесполезен. Задача бота — попасть точно.

**Главные принципы:**

- При неопределённости — отвечай на уровень **ниже**, не выше
- Кризисное состояние временно **снижает** доступный уровень
- SD-фильтр никогда не оставляет пустой список блоков
- При сбое любого SD-модуля — бот продолжает работу без адаптации (fallback на GREEN)

***

## 2. КАРТА ИЗМЕНЕНИЙ

```
voice_bot_pipeline/
├── config/
│   ├── authors/
│   │   ├── salamat_sarsekenov.yaml      ← СОЗДАТЬ
│   │   └── _author_template.yaml        ← СОЗДАТЬ
│   └── sd_levels.yaml                   ← СОЗДАТЬ
├── text_processor/
│   └── sd_labeler.py                    ← СОЗДАТЬ (SD-разметка блоков)
├── data/graphs/
│   ├── base_graph.json                  ← СОЗДАТЬ
│   └── authors/
│       └── salamat_graph.json           ← СОЗДАТЬ
└── pipeline_orchestrator.py             ← ИЗМЕНИТЬ (вызов sd_labeler)

Text_transcription/bot_psychologist/bot_agent/
├── sd_classifier.py                     ← СОЗДАТЬ (главный новый модуль)
├── retrieval/
│   └── sd_filter.py                     ← СОЗДАТЬ
├── response/
│   └── response_generator.py            ← ИЗМЕНИТЬ (подключить SD-промты)
├── prompt_sd_purple.md                  ← СОЗДАТЬ
├── prompt_sd_red.md                     ← СОЗДАТЬ
├── prompt_sd_blue.md                    ← СОЗДАТЬ
├── prompt_sd_orange.md                  ← СОЗДАТЬ
├── prompt_sd_green.md                   ← СОЗДАТЬ
├── prompt_sd_yellow.md                  ← СОЗДАТЬ
├── prompt_system_base.md                ← НЕ ТРОГАТЬ
├── answer_adaptive.py                   ← ИЗМЕНИТЬ (добавить SD-pipeline)
└── conversation_memory.py               ← ИЗМЕНИТЬ (добавить SD-профиль)
```


***

## ЧАСТЬ 1: `voice_bot_pipeline` — Подготовка данных

### 1.1 Конфиг авторов

Создать: `voice_bot_pipeline/config/authors/salamat_sarsekenov.yaml`

```yaml
author_id: "salamat"
display_name: "Саламат Сарсекенов"
youtube_channel_id: ""
primary_sd_levels: ["GREEN", "YELLOW"]
language: "ru"
terminology_file: "config/terminology/salamat_terms.yaml"
collection_name: "salamat_blocks"
active: true
description: >
  Нейросталкинг, работа с состояниями, осознанностью, внутренними конфликтами.
  Фокус: GREEN (эмпатия, чувства) и YELLOW (системное мышление, метанаблюдение).
```

Создать: `voice_bot_pipeline/config/authors/_author_template.yaml`

```yaml
# Шаблон для добавления нового автора.
# Скопируй этот файл, переименуй и заполни все поля.
author_id: ""
display_name: ""
youtube_channel_id: ""
primary_sd_levels: []    # уровни СД которые покрывает автор
language: "ru"
terminology_file: ""
collection_name: ""
active: true
description: ""
```


### 1.2 Конфиг уровней СД

Создать: `voice_bot_pipeline/config/sd_levels.yaml`

```yaml
levels:
  BEIGE:
    label: "Выживание"
    description: "Базовые инстинкты, физическое выживание, потеря контроля над телом"
    keywords: ["выживание", "не могу дышать", "страшно умереть", "инстинкт", "физически плохо"]
    communication_style: "Предельно просто и конкретно. Только про безопасность прямо сейчас."
    forbidden_concepts: ["смысл жизни", "развитие", "цели", "осознанность", "чувства"]

  PURPLE:
    label: "Племя / Магия"
    description: "Коллективная безопасность, традиции, авторитет семьи, магическое мышление"
    keywords: ["традиции", "семья", "предки", "так принято", "ритуал", "боюсь сглазить", "судьба"]
    communication_style: "Уважение к коллективу. Метафоры из привычного мира. Принятие традиций."
    forbidden_concepts: ["сломай шаблон", "твоя жизнь — только твоя", "индивидуализм"]

  RED:
    label: "Сила / Импульс"
    description: "Эго, власть, немедленное действие, нарушение уважения, импульсивность"
    keywords: ["хочу", "достали", "накажу", "не буду терпеть", "должны мне", "уважение", "сила"]
    communication_style: "Коротко, прямо. Признать силу. Конкретное действие — не абстракция."
    forbidden_concepts: ["принятие", "осознанность", "чувства других", "подожди", "потерпи"]

  BLUE:
    label: "Порядок / Долг"
    description: "Правила, долг, вина, дисциплина, иерархия, нарушение должного"
    keywords: ["должен", "должна", "обязан", "грех", "правильно", "нарушил", "вина", "дисциплина"]
    communication_style: "Структура, чёткие шаги. Уважение к правилам. Работа с виной — без отрицания правила."
    forbidden_concepts: ["правила — условность", "делай что хочешь", "всё относительно"]

  ORANGE:
    label: "Успех / Достижения"
    description: "Рациональность, цели, эффективность, конкуренция, причинно-следственный анализ"
    keywords: ["успех", "результат", "эффективно", "цели", "выгода", "карьера", "логично", "что это даст"]
    communication_style: "Логика и причины обязательны. Механизм работы. Связь с практической пользой."
    forbidden_concepts: ["просто почувствуй", "прими без цели", "это не важно"]

  GREEN:
    label: "Эмпатия / Сообщество"
    description: "Чувства, принятие, диалог, связь с людьми, самопонимание"
    keywords: ["чувствую", "хочу понять", "принятие", "поддержка", "вместе", "связь", "тревога"]
    communication_style: "Начать с валидации чувств. Тепло, принятие, без осуждения."
    forbidden_concepts: ["соревнование", "будь эффективнее", "не важно что чувствуешь"]

  YELLOW:
    label: "Интеграция / Системность"
    description: "Метанаблюдение, паттерны, системный взгляд, интеграция противоречий"
    keywords: ["замечаю паттерн", "замечаю что я", "система", "интеграция", "метанаблюдение", "контекст"]
    communication_style: "Мета-уровень. Парадоксы принимаются. Системный взгляд. Нелинейность допустима."
    forbidden_concepts: ["одно правильное решение", "это просто хорошо/плохо"]

  TURQUOISE:
    label: "Холизм / Единство"
    description: "Трансличностное, единство всего, целостность бытия"
    keywords: ["единство", "целостность бытия", "всё одно", "трансцендентность", "планетарное"]
    communication_style: "Холистично. Без дуализма. Трансперсонально."
    forbidden_concepts: ["разделяй", "борись", "победи", "моё vs чужое"]
```


***

### 1.3 SD-разметка блоков

Создать: `voice_bot_pipeline/text_processor/sd_labeler.py`

```python
"""
SD Labeler — автоматическая SD-разметка чанков при подготовке БД.
Вызывается в pipeline_orchestrator.py после нарезки текста на блоки.
Каждый блок получает sd_metadata: уровень СД, сложность, тон.
"""

import json
import logging
from typing import Optional
from openai import OpenAI

logger = logging.getLogger(__name__)

SD_LABELER_SYSTEM_PROMPT = """
Ты — эксперт по теории Спиральной Динамики Клэра Грейвза.
Тебе дан фрагмент психологического или развивающего текста.

Определи, к какому уровню сознания ОБРАЩАЕТСЯ этот текст
(не какой уровень описывает, а какому читателю он подходит).

КРИТЕРИИ УРОВНЕЙ:
- BEIGE: выживание, базовые страхи, физическая безопасность
- PURPLE: традиции, семья важнее личного, магическое мышление, коллектив
- RED: сила, власть, немедленное действие, ego-центризм
- BLUE: правила, долг, вина, дисциплина, иерархия
- ORANGE: успех, цели, эффективность, логика, рациональность
- GREEN: чувства, эмпатия, принятие, сообщество, диалог
- YELLOW: паттерны, системы, метанаблюдение, интеграция противоречий
- TURQUOISE: единство всего, трансличностное, холизм

ПРАВИЛО: при неуверенности — выбери уровень НИЖЕ (безопаснее).

Верни ТОЛЬКО JSON без пояснений:
{
  "sd_level": "GREEN",
  "sd_secondary": "YELLOW",
  "complexity_score": 4,
  "emotional_tone": "validating",
  "requires_prior_concepts": false,
  "reasoning": "краткое объяснение в 1 предложении"
}

emotional_tone: validating / challenging / educational / neutral / grounding
complexity_score: 1 (очень просто) — 10 (требует глубокой подготовки)
"""


class SDLabeler:
    """Автоматическая SD-разметка блоков через LLM."""

    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.1):
        self.client = OpenAI()
        self.model = model
        self.temperature = temperature

    def label_block(self, block_content: str, block_id: str = "") -> dict:
        """Разметить один блок по уровню СД."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                temperature=self.temperature,
                max_tokens=200,
                messages=[
                    {"role": "system", "content": SD_LABELER_SYSTEM_PROMPT},
                    {"role": "user", "content": f"Текст блока:\n\n{block_content[:1500]}"}
                ]
            )
            raw = response.choices[0].message.content.strip()
            result = json.loads(raw)
            logger.info(
                f"[SD_LABELER] block_id={block_id} → {result['sd_level']} "
                f"(complexity={result['complexity_score']})"
            )
            return result
        except json.JSONDecodeError as e:
            logger.warning(f"[SD_LABELER] JSON parse error for block {block_id}: {e}")
            return self._default_label()
        except Exception as e:
            logger.error(f"[SD_LABELER] error for block {block_id}: {e}")
            return self._default_label()

    def label_blocks_batch(self, blocks: list, author_id: str = "") -> list:
        """
        Разметить список блоков. Добавляет поле sd_metadata к каждому блоку.

        Args:
            blocks: список dict с полями block_id, content
            author_id: ID автора из конфига authors/
        Returns:
            blocks с добавленным полем sd_metadata
        """
        labeled = []
        for i, block in enumerate(blocks):
            sd_data = self.label_block(
                block_content=block.get("content", ""),
                block_id=block.get("block_id", str(i))
            )
            block["sd_metadata"] = {
                **sd_data,
                "author_id": author_id,
                "labeled_by": "sd_labeler_v1"
            }
            labeled.append(block)
            if (i + 1) % 10 == 0:
                logger.info(f"[SD_LABELER] Progress: {i + 1}/{len(blocks)} blocks labeled")
        return labeled

    def _default_label(self) -> dict:
        """Безопасное значение при ошибке."""
        return {
            "sd_level": "GREEN",
            "sd_secondary": None,
            "complexity_score": 5,
            "emotional_tone": "neutral",
            "requires_prior_concepts": False,
            "reasoning": "default fallback on error"
        }
```

**Изменить `pipeline_orchestrator.py`** — добавить вызов SDLabeler после нарезки блоков:

```python
# Найти место после получения blocks от SAG-процессора и добавить:

from text_processor.sd_labeler import SDLabeler

# После: blocks = sag_processor.process(...)
# Добавить:
if config.get("sd_labeling", {}).get("enabled", True):
    labeler = SDLabeler(
        model=config.get("sd_labeling", {}).get("model", "gpt-4o-mini"),
        temperature=0.1
    )
    author_id = config.get("author", {}).get("author_id", "unknown")
    blocks = labeler.label_blocks_batch(blocks, author_id=author_id)
    logger.info(f"[PIPELINE] SD labeling complete: {len(blocks)} blocks labeled")
```

**Изменить `vector_db/vector_indexer.py`** — добавить SD-поля в metadata ChromaDB:

```python
# Найти место формирования metadata при индексации и добавить поля:
metadata = {
    # ... существующие поля без изменений ...

    # ДОБАВИТЬ:
    "sd_level": block.get("sd_metadata", {}).get("sd_level", "GREEN"),
    "sd_secondary": block.get("sd_metadata", {}).get("sd_secondary") or "",
    "emotional_tone": block.get("sd_metadata", {}).get("emotional_tone", "neutral"),
    "requires_prior_concepts": block.get("sd_metadata", {}).get("requires_prior_concepts", False),
    "author_id": block.get("sd_metadata", {}).get("author_id", "unknown"),
}
```


***

### 1.4 Граф знаний

Создать: `voice_bot_pipeline/data/graphs/base_graph.json`

```json
{
  "version": "1.0",
  "description": "Universal psychological concepts graph — shared across all authors",
  "nodes": [
    {
      "id": "anxiety", "label": "Тревога", "type": "emotion",
      "sd_levels": ["PURPLE","RED","BLUE","ORANGE","GREEN","YELLOW"],
      "sd_adaptations": {
        "PURPLE": "Страх неизвестного, потеря защиты коллектива",
        "RED": "Угроза контролю или уважению",
        "BLUE": "Страх нарушить правило или потерять порядок",
        "ORANGE": "Риск не достичь цели или потерять позиции",
        "GREEN": "Внутреннее беспокойство, разрыв с собой или другими",
        "YELLOW": "Сигнал системы о рассогласованности паттернов"
      }
    },
    {
      "id": "anger", "label": "Гнев", "type": "emotion",
      "sd_levels": ["RED","BLUE","ORANGE","GREEN"],
      "sd_adaptations": {
        "RED": "Нарушение моей воли или уважения",
        "BLUE": "Нарушение справедливости или правила",
        "ORANGE": "Препятствие к цели",
        "GREEN": "Сигнал о нарушении моих границ или ценностей"
      }
    },
    {
      "id": "shame", "label": "Стыд", "type": "emotion",
      "sd_levels": ["PURPLE","BLUE","ORANGE","GREEN"]
    },
    {
      "id": "guilt", "label": "Вина", "type": "emotion",
      "sd_levels": ["BLUE","GREEN"],
      "sd_adaptations": {
        "BLUE": "Нарушение обязанности или правила",
        "GREEN": "Причинение боли другому человеку"
      }
    },
    {
      "id": "fear", "label": "Страх", "type": "emotion",
      "sd_levels": ["BEIGE","PURPLE","RED","BLUE"]
    },
    {
      "id": "loneliness", "label": "Одиночество", "type": "emotion",
      "sd_levels": ["PURPLE","BLUE","GREEN"]
    },
    {
      "id": "confusion", "label": "Замешательство", "type": "emotion",
      "sd_levels": ["BLUE","ORANGE","GREEN","YELLOW"]
    },
    {
      "id": "emptiness", "label": "Пустота / Бессмысленность", "type": "emotion",
      "sd_levels": ["ORANGE","GREEN","YELLOW"],
      "sd_adaptations": {
        "ORANGE": "Достиг целей, но удовлетворения нет — кризис ORANGE",
        "GREEN": "Потеря связи с собой или другими",
        "YELLOW": "Исчерпание старых смысловых систем"
      }
    },
    {
      "id": "breathing_practice", "label": "Дыхательные практики", "type": "practice",
      "sd_levels": ["RED","BLUE","ORANGE","GREEN","YELLOW"],
      "sd_adaptations": {
        "RED": "Дыши — это контроль над собой. Сила через дыхание.",
        "BLUE": "Техника: 4 счёта вдох, 7 задержка, 8 выдох. Повторить 3 раза.",
        "ORANGE": "Снижает кортизол за 5 минут. Работает через регуляцию CO2.",
        "GREEN": "Дыхание помогает вернуться к себе и своим чувствам.",
        "YELLOW": "Переключение нервной системы из симпатики в парасимпатику."
      }
    },
    {
      "id": "grounding", "label": "Заземление", "type": "practice",
      "sd_levels": ["BEIGE","PURPLE","RED","BLUE","GREEN","YELLOW"],
      "sd_adaptations": {
        "BEIGE": "Почувствуй ноги на полу. Ты здесь. Ты в безопасности.",
        "PURPLE": "Почувствуй землю под ногами, как чувствовали предки.",
        "RED": "Вернись в тело. Ты здесь, ты сильный.",
        "BLUE": "Техника 5-4-3-2-1: назови 5 вещей которые видишь...",
        "GREEN": "Почувствуй своё тело. Побудь с тем, что есть.",
        "YELLOW": "Переключение внимания с абстрактного на сенсорный уровень."
      }
    },
    {
      "id": "self_observation", "label": "Самонаблюдение", "type": "practice",
      "sd_levels": ["GREEN","YELLOW","TURQUOISE"]
    },
    {
      "id": "boundaries", "label": "Границы", "type": "concept",
      "sd_levels": ["RED","BLUE","ORANGE","GREEN","YELLOW"],
      "sd_adaptations": {
        "RED": "Чего ты не позволишь делать с собой",
        "BLUE": "Правила взаимодействия, которые важно соблюдать",
        "ORANGE": "Условия, при которых сотрудничество эффективно",
        "GREEN": "Уважение к своим и чужим потребностям",
        "YELLOW": "Динамическая система соглашений в зависимости от контекста"
      }
    }
  ],
  "edges": [
    {"from": "anxiety", "to": "breathing_practice", "type": "helps_with", "weight": 0.90},
    {"from": "anxiety", "to": "grounding", "type": "helps_with", "weight": 0.85},
    {"from": "fear", "to": "grounding", "type": "helps_with", "weight": 0.80},
    {"from": "anger", "to": "breathing_practice", "type": "helps_with", "weight": 0.75},
    {"from": "emptiness", "to": "self_observation", "type": "helps_with", "weight": 0.70},
    {"from": "guilt", "to": "boundaries", "type": "related_to", "weight": 0.65},
    {"from": "loneliness", "to": "boundaries", "type": "related_to", "weight": 0.60}
  ]
}
```

Создать: `voice_bot_pipeline/data/graphs/authors/salamat_graph.json`

```json
{
  "author_id": "salamat",
  "extends": "base_graph",
  "description": "Авторские концепты Саламата Сарсекенова",
  "custom_nodes": [
    {
      "id": "neurostalking",
      "label": "Нейросталкинг",
      "author_term": true,
      "maps_to_universal": "self_observation",
      "sd_levels": ["GREEN", "YELLOW"],
      "description": "Метод наблюдения за собственными паттернами реагирования"
    },
    {
      "id": "presence_state",
      "label": "Состояние присутствия",
      "author_term": true,
      "maps_to_universal": "grounding",
      "sd_levels": ["GREEN", "YELLOW"]
    }
  ],
  "custom_edges": [
    {"from": "neurostalking", "to": "anxiety", "type": "addresses", "weight": 0.90},
    {"from": "neurostalking", "to": "self_observation", "type": "similar_to", "weight": 0.95},
    {"from": "presence_state", "to": "grounding", "type": "similar_to", "weight": 0.90}
  ]
}
```


***

## ЧАСТЬ 2: `bot_psychologist` — Логика бота

### 2.1 Главный новый модуль: SD-классификатор

Создать: `bot_psychologist/bot_agent/sd_classifier.py`

```python
"""
SD Classifier — определяет уровень Спиральной Динамики пользователя.

Стратегия (3 уровня):
  1. Быстрая эвристика по ключевым словам (0 API-вызовов)
  2. LLM-классификация если эвристика дала confidence < 0.65
  3. Накопленный профиль если 15+ сообщений с confidence >= 0.80

Принцип безопасности: при неопределённости — выбирать уровень НИЖЕ.
"""

import json
import logging
from collections import Counter
from dataclasses import dataclass, field
from typing import List, Optional
from openai import OpenAI

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────
# КОНСТАНТЫ
# ──────────────────────────────────────────────────────────────

SD_LEVELS_ORDER = [
    "BEIGE", "PURPLE", "RED", "BLUE", "ORANGE", "GREEN", "YELLOW", "TURQUOISE"
]

# Ключевые слова-индикаторы уровней (для быстрой эвристики)
SD_KEYWORDS: dict = {
    "BEIGE":     ["не могу дышать", "страшно умереть", "физически плохо", "выживание", "теряю сознание"],
    "PURPLE":    ["традиции", "предки", "семья решает", "так принято", "ритуал",
                  "боюсь сглазить", "судьба", "порча", "у нас в семье"],
    "RED":       ["хочу", "достали", "накажу", "не буду терпеть", "должны мне",
                  "уважение", "он меня", "они меня", "надоело терпеть"],
    "BLUE":      ["должен", "должна", "обязан", "грех", "правильно", "нарушил",
                  "вина", "чувствую вину", "дисциплина", "как положено", "так нельзя"],
    "ORANGE":    ["успех", "результат", "эффективно", "цели", "выгода", "карьера",
                  "логично", "что это даст", "стратегия", "не работает"],
    "GREEN":     ["чувствую", "хочу понять", "принятие", "поддержка", "вместе",
                  "связь", "тревога", "эмпатия", "не могу справиться"],
    "YELLOW":    ["замечаю паттерн", "замечаю что я", "система", "интеграция",
                  "метанаблюдение", "контекст", "откуда это", "всегда так реагирую"],
    "TURQUOISE": ["единство", "целостность бытия", "всё одно", "трансцендентность", "планетарное"],
}

# ──────────────────────────────────────────────────────────────
# БАЗОВАЯ МАТРИЦА СОВМЕСТИМОСТИ
# Правило: текущий уровень + 1 вверх для мягкого роста
# Никогда не прыгать через уровень
# ──────────────────────────────────────────────────────────────
SD_COMPATIBILITY_BASE: dict = {
    "BEIGE":     ["BEIGE", "PURPLE"],
    "PURPLE":    ["PURPLE", "RED"],
    "RED":       ["RED", "BLUE"],
    "BLUE":      ["BLUE", "ORANGE"],
    "ORANGE":    ["ORANGE", "GREEN"],
    "GREEN":     ["GREEN", "YELLOW"],
    "YELLOW":    ["GREEN", "YELLOW", "TURQUOISE"],
    "TURQUOISE": ["YELLOW", "TURQUOISE"],
}

# Для обратной совместимости
SD_COMPATIBILITY = SD_COMPATIBILITY_BASE

# ──────────────────────────────────────────────────────────────
# ПРОМТ ДЛЯ LLM-КЛАССИФИКАЦИИ
# ──────────────────────────────────────────────────────────────
SD_CLASSIFIER_SYSTEM_PROMPT = """
Ты — эксперт по Спиральной Динамике Клэра Грейвза.
Определи, с какого уровня сознания говорит человек.

Анализируй: язык, ценности, что считается проблемой, что считается решением,
эмоциональный фокус, отношение к правилам и другим людям.

УРОВНИ:
- BEIGE: выживание, физические страхи, "не могу", инстинктивные реакции
- PURPLE: "так принято", семья/коллектив важнее личного, магическое мышление
- RED: "я хочу", сила, власть, немедленный результат, ego-центризм
- BLUE: "должен/обязан", правила, вина, дисциплина, иерархия
- ORANGE: цели, эффективность, "что мне даёт", логика, конкуренция
- GREEN: чувства, эмпатия, принятие, "мы вместе", самопонимание
- YELLOW: паттерны, системность, метанаблюдение, "замечаю что..."
- TURQUOISE: единство всего, трансличностное, целостность

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ЧИСТЫЕ УРОВНИ
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"Не могу нормально дышать когда думаю об этом, физически плохо"
→ {"primary":"BEIGE","secondary":null,"confidence":0.87,"indicator":"физический страх, потеря контроля над телом"}

"Мама говорит что так нельзя, у нас в семье никогда так не поступали"
→ {"primary":"PURPLE","secondary":null,"confidence":0.85,"indicator":"авторитет семьи важнее личного решения"}

"Все вокруг бесят, никто не уважает, надоело терпеть"
→ {"primary":"RED","secondary":null,"confidence":0.83,"indicator":"нарушение уважения, импульс к действию"}

"Я должна была этого не делать, это мой долг, чувствую вину"
→ {"primary":"BLUE","secondary":null,"confidence":0.88,"indicator":"долг+вина, нарушение правила"}

"Понимаю что неэффективно, но продолжаю — хочу разобраться почему"
→ {"primary":"ORANGE","secondary":null,"confidence":0.82,"indicator":"анализ эффективности своего поведения"}

"Не могу справиться с тревогой, очень хочу понять что я чувствую"
→ {"primary":"GREEN","secondary":null,"confidence":0.84,"indicator":"фокус на чувствах, самопонимание"}

"Замечаю что каждый раз в стрессе реагирую по одному паттерну — интересно откуда это"
→ {"primary":"YELLOW","secondary":null,"confidence":0.86,"indicator":"метанаблюдение, любопытство к паттерну"}

"Чувствую связь со всем, мои проблемы — часть чего-то большего"
→ {"primary":"TURQUOISE","secondary":null,"confidence":0.79,"indicator":"трансличностный фокус"}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ПОГРАНИЧНЫЕ СЛУЧАИ (переходы)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

— PURPLE → RED (просыпается личная воля, но коллектив ещё важен) —

"Семья говорит одно, а я хочу другого — не знаю кого слушать"
→ {"primary":"PURPLE","secondary":"RED","confidence":0.72,"indicator":"конфликт авторитета семьи с личным желанием"}

"Устал жить по чужим правилам, хочу сам решать — но страшно подвести своих"
→ {"primary":"RED","secondary":"PURPLE","confidence":0.74,"indicator":"пробуждение эго при страхе отвержения коллективом"}

— RED → BLUE (импульс + появляется совесть) —

"Накричал на него, правильно ему — хотя наверное так не должен был"
→ {"primary":"RED","secondary":"BLUE","confidence":0.71,"indicator":"RED-оправдание + BLUE-сомнение в правильности"}

"Хочу наказать, но понимаю что по правилам так нельзя"
→ {"primary":"RED","secondary":"BLUE","confidence":0.75,"indicator":"RED-импульс сдерживается BLUE-правилом"}

"Достали, делаю что хочу — но потом мучает совесть, что подвёл команду"
→ {"primary":"BLUE","secondary":"RED","confidence":0.70,"indicator":"BLUE-вина доминирует над RED-действием"}

— BLUE → ORANGE (правила + вопрос об их эффективности) —

"Всегда делал как положено, честно работал — но результата нет, что-то не так"
→ {"primary":"BLUE","secondary":"ORANGE","confidence":0.73,"indicator":"BLUE-дисциплина + ORANGE-сомнение через отсутствие результата"}

"Понимаю что должен соблюдать правила, но начинаю думать — может это просто неэффективно?"
→ {"primary":"ORANGE","secondary":"BLUE","confidence":0.76,"indicator":"ORANGE-критерий размывает BLUE-авторитет правил"}

— ORANGE → GREEN (достижения + появляется пустота или запрос на смысл) —

"Добился всего что планировал — карьера, деньги — но чего-то не хватает"
→ {"primary":"ORANGE","secondary":"GREEN","confidence":0.78,"indicator":"кризис ORANGE: результаты есть, смысл и связь отсутствуют"}

"Работаю эффективно, но коллеги говорят что я холодный — начинаю задумываться"
→ {"primary":"ORANGE","secondary":"GREEN","confidence":0.74,"indicator":"ORANGE-продуктивность + начало GREEN-рефлексии об отношениях"}

"Важно чтобы всем было хорошо в команде, но и результаты должны быть"
→ {"primary":"GREEN","secondary":"ORANGE","confidence":0.72,"indicator":"GREEN-ценности с ORANGE-обоснованием"}

— GREEN → YELLOW (чувства + начало системного взгляда) —

"Принимаю людей такими как есть, но замечаю что моя эмпатия работает как избегание"
→ {"primary":"GREEN","secondary":"YELLOW","confidence":0.77,"indicator":"GREEN-принятие + YELLOW-наблюдение за собственным паттерном"}

"Понимаю свои чувства, но вижу что реагирую на одни и те же триггеры — хочу разобраться в системе"
→ {"primary":"YELLOW","secondary":"GREEN","confidence":0.80,"indicator":"YELLOW-системный интерес при сохранении GREEN-языка"}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
КРИЗИСНЫЕ СОСТОЯНИЯ (уровень временно снижается)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"Всё рушится, столько работал ради этого, не понимаю что делать"
→ {"primary":"ORANGE","secondary":"RED","confidence":0.76,"indicator":"ORANGE-крах активирует RED-растерянность"}

"Слышу всех, всем сочувствую, но сама уже пустая, не могу больше"
→ {"primary":"GREEN","secondary":"BEIGE","confidence":0.82,"indicator":"GREEN-эмпатическое истощение до BEIGE-предела"}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ПРАВИЛА КЛАССИФИКАЦИИ
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Смотри на то, ЧТО человек считает проблемой и ЧТО считает решением
2. Если два уровня равновесны — выбери более НИЗКИЙ (безопаснее)
3. Острое эмоциональное состояние временно снижает доступный уровень
4. confidence < 0.65 — сигнал неопределённости, LLM должен это указать

Верни ТОЛЬКО JSON:
{"primary":"LEVEL","secondary":"LEVEL_or_null","confidence":0.0-1.0,"indicator":"краткий маркер"}
"""


# ──────────────────────────────────────────────────────────────
# DATACLASSES
# ──────────────────────────────────────────────────────────────

@dataclass
class SDClassificationResult:
    primary: str
    secondary: Optional[str]
    confidence: float
    indicator: str
    method: str                          # "heuristic" | "llm" | "profile"
    allowed_blocks: List[str] = field(default_factory=list)

    def __post_init__(self):
        self.allowed_blocks = SD_COMPATIBILITY_BASE.get(self.primary, ["GREEN"])


# ──────────────────────────────────────────────────────────────
# ДИНАМИЧЕСКАЯ МАТРИЦА СОВМЕСТИМОСТИ
# ──────────────────────────────────────────────────────────────

class SDCompatibilityResolver:
    """
    Динамическая матрица совместимости уровней СД.

    Учитывает:
    - Основной уровень пользователя
    - Текущее эмоциональное состояние (кризис, истощение)
    - Пограничный переход (вторичный уровень и его направление)
    - Уверенность классификации
    - Первая ли сессия
    """

    # Переопределения для кризисных состояний
    # Ключ: (sd_level, user_state) → allowed_blocks
    CRISIS_OVERRIDES: dict = {
        # ORANGE в коллапсе → нужна BLUE структура как опора
        ("ORANGE", "overwhelmed"):  ["BLUE", "ORANGE"],
        ("ORANGE", "crisis"):       ["BLUE", "ORANGE"],
        # BLUE в перегрузке виной → нужна GREEN валидация
        ("BLUE", "overwhelmed"):    ["GREEN", "BLUE"],
        ("BLUE", "crisis"):         ["GREEN", "BLUE"],
        # GREEN в эмпатическом истощении → нужна ORANGE дистанция/границы
        ("GREEN", "overwhelmed"):   ["ORANGE", "GREEN"],
        ("GREEN", "exhausted"):     ["ORANGE", "GREEN"],
        # RED в панике → нужна PURPLE безопасность
        ("RED", "crisis"):          ["PURPLE", "RED"],
        ("RED", "overwhelmed"):     ["PURPLE", "RED"],
        # YELLOW в коллапсе систем → откат к GREEN чувствам как якорю
        ("YELLOW", "overwhelmed"):  ["GREEN", "YELLOW"],
        ("YELLOW", "crisis"):       ["GREEN", "YELLOW"],
        # ORANGE в стагнации → BASE (пустота, нужен смысл)
        ("ORANGE", "stagnant"):     ["GREEN", "ORANGE"],
    }

    def get_allowed_levels(
        self,
        sd_level: str,
        user_state: Optional[str] = None,
        sd_secondary: Optional[str] = None,
        sd_confidence: float = 1.0,
        is_first_session: bool = False,
    ) -> List[str]:
        """
        Получить список разрешённых уровней блоков для данного пользователя.

        Args:
            sd_level: основной уровень СД
            user_state: состояние из state_classifier (overwhelmed/crisis/resistant/etc.)
            sd_secondary: вторичный уровень (направление движения)
            sd_confidence: уверенность классификации
            is_first_session: первый диалог с пользователем
        """
        # 1. Низкая уверенность → консервативный режим (уровень ниже)
        if sd_confidence < 0.60:
            safer_level = self._one_level_down(sd_level)
            allowed = list(SD_COMPATIBILITY_BASE.get(safer_level, ["GREEN"]))
            logger.info(
                f"[SD_COMPAT] Low confidence ({sd_confidence:.2f}) → "
                f"conservative: {sd_level}→{safer_level}, allowed={allowed}"
            )
            return allowed

        # 2. Кризисное состояние → специальные переопределения
        state_norm = (user_state or "").lower()
        crisis_key = (sd_level, state_norm)
        if crisis_key in self.CRISIS_OVERRIDES:
            allowed = self.CRISIS_OVERRIDES[crisis_key]
            logger.info(f"[SD_COMPAT] Crisis override ({sd_level},{state_norm}) → {allowed}")
            return allowed

        # 3. Первая сессия → только базовый уровень без расширений
        if is_first_session:
            allowed = list(SD_COMPATIBILITY_BASE.get(sd_level, ["GREEN"]))
            logger.info(f"[SD_COMPAT] First session → strict base: {allowed}")
            return allowed

        # 4. Базовая матрица
        allowed = list(SD_COMPATIBILITY_BASE.get(sd_level, ["GREEN"]))

        # 5. Пограничный переход — расширяем если вторичный уровень ВЫШЕ
        if sd_secondary and sd_secondary != sd_level:
            try:
                secondary_idx = SD_LEVELS_ORDER.index(sd_secondary)
                primary_idx = SD_LEVELS_ORDER.index(sd_level)
                is_upward = secondary_idx > primary_idx

                if is_upward and sd_secondary not in allowed:
                    allowed.append(sd_secondary)
                    logger.info(
                        f"[SD_COMPAT] Upward transition {sd_level}→{sd_secondary}: "
                        f"expanded to {allowed}"
                    )
                elif not is_upward:
                    logger.info(
                        f"[SD_COMPAT] Downward transition {sd_level}→{sd_secondary}: "
                        f"no expansion (regression)"
                    )
            except ValueError:
                pass  # неизвестный уровень — пропустить

        logger.info(f"[SD_COMPAT] Final allowed for {sd_level}: {allowed}")
        return allowed

    def _one_level_down(self, level: str) -> str:
        """Безопасное снижение уровня на одну ступень."""
        idx = SD_LEVELS_ORDER.index(level) if level in SD_LEVELS_ORDER else 4
        return SD_LEVELS_ORDER[max(0, idx - 1)]


# ──────────────────────────────────────────────────────────────
# ОСНОВНОЙ КЛАССИФИКАТОР
# ──────────────────────────────────────────────────────────────

class SDClassifier:
    """
    Классификатор уровня СД пользователя.
    Использует трёхуровневую стратегию: эвристика → LLM → профиль.
    """

    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.1):
        self.client = OpenAI()
        self.model = model
        self.temperature = temperature

    def classify(
        self,
        message: str,
        conversation_history: Optional[List[dict]] = None,
        user_sd_profile: Optional[dict] = None,
    ) -> SDClassificationResult:
        """
        Определить уровень СД пользователя.

        Args:
            message: текущее сообщение пользователя
            conversation_history: последние сообщения [{"role":"user","content":"..."}]
            user_sd_profile: накопленный профиль из памяти пользователя

        Returns:
            SDClassificationResult
        """
        # Уровень 3: стабильный накопленный профиль
        if (
            user_sd_profile
            and user_sd_profile.get("message_count", 0) >= 15
            and user_sd_profile.get("confidence", 0) >= 0.80
        ):
            result = SDClassificationResult(
                primary=user_sd_profile["primary"],
                secondary=user_sd_profile.get("secondary"),
                confidence=user_sd_profile["confidence"],
                indicator="accumulated_profile",
                method="profile",
            )
            logger.info(f"[SD_CLASSIFIER] Profile: {result.primary} ({result.confidence:.2f})")
            return result

        # Уровень 1: эвристика
        heuristic = self._heuristic_classify(message, conversation_history)
        if heuristic.confidence >= 0.65:
            logger.info(
                f"[SD_CLASSIFIER] Heuristic: {heuristic.primary} ({heuristic.confidence:.2f})"
            )
            return heuristic

        # Уровень 2: LLM
        llm_result = self._llm_classify(message, conversation_history)
        logger.info(f"[SD_CLASSIFIER] LLM: {llm_result.primary} ({llm_result.confidence:.2f})")
        return llm_result

    def _heuristic_classify(
        self,
        message: str,
        history: Optional[List[dict]] = None,
    ) -> SDClassificationResult:
        """Классификация по ключевым словам."""
        text = message.lower()
        if history:
            for turn in history[-5:]:
                text += " " + (turn.get("content") or "").lower()

        scores = {level: 0 for level in SD_LEVELS_ORDER}
        for level, keywords in SD_KEYWORDS.items():
            for kw in keywords:
                if kw in text:
                    scores[level] += 1

        best_level = max(scores, key=scores.get)
        best_score = scores[best_level]

        if best_score == 0:
            return SDClassificationResult(
                primary="GREEN",
                secondary=None,
                confidence=0.40,
                indicator="no_keywords_found",
                method="heuristic",
            )

        total = sum(scores.values())
        confidence = min(0.85, (best_score / total) * 2) if total > 0 else 0.40

        sorted_levels = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        secondary = (
            sorted_levels[1][0]
            if len(sorted_levels) > 1 and sorted_levels[1][1] > 0
            else None
        )

        return SDClassificationResult(
            primary=best_level,
            secondary=secondary,
            confidence=confidence,
            indicator=f"keywords_matched_{best_score}",
            method="heuristic",
        )

    def _llm_classify(
        self,
        message: str,
        history: Optional[List[dict]] = None,
    ) -> SDClassificationResult:
        """LLM-классификация для неоднозначных случаев."""
        context = ""
        if history:
            context = "\n".join([
                f"Пользователь: {t['content']}"
                for t in history[-5:]
                if t.get("role") == "user"
            ])

        user_content = f"Текущее сообщение: {message}"
        if context:
            user_content = f"История:\n{context}\n\n{user_content}"

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                temperature=self.temperature,
                max_tokens=150,
                messages=[
                    {"role": "system", "content": SD_CLASSIFIER_SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
            )
            raw = response.choices[0].message.content.strip()
            data = json.loads(raw)
            return SDClassificationResult(
                primary=data.get("primary", "GREEN"),
                secondary=data.get("secondary"),
                confidence=float(data.get("confidence", 0.60)),
                indicator=data.get("indicator", "llm_classified"),
                method="llm",
            )
        except Exception as e:
            logger.error(f"[SD_CLASSIFIER] LLM error: {e}")
            return SDClassificationResult(
                primary="GREEN",
                secondary=None,
                confidence=0.50,
                indicator="llm_fallback_on_error",
                method="llm",
            )

    def one_level_down(self, level: str) -> str:
        idx = SD_LEVELS_ORDER.index(level) if level in SD_LEVELS_ORDER else 4
        return SD_LEVELS_ORDER[max(0, idx - 1)]


# ──────────────────────────────────────────────────────────────
# СИНГЛТОНЫ
# ──────────────────────────────────────────────────────────────
sd_classifier = SDClassifier()
sd_compatibility_resolver = SDCompatibilityResolver()
```


***

### 2.2 SD-фильтр блоков

Создать: `bot_psychologist/bot_agent/retrieval/sd_filter.py`

```python
"""
SD Filter — фильтрует блоки по динамической совместимости с уровнем СД пользователя.
Применяется после retrieval, до генерации ответа.
"""

import logging
from typing import List, Optional, Tuple
from ..sd_classifier import sd_compatibility_resolver

logger = logging.getLogger(__name__)


def filter_by_sd_level(
    blocks_with_scores: List[Tuple],
    user_sd_level: str,
    user_state: Optional[str] = None,
    sd_secondary: Optional[str] = None,
    sd_confidence: float = 1.0,
    is_first_session: bool = False,
    min_blocks: int = 3,
) -> List[Tuple]:
    """
    Фильтровать блоки по совместимости уровней СД.

    Args:
        blocks_with_scores: [(Block, score), ...]
        user_sd_level: основной уровень СД пользователя
        user_state: эмоциональное состояние (overwhelmed/crisis/resistant/etc.)
        sd_secondary: вторичный уровень
        sd_confidence: уверенность SD-классификации
        is_first_session: первый диалог
        min_blocks: минимум блоков на выходе

    Returns:
        Отфильтрованный список (block, score)
    """
    allowed_levels = sd_compatibility_resolver.get_allowed_levels(
        sd_level=user_sd_level,
        user_state=user_state,
        sd_secondary=sd_secondary,
        sd_confidence=sd_confidence,
        is_first_session=is_first_session,
    )

    filtered = []
    no_sd_metadata = []   # блоки без SD-разметки (старые данные)

    for block, score in blocks_with_scores:
        block_sd = (
            getattr(block, "sd_level", None)
            or (block.metadata or {}).get("sd_level", None)
        )

        if block_sd is None:
            no_sd_metadata.append((block, score))
            continue

        if block_sd in allowed_levels:
            filtered.append((block, score))

    logger.info(
        f"[SD_FILTER] {len(blocks_with_scores)} → {len(filtered)} filtered "
        f"(user={user_sd_level}, state={user_state}, allowed={allowed_levels}, "
        f"untagged={len(no_sd_metadata)})"
    )

    # Если мало блоков — добавить неразмеченные
    if len(filtered) < min_blocks:
        needed = min_blocks - len(filtered)
        filtered += no_sd_metadata[:needed]
        logger.warning(
            f"[SD_FILTER] Added {min(needed, len(no_sd_metadata))} untagged blocks as fallback"
        )

    # Крайний случай — вернуть исходные
    if len(filtered) < min_blocks:
        logger.warning(
            f"[SD_FILTER] Critical fallback: returning original blocks"
        )
        return blocks_with_scores[:min_blocks * 2]

    return filtered
```

Добавить экспорт в `bot_psychologist/bot_agent/retrieval/__init__.py`:

```python
from .sd_filter import filter_by_sd_level
```


***

### 2.3 Системные промты — SD-оверлеи

**`prompt_system_base.md` — НЕ ТРОГАТЬ.** Это ядро бота — хорошо написан.

Создать следующие файлы в `bot_psychologist/bot_agent/`:

**`prompt_sd_purple.md`:**

```markdown
## SD-адаптация: PURPLE (Племя / Традиции)

Стиль:
- Уважай коллективный контекст: семья, близкие, "наши" — важны для человека
- Используй образы из привычного мира: природа, дом, предки
- Не предлагай "сломать шаблон" или "действовать вопреки всем"
- Безопасность и принадлежность — главные ценности
- Говори тепло, как близкий человек, а не как эксперт

Запрещено:
- "Твоя жизнь — только твоя" (угрожает ощущению принадлежности)
- Абстрактные концепции без конкретики
- Призывы к индивидуализму и независимости от семьи

Ключевые слова для использования:
вместе, поддержка, привычный, знакомый, безопасно, понятно
```

**`prompt_sd_red.md`:**

```markdown
## SD-адаптация: RED (Сила / Импульс)

Стиль:
- Коротко, прямо, без лирики и философии
- Признавай силу и компетентность: "ты справлялся с трудным"
- Не читай мораль, не объясняй "как правильно жить"
- Предлагай конкретное действие здесь и сейчас
- Энергия, динамика — не медитативность и пауза

Запрещено:
- "Принятие", "осознанность", "чувства других людей"
- "Подожди", "потерпи", "понаблюдай"
- Долгие объяснения и теории
- Любые упрёки и указания на "как надо было"

Ключевые слова для использования:
конкретно, прямо сейчас, действие, ты можешь, сила
```

**`prompt_sd_blue.md`:**

```markdown
## SD-адаптация: BLUE (Порядок / Долг)

Стиль:
- Чёткая структура: шаги, последовательность, критерии
- Уважение к тому, что человек "делал всё правильно"
- Работа с виной через смягчение — без отрицания самого правила
- Опирайся на факты и проверенные источники, не на "я думаю"
- Давай чёткую рекомендацию, не размытые "это зависит от..."

Запрещено:
- "Правила — это условность", "делай как хочешь"
- Нарушение авторитетов и иерархии
- Размытые ответы без конкретной рекомендации
- Моральный релятивизм

Ключевые слова для использования:
правильно, шаг за шагом, как это работает, надёжно, проверено
```

**`prompt_sd_orange.md`:**

```markdown
## SD-адаптация: ORANGE (Успех / Достижения)

Стиль:
- Объясни механизм: "это работает потому что..."
- Причинно-следственные связи обязательны
- Связывай с практической пользой и конкретным результатом
- Рациональность — ключевая ценность
- Ценится автономность: "ты сам решаешь"

Запрещено:
- "Просто почувствуй", "прими без цели"
- Размытые ответы без конкретики
- Излишняя эмоциональность вместо логики
- Обесценивание достижений

Ключевые слова для использования:
потому что, это даёт, механизм, результат, эффективно, разберём
```

**`prompt_sd_green.md`:**

```markdown
## SD-адаптация: GREEN (Эмпатия / Чувства)

Стиль:
- Начинай с валидации чувств: "я слышу, что тебе сейчас..."
- Тепло, принятие, без осуждения и директивности
- "Мы вместе разберёмся" — ощущение поддержки
- Чувства важнее правил и эффективности
- Пространство для самовыражения — не торопи

Запрещено:
- Директивность: "тебе нужно сделать так"
- Соревнование, сравнение с другими
- Обесценивание чувств логикой: "это нерационально"
- Торопить к выводам

Ключевые слова для использования:
чувствую, слышу тебя, важно, вместе, понятно, пространство
```

**`prompt_sd_yellow.md`:**

```markdown
## SD-адаптация: YELLOW (Системность / Интеграция)

Стиль:
- Мета-уровень: можно обсуждать сам паттерн разговора
- Парадоксы приветствуются, нет "одного правильного ответа"
- Системный взгляд: как это явление вписывается в контекст
- Допускается сложность и нелинейность
- Честность важнее комфорта

Запрещено:
- Упрощение до одного правильного решения
- "Это хорошо/плохо" — бинарные оценки
- Игнорирование контекста и паттернов
- Подача информации без учёта системной картины

Ключевые слова для использования:
паттерн, контекст, замечаю, система, это работает как..., интересно что
```


***

### 2.4 Изменения в `response/response_generator.py`

Найти класс `ResponseGenerator` и добавить метод загрузки SD-промта. Также добавить SD-промт в финальный системный промт.

```python
# ДОБАВИТЬ метод в класс ResponseGenerator:

from pathlib import Path

def _load_sd_prompt(self, sd_level: str) -> str:
    """Загрузить SD-оверлей промта для уровня пользователя."""
    sd_file_map = {
        "BEIGE":     "prompt_sd_purple.md",   # BEIGE → используем PURPLE (ближайший)
        "PURPLE":    "prompt_sd_purple.md",
        "RED":       "prompt_sd_red.md",
        "BLUE":      "prompt_sd_blue.md",
        "ORANGE":    "prompt_sd_orange.md",
        "GREEN":     "prompt_sd_green.md",
        "YELLOW":    "prompt_sd_yellow.md",
        "TURQUOISE": "prompt_sd_yellow.md",   # TURQUOISE → используем YELLOW (ближайший)
    }
    filename = sd_file_map.get(sd_level, "prompt_sd_green.md")
    prompt_path = Path(__file__).parent.parent / filename
    try:
        return prompt_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        logger.warning(f"[RESPONSE_GEN] SD prompt not found: {filename}, using empty")
        return ""

# ИЗМЕНИТЬ метод generate() — добавить sd_level параметр и подключение промта:
# В сигнатуру добавить: sd_level: str = "GREEN"
# В тело — сформировать полный системный промт:

# Найти место где собирается system_prompt и добавить:
sd_overlay = self._load_sd_prompt(sd_level)
if sd_overlay:
    full_system_prompt = f"{base_system_prompt}\n\n{sd_overlay}"
else:
    full_system_prompt = base_system_prompt
```


***

### 2.5 Изменения в `conversation_memory.py`

Найти класс `ConversationMemory` и добавить методы работы с SD-профилем:

```python
# ДОБАВИТЬ в класс ConversationMemory (в __init__ или как property):

def get_user_sd_profile(self) -> Optional[dict]:
    """Получить накопленный SD-профиль пользователя."""
    return getattr(self, "_sd_profile", None)

def update_sd_profile(self, level: str, confidence: float) -> None:
    """
    Обновить SD-профиль на основе новой классификации.
    Вызывается каждые 5 сообщений из answer_adaptive.py.
    """
    if not hasattr(self, "_sd_profile") or self._sd_profile is None:
        self._sd_profile = {
            "primary": level,
            "secondary": None,
            "confidence": confidence,
            "message_count": 0,
            "history": [],
        }

    self._sd_profile["history"].append({"level": level, "confidence": confidence})
    self._sd_profile["message_count"] = len(self.turns)

    # Пересчитать как наиболее частый за последние 10 классификаций
    recent = self._sd_profile["history"][-10:]
    from collections import Counter
    level_counts = Counter(h["level"] for h in recent)
    most_common = level_counts.most_common(1)[0][0]

    self._sd_profile["primary"] = most_common
    self._sd_profile["confidence"] = sum(
        h["confidence"] for h in recent if h["level"] == most_common
    ) / max(1, level_counts[most_common])

    logger.debug(
        f"[SD_PROFILE] Updated: {self._sd_profile['primary']} "
        f"(conf={self._sd_profile['confidence']:.2f}, "
        f"msgs={self._sd_profile['message_count']})"
    )
```


***

### 2.6 Изменения в `answer_adaptive.py`

Это главный файл оркестратора. Добавляем SD-pipeline точечно — **не переписывая существующую логику**.

**Шаг 1** — добавить импорты в начало файла:

```python
# ДОБАВИТЬ к существующим импортам:
from .sd_classifier import sd_classifier, SDClassificationResult
from .retrieval.sd_filter import filter_by_sd_level
```

**Шаг 2** — добавить Этап 2б между существующими Этапом 2 и Этапом 3:

```python
# ================================================================
# ЭТАП 2б: SD-классификация пользователя (НОВОЕ)
# ================================================================
logger.debug("🌀 Этап 2б: SD-классификация...")

conversation_history_for_sd = [
    {"role": "user", "content": turn.user_input}
    for turn in memory.get_last_turns(10)
]

try:
    sd_result: SDClassificationResult = sd_classifier.classify(
        message=query,
        conversation_history=conversation_history_for_sd,
        user_sd_profile=memory.get_user_sd_profile(),
    )

    # Обновлять профиль каждые 5 сообщений
    if len(memory.turns) % 5 == 0:
        memory.update_sd_profile(
            level=sd_result.primary,
            confidence=sd_result.confidence,
        )

    logger.info(
        f"✅ SD уровень: {sd_result.primary} "
        f"(conf={sd_result.confidence:.2f}, method={sd_result.method})"
    )
except Exception as sd_exc:
    logger.warning(f"[ADAPTIVE] SD classification failed: {sd_exc}, using GREEN fallback")
    from .sd_classifier import SDClassificationResult
    sd_result = SDClassificationResult(
        primary="GREEN", secondary=None, confidence=0.5,
        indicator="fallback_on_error", method="fallback"
    )

if debug_info is not None:
    debug_info["sd_classification"] = {
        "primary": sd_result.primary,
        "secondary": sd_result.secondary,
        "confidence": sd_result.confidence,
        "indicator": sd_result.indicator,
        "method": sd_result.method,
        "allowed_blocks": sd_result.allowed_blocks,
    }
```

**Шаг 3** — добавить SD-фильтр после `retrieved_blocks = retriever.retrieve(...)`:

```python
# ДОБАВИТЬ сразу после строки: retrieved_blocks = retriever.retrieve(hybrid_query, top_k=top_k)

retrieved_blocks = filter_by_sd_level(
    blocks_with_scores=retrieved_blocks,
    user_sd_level=sd_result.primary,
    user_state=state_analysis.primary_state.value,
    sd_secondary=sd_result.secondary,
    sd_confidence=sd_result.confidence,
    is_first_session=(len(memory.turns) == 0),
    min_blocks=3,
)
_log_retrieval_pairs("After SD filter", retrieved_blocks, limit=10)
```

**Шаг 4** — передать sd_level в `ResponseGenerator.generate()`:

```python
# НАЙТИ вызов response_generator.generate() и добавить параметр sd_level:
llm_result = response_generator.generate(
    query,
    adapted_blocks,
    conversation_context=conversation_context,
    mode=routing_result.mode,
    confidence_level=routing_result.confidence_level,
    forbid=routing_result.decision.forbid,
    user_level_adapter=level_adapter,
    additional_system_context=state_context,
    sd_level=sd_result.primary,          # ← ДОБАВИТЬ
    model=config.LLM_MODEL,
    temperature=config.LLM_TEMPERATURE,
    max_tokens=config.LLM_MAX_TOKENS,
)
```

**Шаг 5** — добавить SD-поля в metadata финального ответа:

```python
# НАЙТИ блок "metadata": { ... } в финальном result и добавить:
"sd_level": sd_result.primary,
"sd_secondary": sd_result.secondary,
"sd_confidence": round(sd_result.confidence, 3),
"sd_method": sd_result.method,
"sd_allowed_blocks": sd_result.allowed_blocks,
```

**Шаг 6** — обновить `_build_state_context` для включения SD-информации:

```python
# ИЗМЕНИТЬ функцию _build_state_context — добавить параметр sd_level:

def _build_state_context(
    state_analysis: StateAnalysis,
    mode_prompt: str,
    sd_level: str = "GREEN",        # ← ДОБАВИТЬ ПАРАМЕТР
) -> str:
    recommendation = (
        state_analysis.recommendations[0]
        if state_analysis and state_analysis.recommendations
        else "Respond in a clear and grounded way."
    )
    return f"""
КОНТЕКСТ ПОЛЬЗОВАТЕЛЯ:
- Текущее состояние: {state_analysis.primary_state.value}
- Эмоциональный тон: {state_analysis.emotional_tone}
- Глубина вовлечения: {state_analysis.depth}
- Уровень развития (СД): {sd_level}

РЕКОМЕНДАЦИЯ ПО ОТВЕТУ:
{recommendation}

Адаптируй стиль ответа к уровню СД пользователя.
SD-оверлей применяется автоматически через системный промт.

РЕЖИМНАЯ ДИРЕКТИВА:
{mode_prompt}
"""

# И обновить ВСЕ вызовы _build_state_context в файле:
state_context = _build_state_context(state_analysis, mode_directive.prompt, sd_level=sd_result.primary)
```


***

## 3. КОНФИГ SD-КЛАССИФИКАЦИИ

Создать: `bot_psychologist/config/sd_classification.yaml`

```yaml
sd_classification:
  model: gpt-4o-mini
  temperature: 0.1

  # Пороги
  heuristic_confidence_threshold: 0.65
  profile_min_messages: 15
  profile_min_confidence: 0.80
  update_profile_every_n_messages: 5

  # Безопасность
  uncertainty_fallback: "one_level_down"
  default_level: "GREEN"

  # Матрица (дублирует код, используется для документации и тестов)
  compatibility_base:
    BEIGE:     ["BEIGE", "PURPLE"]
    PURPLE:    ["PURPLE", "RED"]
    RED:       ["RED", "BLUE"]
    BLUE:      ["BLUE", "ORANGE"]
    ORANGE:    ["ORANGE", "GREEN"]
    GREEN:     ["GREEN", "YELLOW"]
    YELLOW:    ["GREEN", "YELLOW", "TURQUOISE"]
    TURQUOISE: ["YELLOW", "TURQUOISE"]

  # Кризисные переопределения (дублирует код для документации)
  crisis_overrides:
    - condition: [ORANGE, overwhelmed]
      allowed: [BLUE, ORANGE]
      reason: "В коллапсе нужна BLUE структура как опора"
    - condition: [BLUE, overwhelmed]
      allowed: [GREEN, BLUE]
      reason: "В перегрузке виной нужна GREEN валидация"
    - condition: [GREEN, overwhelmed]
      allowed: [ORANGE, GREEN]
      reason: "В истощении нужна ORANGE дистанция/границы"
    - condition: [RED, crisis]
      allowed: [PURPLE, RED]
      reason: "В панике нужна PURPLE безопасность"
    - condition: [YELLOW, overwhelmed]
      allowed: [GREEN, YELLOW]
      reason: "В коллапсе систем нужна GREEN земля"
```


***

## 4. ПОРЯДОК РЕАЛИЗАЦИИ

### Фаза 0: Изучение кода (не пропускать!)

```
Прочитай полностью:
1. bot_psychologist/bot_agent/answer_adaptive.py
2. bot_psychologist/bot_agent/conversation_memory.py
3. bot_psychologist/bot_agent/retrieval/ (все файлы)
4. bot_psychologist/bot_agent/response/ (все файлы)
5. voice_bot_pipeline/pipeline_orchestrator.py

Создай ветку: git checkout -b feature/sd-integration
```


### Фаза 1: Данные (voice_bot_pipeline)

```
1. Создать config/authors/salamat_sarsekenov.yaml
2. Создать config/authors/_author_template.yaml
3. Создать config/sd_levels.yaml
4. Создать text_processor/sd_labeler.py
5. Создать data/graphs/base_graph.json
6. Создать data/graphs/authors/salamat_graph.json
7. Изменить pipeline_orchestrator.py → добавить SDLabeler
8. Изменить vector_db/vector_indexer.py → добавить SD-поля в metadata
9. Тест: запустить на 10 тестовых блоках, проверить sd_metadata
```


### Фаза 2: Классификатор

```
1. Создать bot_psychologist/bot_agent/sd_classifier.py
2. Создать bot_psychologist/config/sd_classification.yaml
3. Написать unit-тесты: tests/test_sd_classifier.py
   - По 2 теста на каждый уровень СД (чистые случаи)
   - По 1 тесту на каждый пограничный случай
   - Тест fallback при ошибке LLM
```


### Фаза 3: Фильтр и промты

```
1. Создать bot_psychologist/bot_agent/retrieval/sd_filter.py
2. Обновить retrieval/__init__.py
3. Создать все 6 файлов prompt_sd_*.md
4. Изменить response/response_generator.py
   - Добавить _load_sd_prompt()
   - Добавить sd_level параметр в generate()
```


### Фаза 4: Интеграция в answer_adaptive.py

```
Строго по инструкции в разделе 2.6:
1. Добавить импорты
2. Добавить Этап 2б (SD-классификация)
3. Добавить SD-фильтр после retrieval
4. Обновить вызов generate() с sd_level
5. Обновить _build_state_context()
6. Добавить SD-поля в metadata

Изменить conversation_memory.py (раздел 2.5)
```


### Фаза 5: Интеграционные тесты

```
Создать: tests/test_sd_integration.py

ТЕСТ 1 (RED):
  input: "Все достали, никто не уважает меня"
  assert: sd_result.primary == "RED"
  assert: "GREEN" not in sd_result.allowed_blocks  # не показываем GREEN блоки
  assert: "YELLOW" not in response_metadata["sd_allowed_blocks"]

ТЕСТ 2 (BLUE + вина):
  input: "Я должна была этого не делать, чувствую вину перед семьёй"
  assert: sd_result.primary == "BLUE"
  assert: response начинается НЕ с абстрактной теории
  assert: response содержит структуру или шаги

ТЕСТ 3 (GREEN):
  input: "Не могу справиться с тревогой, хочу понять что чувствую"
  assert: sd_result.primary == "GREEN"
  assert: "GREEN" in sd_result.allowed_blocks
  assert: response содержит валидацию чувств

ТЕСТ 4 (YELLOW):
  input: "Замечаю паттерн — каждый раз в стрессе реагирую одинаково"
  assert: sd_result.primary == "YELLOW"
  assert: "TURQUOISE" in sd_result.allowed_blocks  # YELLOW расширяется до TURQUOISE

ТЕСТ 5 (БЕЗОПАСНОСТЬ — критический):
  input: "Мне страшно, всё плохо, не знаю что делать"
  sd_level = "PURPLE" или "RED"
  assert: "YELLOW" not in sd_result.allowed_blocks  # YELLOW блоки запрещены
  assert: "TURQUOISE" not in sd_result.allowed_blocks

ТЕСТ 6 (КРИЗИС):
  input: "Всё рушится, столько работал ради этого"
  user_state = "overwhelmed"
  sd_level = "ORANGE"
  assert: allowed_blocks == ["BLUE", "ORANGE"]  # ORANGE в кризисе → BLUE структура

ТЕСТ 7 (FALLBACK при ошибке):
  Сломать OpenAI client (mock)
  assert: бот не падает
  assert: sd_result.primary == "GREEN"
  assert: ответ всё равно генерируется
```


***

## 5. ЧЕКЛИСТ ДЛЯ CODEX

### Обязательные требования к коду:

- [ ] Все новые модули имеют docstrings
- [ ] Все параметры — в YAML конфигах, не хардкод
- [ ] Логирование: `logger.info` для ключевых шагов, `logger.warning` для fallback
- [ ] Типизация везде: `from typing import List, Optional, Dict, Tuple`
- [ ] При сбое любого SD-модуля — fallback на GREEN, бот не падает


### Запрещено:

- [ ] Переписывать `prompt_system_base.md`
- [ ] Переписывать существующую логику `answer_adaptive.py` (только добавлять)
- [ ] Хардкодить уровни СД в коде (все в конфиге и константах)
- [ ] Оставлять SD-фильтр с 0 блоками на выходе


### Финальная проверка:

- [ ] Все 7 интеграционных тестов проходят
- [ ] SD-уровень виден в metadata каждого ответа при `debug=True`
- [ ] Логи показывают цепочку: classify → filter → allowed_blocks
- [ ] При `user_state=overwhelmed` матрица переключается на кризисные правила
- [ ] При `confidence < 0.6` уровень снижается на одну ступень

***

## 6. СТАРТОВАЯ КОМАНДА ДЛЯ CURSOR AI

```
Привет! Реализуй SD-интеграцию (Спиральная Динамика Клэра Грейвза) 
в бот-психолога. Проект состоит из двух репозиториев:
  1. voice_bot_pipeline — подготовка БД (офлайн)
  2. Text_transcription/bot_psychologist — сам бот (онлайн)

Главная цель: бот должен определять уровень сознания пользователя 
и отвечать на его языке, не поднимая выше его готовности.

НАЧНИ с Фазы 0 — прочитай все указанные файлы целиком.
Затем строго по фазам: 1 → 2 → 3 → 4 → 5.

Ключевые правила:
- НЕ переписывай answer_adaptive.py — только добавляй
- НЕ трогай prompt_system_base.md
- При любой ошибке SD → fallback GREEN, бот не должен падать
- Все параметры в YAML, не хардкод
- После каждой фазы — запусти тесты и сообщи результат

Весь код новых модулей полностью описан в PRD v3.0.
```

