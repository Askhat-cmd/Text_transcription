# PRD-020 · Writer Agent (NEO)
## Мультиагентная система NEO — Эпоха №4

---

**Документ:** PRD-020  
**Агент:** Writer / NEO  
**Версия:** 1.0  
**Статус:** В разработке  
**Автор:** Askhat (соло)  
**Репозиторий:** github.com/Askhat-cmd/Text_transcription  
**Целевая директория:** `bot_psychologist/bot_agent/multiagent/agents/`  
**Дата создания:** 2026-04-25  
**Зависимости:** PRD-017 ✅ · PRD-018 ✅ · PRD-019 ✅  

---

## 1. Контекст и назначение

### 1.1 Что уже сделано

После PRD-017 → PRD-019 пайплайн работает на 75%:

```
User Message
     │
     ▼
[State Analyzer]   ← PRD-018 ✅  гибридный (детерм. + nano LLM)
     │ StateSnapshot
     ▼
[Thread Manager]   ← PRD-017 ✅  полностью детерминированный
     │ ThreadState  (phase, response_mode, must_avoid, open_loops...)
     ▼
[Memory+Retrieval] ← PRD-019 ✅  детерминированный, параллельная сборка
     │ MemoryBundle (conversation_context, user_profile, semantic_hits)
     ▼
[Writer / NEO]     ← PRD-020 (ВЫ ЗДЕСЬ) — ЕДИНСТВЕННЫЙ LLM mini-вызов
     │
     ▼
[Orchestrator → Telegram]
```

Orchestrator сейчас возвращает статический `_build_answer()` — это единственная заглушка.  
Writer заменяет её реальным LLM-ответом.

### 1.2 Что такое Writer Agent

Writer — это NEO. Он:
- Получает полный контекст через `WriterContract` (ThreadState + MemoryBundle + user_message)
- Генерирует один психологически точный ответ
- Использует `gpt-5-mini` (не nano — качество ответа критично)
- Это **единственный агент в пайплайне с творческой задачей**
- Все остальные агенты — анализ, маршрутизация, сборка контекста

### 1.3 Текущий `WriterContract` в репозитории

```python
# contracts/writer_contract.py — уже существует как заглушка
@dataclass
class WriterContract:
    user_message: str
    thread_state: ThreadState
    memory_bundle: MemoryBundle
```

PRD-020 расширяет этот контракт минимально и реализует агента.

### 1.4 Ключевое архитектурное решение

Writer НЕ принимает решений о тоне, фазе или стратегии. Это уже сделал Thread Manager.  
Writer только **исполняет** то что сказал ThreadState:
- `response_mode` → какой стиль ответа
- `response_goal` → чего достичь
- `must_avoid` → что запрещено
- `phase` + `open_loops` → куда направлен разговор

Writer — переводчик между машинным решением и человеческим текстом.

---

## 2. Расширение `WriterContract`

```python
# contracts/writer_contract.py — заменить полностью

from __future__ import annotations
from dataclasses import dataclass, field
from .thread_state import ThreadState
from .memory_bundle import MemoryBundle


@dataclass
class WriterContract:
    user_message: str
    thread_state: ThreadState
    memory_bundle: MemoryBundle

    # Опциональное явное указание языка ответа
    # None = определить автоматически по user_message
    response_language: str | None = None

    def to_prompt_context(self) -> dict:
        """Сериализация для подстановки в промпт."""
        return {
            "user_message": self.user_message,
            "phase": self.thread_state.phase,
            "response_mode": self.thread_state.response_mode,
            "response_goal": self.thread_state.response_goal,
            "must_avoid": self.thread_state.must_avoid,
            "ok_position": self.thread_state.ok_position,
            "openness": self.thread_state.openness,
            "open_loops": self.thread_state.open_loops,
            "closed_loops": self.thread_state.closed_loops,
            "core_direction": self.thread_state.core_direction,
            "nervous_state": self.thread_state.nervous_state,
            "safety_active": self.thread_state.safety_active,
            "conversation_context": self.memory_bundle.conversation_context,
            "user_profile_patterns": self.memory_bundle.user_profile.patterns,
            "user_profile_values": self.memory_bundle.user_profile.values,
            "semantic_hits": [
                h.content for h in self.memory_bundle.semantic_hits[:2]
            ],
            "has_relevant_knowledge": self.memory_bundle.has_relevant_knowledge,
        }
```

---

## 3. Системный промпт NEO

### 3.1 Главный принцип промпта

