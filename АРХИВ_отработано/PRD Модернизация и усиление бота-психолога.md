# PRD: Модернизация и усиление бота-психолога

**Версия:** 2.0 · **Проект:** `Askhat-cmd/Text_transcription` · **Ветка:** `main` · **Дата:** 2026-03-26

***

## 1. Контекст и цель

Бот-психолог — многослойный RAG-агент с адаптивной маршрутизацией, памятью пользователя, двумя классификаторами (StateClassifier + SDClassifier), rule-based routing и Voyage AI reranking. Система работает: 80 из 91 теста проходят, SDClassifier корректно классифицирует все 10 уровней Spiral Dynamics.

**Цель PRD** — провести миграцию embedding-модели, упростить избыточные компоненты и добавить пять улучшений, которые делают бота по-настоящему умным психологическим собеседником. Ни одно изменение не вносится без предварительного измерения.

**Главный инвариант:** после завершения всех фаз бот должен быть не хуже текущего по всем измеримым метрикам и заметно лучше по качеству диалога.

***

## 2. Scope

### В рамках этого PRD

- Фаза 0: Бэкап + baseline eval из существующих тестов
- Фаза 1: Миграция embedding на `intfloat/multilingual-e5-base` + EmbeddingProvider interface
- Фаза 2: Conditional reranker (замена бинарного ON/OFF)
- Фаза 3: Level-0 fast detector для StateClassifier и SDClassifier
- Фаза 4: Три Feature Flags + `.env.example`
- Фаза 5: Пять улучшений интеллекта бота (новые возможности)


### Вне рамок этого PRD

- Переписывание `answer_question_adaptive()` как оркестратора
- Изменение формата `ConversationMemory`, `WorkingState`, `add_turn()`
- Изменение `ResponseGenerator`, `ResponseFormatter`, prompt-файлов SD/user-level
- LLM Router в маршрутизации (избыточно — rule-based работает)
- Weighted average для SD-профиля (преждевременная оптимизация)
- Сложный session consistency eval как отдельная фаза

***

## 3. Текущее состояние системы

### Реальная структура проекта

```
bot_psychologist/
├── bot_agent/
│   ├── answer_adaptive.py        ← главный оркестратор (НЕ ТРОГАТЬ)
│   ├── decision/
│   │   ├── decision_gate.py      ← МИНИМАЛЬНЫЕ ПРАВКИ (логирование)
│   │   ├── decision_table.py     ← ДОБАВИТЬ одно правило (VALIDATION-first)
│   │   ├── signal_detector.py    ← ДОБАВИТЬ ContradictionDetector
│   │   └── mode_handlers.py      ← НЕ ТРОГАТЬ
│   ├── state_classifier.py       ← ДОБАВИТЬ Level-0 fast detector
│   ├── sd_classifier.py          ← ДОБАВИТЬ Level-0 fast detector
│   ├── retriever.py              ← ПЕРЕРАБОТАТЬ (embedding backend)
│   ├── chroma_loader.py          ← ПЕРЕРАБОТАТЬ (E5 prefixes + rebuild)
│   ├── hybrid_query_builder.py   ← МИНИМАЛЬНЫЕ ПРАВКИ (query: prefix)
│   ├── conversation_memory.py    ← РАСШИРИТЬ (cross-session summary)
│   ├── response_formatter.py     ← ДОБАВИТЬ адаптивную длину ответа
│   └── path_builder.py           ← НЕ ТРОГАТЬ
├── config/
│   └── feature_flags.py          ← СОЗДАТЬ
├── scripts/
│   └── eval_retrieval.py         ← СОЗДАТЬ
└── tests/
    └── eval/                     ← СОЗДАТЬ (наборы из существующих тестов)
```


### Технический долг

| Компонент | Проблема | Решение в этом PRD |
| :-- | :-- | :-- |
| Embedding (текущая) | Слабая модель, компенсируется reranker | Миграция на E5-base |
| `VoyageReranker` | Бинарный ON/OFF, 100% запросов | Conditional: ≤ 25% запросов |
| `StateClassifier` | Нет Level-0 для очевидных случаев | Добавить fast detector |
| `SDClassifier` | Нет Level-0 для очевидных случаев | Добавить fast detector |
| `ResponseFormatter` | Одинаковая длина ответа при любом сообщении | Адаптивная длина |
| Память | Только внутри сессии | Cross-session summary |
| Маршрутизация | Нет принудительного VALIDATION на новую тему | Одно правило в decision_table |


***

## 4. Фаза 0 — Бэкап и Baseline

