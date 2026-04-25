# PRD-019 · Memory + Retrieval Agent
## Мультиагентная система NEO — Эпоха №4

---

**Документ:** PRD-019  
**Агент:** Memory + Retrieval Agent  
**Версия:** 1.0  
**Статус:** В разработке  
**Автор:** Askhat (соло)  
**Репозиторий:** github.com/Askhat-cmd/Text_transcription  
**Целевая директория:** `bot_psychologist/bot_agent/multiagent/agents/`  
**Дата создания:** 2026-04-25  
**Зависимости:** PRD-017 ✅ · PRD-018 ✅  

---

## 1. Контекст и назначение

### 1.1 Что уже сделано

После PRD-017 и PRD-018 в репозитории работает полная цепочка:

```
User Message
     │
     ▼
[State Analyzer]     ← PRD-018 ✅ (гибридный, nano LLM)
     │ StateSnapshot
     ▼
[Thread Manager]     ← PRD-017 ✅ (детерминированный)
     │ ThreadState
     ▼
[Orchestrator]       ← заглушка _build_answer() → Writer не подключён
```

Orchestrator уже интегрирует State Analyzer и Thread Manager, но `_build_answer()` — статическая заглушка [cite:19]. Writer нельзя подключить пока нет контекста: Memory + Retrieval Agent — это именно тот слой, который собирает всё что нужно Writer-у для ответа. Без него Writer пишет вслепую.

### 1.2 Текущий `MemoryBundle` в репозитории

```python
# contracts/memory_bundle.py — уже существует
@dataclass
class MemoryBundle:
    conversation_context: str
    semantic_hits: list
    retrieved_chunks: list
```

Это заглушка. PRD-019 расширяет контракт и реализует агента, который его заполняет.

### 1.3 Что уже делают существующие модули

| Существующий модуль | Размер | Что делает | Отношение к MRA |
|---|---|---|---|
| `conversation_memory.py` | ~8kb | Хранит историю диалога, даёт sliding window | Используется MRA напрямую |
| `semantic_memory.py` | ~11kb | Профиль пользователя: паттерны, триггеры, прогресс | Используется MRA напрямую |
| `chroma_loader.py` | 21kb | Загрузка ChromaDB коллекций, RAG-запросы | Используется MRA для retrieved_chunks |
| `answer_adaptive.py` | 17kb | Сейчас вызывает всё это напрямую | MRA инкапсулирует эту логику чисто |

**Ключевая задача PRD-019:** собрать все три источника памяти в `MemoryBundle` с учётом `ThreadState` — без дополнительных LLM-вызовов. MRA — детерминированный слой сборки контекста.

### 1.4 Место в пайплайне

```
[Thread Manager] → ThreadState
                       │
                       ▼
              [Memory + Retrieval]     ← PRD-019 (ВЫ ЗДЕСЬ)
                       │ MemoryBundle
                       ▼
                  [Writer / NEO]       ← PRD-020
```

---

## 2. Расширение контракта `MemoryBundle`

**Важно:** Текущий `MemoryBundle` является заглушкой, поля нетипизированы. PRD-019 расширяет его. Это единственное изменение контрактного файла в данном PRD.

```python
# contracts/memory_bundle.py — заменить полностью

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SemanticHit:
    """Элемент из ChromaDB RAG-поиска."""
    chunk_id: str
    content: str          # текст чанка
    source: str           # имя коллекции или файла
    score: float          # релевантность 0.0–1.0


@dataclass
class UserProfile:
    """Долговременный профиль из semantic_memory.py"""
    patterns: list[str] = field(default_factory=list)   # поведенческие паттерны
    triggers: list[str] = field(default_factory=list)   # известные триггеры
    values: list[str] = field(default_factory=list)     # ценности и приоритеты
    progress_notes: list[str] = field(default_factory=list)  # отмеченный прогресс


@dataclass
class MemoryBundle:
    # Последние N ходов диалога в виде форматированной строки
    conversation_context: str

    # Профиль из долговременной памяти
    user_profile: UserProfile = field(default_factory=UserProfile)

    # RAG-чанки из ChromaDB, отсортированные по score DESC
    semantic_hits: list[SemanticHit] = field(default_factory=list)

    # Сырые retrieved chunks (обратная совместимость, deprecated — использовать semantic_hits)
    retrieved_chunks: list[Any] = field(default_factory=list)

    # Мета-информация для Writer-а
    has_relevant_knowledge: bool = False   # True если semantic_hits непустой и score > 0.5
    context_turns: int = 0                 # сколько ходов вошло в conversation_context
```