Промпт NEO НЕ описывает "как быть психологом". Он описывает **как исполнять конкретный response_mode**, потому что стратегия уже выбрана Thread Manager-ом. Промпт — это инструкция исполнителя, не стратега.

### 3.2 writer_agent_prompts.py

```python
# multiagent/agents/writer_agent_prompts.py

WRITER_SYSTEM = """
Ты — NEO, психологический бот-собеседник. Ты работаешь как часть мультиагентной системы.
Стратегия и анализ уже выполнены другими агентами. Твоя задача — написать ОДИН ответ.

РЕЖИМЫ ОТВЕТА (response_mode) и как их исполнять:

reflect — помоги человеку сформулировать суть происходящего
  - Повтори или перефразируй ключевую мысль, добавь немного глубины
  - Один уточняющий вопрос в конце (не риторический)
  - Не интерпретируй, не советуй, не анализируй

validate — дай пространство и признание
  - Подтверди что слышишь: "я слышу тебя", "это звучит тяжело"
  - Не добавляй советов, не переключай тему
  - Максимум 3–4 предложения

explore — расширь перспективу
  - Предложи один угол зрения который человек мог не рассматривать
  - Не навязывай — предложи как возможность: "а что если взглянуть с..."
  - Завершить открытым вопросом

regulate — помоги стабилизировать состояние
  - Простое заземляющее присутствие: "я рядом", "ты не один"
  - Одно простое действие: "сделай медленный вдох"
  - Без анализа, без вопросов, без структуры

practice — дай один конкретный шаг
  - Один реалистичный микрошаг на ближайшие 24 часа
  - Конкретно: что именно, когда, сколько времени
  - Не список — один шаг

safe_override — кризисный режим
  - ТОЛЬКО: присутствие + линия помощи если уместно
  - "Я здесь. Ты не один."
  - Нельзя: анализ, вопросы, советы, практики, структура
  - Если есть риск — мягко упомянуть линию психологической помощи

ЖЁСТКИЕ ПРАВИЛА:
- Отвечать на том языке на котором написал пользователь
- must_avoid — список того что ЗАПРЕЩЕНО включать в ответ
- Длина: 2–5 предложений для validate/regulate/safe_override, 4–8 для остальных
- Никаких нумерованных списков в ответе — только живой текст
- Никогда не начинать с "Я понимаю что..." или "Как специалист..."
- Никакого самораскрытия от лица бота
- Не упоминать что ты ИИ или бот
"""

WRITER_USER_TEMPLATE = """
СООБЩЕНИЕ ПОЛЬЗОВАТЕЛЯ:
{user_message}

РЕЖИМ ОТВЕТА: {response_mode}
ЦЕЛЬ: {response_goal}
ФАЗА РАЗГОВОРА: {phase}
СОСТОЯНИЕ НЕРВНОЙ СИСТЕМЫ: {nervous_state}
OK-ПОЗИЦИЯ: {ok_position}
ОТКРЫТОСТЬ: {openness}
SAFETY АКТИВЕН: {safety_active}

ОТКРЫТЫЕ ПЕТЛИ (что ещё не разрешено):
{open_loops}

НЕЛЬЗЯ ВКЛЮЧАТЬ В ОТВЕТ (must_avoid):
{must_avoid}

КОНТЕКСТ ПРЕДЫДУЩИХ ХОДОВ:
{conversation_context}

ПРОФИЛЬ ПОЛЬЗОВАТЕЛЯ (паттерны/ценности):
Паттерны: {user_profile_patterns}
Ценности: {user_profile_values}

ЗНАНИЯ ИЗ БАЗЫ (если релевантны):
{semantic_hits}

Напиши ответ. Только текст ответа, без кавычек, без пояснений.
"""
```

---

## 4. Реализация writer_agent.py