### 4.1 Цель

Зафиксировать текущее состояние системы численно и создать точку возврата перед любыми изменениями. Эта фаза — обязательное условие для всех последующих.

### 4.2 ChromaDB Backup

Агент должен создать `scripts/chroma_backup.py`:

```python
"""
Использование: python scripts/chroma_backup.py --tag pre-e5-migration
Создаёт: backups/chroma_{tag}_{timestamp}/
"""
import shutil, os, argparse
from datetime import datetime

def backup_chroma(tag: str):
    chroma_path = os.getenv("CHROMA_DB_PATH", "./data/chroma")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = f"backups/chroma_{tag}_{timestamp}"
    shutil.copytree(chroma_path, backup_dir)
    print(f"✅ Backup saved: {backup_dir}")
    return backup_dir
```

**Acceptance criteria:**

- Скрипт выполняется без ошибок
- Backup-директория содержит полную копию ChromaDB
- При запуске `--rebuild-index` без бэкапа — система выдаёт предупреждение и требует `--confirm`


### 4.3 Создание Eval-наборов из существующих тестов

**Важно:** eval-наборы создаются из реальных тест-кейсов проекта, а НЕ генерируются агентом самостоятельно.

Агент должен создать скрипт `scripts/bootstrap_eval_sets.py`, который извлекает примеры из существующих тестов:

```python
"""
Извлекает eval-примеры из:
- tests/test_sd_classifier.py       → classifier_eval_set.json
- tests/test_decision_table.py      → routing_eval_set.json
- tests/test_retrieval_pipeline_simplified.py → retrieval_eval_set.json
"""
```

**Минимальный состав eval-наборов для старта:**

```
tests/eval/
├── classifier_eval_set.json    ← 30+ примеров (из test_sd_classifier.py)
├── routing_eval_set.json       ← 20+ кейсов (из test_decision_table.py + test_decision_gate.py)
├── retrieval_eval_set.json     ← 20+ пар (20 ручных вопросов к боту)
└── baseline.json               ← зафиксированные метрики ДО изменений
```

**Формат `baseline.json`:**

```json
{
  "date": "2026-03-26",
  "embedding_model": "текущая_модель",
  "retrieval": {
    "recall_at_5": null,
    "mrr": null,
    "note": "измерено после создания retrieval_eval_set"
  },
  "classifiers": {
    "sd_classifier_accuracy_at_1": null,
    "state_classifier_accuracy_at_1": null
  },
  "routing": {
    "mode_accuracy": null
  }
}
```

Поля `null` заполняются агентом после первого прогона eval-скриптов на текущей системе.

**Acceptance criteria Фазы 0:**

- `backups/` содержит ChromaDB snapshot с тегом `pre-e5-migration`
- Все четыре файла в `tests/eval/` существуют и не пусты
- `baseline.json` заполнен числами (не null) по всем измеримым метрикам
- Только после этого — переход к Фазе 1

***

## 5. Фаза 1 — Embedding Migration

### 5.1 Цель

Заменить текущий embedding backend на `intfloat/multilingual-e5-base`, переиндексировать базу знаний с E5-префиксами, создать абстрактный интерфейс для смены модели в будущем.

### 5.2 EmbeddingProvider Interface

Агент должен создать `bot_agent/embedding_provider.py`:

```python
from abc import ABC, abstractmethod
from typing import List

class EmbeddingProvider(ABC):
    """Единый интерфейс. Замена модели — только здесь, без изменений в retriever.py."""

    @abstractmethod
    def embed_query(self, text: str) -> List[float]:
        """Для поисковых запросов. E5: добавляет prefix 'query: '"""
        pass

    @abstractmethod
    def embed_passages(self, texts: List[str]) -> List[List[float]]:
        """Для индексации блоков. E5: добавляет prefix 'passage: '"""
        pass

    @abstractmethod
    def model_name(self) -> str:
        pass


class E5EmbeddingProvider(EmbeddingProvider):
    """
    Реализация для intfloat/multilingual-e5-base и e5-large.
    КРИТИЧНО: E5-large требует GPU. При CUDA недоступен — упасть с явной ошибкой.
    """
    def __init__(self, model_name: str = "intfloat/multilingual-e5-base", device: str = "auto"):
        from sentence_transformers import SentenceTransformer
        import torch

        if "large" in model_name and not torch.cuda.is_available() and device != "cpu":
            raise RuntimeError(
                f"❌ Модель {model_name} требует GPU (CUDA). "
                f"Если хотите CPU — явно укажите device='cpu' в конфиге, "
                f"но ожидайте latency 8-12x выше. "
                f"Рекомендация: используйте e5-base на CPU."
            )

        effective_device = "cuda" if torch.cuda.is_available() else "cpu"
        self._model = SentenceTransformer(model_name, device=effective_device)
        self._model_name = model_name

    def embed_query(self, text: str) -> List[float]:
        return self._model.encode(f"query: {text}").tolist()

    def embed_passages(self, texts: List[str]) -> List[List[float]]:
        prefixed = [f"passage: {t}" for t in texts]
        return self._model.encode(prefixed).tolist()

    def model_name(self) -> str:
        return self._model_name
```


