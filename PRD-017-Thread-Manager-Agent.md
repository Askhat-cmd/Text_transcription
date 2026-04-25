# PRD-017 · Thread Manager Agent
## Мультиагентная система NEO — Эпоха №4

---

**Документ:** PRD-017  
**Агент:** Thread Manager  
**Версия:** 1.0  
**Статус:** В разработке  
**Автор:** Askhat (соло)  
**Репозиторий:** github.com/Askhat-cmd/Text_transcription  
**Целевая директория:** `bot_psychologist/bot_agent/multiagent/`  
**Дата создания:** 2026-04-25  

---

## 1. Контекст и назначение

### 1.1 Место в архитектуре

Thread Manager — второй из четырёх агентов мультиагентной системы NEO.  
Он вызывается Orchestrator-ом после State Analyzer и **до** Memory+Retrieval Agent.

```
User Message
     │
     ▼
[Orchestrator]
     │
     ├──► [State Analyzer]      → StateSnapshot (nano)
     │
     ├──► [Thread Manager]      ← PRD-017 (nano)  ← ВЫ ЗДЕСЬ
     │
     ├──► [Memory+Retrieval]    → MemoryBundle (детерм.)
     │
     └──► [Writer / NEO]        → Response (mini)
```

### 1.2 Зачем нужен этот агент

Нынешняя NEO-система (Эпоха №3) обрабатывает каждый запрос независимо:
`state_classifier.py` делает снимок, `route_resolver.py` принимает решение,
`path_builder.py` строит путь — и всё это без памяти о том, куда шёл разговор.

Thread Manager решает одну задачу: **дать системе живую нить разговора**.
Он помнит, что уже было сказано, что закрыто, что открыто, в какой фазе
находится пользователь — и на основе этого говорит Writer-у: "вот куда идём".

### 1.3 Связь с существующим кодом

| Существующий модуль | Отношение к Thread Manager |
|---|---|
| `state_classifier.py` | Поставляет StateSnapshot (вход в TM) |
| `diagnostics_classifier.py` → `DiagnosticsV1` | Логика nervous_state/request_function поглощается State Analyzer, TM использует результат |
| `route_resolver.py` | **Заменяется** Thread Manager + Orchestrator |
| `path_builder.py` | **Архивируется** — маршрутизация переходит в TM |
| `conversation_memory.py` | TM читает историю ходов через Memory Agent |
| `semantic_memory.py` | TM читает долговременный профиль через Memory Agent |
| `feature_flags.py` | TM активируется через `MULTIAGENT_ENABLED` |
| `output_validator.py` | Логика избегания повторов — частично в TM (must_avoid) |

---

## 2. Функциональные требования

### 2.1 Основная функция

Thread Manager принимает:
- `user_message: str` — текущее сообщение пользователя
- `state_snapshot: StateSnapshot` — выход State Analyzer (nervous_state, intent, openness, ok_position)
- `current_thread: ThreadState | None` — активная нить (None = первый разговор)
- `archived_threads: list[ArchivedThread]` — архив предыдущих нитей

Thread Manager возвращает:
- `updated_thread: ThreadState` — обновлённое состояние нити, готовое к передаче Writer-у

### 2.2 Логика обновления нити

**Определение relation_to_thread:**

| Условие | Решение | Действие |
|---|---|---|
| Тема смежная с `core_direction`, `continuity_score > 0.70` | `continue` | Нить продолжается |
| Тема смежная, но открывается новый под-вопрос | `branch` | Добавляется в `open_loops` |
| Резкая смена темы (`continuity_score < 0.35`) | `new_thread` | Старая архивируется (статус `open`), создаётся новая |
| Пользователь явно возвращается к теме из архива | `return_to_old` | Архивная нить восстанавливается |
| Первое сообщение пользователя | `new_thread` | Создаётся первая нить |

**Определение phase:**