---

## 3. Функциональные требования

### 3.1 Входящий контракт

```python
async def assemble(
    user_message: str,
    thread_state: ThreadState,
    user_id: str,
) -> MemoryBundle
```

`assemble()` — главный метод. Собирает MemoryBundle из трёх источников параллельно.

### 3.2 Источник 1 — Conversation Context

**Откуда:** `conversation_memory.py`  
**Что собираем:** Последние N ходов диалога в виде строки

Правила формирования:
- Базовый N = 6 ходов (3 пары user/assistant)
- Если `thread_state.phase == "stabilize"` → N = 3 (короткий контекст, не перегружать)
- Если `thread_state.phase == "integrate"` → N = 10 (больше истории для интеграции)
- Если `thread_state.relation_to_thread == "new_thread"` → N = 2 (только последнее)
- Формат: `"User: {text}
Assistant: {text}
---
"` для каждого хода

### 3.3 Источник 2 — User Profile

**Откуда:** `semantic_memory.py`  
**Что собираем:** Профиль пользователя

Правила:
- Загружается всегда (быстрая операция)
- Если профиль пустой → возвращается `UserProfile()` с пустыми списками
- Ошибка загрузки → логируется, возвращается пустой профиль (не бросаем исключение)

### 3.4 Источник 3 — ChromaDB RAG

**Откуда:** `chroma_loader.py`  
**Что собираем:** Релевантные чанки по запросу пользователя

Правила формирования RAG-запроса:
- Базовый запрос = `user_message`
- Если `thread_state.core_direction` длиннее 10 символов → добавить к запросу: `"{user_message} {core_direction}"`
- Если `thread_state.open_loops` непустой → добавить первый open_loop: `"{query} {open_loops[0]}"`
- Количество чанков: n_results = 4 (фиксировано)
- Минимальный порог релевантности: score ≥ 0.45
- Если ChromaDB недоступна → возвращается пустой список (graceful degradation)

### 3.5 Параллельная сборка

Все три источника запрашиваются параллельно через `asyncio.gather`:

```python
conv_ctx, user_profile, rag_hits = await asyncio.gather(
    self._load_conversation(user_id, n_turns),
    self._load_profile(user_id),
    self._load_rag(query, thread_state),
    return_exceptions=True,
)
```

Каждый результат проверяется: если это `Exception` → логировать и вернуть дефолт.  
Сборка не должна падать из-за отдельного источника.

### 3.6 Постобработка

После получения трёх источников:
- Фильтровать `semantic_hits` по `score >= 0.45`
- Сортировать по score DESC
- Установить `has_relevant_knowledge = len(filtered_hits) > 0`
- Установить `context_turns = N` (сколько ходов реально вошло)

### 3.7 Async update после Writer-а (будущее)

Метод `update()` для записи нового хода в память — заглушка в PRD-019, реализуется в PRD-022 когда Writer будет готов:

```python
async def update(
    user_id: str,
    user_message: str,
    assistant_response: str,
    thread_state: ThreadState,
) -> None:
    """Записывает новый ход в conversation_memory и обновляет semantic_memory."""
    ...  # scaffold в PRD-019, реализация в PRD-022
```

---

## 4. Структура файлов

```
bot_psychologist/
└── bot_agent/
    └── multiagent/
        ├── agents/
        │   ├── __init__.py                       ← добавить экспорт memory_retrieval_agent
        │   ├── state_analyzer.py                 ← не трогать ✅
        │   ├── thread_manager.py                 ← не трогать ✅
        │   ├── memory_retrieval.py               ← ОСНОВНОЙ ФАЙЛ PRD-019  [новый]
        │   └── memory_retrieval_config.py        ← конфиг MRA изолированно [новый]
        └── contracts/
            └── memory_bundle.py                  ← РАСШИРИТЬ (заменить заглушку)

tests/
└── multiagent/
    ├── fixtures/
    │   └── memory_retrieval_fixtures.json        ← [новый]
    └── test_memory_retrieval.py                  ← [новый]
```