### 5.3 Обновление chroma_loader.py

Добавить параметр `--rebuild-index` с обязательной проверкой бэкапа:

```python
# В chroma_loader.py

def rebuild_index(provider: EmbeddingProvider, confirm: bool = False):
    """
    Пересчитывает все embeddings с новым провайдером.
    СОЗДАЁТ НОВУЮ КОЛЛЕКЦИЮ: psychologist_{model_shortname}
    Старая коллекция НЕ удаляется — хранится для A/B сравнения.
    """
    if not confirm:
        raise ValueError(
            "Переиндексация необратима без бэкапа. "
            "Запустите сначала: python scripts/chroma_backup.py --tag pre-migration "
            "Затем добавьте флаг --confirm"
        )

    model_tag = provider.model_name().split("/")[-1]  # e.g. "multilingual-e5-base"
    collection_name = f"psychologist_{model_tag}"
    # ... логика переиндексации с passage: prefix
```

**Важно:** новая коллекция создаётся параллельно со старой. Это позволяет A/B сравнение без риска потери данных.

### 5.4 Обновление HybridQueryBuilder

В `hybrid_query_builder.py` — минимальное изменение: query: prefix применяется автоматически через `EmbeddingProvider.embed_query()`, не вручную в коде. Никаких других изменений в файле.

### 5.5 Eval Retrieval Script

Агент создаёт `scripts/eval_retrieval.py`:

```python
"""
Сравнивает текущую модель vs E5-base на retrieval_eval_set.json
Метрики: Recall@3, Recall@5, MRR, Hit@1

Запуск: python scripts/eval_retrieval.py --compare
Вывод:
  Модель              | Recall@5 | MRR   | Hit@1
  ─────────────────────────────────────────────
  Текущая (baseline)  | 0.62     | 0.54  | 0.41
  E5-base             | 0.71     | 0.63  | 0.52
  E5-base + reranker  | 0.74     | 0.66  | 0.55
"""
```


### 5.6 Выбор между E5-base и E5-large

| Условие | Решение |
| :-- | :-- |
| GPU доступен + Recall@5(large) > Recall@5(base) + 3% | Использовать E5-large |
| GPU недоступен | Только E5-base |
| Разница < 3% при GPU | Использовать E5-base (меньше VRAM, быстрее) |

**Acceptance criteria Фазы 1:**

- Новая ChromaDB-коллекция создана, старая не удалена
- Все блоки переиндексированы с `passage:` prefix
- Recall@5 нового embedding ≥ Recall@5 baseline из `baseline.json`
- MRR нового embedding ≥ MRR baseline
- При несоответствии — откат к старой коллекции, фаза 1 отклонена

***

## 6. Фаза 2 — Conditional Reranker

### 6.1 Цель

Заменить бинарный `VOYAGE_ENABLED=True/False` на умный conditional режим: reranker вызывается только когда действительно нужен (цель — ≤ 25% запросов).

### 6.2 Логика включения

```python
# bot_agent/reranker_gate.py  (новый файл)

def should_rerank(
    confidence_score: float,
    routing_mode: str,
    retrieved_block_count: int,
    flags: dict
) -> tuple[bool, str]:
    """
    Возвращает (bool, reason) для debug_trace.
    """
    if not flags.get("RERANKER_ENABLED", False):
        return False, "reranker_disabled_by_flag"

    threshold = flags.get("RERANKER_CONFIDENCE_THRESHOLD", 0.55)
    whitelist = flags.get("RERANKER_MODE_WHITELIST", ["THINKING", "INTERVENTION"])
    block_threshold = flags.get("RERANKER_BLOCK_THRESHOLD", 8)

    if confidence_score < threshold:
        return True, f"low_confidence={confidence_score:.2f}"
    if routing_mode in whitelist:
        return True, f"mode_in_whitelist={routing_mode}"
    if retrieved_block_count > block_threshold:
        return True, f"high_block_count={retrieved_block_count}"

    return False, "conditions_not_met"
```