```
stabilize → clarify:    nervous_state изменился с hyper/hypo → window
clarify → explore:      core_direction зафиксирован ≥ 2 хода подряд
explore → integrate:    len(closed_loops) ≥ 2
integrate → clarify:    появился новый open_loop при существующих closed_loops
```

Правило: **фаза не меняется без явного сигнала**. Если `continuity_score > 0.85`,
фаза остаётся прежней даже при незначительных изменениях стейта.

**Обновление open_loops и closed_loops:**

- `open_loop` добавляется когда пользователь задаёт вопрос или обозначает проблему
- `closed_loop` добавляется когда пользователь подтверждает инсайт или сам формулирует ответ
- `open_loop` переходит в `closed_loop` автоматически при совпадении семантического смысла ответа

**Определение response_goal и response_mode:**

| phase | nervous_state | intent | response_mode | response_goal |
|---|---|---|---|---|
| stabilize | hyper/hypo | любой | regulate | успокоить, создать безопасное поле |
| clarify | window | clarify | reflect | помочь сформулировать суть |
| clarify | window | vent | validate | дать пространство, не анализировать |
| explore | window | explore | explore | расширить перспективу |
| explore | window | solution | practice | предложить конкретный инструмент |
| integrate | window | любой | reflect | поддержать интеграцию инсайта |
| любая | любой | contact | validate | только присутствие, без структуры |

**Формирование must_avoid:**

TM автоматически добавляет в `must_avoid`:
- Все тексты из `closed_loops` (не повторять то, что уже закрыто)
- Если `relation_to_thread == "continue"` → добавить `"открывать новые темы"`
- Если `phase == "stabilize"` → добавить `"давать практики"`, `"глубокий анализ"`
- Если `ok_position == "I-W-"` → добавить `"задавать риторические вопросы"`

### 2.3 Безопасность (Safety Override)

Если `StateSnapshot.safety_flag == True`:
- `response_mode` принудительно = `"safe_override"`
- `phase` принудительно = `"stabilize"`
- `must_avoid` добавляет `"любой анализ"`, `"практики"`, `"вопросы"`
- Флаг `safety_active: bool = True` выставляется в ThreadState

Это НЕ заменяет существующий `safe_override` в `route_resolver.py` —
оба работают параллельно пока `MULTIAGENT_ENABLED = False`.

---

## 3. Структура данных

### 3.1 ThreadState (полный контракт)

```python
# multiagent/thread_state.py

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal, Optional


PhaseType = Literal["stabilize", "clarify", "explore", "integrate"]
RelationType = Literal["continue", "branch", "new_thread", "return_to_old"]
ResponseModeType = Literal[
    "reflect", "validate", "explore", "regulate",
    "practice", "safe_override"
]


@dataclass
class ThreadState:
    # Идентификация
    thread_id: str
    user_id: str

    # Суть нити
    core_direction: str          # "страх видимости", "конфликт с ожиданиями"
    phase: PhaseType

    # Петли
    open_loops: list[str] = field(default_factory=list)
    closed_loops: list[str] = field(default_factory=list)

    # Состояние пользователя в ЭТОМ ходу (из State Analyzer)
    nervous_state: str = "window"    # window / hyper / hypo
    intent: str = "explore"          # clarify / vent / explore / contact / solution
    openness: str = "open"           # open / mixed / defensive / collapsed
    ok_position: str = "I+W+"        # I+W+ / I-W+ / I+W- / I-W-

    # Управление Writer-ом
    relation_to_thread: RelationType = "continue"
    response_goal: str = ""
    response_mode: ResponseModeType = "reflect"
    must_avoid: list[str] = field(default_factory=list)

    # Метрики нити
    continuity_score: float = 1.0    # 0.0–1.0
    turns_in_phase: int = 1          # сколько ходов в текущей фазе
    last_meaningful_shift: str = ""  # описание последнего значимого изменения

    # Безопасность
    safety_active: bool = False

    # Временные метки
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "thread_id": self.thread_id,
            "user_id": self.user_id,
            "core_direction": self.core_direction,
            "phase": self.phase,
            "open_loops": self.open_loops,
            "closed_loops": self.closed_loops,
            "nervous_state": self.nervous_state,
            "intent": self.intent,
            "openness": self.openness,
            "ok_position": self.ok_position,
            "relation_to_thread": self.relation_to_thread,
            "response_goal": self.response_goal,
            "response_mode": self.response_mode,
            "must_avoid": self.must_avoid,
            "continuity_score": self.continuity_score,
            "turns_in_phase": self.turns_in_phase,
            "last_meaningful_shift": self.last_meaningful_shift,
            "safety_active": self.safety_active,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ThreadState":
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        data["updated_at"] = datetime.fromisoformat(data["updated_at"])
        return cls(**data)
```