**Принцип:** `memory_retrieval.py` — только оркестрация сборки.  
`memory_retrieval_config.py` — только константы и N-правила.  
Прямая работа с `conversation_memory` и `semantic_memory` остаётся в их модулях.

---

## 5. memory_retrieval_config.py

```python
# multiagent/agents/memory_retrieval_config.py

"""Конфигурация Memory + Retrieval Agent. Все числовые параметры изолированы здесь."""

# Количество ходов диалога по фазам
CONVERSATION_TURNS_BY_PHASE: dict[str, int] = {
    "stabilize": 3,
    "clarify": 6,
    "explore": 6,
    "integrate": 10,
}
CONVERSATION_TURNS_DEFAULT: int = 6
CONVERSATION_TURNS_NEW_THREAD: int = 2

# RAG параметры
RAG_N_RESULTS: int = 4
RAG_MIN_SCORE: float = 0.45
RAG_QUERY_MAX_LEN: int = 300

# Минимальная длина core_direction для добавления к RAG-запросу
CORE_DIRECTION_MIN_LEN: int = 10
```

---

## 6. Реализация memory_retrieval.py

```python
# multiagent/agents/memory_retrieval.py

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from ..contracts.memory_bundle import MemoryBundle, SemanticHit, UserProfile
from ..contracts.thread_state import ThreadState
from .memory_retrieval_config import (
    CONVERSATION_TURNS_BY_PHASE,
    CONVERSATION_TURNS_DEFAULT,
    CONVERSATION_TURNS_NEW_THREAD,
    CORE_DIRECTION_MIN_LEN,
    RAG_MIN_SCORE,
    RAG_N_RESULTS,
    RAG_QUERY_MAX_LEN,
)

logger = logging.getLogger(__name__)


class MemoryRetrievalAgent:
    """
    Собирает MemoryBundle из трёх источников параллельно:
    1. Conversation context (последние N ходов)
    2. User profile (долговременная семантическая память)
    3. ChromaDB RAG (релевантные чанки по теме)
    Не делает LLM-вызовов. Все ошибки — graceful degradation.
    """

    async def assemble(
        self,
        *,
        user_message: str,
        thread_state: ThreadState,
        user_id: str,
    ) -> MemoryBundle:
        n_turns = self._resolve_n_turns(thread_state)
        rag_query = self._build_rag_query(user_message, thread_state)

        results = await asyncio.gather(
            self._load_conversation(user_id, n_turns),
            self._load_profile(user_id),
            self._load_rag(rag_query),
            return_exceptions=True,
        )

        conversation_context = results[0] if not isinstance(results[0], Exception) else ""
        user_profile = results[1] if not isinstance(results[1], Exception) else UserProfile()
        raw_hits = results[2] if not isinstance(results[2], Exception) else []

        for i, (label, exc) in enumerate(zip(
            ["conversation", "profile", "rag"], results
        )):
            if isinstance(exc, Exception):
                logger.warning("[MRA] %s load failed: %s", label, exc)

        filtered_hits = [h for h in raw_hits if h.score >= RAG_MIN_SCORE]
        filtered_hits.sort(key=lambda h: h.score, reverse=True)

        return MemoryBundle(
            conversation_context=conversation_context if isinstance(conversation_context, str) else "",
            user_profile=user_profile if isinstance(user_profile, UserProfile) else UserProfile(),
            semantic_hits=filtered_hits,
            retrieved_chunks=[h.content for h in filtered_hits],  # deprecated compat
            has_relevant_knowledge=len(filtered_hits) > 0,
            context_turns=n_turns,
        )

    async def update(
        self,
        *,
        user_id: str,
        user_message: str,
        assistant_response: str,
        thread_state: ThreadState,
    ) -> None:
        """Scaffold для записи хода в память. Реализуется в PRD-022."""
        logger.debug(
            "[MRA] update called for user=%s (scaffold, not yet implemented)", user_id
        )

    # ── Внутренние методы ────────────────────────────────────────────────

    @staticmethod
    def _resolve_n_turns(thread_state: ThreadState) -> int:
        if thread_state.relation_to_thread == "new_thread":
            return CONVERSATION_TURNS_NEW_THREAD
        return CONVERSATION_TURNS_BY_PHASE.get(thread_state.phase, CONVERSATION_TURNS_DEFAULT)

    @staticmethod
    def _build_rag_query(user_message: str, thread_state: ThreadState) -> str:
        parts = [user_message.strip()]
        if len(thread_state.core_direction) >= CORE_DIRECTION_MIN_LEN:
            parts.append(thread_state.core_direction)
        if thread_state.open_loops:
            parts.append(thread_state.open_loops[0])
        query = " ".join(parts)
        return query[:RAG_QUERY_MAX_LEN]

    @staticmethod
    async def _load_conversation(user_id: str, n_turns: int) -> str:
        try:
            from ...conversation_memory import ConversationMemory  # noqa: PLC0415
            mem = ConversationMemory(user_id=user_id)
            history = mem.get_recent(n=n_turns)
            if not history:
                return ""
            lines = []
            for turn in history:
                role = turn.get("role", "user").capitalize()
                text = turn.get("content", "").strip()
                lines.append(f"{role}: {text}")
                lines.append("---")
            return "\n".join(lines)
        except Exception as exc:
            logger.warning("[MRA] conversation load error: %s", exc)
            return ""

    @staticmethod
    async def _load_profile(user_id: str) -> UserProfile:
        try:
            from ...semantic_memory import SemanticMemory  # noqa: PLC0415
            mem = SemanticMemory(user_id=user_id)
            raw = mem.get_profile()
            return UserProfile(
                patterns=raw.get("patterns", []),
                triggers=raw.get("triggers", []),
                values=raw.get("values", []),
                progress_notes=raw.get("progress_notes", []),
            )
        except Exception as exc:
            logger.warning("[MRA] profile load error: %s", exc)
            return UserProfile()

    @staticmethod
    async def _load_rag(query: str) -> list[SemanticHit]:
        try:
            from ...chroma_loader import ChromaLoader  # noqa: PLC0415
            loader = ChromaLoader()
            results = loader.query(query_text=query, n_results=RAG_N_RESULTS)
            hits = []
            for item in results:
                hits.append(SemanticHit(
                    chunk_id=item.get("id", ""),
                    content=item.get("content", item.get("document", "")),
                    source=item.get("source", item.get("collection", "unknown")),
                    score=float(item.get("score", item.get("distance", 0.0))),
                ))
            return hits
        except Exception as exc:
            logger.warning("[MRA] rag load error: %s", exc)
            return []


memory_retrieval_agent = MemoryRetrievalAgent()
```