**Обратная совместимость:** если в `.env` стоит `VOYAGE_ENABLED=True` (старый флаг) — поведение прежнее (reranker всегда ON). Миграция на новый флаг — добровольная.

**Acceptance criteria Фазы 2:**

- При `confidence=HIGH`, `mode=CLARIFICATION`, `blocks=4` → reranker НЕ вызывается
- При `confidence=LOW`, `mode=THINKING`, `blocks=10` → reranker вызывается
- В `debug_trace` всегда логируется `should_rerank` результат с причиной
- Количество reranker-вызовов ≤ 25% от всех запросов (измеряется на 100 тестовых запросах)

***

## 7. Фаза 3 — Level-0 Fast Detector для Классификаторов

### 7.1 Цель

Добавить быстрый regex/keyword слой перед существующей логикой классификаторов. Типовые очевидные случаи (~60% сообщений) обрабатываются без тяжёлых вычислений. Существующая логика классификаторов (Level 1) не изменяется.

### 7.2 Архитектура

```
Входящее сообщение
        │
        ▼
  Level 0: Fast Detector (regex/keyword, < 1ms)
  Ловит явные однозначные сигналы:
  - "мне плохо", "не могу дышать", "страшно умереть" → BEIGE/OVERWHELMED, conf=0.90
  - "хочу стратегию", "какая выгода", "как эффективно" → ORANGE/CURIOUS, conf=0.88
  - "всё хорошо", "справляюсь", "доволен" → GREEN/INTEGRATED, conf=0.85
        │
        ├── confidence >= 0.85 → результат принят, Level 1 пропущен
        │
        ▼
  Level 1: Существующий классификатор (без изменений)
        │
        ▼
  Финальный результат + confidence в debug_trace
```


### 7.3 Реализация

Агент создаёт `bot_agent/fast_detector.py`:

```python
"""
Level-0 fast detector для StateClassifier и SDClassifier.
Не заменяет — дополняет существующую логику как первый быстрый фильтр.
"""
import re
from typing import Optional

# Словари берутся из СУЩЕСТВУЮЩИХ тест-кейсов test_sd_classifier.py
# Не изобретаются заново — переиспользуются проверенные примеры

SD_FAST_PATTERNS = {
    "BEIGE": {
        "patterns": [
            r"не могу дышать", r"физически плохо", r"страшно умереть",
            r"теряю сознание", r"чистое выживание"
        ],
        "confidence": 0.90
    },
    "PURPLE": {
        "patterns": [
            r"в семье так принято", r"нужен ритуал", r"предки.*важн",
            r"традиция", r"поддержка семьи"
        ],
        "confidence": 0.87
    },
    "RED": {
        "patterns": [
            r"меня не уважают", r"достали", r"хочу действовать",
            r"они должны мне"
        ],
        "confidence": 0.87
    },
    "ORANGE": {
        "patterns": [
            r"какая выгода", r"хочу стратегию", r"как эффективно",
            r"результат и эффективность"
        ],
        "confidence": 0.88
    },
    "GREEN": {
        "patterns": [
            r"нужна поддержка и эмпатия", r"важно чувствую связь",
            r"не могу справиться с тревогой", r"хочу понять что чувствую"
        ],
        "confidence": 0.86
    },
    # ... остальные уровни по аналогии
}

def fast_detect_sd(text: str) -> Optional[tuple[str, float]]:
    """Возвращает (sd_level, confidence) или None если нет уверенного совпадения."""
    text_lower = text.lower()
    for level, config in SD_FAST_PATTERNS.items():
        for pattern in config["patterns"]:
            if re.search(pattern, text_lower):
                return level, config["confidence"]
    return None
```

**Acceptance criteria Фазы 3:**

- На типовых фразах из `test_sd_classifier.py` — Level-0 срабатывает в ≥ 60% случаев
- Accuracy существующего Level-1 классификатора не снижается (тест `test_sd_classifier.py` должен оставаться зелёным)
- Все три уровня (срабатывание/пропуск Level-0, результат Level-1) логируются в `debug_trace`
- Среднее время классификации при Level-0 hit ≤ 2ms

***

## 8. Фаза 4 — Feature Flags

### 8.1 Цель

Три независимых флага для безопасного включения каждого нового компонента без перезапуска бота.

### 8.2 Реализация

Агент создаёт `config/feature_flags.py`:

```python
import os

FEATURE_FLAGS = {
    # Фаза 1: Embedding
    "USE_E5_EMBEDDING": os.getenv("USE_E5_EMBEDDING", "false").lower() == "true",
    "EMBEDDING_MODEL": os.getenv("EMBEDDING_MODEL", "intfloat/multilingual-e5-base"),

    # Фаза 2: Reranker
    "RERANKER_ENABLED": os.getenv("RERANKER_ENABLED", "false").lower() == "true",
    "RERANKER_CONFIDENCE_THRESHOLD": float(os.getenv("RERANKER_CONFIDENCE_THRESHOLD", "0.55")),
    "RERANKER_MODE_WHITELIST": os.getenv(
        "RERANKER_MODE_WHITELIST", "THINKING,INTERVENTION"
    ).split(","),
    "RERANKER_BLOCK_THRESHOLD": int(os.getenv("RERANKER_BLOCK_THRESHOLD", "8")),

    # Фаза 3: Fast Detector
    "FAST_DETECTOR_ENABLED": os.getenv("FAST_DETECTOR_ENABLED", "false").lower() == "true",

    # Фаза 5: Новые возможности
    "CROSS_SESSION_MEMORY_ENABLED": os.getenv("CROSS_SESSION_MEMORY_ENABLED", "false").lower() == "true",
    "CONTRADICTION_DETECTOR_ENABLED": os.getenv("CONTRADICTION_DETECTOR_ENABLED", "false").lower() == "true",
    "ADAPTIVE_RESPONSE_LENGTH_ENABLED": os.getenv("ADAPTIVE_RESPONSE_LENGTH_ENABLED", "false").lower() == "true",
    "VALIDATION_FIRST_ENABLED": os.getenv("VALIDATION_FIRST_ENABLED", "false").lower() == "true",
    "PROGRESSIVE_RAG_ENABLED": os.getenv("PROGRESSIVE_RAG_ENABLED", "false").lower() == "true",
}

def get_flag(name: str):
    return FEATURE_FLAGS.get(name, False)
```

**Acceptance criteria Фазы 4:**

- Каждый флаг работает независимо — изменение одного не затрагивает другие
- При `USE_E5_EMBEDDING=false` — используется текущая модель без изменений
- `debug_trace` при каждом запросе содержит снапшот активных флагов
- `.env.example` обновлён со всеми новыми переменными и комментариями
- `README.md` обновлён: раздел "Feature Flags" с описанием каждого флага

***

## 9. Фаза 5 — Пять улучшений интеллекта бота

Это новые возможности, которых нет в исходном PRD. Каждое изменение минимально по коду, но значительно по эффекту.

***

### 9.1 Адаптивная длина ответа

**Проблема:** бот отвечает одинаково длинно на «мне плохо» и на развёрнутый вопрос — это психологически неправильно.

**Реализация в `response_formatter.py`** (добавить функцию, не изменять существующую):

```python
def calculate_target_length(
    user_message: str,
    routing_mode: str,
    sd_level: str
) -> dict:
    """
    Возвращает {max_sentences: int, style: str}
    Правило: длина ответа пропорциональна длине сообщения + режиму.
    """
    word_count = len(user_message.split())

    # Базовая длина от режима
    mode_lengths = {
        "VALIDATION": 2,      # Коротко и тепло — всегда
        "PRESENCE": 3,        # Присутствие, не монолог
        "CLARIFICATION": 3,   # Уточнить, не объяснять
        "THINKING": 5,        # Развёрнуто — уместно
        "INTERVENTION": 2,    # Кризис: кратко и чётко
        "INTEGRATION": 4,     # Подведение итогов
    }

    base = mode_lengths.get(routing_mode, 3)

    # Корректировка по длине сообщения пользователя
    if word_count <= 5:
        max_sentences = min(base, 2)  # Короткое сообщение → короткий ответ
    elif word_count <= 20:
        max_sentences = base
    else:
        max_sentences = base + 1  # Развёрнутый вопрос → чуть больше

    return {"max_sentences": max_sentences, "mode": routing_mode}
```

**Acceptance criteria:**

- На сообщение ≤ 5 слов в режиме VALIDATION → ответ не более 2 предложений
- На сообщение > 20 слов в режиме THINKING → ответ 5–6 предложений
- Существующие тесты `test_response_formatter.py` остаются зелёными

***

### 9.2 Принудительный VALIDATION на новую эмоциональную тему

**Проблема:** бот может сразу давать советы, не подтвердив понимание. Это нарушает базовые принципы психологической поддержки.