### 3.2 StateSnapshot (входящий контракт от State Analyzer)

```python
# multiagent/contracts/state_snapshot.py

@dataclass(frozen=True)
class StateSnapshot:
    nervous_state: str       # window / hyper / hypo
    intent: str              # clarify / vent / explore / contact / solution
    openness: str            # open / mixed / defensive / collapsed
    ok_position: str         # I+W+ / I-W+ / I+W- / I-W-
    safety_flag: bool        # True = кризис/риск
    confidence: float        # 0.0–1.0
```

### 3.3 ArchivedThread (архивная нить)

```python
# multiagent/thread_storage.py

@dataclass
class ArchivedThread:
    thread_id: str
    core_direction: str
    closed_loops: list[str]
    open_loops: list[str]   # незакрытые при архивации
    final_phase: str
    archived_at: datetime
    archive_reason: str     # "new_thread" / "user_reset" / "session_end"
```

---

## 4. Структура файлов

```
bot_psychologist/
└── bot_agent/
    └── multiagent/                          ← новый пакет (PRD-017 создаёт частично)
        ├── __init__.py                      ← экспорты пакета
        ├── contracts/
        │   ├── __init__.py
        │   ├── state_snapshot.py            ← StateSnapshot dataclass
        │   ├── thread_state.py              ← ThreadState dataclass  [PRD-017]
        │   ├── writer_contract.py           ← WriterContract dataclass
        │   └── memory_bundle.py             ← MemoryBundle dataclass
        ├── thread_storage.py                ← персистентность ThreadState  [PRD-017]
        ├── orchestrator.py                  ← главный оркестратор
        └── agents/
            ├── __init__.py
            ├── state_analyzer.py            ← PRD-016 (предыдущий)
            ├── thread_manager.py            ← ОСНОВНОЙ ФАЙЛ PRD-017  [PRD-017]
            ├── thread_manager_prompts.py    ← промпты TM изолированно  [PRD-017]
            ├── memory_retrieval.py          ← PRD-018 (следующий)
            ├── writer_agent.py              ← PRD-019
            └── validator.py                 ← PRD-020

tests/
└── multiagent/                              ← новая директория тестов  [PRD-017]
    ├── __init__.py
    ├── fixtures/
    │   ├── thread_states.json               ← синтетические ThreadState для тестов
    │   ├── state_snapshots.json             ← синтетические StateSnapshot
    │   └── archived_threads.json           ← архивные нити
    ├── test_thread_state_contracts.py       ← тесты контракта  [PRD-017]
    ├── test_thread_storage.py               ← тесты персистентности  [PRD-017]
    └── test_thread_manager.py               ← тесты логики TM  [PRD-017]
```

**Принцип модульности:** каждый файл — одна ответственность.
`thread_manager.py` содержит только логику обновления нити.
`thread_manager_prompts.py` содержит только промпты (чтобы менять их без риска).
`thread_storage.py` содержит только I/O нити.
`contracts/thread_state.py` содержит только dataclass.

---

## 5. Промпты Thread Manager

### 5.1 Системный промпт (thread_manager_prompts.py)