---

## 7. Обновление Orchestrator

```python
# multiagent/orchestrator.py — обновить метод run()

from .agents.memory_retrieval import memory_retrieval_agent

async def run(self, *, query: str, user_id: str) -> dict:
    current_thread = thread_storage.load_active(user_id)
    archived_threads = thread_storage.load_archived(user_id)

    # 1. State Analyzer
    state_snapshot = await state_analyzer_agent.analyze(
        user_message=query,
        previous_thread=current_thread,
    )

    # 2. Thread Manager
    updated_thread = await thread_manager_agent.update(
        user_message=query,
        state_snapshot=state_snapshot,
        user_id=user_id,
        current_thread=current_thread,
        archived_threads=archived_threads,
    )

    # 3. Сохранить нить ДО сборки контекста
    if updated_thread.relation_to_thread == "new_thread" and current_thread is not None:
        thread_storage.archive_thread(current_thread, reason="new_thread")
    thread_storage.save_active(updated_thread)

    # 4. Memory + Retrieval  ←── PRD-019
    memory_bundle = await memory_retrieval_agent.assemble(
        user_message=query,
        thread_state=updated_thread,
        user_id=user_id,
    )

    # 5. Writer (PRD-020) — пока заглушка
    answer = self._build_answer(query=query, thread=updated_thread, memory_bundle=memory_bundle)

    # 6. Async update памяти (scaffold — реализуется в PRD-022)
    asyncio.create_task(memory_retrieval_agent.update(
        user_id=user_id,
        user_message=query,
        assistant_response=answer,
        thread_state=updated_thread,
    ))

    return {
        "status": "ok",
        "answer": answer,
        "thread_id": updated_thread.thread_id,
        "phase": updated_thread.phase,
        "response_mode": updated_thread.response_mode,
        "relation_to_thread": updated_thread.relation_to_thread,
        "continuity_score": updated_thread.continuity_score,
        "debug": {
            "multiagent_enabled": True,
            "nervous_state": state_snapshot.nervous_state,
            "intent": state_snapshot.intent,
            "safety_flag": state_snapshot.safety_flag,
            "confidence": state_snapshot.confidence,
            "has_relevant_knowledge": memory_bundle.has_relevant_knowledge,
            "context_turns": memory_bundle.context_turns,
            "semantic_hits_count": len(memory_bundle.semantic_hits),
        },
    }
```