**Реализация в `decision_table.py`** — добавить одно правило с наивысшим приоритетом:

```python
# Добавить в начало таблицы правил (priority=100, перекрывает всё остальное)
{
    "rule_id": "VALIDATION_FIRST_NEW_TOPIC",
    "description": "Первый ответ на новую эмоциональную тему — всегда VALIDATION",
    "conditions": {
        "is_first_response_on_topic": True,
        "has_emotional_signal": True,
        "current_turn_in_topic": {"lte": 1}
    },
    "mode": "VALIDATION",
    "priority": 100,
    "confidence_weight": 1.0,
    "flag": "VALIDATION_FIRST_ENABLED"
}
```

Агент добавляет в `signal_detector.py` функцию `is_first_response_on_topic()`, которая проверяет по `WorkingState`: была ли текущая тема уже в предыдущих ходах.

**Acceptance criteria:**

- При первом сообщении с эмоциональным сигналом → режим VALIDATION независимо от других правил
- При повторном сообщении на ту же тему → обычная маршрутизация
- Тест `test_decision_table.py` остаётся зелёным, добавляется один новый тест

***

### 9.3 Детектор противоречий

**Проблема:** пользователь говорит «всё нормально», но использует маркеры тревоги. Бот игнорирует это — теряет важный сигнал.

**Реализация:** новый файл `bot_agent/contradiction_detector.py`:

```python
"""
Обнаруживает расхождение между декларируемым состоянием и эмоциональными маркерами.
НЕ меняет маршрутизацию — только добавляет сигнал в debug_trace и context.
"""

# Декларативные "всё хорошо" фразы
POSITIVE_DECLARATIONS = [
    r"всё (хорошо|нормально|ок)", r"я (справляюсь|в порядке)",
    r"не жалуюсь", r"всё под контролем"
]

# Эмоциональные маркеры тревоги/напряжения
ANXIETY_MARKERS = [
    r"(устал|выматывает|тяжело|напряжение|не высыпаюсь)",
    r"(раздражает|бесит|злит|достало)",
    r"(не знаю (как|что)|запутался|не понимаю)"
]

def detect_contradiction(text: str) -> dict:
    """
    Возвращает:
    {
        "has_contradiction": bool,
        "declared": str | None,
        "actual_signal": str | None,
        "suggestion": str  # что передать в контекст для ResponseGenerator
    }
    """
    has_positive = any(re.search(p, text.lower()) for p in POSITIVE_DECLARATIONS)
    has_anxiety = any(re.search(p, text.lower()) for p in ANXIETY_MARKERS)

    if has_positive and has_anxiety:
        return {
            "has_contradiction": True,
            "declared": "позитивное состояние",
            "actual_signal": "маркеры тревоги/напряжения",
            "suggestion": "Пользователь говорит что всё хорошо, но текст содержит маркеры напряжения. Мягко отметь это расхождение."
        }
    return {"has_contradiction": False}
```

Результат `detect_contradiction()` передаётся в `debug_trace` и как дополнительный контекст в `ResponseGenerator` — без изменения интерфейса `ResponseGenerator`.

**Acceptance criteria:**

- На фразу «всё нормально, просто немного устал и раздражаюсь» → `has_contradiction=True`
- На фразу «мне плохо, очень тяжело» → `has_contradiction=False`
- Детектор добавляет сигнал в debug_trace, не меняет routing

***

### 9.4 Память между сессиями (Cross-Session Memory)

**Проблема:** после завершения сессии бот «забывает» всё. При следующем разговоре — начинает с нуля, не помня ключевых тем.

**Реализация:** расширение `conversation_memory.py` (только новые методы, без изменения существующего интерфейса):

```python
# Добавить в ConversationMemory — новые методы, старые НЕ ТРОГАТЬ

def save_session_summary(self, user_id: str, summary: dict):
    """
    Сохраняет краткое резюме сессии в SQLite (уже используется в тестах).
    summary = {
        "session_id": str,
        "date": str,
        "key_themes": List[str],   # топ-3 темы сессии
        "sd_level_end": str,       # SD уровень в конце сессии
        "state_end": str,          # состояние в конце сессии
        "notable_moments": List[str]  # до 3 значимых моментов
    }
    """
    # Сохранить в таблицу session_summaries в существующей SQLite БД
    pass

def load_cross_session_context(self, user_id: str, limit: int = 3) -> str:
    """
    Загружает контекст из последних N сессий для подстановки в промт.
    Возвращает строку для вставки в системный промт:
    "Из предыдущих сессий: [тема1], [тема2]. Последнее состояние: GREEN."
    """
    pass
```