```
THREAD_MANAGER_SYSTEM = """
Ты — Thread Manager психологического бота NEO.
Твоя задача: обновить состояние живой нити разговора.

Ты получаешь:
- Текущее сообщение пользователя
- Анализ состояния пользователя (StateSnapshot)
- Текущую активную нить (ThreadState) или null если первый разговор
- Список архивных нитей

Ты должен вернуть ТОЛЬКО валидный JSON обновлённого ThreadState.
Без объяснений, без markdown, только JSON.

ПРАВИЛА ФАЗ:
- stabilize: нервная система дерегулирована. Фокус — безопасность и заземление.
- clarify: человек в окне, нужно прояснить суть. Фокус — что именно происходит.
- explore: суть ясна, можно исследовать. Фокус — расширение перспективы.
- integrate: инсайты накоплены. Фокус — осмысление и включение в жизнь.

ПРАВИЛА ПЕРЕХОДОВ ФАЗ:
- stabilize → clarify: ТОЛЬКО если nervous_state изменился на "window"
- clarify → explore: ТОЛЬКО если core_direction стабилен ≥ 2 хода
- explore → integrate: ТОЛЬКО если closed_loops содержит ≥ 2 элемента
- integrate → clarify: ТОЛЬКО если появился новый открытый вопрос

ПРАВИЛА ПЕТЕЛЬ:
- open_loops: незавершённые вопросы, проблемы, темы требующие внимания
- closed_loops: инсайты которые пользователь сам подтвердил или сформулировал
- Никогда не закрывай петлю если пользователь сам не подтвердил понимание

ПРАВИЛА must_avoid:
- Всегда включай все closed_loops (не повторять завершённое)
- При phase=stabilize: добавь "практики", "глубокий анализ", "новые темы"
- При ok_position содержащем I-W-: добавь "риторические вопросы"
- При relation_to_thread=continue: добавь "открывать новые темы без необходимости"

SAFETY OVERRIDE:
Если safety_flag=true в StateSnapshot:
- response_mode ДОЛЖЕН быть "safe_override"
- phase ДОЛЖНА быть "stabilize"
- safety_active ДОЛЖЕН быть true
- must_avoid ДОЛЖЕН включать "любой анализ", "практики", "вопросы пользователю"

ПРАВИЛА continuity_score:
- 0.9–1.0: прямое продолжение темы
- 0.7–0.9: смежная тема
- 0.5–0.7: связанная но другая тема
- 0.3–0.5: смена темы
- 0.0–0.3: полная смена темы → new_thread

Верни JSON строго по схеме ThreadState.
"""
```

### 5.2 Пользовательский промпт (thread_manager_prompts.py)

```
THREAD_MANAGER_USER_TEMPLATE = """
ТЕКУЩЕЕ СООБЩЕНИЕ ПОЛЬЗОВАТЕЛЯ:
{user_message}

АНАЛИЗ СОСТОЯНИЯ (State Analyzer):
{state_snapshot_json}

АКТИВНАЯ НИТЬ (null если первый разговор):
{current_thread_json}

АРХИВНЫЕ НИТИ (последние 3):
{archived_threads_json}

Обнови ThreadState и верни валидный JSON.
"""
```

---

## 6. Реализация thread_manager.py