---

## 8. Обновление `agents/__init__.py`

```python
# multiagent/agents/__init__.py

from .state_analyzer import state_analyzer_agent
from .thread_manager import thread_manager_agent
from .memory_retrieval import memory_retrieval_agent

__all__ = [
    "state_analyzer_agent",
    "thread_manager_agent",
    "memory_retrieval_agent",
]
```

---

## 9. Обновление `feature_flags.py`

```python
# bot_agent/feature_flags.py — добавить:

MEMORY_RAG_N_RESULTS: int = int(os.getenv("MEMORY_RAG_N_RESULTS", "4"))
MEMORY_RAG_MIN_SCORE: float = float(os.getenv("MEMORY_RAG_MIN_SCORE", "0.45"))
MEMORY_CONV_TURNS_DEFAULT: int = int(os.getenv("MEMORY_CONV_TURNS_DEFAULT", "6"))
```

---

## 10. Fixtures для тестов

Файл `tests/multiagent/fixtures/memory_retrieval_fixtures.json`:

```json
[
  {
    "id": "MR-F01",
    "user_message": "хочу разобраться с тревогой",
    "thread_phase": "clarify",
    "thread_relation": "continue",
    "core_direction": "тревога на работе",
    "open_loops": ["почему я так реагирую"],
    "expected_n_turns": 6,
    "expected_query_contains": ["тревог", "работ"]
  },
  {
    "id": "MR-F02",
    "user_message": "новая тема",
    "thread_phase": "clarify",
    "thread_relation": "new_thread",
    "core_direction": "новая тема",
    "open_loops": [],
    "expected_n_turns": 2
  },
  {
    "id": "MR-F03",
    "user_message": "хочу осмыслить всё что понял",
    "thread_phase": "integrate",
    "thread_relation": "continue",
    "core_direction": "паттерн избегания",
    "open_loops": [],
    "expected_n_turns": 10
  },
  {
    "id": "MR-F04",
    "user_message": "срочно нужна помощь",
    "thread_phase": "stabilize",
    "thread_relation": "continue",
    "core_direction": "кризис",
    "open_loops": [],
    "expected_n_turns": 3
  }
]
```

---

## 11. Тесты

### 11.1 test_memory_retrieval.py — полный список

```
MR-01  BUNDLE_FIELDS — MemoryBundle содержит все обязательные поля
MR-02  BUNDLE_ROUND_TRIP — MemoryBundle с заполненными данными сериализуется без потерь
MR-03  SEMANTIC_HIT_FIELDS — SemanticHit содержит chunk_id, content, source, score
MR-04  USER_PROFILE_FIELDS — UserProfile содержит patterns, triggers, values, progress_notes
MR-05  N_TURNS_STABILIZE — phase=stabilize → n_turns=3
MR-06  N_TURNS_INTEGRATE — phase=integrate → n_turns=10
MR-07  N_TURNS_NEW_THREAD — relation=new_thread → n_turns=2
MR-08  N_TURNS_DEFAULT — phase=clarify/explore → n_turns=6
MR-09  RAG_QUERY_WITH_CORE — core_direction >= 10 символов → добавляется к query
MR-10  RAG_QUERY_WITH_LOOP — open_loops непустой → первый loop добавляется к query
MR-11  RAG_QUERY_SHORT_CORE — core_direction < 10 символов → не добавляется
MR-12  RAG_QUERY_MAX_LEN — query не превышает 300 символов
MR-13  RAG_SCORE_FILTER — hits с score < 0.45 фильтруются
MR-14  RAG_SORT_DESC — hits отсортированы по score DESC
MR-15  HAS_KNOWLEDGE_TRUE — при непустых filtered_hits: has_relevant_knowledge=True
MR-16  HAS_KNOWLEDGE_FALSE — при пустых hits: has_relevant_knowledge=False
MR-17  CONV_FAIL_GRACEFUL — exception в _load_conversation → conversation_context=""
MR-18  PROFILE_FAIL_GRACEFUL — exception в _load_profile → UserProfile() пустой
MR-19  RAG_FAIL_GRACEFUL — exception в _load_rag → semantic_hits=[]
MR-20  ALL_FAIL_GRACEFUL — все три источника падают → MemoryBundle с дефолтами, без исключения
MR-21  PARALLEL_GATHER — три источника вызываются через asyncio.gather
MR-22  NO_LLM_CALLS — ни один LLM-вызов не происходит в assemble()
MR-23  UPDATE_SCAFFOLD — update() возвращает None, не бросает исключений
MR-24  COMPAT_CHUNKS — retrieved_chunks = [h.content for h in semantic_hits]
MR-25  CONTEXT_TURNS_SET — context_turns = n_turns
MR-26  ORCHESTRATOR_INTEGRATION — orchestrator.run() вызывает memory_retrieval_agent.assemble()
MR-27  ORCHESTRATOR_DEBUG — поле debug содержит has_relevant_knowledge, context_turns
MR-28  FIXTURE_F01 — n_turns=6 для clarify/continue
MR-29  FIXTURE_F02 — n_turns=2 для new_thread
MR-30  FIXTURE_F03 — n_turns=10 для integrate
```