```python
# multiagent/agents/writer_agent.py

from __future__ import annotations

import logging
from typing import Optional

from ..contracts.writer_contract import WriterContract
from .writer_agent_prompts import WRITER_SYSTEM, WRITER_USER_TEMPLATE
from ...config import config
from ...feature_flags import feature_flags

logger = logging.getLogger(__name__)

WRITER_MODEL_DEFAULT = "gpt-5-mini"

_SAFE_OVERRIDE_FALLBACKS = {
    "ru": "Я здесь. Ты не один. Сделай медленный вдох — я рядом.",
    "en": "I'm here. You're not alone. Take a slow breath — I'm with you.",
}
_DEFAULT_LANG = "ru"


class WriterAgent:
    """
    Генерирует финальный ответ NEO на основе WriterContract.
    Единственный агент в пайплайне с творческой LLM-задачей (gpt-5-mini).
    """

    def __init__(self, client=None, model: Optional[str] = None):
        self._client = client
        self._model = model or feature_flags.value("WRITER_MODEL", WRITER_MODEL_DEFAULT)

    async def write(self, contract: WriterContract) -> str:
        try:
            # safety_override: если LLM недоступен — безопасный хардкод
            if contract.thread_state.safety_active:
                lang = self._detect_language(contract.user_message)
                fallback = _SAFE_OVERRIDE_FALLBACKS.get(lang, _SAFE_OVERRIDE_FALLBACKS[_DEFAULT_LANG])
                try:
                    result = await self._call_llm(contract)
                    return result if result.strip() else fallback
                except Exception:
                    return fallback

            result = await self._call_llm(contract)
            return result if result.strip() else self._static_fallback(contract)

        except Exception as exc:
            logger.error("[WRITER] write failed: %s", exc, exc_info=True)
            return self._static_fallback(contract)

    async def _call_llm(self, contract: WriterContract) -> str:
        client = self._get_client()
        if client is None:
            raise RuntimeError("No LLM client available")

        ctx = contract.to_prompt_context()
        user_prompt = WRITER_USER_TEMPLATE.format(
            user_message=ctx["user_message"],
            response_mode=ctx["response_mode"],
            response_goal=ctx["response_goal"],
            phase=ctx["phase"],
            nervous_state=ctx["nervous_state"],
            ok_position=ctx["ok_position"],
            openness=ctx["openness"],
            safety_active=ctx["safety_active"],
            open_loops=", ".join(ctx["open_loops"]) or "нет",
            must_avoid=", ".join(ctx["must_avoid"]) or "нет",
            conversation_context=ctx["conversation_context"][:2000] or "нет",
            user_profile_patterns=", ".join(ctx["user_profile_patterns"]) or "нет",
            user_profile_values=", ".join(ctx["user_profile_values"]) or "нет",
            semantic_hits=self._format_hits(ctx["semantic_hits"]),
        )

        response = await client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": WRITER_SYSTEM},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
            max_tokens=400,
        )
        return (response.choices[0].message.content or "").strip()

    def _get_client(self):
        if self._client is not None:
            return self._client
        try:
            from openai import AsyncOpenAI
            api_key = getattr(config, "OPENAI_API_KEY", None)
            if not api_key:
                return None
            self._client = AsyncOpenAI(api_key=api_key)
            return self._client
        except Exception:
            return None

    @staticmethod
    def _detect_language(text: str) -> str:
        cyrillic = sum(1 for ch in text if "а" <= ch.lower() <= "я" or ch.lower() == "ё")
        return "ru" if cyrillic > len(text) * 0.2 else "en"

    @staticmethod
    def _format_hits(hits: list[str]) -> str:
        if not hits:
            return "нет релевантных знаний"
        return "\n---\n".join(f"• {h[:300]}" for h in hits[:2])

    @staticmethod
    def _static_fallback(contract: WriterContract) -> str:
        mode = contract.thread_state.response_mode
        if mode == "safe_override":
            return "Я здесь. Ты не один."
        if mode == "validate":
            return "Я слышу тебя. Расскажи больше если хочешь."
        if mode == "regulate":
            return "Сделай медленный вдох. Я рядом."
        return "Я слышу тебя."


writer_agent = WriterAgent()
```

---

## 5. Обновление Orchestrator

```python
# multiagent/orchestrator.py — финальная версия

from .agents.state_analyzer import state_analyzer_agent
from .agents.thread_manager import thread_manager_agent
from .agents.memory_retrieval import memory_retrieval_agent
from .agents.writer_agent import writer_agent          # ← новый импорт
from .contracts.writer_contract import WriterContract  # ← новый импорт
from .thread_storage import thread_storage

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

    # 3. Сохранить нить
    if updated_thread.relation_to_thread == "new_thread" and current_thread is not None:
        thread_storage.archive_thread(current_thread, reason="new_thread")
    thread_storage.save_active(updated_thread)

    # 4. Memory + Retrieval
    memory_bundle = await memory_retrieval_agent.assemble(
        user_message=query,
        thread_state=updated_thread,
        user_id=user_id,
    )

    # 5. Writer / NEO  ← PRD-020 (заменяет _build_answer)
    writer_contract = WriterContract(
        user_message=query,
        thread_state=updated_thread,
        memory_bundle=memory_bundle,
    )
    answer = await writer_agent.write(writer_contract)

    # 6. Async update памяти (scaffold)
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

## 6. Обновление `agents/__init__.py`

```python
from .state_analyzer import state_analyzer_agent
from .thread_manager import thread_manager_agent
from .memory_retrieval import memory_retrieval_agent
from .writer_agent import writer_agent