```python
# multiagent/agents/thread_manager.py

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from typing import Optional

from openai import AsyncOpenAI

from ..contracts.state_snapshot import StateSnapshot
from ..contracts.thread_state import ThreadState, ArchivedThread
from .thread_manager_prompts import THREAD_MANAGER_SYSTEM, THREAD_MANAGER_USER_TEMPLATE
from ...config import config

logger = logging.getLogger(__name__)

THREAD_MANAGER_MODEL = "gpt-5-nano"   # env: THREAD_MANAGER_MODEL


class ThreadManagerAgent:
    """
    Обновляет живую нить разговора на основе State Snapshot.
    Возвращает обновлённый ThreadState с полными инструкциями для Writer-а.
    """

    def __init__(self, client: Optional[AsyncOpenAI] = None):
        self._client = client or AsyncOpenAI(api_key=config.openai_api_key)
        self._model = getattr(config, "thread_manager_model", THREAD_MANAGER_MODEL)

    async def update(
        self,
        user_message: str,
        state_snapshot: StateSnapshot,
        current_thread: Optional[ThreadState],
        archived_threads: Optional[list[ArchivedThread]] = None,
    ) -> ThreadState:
        """
        Основной метод. Принимает контекст, возвращает обновлённый ThreadState.
        При ошибке LLM возвращает безопасный fallback ThreadState.
        """
        archived = archived_threads or []

        user_prompt = THREAD_MANAGER_USER_TEMPLATE.format(
            user_message=user_message,
            state_snapshot_json=json.dumps(
                state_snapshot.__dict__, ensure_ascii=False, indent=2
            ),
            current_thread_json=(
                json.dumps(current_thread.to_dict(), ensure_ascii=False, indent=2)
                if current_thread else "null"
            ),
            archived_threads_json=json.dumps(
                [a.__dict__ for a in archived[-3:]], ensure_ascii=False,
                indent=2, default=str
            ),
        )

        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": THREAD_MANAGER_SYSTEM},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,
                max_tokens=800,
            )
            raw = response.choices[0].message.content
            data = json.loads(raw)

            # Если нет thread_id — создаём новый
            if not data.get("thread_id"):
                data["thread_id"] = str(uuid.uuid4())[:8]
            data["user_id"] = current_thread.user_id if current_thread else "unknown"
            data["updated_at"] = datetime.utcnow().isoformat()
            if "created_at" not in data:
                data["created_at"] = (
                    current_thread.created_at.isoformat()
                    if current_thread
                    else datetime.utcnow().isoformat()
                )

            thread = ThreadState.from_dict(data)
            logger.info(
                f"[TM] updated thread={thread.thread_id} "
                f"phase={thread.phase} mode={thread.response_mode} "
                f"relation={thread.relation_to_thread}"
            )
            return thread

        except Exception as exc:
            logger.error(f"[TM] LLM error: {exc}, returning safe fallback")
            return self._safe_fallback(
                user_id=current_thread.user_id if current_thread else "unknown",
                existing=current_thread,
                safety=state_snapshot.safety_flag,
            )

    @staticmethod
    def _safe_fallback(
        user_id: str,
        existing: Optional[ThreadState],
        safety: bool,
    ) -> ThreadState:
        """Минимально безопасный ThreadState при сбое LLM."""
        now = datetime.utcnow()
        return ThreadState(
            thread_id=existing.thread_id if existing else str(uuid.uuid4())[:8],
            user_id=user_id,
            core_direction=existing.core_direction if existing else "неизвестно",
            phase="stabilize" if safety else (existing.phase if existing else "clarify"),
            open_loops=existing.open_loops if existing else [],
            closed_loops=existing.closed_loops if existing else [],
            nervous_state="hyper" if safety else "window",
            response_mode="safe_override" if safety else "reflect",
            response_goal="создать безопасное поле" if safety else "поддержать",
            must_avoid=["анализ", "практики", "вопросы"] if safety else [],
            safety_active=safety,
            continuity_score=0.5,
            created_at=existing.created_at if existing else now,
            updated_at=now,
        )


thread_manager_agent = ThreadManagerAgent()
```

---

## 7. Реализация thread_storage.py