### 11.2 Регрессионные чеки

```
REG-01  pytest tests/multiagent/ — все тесты PRD-017 и PRD-018 остаются зелёными
REG-02  memory_retrieval.py не импортирует openai напрямую
REG-03  memory_retrieval.py не импортирует adaptive_runtime/
REG-04  contracts/state_snapshot.py не изменён
REG-05  contracts/thread_state.py не изменён
REG-06  contracts/memory_bundle.py расширен (не заменены поля, только добавлены)
```

---

## 12. Acceptance Criteria (Definition of Done)

PRD-019 завершён когда:

- [ ] `contracts/memory_bundle.py` расширен: `SemanticHit`, `UserProfile`, новые поля `MemoryBundle`
- [ ] `agents/memory_retrieval.py` создан
- [ ] `agents/memory_retrieval_config.py` создан с параметрами N-turns и RAG
- [ ] `agents/__init__.py` экспортирует `memory_retrieval_agent`
- [ ] `orchestrator.py` вызывает `memory_retrieval_agent.assemble()` и добавляет debug-поля
- [ ] Все 30 тестов MRA зелёные
- [ ] Все тесты PRD-017 и PRD-018 зелёные (REG-01)
- [ ] `memory_retrieval.py` не делает LLM-вызовов (MR-22)
- [ ] Graceful degradation при падении любого из трёх источников (MR-17–20)
- [ ] `pytest tests/multiagent/ -q` — 100% pass (все тесты PRD-017 + PRD-018 + PRD-019)

---

## 13. Что НЕ входит в PRD-019

| Что | PRD |
|---|---|
| Запись нового хода в conversation_memory (update) | PRD-022 |
| Writer Agent / NEO (генерация ответа) | PRD-020 |
| Validator | PRD-021 |
| Полный Orchestrator с Writer | PRD-022 |
| Архивирование legacy | PRD-023 |

---

## 14. Важные замечания для IDE-агента

1. **`memory_retrieval.py` — без LLM-вызовов.** Это чистый слой оркестрации. Ни одного `client.chat.completions.create`.
2. **Импорты `conversation_memory`, `semantic_memory`, `chroma_loader`** — через ленивые локальные импорты внутри методов. Это позволяет тестировать без реальных зависимостей через mock.
3. **`contracts/memory_bundle.py` — расширить, не переписать.** Поле `retrieved_chunks: list` должно остаться для обратной совместимости.
4. **`update()` — только scaffold** (`pass` или `logger.debug`). Реализация в PRD-022.
5. **В тестах** — mock все три источника (`_load_conversation`, `_load_profile`, `_load_rag`) через `unittest.mock.AsyncMock`.
6. **ChromaDB** может быть недоступна в CI — обязательный graceful fallback.

---

*Конец PRD-019 · Memory + Retrieval Agent*  
*Следующий документ: PRD-020 · Writer Agent / NEO (пишется после реализации PRD-019)*