__all__ = [
    "state_analyzer_agent",
    "thread_manager_agent",
    "memory_retrieval_agent",
    "writer_agent",
]
```

---

## 7. Обновление `feature_flags.py`

```python
# bot_agent/feature_flags.py — добавить:

WRITER_MODEL: str = os.getenv("WRITER_MODEL", "gpt-5-mini")
WRITER_MAX_TOKENS: int = int(os.getenv("WRITER_MAX_TOKENS", "400"))
WRITER_TEMPERATURE: float = float(os.getenv("WRITER_TEMPERATURE", "0.7"))
```

---

## 8. Структура файлов

```
bot_psychologist/
└── bot_agent/
    └── multiagent/
        ├── agents/
        │   ├── __init__.py                    ← добавить writer_agent
        │   ├── state_analyzer.py              ← не трогать ✅
        │   ├── thread_manager.py              ← не трогать ✅
        │   ├── memory_retrieval.py            ← не трогать ✅
        │   ├── writer_agent.py                ← ОСНОВНОЙ ФАЙЛ PRD-020  [новый]
        │   └── writer_agent_prompts.py        ← промпты Writer изолированно [новый]
        ├── orchestrator.py                    ← заменить _build_answer на writer_agent
        └── contracts/
            └── writer_contract.py             ← расширить to_prompt_context()

tests/
└── multiagent/
    ├── fixtures/
    │   └── writer_agent_fixtures.json         ← [новый]
    └── test_writer_agent.py                   ← [новый]