```python
# multiagent/thread_storage.py

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from .contracts.thread_state import ThreadState, ArchivedThread

logger = logging.getLogger(__name__)

STORAGE_DIR = Path(os.getenv("THREAD_STORAGE_DIR", "data/threads"))


class ThreadStorage:
    """
    Персистентное хранилище ThreadState.
    Текущий бэкенд: JSON-файлы per user_id.
    Будущий бэкенд: PostgreSQL / Redis (интерфейс не меняется).
    """

    def __init__(self, storage_dir: Path = STORAGE_DIR):
        self._dir = storage_dir
        self._dir.mkdir(parents=True, exist_ok=True)

    def _active_path(self, user_id: str) -> Path:
        return self._dir / f"{user_id}_active.json"

    def _archive_path(self, user_id: str) -> Path:
        return self._dir / f"{user_id}_archive.json"

    def load_active(self, user_id: str) -> Optional[ThreadState]:
        path = self._active_path(user_id)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return ThreadState.from_dict(data)
        except Exception as exc:
            logger.error(f"[Storage] load_active error user={user_id}: {exc}")
            return None

    def save_active(self, thread: ThreadState) -> None:
        path = self._active_path(thread.user_id)
        try:
            path.write_text(
                json.dumps(thread.to_dict(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as exc:
            logger.error(f"[Storage] save_active error: {exc}")

    def load_archived(self, user_id: str) -> list[ArchivedThread]:
        path = self._archive_path(user_id)
        if not path.exists():
            return []
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            return [ArchivedThread(**item) for item in raw]
        except Exception as exc:
            logger.error(f"[Storage] load_archived error: {exc}")
            return []

    def archive_thread(
        self,
        thread: ThreadState,
        reason: str = "new_thread",
    ) -> None:
        archived = self.load_archived(thread.user_id)
        archived.append(
            ArchivedThread(
                thread_id=thread.thread_id,
                core_direction=thread.core_direction,
                closed_loops=thread.closed_loops,
                open_loops=thread.open_loops,
                final_phase=thread.phase,
                archived_at=datetime.utcnow(),
                archive_reason=reason,
            )
        )
        path = self._archive_path(thread.user_id)
        path.write_text(
            json.dumps(
                [a.__dict__ for a in archived],
                ensure_ascii=False, indent=2, default=str,
            ),
            encoding="utf-8",
        )


thread_storage = ThreadStorage()
```

---

## 8. Интеграция в Orchestrator

```python
# multiagent/orchestrator.py (фрагмент — место Thread Manager)

async def run(user_message: str, user_id: str) -> dict:

    # 1. Загрузить активную нить и архив
    current_thread = thread_storage.load_active(user_id)
    archived_threads = thread_storage.load_archived(user_id)

    # 2. State Analyzer (nano)
    state_snapshot = await state_analyzer_agent.analyze(
        user_message=user_message,
        previous_thread=current_thread,
    )

    # 3. Thread Manager (nano)  ←── PRD-017
    updated_thread = await thread_manager_agent.update(
        user_message=user_message,
        state_snapshot=state_snapshot,
        current_thread=current_thread,
        archived_threads=archived_threads,
    )

    # 4. Сохранить нить ДО генерации ответа (критично!)
    if updated_thread.relation_to_thread == "new_thread" and current_thread:
        thread_storage.archive_thread(current_thread, reason="new_thread")
    thread_storage.save_active(updated_thread)

    # 5. Memory + Retrieval (без LLM)
    memory_bundle = memory_retrieval_agent.assemble(
        user_id=user_id,
        user_message=user_message,
        thread_state=updated_thread,
    )

    # 6. Writer / NEO (mini)
    writer_contract = WriterContract(
        user_message=user_message,
        thread_state=updated_thread,
        memory_bundle=memory_bundle,
    )
    response_text = await writer_agent.write(writer_contract)

    # 7. Async обновление памяти (не блокирует ответ)
    asyncio.create_task(
        memory_retrieval_agent.update(user_id, user_message, response_text)
    )

    return {
        "status": "ok",
        "answer": response_text,
        "thread_id": updated_thread.thread_id,
        "phase": updated_thread.phase,
        "response_mode": updated_thread.response_mode,
    }
```

---

## 9. Feature Flag интеграция

```python
# bot_agent/feature_flags.py — добавить:

MULTIAGENT_ENABLED: bool = os.getenv("MULTIAGENT_ENABLED", "false").lower() == "true"
THREAD_MANAGER_MODEL: str = os.getenv("THREAD_MANAGER_MODEL", "gpt-5-nano")
THREAD_STORAGE_DIR: str = os.getenv("THREAD_STORAGE_DIR", "data/threads")
```