**Где вызывается:** в начале новой сессии `answer_question_adaptive()` получает `cross_session_context` и подставляет его в системный промт. Изменение в оркестраторе минимальное — добавить одну строку загрузки контекста.

**Acceptance criteria:**

- После завершения сессии — `session_summaries` в SQLite содержит запись
- При старте новой сессии того же пользователя — контекст подгружается
- При первой сессии пользователя — `load_cross_session_context` возвращает пустую строку (не ошибку)
- Тест `test_conversation_memory_persistence.py` остаётся зелёным, добавляется два новых теста

***

### 9.5 Progressive RAG — Весовые блоки знаний

**Проблема:** все блоки базы знаний равнозначны при retrieval. Но некоторые блоки оказываются полезнее — это никак не учитывается.

**Реализация:** новая таблица `block_weights` в SQLite:

```python
# bot_agent/progressive_rag.py  (новый файл)

class ProgressiveRAG:
    """
    Хранит веса блоков знаний на основе обратной связи.
    Не изменяет ChromaDB — только постобработка результатов retrieval.
    """

    def get_weight(self, block_id: str) -> float:
        """Возвращает вес блока (1.0 по умолчанию, растёт при positive feedback)."""
        pass

    def record_positive_feedback(self, block_id: str):
        """
        Вызывается когда пользователь явно выражает удовлетворение ответом.
        Сигнал: "это именно то", "спасибо, помогло", "да, именно"
        """
        # weight = min(current_weight * 1.1, 2.0)  # максимум +100% от базового
        pass

    def rerank_by_weights(self, blocks: List[dict]) -> List[dict]:
        """
        Применяет веса к результатам retrieval.
        Вызывается ПОСЛЕ основного retrieval, ПЕРЕД reranker.
        """
        pass
```

**Детектор позитивной обратной связи** добавляется в `signal_detector.py`:

```python
POSITIVE_FEEDBACK_PATTERNS = [
    r"(это именно|именно то|спасибо.*помогло|да.*именно|точно|в точку)"
]
```

**Acceptance criteria:**

- Блок с 5+ позитивными feedback появляется в топ-3 при релевантных запросах
- Веса сохраняются между сессиями в SQLite
- При полном сбросе (`--reset-weights`) — все веса возвращаются к 1.0

***

## 10. Порядок выполнения

```
ФАЗА 0: Подготовка (до написания кода)
───────────────────────────────────────
0.1  Прочитать все файлы в bot_agent/, config/, tests/
0.2  Создать scripts/chroma_backup.py и выполнить бэкап
0.3  Создать scripts/bootstrap_eval_sets.py
0.4  Запустить bootstrap: извлечь eval-примеры из существующих тестов
0.5  Создать tests/eval/ со всеми четырьмя файлами
0.6  Запустить eval на ТЕКУЩЕЙ системе → заполнить baseline.json числами
0.7  ✅ Gate: baseline зафиксирован численно → переход к Фазе 1

ФАЗА 1: Embedding Migration
─────────────────────────────
1.1  Создать bot_agent/embedding_provider.py (interface + E5Provider)
1.2  Обновить retriever.py: использовать EmbeddingProvider
1.3  Обновить chroma_loader.py: --rebuild-index + параллельная коллекция
1.4  Создать новую ChromaDB-коллекцию psychologist_e5 (старую НЕ удалять)
1.5  Запустить eval_retrieval.py --compare
1.6  ✅ Gate: Recall@5 и MRR ≥ baseline → мердж. Иначе → откат коллекции.

ФАЗА 2: Conditional Reranker
──────────────────────────────
2.1  Создать bot_agent/reranker_gate.py
2.2  Подключить к retrieval pipeline
2.3  Проверить: reranker вызывается ≤ 25% запросов на тест-наборе
2.4  ✅ Gate: тест test_voyage_reranker.py зелёный → мердж

ФАЗА 3: Fast Detector
───────────────────────
3.1  Создать bot_agent/fast_detector.py
3.2  Подключить в state_classifier.py (перед Level-1, не вместо)
3.3  Подключить в sd_classifier.py (перед Level-1, не вместо)
3.4  ✅ Gate: test_sd_classifier.py полностью зелёный → мердж

ФАЗА 4: Feature Flags
───────────────────────
4.1  Создать config/feature_flags.py
4.2  Подключить ко всем новым компонентам (фазы 1-3)
4.3  Обновить .env.example
4.4  ✅ Gate: каждый флаг переключается независимо → мердж

ФАЗА 5: Улучшения интеллекта (порядок важен)
─────────────────────────────────────────────
5.1  Адаптивная длина ответа (response_formatter.py)
     → Gate: test_response_formatter.py зелёный
5.2  Принудительный VALIDATION (decision_table.py + signal_detector.py)
     → Gate: test_decision_table.py зелёный + новый тест
5.3  Детектор противоречий (contradiction_detector.py)
     → Gate: новый тест test_contradiction_detector.py зелёный
5.4  Cross-session память (conversation_memory.py расширение)
     → Gate: test_conversation_memory_persistence.py зелёный + 2 новых теста
5.5  Progressive RAG (progressive_rag.py)
     → Gate: тест на рост веса блоков после feedback
```