```

---

## 9. Fixtures для тестов

```json
[
  {
    "id": "WA-F01",
    "response_mode": "validate",
    "safety_active": false,
    "must_avoid": [],
    "llm_mock_response": "Я слышу тебя. Это звучит непросто.",
    "expected_non_empty": true
  },
  {
    "id": "WA-F02",
    "response_mode": "safe_override",
    "safety_active": true,
    "must_avoid": ["анализ", "практики"],
    "llm_mock_response": "Я здесь рядом. Ты не один.",
    "expected_non_empty": true
  },
  {
    "id": "WA-F03",
    "response_mode": "safe_override",
    "safety_active": true,
    "must_avoid": [],
    "llm_mock_response": "",
    "expected_fallback": true,
    "expected_contains": ["здесь", "один"]
  },
  {
    "id": "WA-F04",
    "response_mode": "practice",
    "safety_active": false,
    "must_avoid": [],
    "llm_mock_response": "Попробуй завтра утром написать три вещи за которые благодарен.",
    "expected_non_empty": true
  },
  {
    "id": "WA-F05",
    "response_mode": "regulate",
    "safety_active": false,
    "llm_throws": true,
    "expected_fallback": true,
    "expected_contains": ["вдох", "рядом"]
  }
]
```

---

## 10. Тесты

### 10.1 test_writer_agent.py — полный список

```
WA-01  WRITE_RETURNS_STRING — write() всегда возвращает непустую строку
WA-02  WRITE_NON_EMPTY_MOCK — при LLM-мок с текстом: возвращает текст мока
WA-03  SAFETY_FALLBACK_EMPTY_LLM — safety_active=True + LLM вернул "": hardcoded fallback
WA-04  SAFETY_FALLBACK_LLM_ERROR — safety_active=True + LLM ошибка: hardcoded fallback
WA-05  SAFETY_FALLBACK_RU — русский текст → fallback на русском
WA-06  SAFETY_FALLBACK_EN — английский текст → fallback на английском
WA-07  STATIC_FALLBACK_VALIDATE — LLM ошибка + mode=validate: статический текст
WA-08  STATIC_FALLBACK_REGULATE — LLM ошибка + mode=regulate: текст про вдох
WA-09  STATIC_FALLBACK_SAFE — LLM ошибка + mode=safe_override: "Я здесь"
WA-10  WRITER_CONTRACT_FIELDS — WriterContract содержит все обязательные поля
WA-11  TO_PROMPT_CONTEXT_KEYS — to_prompt_context() содержит все нужные ключи
WA-12  MUST_AVOID_IN_PROMPT — must_avoid передаётся в промпт (в user_prompt)
WA-13  OPEN_LOOPS_IN_PROMPT — open_loops передаются в промпт
WA-14  CONV_CONTEXT_TRUNCATED — conversation_context > 2000 символов: обрезается до 2000
WA-15  SEMANTIC_HITS_LIMIT — максимум 2 чанка передаётся в промпт
WA-16  MODEL_FROM_CONFIG — используется модель из feature_flags, не хардкод
WA-17  TEMPERATURE_07 — temperature=0.7 передаётся в LLM-вызов
WA-18  MAX_TOKENS_400 — max_tokens=400 передаётся в LLM-вызов
WA-19  ASYNC_METHOD — writer_agent.write() является корутиной
WA-20  NO_CLIENT_FALLBACK — при отсутствии API-ключа: статический fallback без краша
WA-21  DETECT_LANG_RU — кириллица > 20%: язык = ru
WA-22  DETECT_LANG_EN — нет кириллицы: язык = en
WA-23  ORCHESTRATOR_CALLS_WRITER — orchestrator.run() вызывает writer_agent.write()
WA-24  ORCHESTRATOR_ANSWER_IN_RESULT — поле "answer" в результате orchestrator.run()
WA-25  ORCHESTRATOR_NO_BUILD_ANSWER — статический _build_answer больше не в orchestrator
WA-26  FIXTURE_F01 — validate mode: LLM-мок возвращает текст
WA-27  FIXTURE_F02 — safe_override + LLM текст: возвращается LLM текст
WA-28  FIXTURE_F03 — safe_override + пустой LLM: fallback с "один"
WA-29  FIXTURE_F04 — practice mode: LLM-мок возвращает текст
WA-30  FIXTURE_F05 — regulate + LLM ошибка: fallback с "вдох"
```

### 10.2 Регрессионные чеки

```
REG-01  pytest tests/multiagent/ — все тесты PRD-017/018/019 зелёные
REG-02  writer_agent.py не содержит логики маршрутизации (нет if phase == ...)
REG-03  writer_agent_prompts.py содержит оба шаблона: WRITER_SYSTEM, WRITER_USER_TEMPLATE
REG-04  contracts/memory_bundle.py не изменён
REG-05  contracts/thread_state.py не изменён
REG-06  contracts/state_snapshot.py не изменён
REG-07  MULTIAGENT_ENABLED=False → классический path без изменений
```

---

## 11. Acceptance Criteria (Definition of Done)

PRD-020 завершён когда:

- [ ] `agents/writer_agent.py` создан
- [ ] `agents/writer_agent_prompts.py` создан с `WRITER_SYSTEM` и `WRITER_USER_TEMPLATE`
- [ ] `contracts/writer_contract.py` расширен методом `to_prompt_context()`
- [ ] `agents/__init__.py` экспортирует `writer_agent`
- [ ] `orchestrator.py` вызывает `writer_agent.write(writer_contract)`, `_build_answer` удалён
- [ ] Все 30 тестов WA зелёные при LLM-мок
- [ ] Все тесты PRD-017/018/019 зелёные (REG-01)
- [ ] Safety fallback работает без LLM (WA-03, WA-04)
- [ ] `pytest tests/multiagent/ -q` → 100% pass (все 105+ тестов)

---

## 12. Что НЕ входит в PRD-020

| Что | PRD |
|---|---|
| Запись ответа в conversation_memory | PRD-022 |
| Validator (проверка черновика Writer-а) | PRD-021 |
| Полный E2E тест с реальным LLM | PRD-022 |
| Архивирование legacy | PRD-023 |
| Telegram Adapter | PRD-024 |

---

## 13. Важные замечания для IDE-агента

1. **Writer не принимает решений о стратегии.** Всё уже в ThreadState. Промпт говорит "как писать", не "о чём думать".
2. **Safety override — два уровня защиты:** (а) LLM получает промпт с safe_override инструкцией; (б) если LLM вернул пустую строку или упал — хардкодный fallback. Обязательно оба.
3. **`_build_answer()` в orchestrator — удалить.** Заменить на `writer_agent.write(writer_contract)`. Метод больше не нужен.
4. **В тестах** — мокать `_call_llm()` или `client.chat.completions.create` через `unittest.mock.AsyncMock`. Не делать реальных LLM-вызовов.
5. **Temperature 0.7** — Writer генерирует живой текст, не структуру. Не снижать до 0.1.
6. **`contracts/writer_contract.py`** — расширить через добавление `to_prompt_context()`. Не ломать существующие поля.

---

*Конец PRD-020 · Writer Agent (NEO)*  
*Следующий документ: PRD-021 · Validator (пишется после реализации PRD-020)*