```python
# bot_agent/answer_adaptive.py — добавить ветку в начале функции:

from .feature_flags import feature_flags

def answer_question_adaptive(query: str, user_id: str = "default", ...) -> Dict:
    if feature_flags.MULTIAGENT_ENABLED:
        import asyncio
        from .multiagent.orchestrator import orchestrator
        return asyncio.run(orchestrator.run(query, user_id))
    # ... существующий код без изменений ...
```

---

## 10. Тесты

### 10.1 test_thread_state_contracts.py

```
TS-01  ThreadState сериализуется в dict без потери данных
TS-02  ThreadState.from_dict(state.to_dict()) == state (round-trip)
TS-03  Все обязательные поля присутствуют при минимальной инициализации
TS-04  phase принимает только допустимые значения (stabilize/clarify/explore/integrate)
TS-05  response_mode принимает только допустимые значения
TS-06  relation_to_thread принимает только допустимые значения
TS-07  continuity_score всегда ∈ [0.0, 1.0]
TS-08  created_at десериализуется как datetime объект
TS-09  updated_at всегда ≥ created_at
TS-10  ThreadState с safety_active=True имеет response_mode="safe_override"
```

### 10.2 test_thread_storage.py

```
ST-01  save_active + load_active возвращает тот же объект (round-trip)
ST-02  load_active для нового user_id возвращает None
ST-03  archive_thread перемещает нить в архив
ST-04  load_archived возвращает список ArchivedThread
ST-05  archive_thread добавляет, а не перезаписывает (накопительно)
ST-06  load_archived возвращает [] если файла нет
ST-07  save_active при ошибке IO логирует ошибку и не бросает исключение
ST-08  STORAGE_DIR создаётся автоматически если не существует
ST-09  Хранилище thread-safe при параллельных записях (concurrent.futures)
ST-10  ArchivedThread содержит все поля оригинального ThreadState
```

### 10.3 test_thread_manager.py

```
TM-01  CONTINUITY — одна тема 5 ходов подряд: relation_to_thread="continue"
TM-02  NEW_THREAD — резкая смена темы: relation_to_thread="new_thread"
TM-03  BRANCH — под-вопрос внутри темы: relation_to_thread="branch", добавлен open_loop
TM-04  RETURN — сообщение о возврате к архивной теме: relation_to_thread="return_to_old"
TM-05  PHASE_STABILIZE_TO_CLARIFY — nervous_state переходит в window: фаза меняется
TM-06  PHASE_NO_CHANGE — continuity_score > 0.85 без явного сигнала: фаза не меняется
TM-07  PHASE_EXPLORE_TO_INTEGRATE — 2+ closed_loops: фаза интеграции
TM-08  CLOSED_LOOP — подтверждённый инсайт добавляется в closed_loops
TM-09  MUST_AVOID_CLOSED — closed_loops включены в must_avoid
TM-10  SAFETY_OVERRIDE — safety_flag=True: response_mode="safe_override", phase="stabilize"
TM-11  SAFETY_MUST_AVOID — safety_flag=True: must_avoid содержит "анализ", "практики"
TM-12  FIRST_MESSAGE — current_thread=None: создаётся новая нить с валидными defaults
TM-13  FALLBACK — при LLM ошибке: возвращается безопасный fallback ThreadState
TM-14  FALLBACK_SAFETY — при LLM ошибке + safety=True: fallback с safe_override
TM-15  RESPONSE_MODE_REGULATE — nervous_state=hyper/hypo: response_mode="regulate"
TM-16  RESPONSE_MODE_VALIDATE — intent=contact: response_mode="validate"
TM-17  RESPONSE_MODE_PRACTICE — phase=explore + intent=solution: response_mode="practice"
TM-18  OK_POSITION_IW — ok_position=I-W-: must_avoid содержит "риторические вопросы"
TM-19  TURNS_IN_PHASE — счётчик turns_in_phase растёт при continue в той же фазе
TM-20  THREAD_ID_PRESERVED — при continue: thread_id не меняется
TM-21  JSON_VALID — ответ TM всегда является валидным JSON
TM-22  CONFIDENCE_RANGE — confidence из StateSnapshot всегда ∈ [0, 1]
TM-23  MODEL_PARAM — TM использует модель из конфига (не хардкод)
TM-24  ASYNC_CALL — thread_manager_agent.update() является корутиной
TM-25  ARCHIVED_LIMIT — TM получает не более 3 последних архивных нитей
```