***

## 11. Hard Constraints — что агент НЕ делает никогда

1. **Не изменять** `answer_question_adaptive()` как оркестратор — только его зависимости
2. **Не изменять** формат `WorkingState`, `ConversationMemory`, `add_turn()` — только расширять новыми методами
3. **Не изменять** `ResponseGenerator`, `ResponseFormatter` в существующей части — только добавлять новые функции
4. **Не удалять** `VoyageReranker` — только перевести в conditional mode
5. **Не менять** embedding без прохождения gate в Фазе 1
6. **Не удалять** старую ChromaDB-коллекцию до завершения Фазы 5
7. **Не генерировать** eval-наборы самостоятельно — только извлекать из существующих тестов или ждать заполнения от человека
8. **Каждый коммит** должен содержать номер фазы: `[Phase 1.2] Add E5EmbeddingProvider`

***

## 12. Метрики успеха

| Метрика | Baseline | Целевое значение |
| :-- | :-- | :-- |
| Recall@5 retrieval | измеряется в Ф.0 | ≥ baseline + 5% |
| MRR retrieval | измеряется в Ф.0 | ≥ baseline |
| SDClassifier accuracy@1 | измеряется в Ф.0 | ≥ 75% |
| StateClassifier accuracy@1 | измеряется в Ф.0 | ≥ baseline |
| % reranker вызовов | ~100% | ≤ 25% |
| % запросов через Level-0 | 0% | ≥ 60% |
| Latency классификации (Level-0 hit) | — | ≤ 2ms |
| Latency классификации (Level-1) | измеряется в Ф.0 | не хуже + 10% |
| Tестовый suite (pytest) | 80 pass / 11 skip | ≥ 80 pass, новые добавлены |


***

## 13. Зависимости и окружение

```
Новые зависимости (добавить в requirements_bot.txt):
sentence-transformers>=2.7.0    # EmbeddingProvider
torch>=2.0.0                    # GPU inference (опционально)
transformers>=4.40.0            # E5 backend

Уже есть (не менять):
voyageai                        # остаётся, conditional
chromadb                        # без изменений
```

**GPU-рекомендации:**

- E5-base: CPU приемлем (~200ms на запрос), GPU (~15ms)
- E5-large: только GPU, на CPU неприемлемая latency
- При отсутствии GPU → использовать E5-base, не E5-large

***

## 14. Документация после каждой фазы

| Документ | Что обновлять |
| :-- | :-- |
| `CHANGELOG.md` | Описание изменений фазы, дата, коммит |
| `README.md` → "Конфигурация" | Новые env-переменные с примерами |
| `README.md` → "Feature Flags" | Описание каждого флага |
| `README.md` → "Eval" | Инструкция запуска `scripts/eval_*.py` |
| `.env.example` | Все новые переменные с дефолтами и комментариями |


***

## 15. Приоритеты для агента

```
ПРИОРИТЕТ 1 — Критично, делать первым:
  → Фаза 0: бэкап + baseline (без этого ничего не трогать)
  → Фаза 1: E5 embedding + переиндексация в новую коллекцию
  → Gate check: Recall@5 и MRR

ПРИОРИТЕТ 2 — Высокий:
  → Фаза 2: Conditional reranker
  → Фаза 4: Feature flags
  → Фаза 5.1: Адаптивная длина ответа
  → Фаза 5.2: VALIDATION-first

ПРИОРИТЕТ 3 — Средний:
  → Фаза 3: Fast detector
  → Фаза 5.3: Детектор противоречий
  → Фаза 5.4: Cross-session память

ПРИОРИТЕТ 4 — Желательно:
  → Фаза 5.5: Progressive RAG
  → Полная документация
  → Дополнение eval-наборов до 80/60/50 пар
```