### 10.4 Интеграционные чеки (CI)

```
CI-01  Все 25 тестов зелёные при MULTIAGENT_ENABLED=False (нет регрессий)
CI-02  thread_manager.py не импортирует ничего из adaptive_runtime/
CI-03  thread_manager.py не импортирует route_resolver.py
CI-04  thread_manager.py не импортирует diagnostics_classifier.py напрямую
CI-05  contracts/ не содержит бизнес-логики (только dataclass/typing)
CI-06  thread_storage.py не зависит от LLM (нет импортов openai)
CI-07  Размер thread_manager.py не превышает 200 строк (SRP)
CI-08  Размер thread_manager_prompts.py не превышает 100 строк
CI-09  MULTIAGENT_ENABLED=True + LLM mock → полный pipeline без исключений
CI-10  Тест на утечку: после 100 вызовов thread_manager_agent.update() нет memory leak
```

---

## 11. Acceptance Criteria (Definition of Done)

Фаза PRD-017 считается завершённой когда:

- [ ] Все файлы из раздела 4 созданы по указанным путям
- [ ] `ThreadState.to_dict()` / `from_dict()` работают без потерь (TS-01, TS-02)
- [ ] `ThreadStorage` сохраняет и загружает нить корректно (ST-01 – ST-04)
- [ ] Все 25 тестов TM зелёные при LLM-мок (gpt-5-nano заменён mock-ом в тестах)
- [ ] Safety override работает безусловно (TM-10, TM-11)
- [ ] Fallback не бросает исключений (TM-13, TM-14)
- [ ] `feature_flags.MULTIAGENT_ENABLED = False` → старый пайплайн без изменений (CI-01)
- [ ] `thread_manager.py` не импортирует ничего из `adaptive_runtime/` (CI-02)
- [ ] Нет прямых зависимостей на `route_resolver` (CI-03)
- [ ] `pytest tests/multiagent/` — 100% pass

---

## 12. Что НЕ входит в PRD-017

Следующие элементы задокументированы в отдельных PRD:

| Что | PRD |
|---|---|
| State Analyzer (производит StateSnapshot) | PRD-016 |
| Memory + Retrieval Agent (MemoryBundle) | PRD-018 |
| Writer Agent / NEO (генерация ответа) | PRD-019 |
| Validator (проверка черновика) | PRD-020 |
| Orchestrator (сборка полного пайплайна) | PRD-021 |
| Архивирование legacy-модулей | PRD-022 |
| Telegram Adapter подключение | PRD-023 |

---

## 13. Риски и митигации

| Риск | Вероятность | Митигация |
|---|---|---|
| LLM возвращает невалидный JSON | Средняя | `response_format=json_object` + fallback в `_safe_fallback()` |
| LLM меняет фазу без сигнала | Средняя | Явная инструкция в промпте + тест TM-06 |
| Safety override игнорируется LLM | Низкая | Post-processing: если `safety_flag=True`, принудительно патчить поля после LLM |
| Потеря ThreadState при сбое I/O | Низкая | Логирование ошибки, graceful degradation (None = новая нить) |
| Гонка при параллельных записях | Низкая | File lock в `ThreadStorage.save_active()` (ST-09) |
| Промпт TM слишком длинный | Средняя | Ограничить archived_threads до 3, max_tokens=800 |

---

*Конец PRD-017 · Thread Manager Agent*
*Следующий документ: PRD-018 · Memory + Retrieval Agent*
