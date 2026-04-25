# PRD-018 · State Analyzer Agent
## Мультиагентная система NEO — Эпоха №4

---

**Документ:** PRD-018  
**Агент:** State Analyzer  
**Версия:** 1.0  
**Статус:** В разработке  
**Автор:** Askhat (соло)  
**Репозиторий:** github.com/Askhat-cmd/Text_transcription  
**Целевая директория:** `bot_psychologist/bot_agent/multiagent/agents/`  
**Дата создания:** 2026-04-25  
**Зависимость:** PRD-017 (реализован ✅)  

---

## 1. Контекст и назначение

### 1.1 Что уже сделано (PRD-017)

После реализации PRD-017 в репозитории существует:

```
multiagent/
├── __init__.py
├── orchestrator.py                  ← минимальная заглушка
├── thread_storage.py                ← полная реализация
├── contracts/
│   ├── __init__.py
│   ├── state_snapshot.py            ← StateSnapshot dataclass (уже есть!)
│   ├── thread_state.py              ← ThreadState + ArchivedThread (уже есть!)
│   ├── memory_bundle.py             ← заглушка
│   └── writer_contract.py           ← заглушка
└── agents/
    ├── __init__.py
    ├── thread_manager.py            ← полная детерминированная реализация
    └── thread_manager_prompts.py    ← scaffold промптов
```

**Ключевое наблюдение:** `thread_manager.py` реализован как **полностью детерминированный агент** без LLM — через регулярки, токен-пересечения и правила. Это сильное архитектурное решение: Thread Manager не тратит токены, работает мгновенно, предсказуемо. PRD-018 должен следовать той же философии там, где это возможно.

### 1.2 Что такое State Analyzer

State Analyzer — **первый агент** в цепочке Orchestrator-а. Он получает сырое сообщение пользователя и текущий ThreadState, и возвращает `StateSnapshot` — структурированный анализ состояния человека в этом конкретном ходу.

`StateSnapshot` уже определён в `contracts/state_snapshot.py`. State Analyzer — это агент, который **заполняет** этот контракт.

### 1.3 Место в пайплайне

```
User Message
     │
     ▼
[Orchestrator]
     │
     ├──► [State Analyzer]      ← PRD-018 (ВЫ ЗДЕСЬ)
     │         │ StateSnapshot
     │         ▼
     ├──► [Thread Manager]      ← PRD-017 ✅ (принимает StateSnapshot)
     │         │ ThreadState
     │         ▼
     ├──► [Memory+Retrieval]    ← PRD-019
     │
     └──► [Writer / NEO]        ← PRD-020
```

### 1.4 Что в текущем коде уже решает похожую задачу

| Существующий модуль | Что делает | Отношение к State Analyzer |
|---|---|---|
| `state_classifier.py` (21kb) | Классифицирует состояние через LLM, возвращает `StateAnalysis` | Основной донор логики — SA поглощает его функцию |
| `diagnostics_classifier.py` (13kb) | Классифицирует `nervous_system_state`, `request_function`, `interaction_mode` через LLM | Логика nervous_state и intent переходит в SA |
| `fast_detector.py` (7kb) | Быстрые детерминированные проверки (кризис, приветствие) | Логика safety_flag и fast-path переходит в SA |
| `semantic_analyzer.py` (10kb) | Семантический анализ текста | Вспомогательная утилита, SA может использовать |
| `contradiction_detector.py` (2kb) | Обнаружение противоречий | Опционально включается через SA |

**Вывод:** State Analyzer НЕ создаётся с нуля — он интегрирует существующую логику в чистый контракт.

---

## 2. Анализ существующего `StateSnapshot`

Смотрим что уже определено в `contracts/state_snapshot.py`:

```python
# Уже существует в репозитории
@dataclass(frozen=True)
class StateSnapshot:
    nervous_state: str       # window / hyper / hypo
    intent: str              # clarify / vent / explore / contact / solution
    openness: str            # open / mixed / defensive / collapsed
    ok_position: str         # I+W+ / I-W+ / I+W- / I-W-
    safety_flag: bool        # True = кризис/риск
    confidence: float        # 0.0–1.0
```

**Этот контракт уже используется Thread Manager.** Нельзя менять поля без синхронизации с `thread_manager.py`. Все поля обязательны.

---

## 3. Стратегия реализации: гибридный агент

Изучив как Thread Manager сделан детерминированно, принимаю аналогичное решение для State Analyzer: **гибридный подход**.

**Уровень 1 — Детерминированные правила (быстро, бесплатно):**
- `safety_flag`: ключевые слова кризиса → мгновенное срабатывание
- `nervous_state = hyper`: паника/тревога ключевые слова → без LLM
- `intent = contact`: "просто хочу поговорить", "не нужно советов" → без LLM
- Приветствия и /start команды → специальная обработка

**Уровень 2 — LLM (gpt-5-nano, только если детерминированный уровень не дал достаточной уверенности):**
- Сложные случаи: openness, ok_position, неоднозначный intent
- Когда `fast_confidence < 0.75` — передать в LLM с уже собранными сигналами

Это экономит токены и ускоряет ответ на простых случаях. Примерно 40–50% запросов могут быть обработаны детерминированно.

---

## 4. Функциональные требования

### 4.1 Входящий контракт

```python
async def analyze(
    user_message: str,
    previous_thread: Optional[ThreadState] = None,  # контекст предыдущего хода
) -> StateSnapshot
```

### 4.2 Логика определения полей

**`safety_flag`** (детерминированный, приоритетный):

Немедленно `True` если сообщение содержит:
- Слова кризиса: "суицид", "убить себя", "не хочу жить", "всё кончено",
  "suicide", "kill myself", "end it all", "hurt myself"
- Слова острого дистресса: "не могу больше", "срываюсь", "паника атака"
- Уточнение: проверка регистронезависимая, с учётом частичных совпадений

Если `safety_flag = True` → остальные поля задаются безопасными дефолтами,
LLM НЕ вызывается.

**`nervous_state`** (детерминированный + LLM fallback):

| Сигнал | Значение |
|---|---|
| Слова тревоги: "паника", "тревога", "не могу успокоиться", "сердце бьётся" | `hyper` |
| Слова апатии: "ничего не чувствую", "пустота", "всё равно", "не могу встать" | `hypo` |
| Восклицательные знаки 3+, CAPS 30%+ текста | `hyper` |
| Очень короткие ответы (< 8 слов), отстранённость | `hypo` |
| Нет явных сигналов | `window` (LLM подтверждает) |

**`intent`** (детерминированный + LLM):

| Сигнал | Значение |
|---|---|
| "как мне", "что делать", "помоги решить", "что посоветуешь" | `solution` |
| "просто хочу поговорить", "не надо советов", "хочу чтобы выслушали" | `contact` |
| "я злюсь", "я боюсь", "это несправедливо" (эмоц. выражение) | `vent` |
| "почему я", "как понять", "хочу разобраться" | `clarify` |
| "а что если", "интересно", "расскажи" | `explore` |

**`openness`** (преимущественно LLM):

Детерминировано только крайние случаи:
- "нет смысла", "всё равно не поможет", "я уже пробовал" → `defensive`
- "да, понимаю", "точно так" → `open`
- Иначе → LLM

**`ok_position`** (LLM):

Транзактный анализ — всегда через LLM. Детерминированные правила только как подсказка:
- "я ужасный человек" + "другие лучше знают" → I-W+
- "я справлюсь сам" + "все остальные не понимают" → I+W-
- "никто не поможет" + "я безнадёжен" → I-W-

**`confidence`**:

Финальный score рассчитывается как:
```
confidence = mean([
    safety_confidence,
    nervous_confidence,
    intent_confidence,
    openness_confidence,
    ok_position_confidence,
])
```
Где каждый подскор: 1.0 если детерминировано, 0.75–0.95 если LLM.

### 4.3 Обработка граничных случаев

| Случай | Поведение |
|---|---|
| Пустое сообщение ("", " ") | Вернуть дефолтный snapshot: window/explore/open/I+W+/False/0.5 |
| Команда /start | Вернуть onboarding snapshot: window/contact/open/I+W+/False/0.9 |
| Только эмодзи | Детерминированный анализ по эмодзи-словарю, confidence=0.6 |
| Очень длинное сообщение (>1000 символов) | Truncate до 1000 перед LLM, логировать |
| LLM ошибка/timeout | Вернуть безопасный дефолт с confidence=0.5, safety_flag=False |

---

## 5. Структура файлов

```
bot_psychologist/
└── bot_agent/
    └── multiagent/
        ├── agents/
        │   ├── __init__.py                          ← добавить экспорт state_analyzer_agent
        │   ├── thread_manager.py                    ← не трогать ✅
        │   ├── thread_manager_prompts.py            ← не трогать ✅
        │   ├── state_analyzer.py                    ← ОСНОВНОЙ ФАЙЛ PRD-018  [новый]
        │   └── state_analyzer_prompts.py            ← промпты SA изолированно [новый]
        └── contracts/
            └── state_snapshot.py                    ← НЕ ТРОГАТЬ (уже используется TM)

tests/
└── multiagent/
    ├── fixtures/
    │   └── state_analyzer_fixtures.json             ← синтетические сообщения [новый]
    └── test_state_analyzer.py                       ← тесты SA [новый]
```

**Правило:** `state_snapshot.py` не модифицируется. Если нужны новые поля — обсудить
отдельно, так как изменение сломает Thread Manager.

---

## 6. Промпты State Analyzer

### 6.1 state_analyzer_prompts.py

```python
STATE_ANALYZER_SYSTEM = """
Ты — State Analyzer психологического бота NEO.
Твоя задача: проанализировать одно сообщение пользователя и вернуть
структурированную оценку его психологического состояния.

Верни ТОЛЬКО валидный JSON. Без пояснений, без markdown.

ПОЛЯ ДЛЯ ЗАПОЛНЕНИЯ:

nervous_state: состояние нервной системы
  - "window": человек относительно спокоен, может думать и воспринимать
  - "hyper": тревога, возбуждение, паника, нервозность
  - "hypo": апатия, пустота, заторможенность, нет сил

intent: что хочет человек от этого обращения
  - "clarify": хочет разобраться, понять что происходит
  - "vent": хочет выразить эмоции, быть услышанным
  - "explore": хочет исследовать тему, нет конкретного запроса
  - "contact": хочет просто присутствия, не нуждается в советах
  - "solution": хочет конкретный шаг, практику, ответ

openness: насколько открыт к диалогу и новым идеям
  - "open": готов воспринимать, отвечает развёрнуто
  - "mixed": частично открыт, есть сомнения
  - "defensive": сопротивляется, обесценивает, "всё равно не поможет"
  - "collapsed": нет ресурса, минимальные ответы, апатия

ok_position: позиция из транзактного анализа
  - "I+W+": я ок и мир ок (здоровая позиция)
  - "I-W+": я не ок, но другие лучше (самокритика, недооценка себя)
  - "I+W-": я ок, другие не ок (недоверие, отчуждение)
  - "I-W-": я не ок и мир не ок (отчаяние, безнадёжность)

confidence: твоя уверенность в оценке (0.0–1.0)

ВАЖНО:
- Если сообщение короткое или неоднозначное — снижай confidence до 0.6–0.7
- Не придумывай то чего нет в тексте
- При сомнении между I-W+ и I+W+ выбирай I+W+
- Никогда не ставь safety_flag=true (это обрабатывается до тебя)
"""

STATE_ANALYZER_USER_TEMPLATE = """
СООБЩЕНИЕ ПОЛЬЗОВАТЕЛЯ:
{user_message}

КОНТЕКСТ ПРЕДЫДУЩЕГО ХОДА (если есть):
{previous_context}

Верни JSON строго по схеме:
{{
  "nervous_state": "window"|"hyper"|"hypo",
  "intent": "clarify"|"vent"|"explore"|"contact"|"solution",
  "openness": "open"|"mixed"|"defensive"|"collapsed",
  "ok_position": "I+W+"|"I-W+"|"I+W-"|"I-W-",
  "confidence": 0.0-1.0
}}
"""
```

---

## 7. Реализация state_analyzer.py

```python
# multiagent/agents/state_analyzer.py

from __future__ import annotations

import json
import logging
import re
from typing import Optional

from openai import AsyncOpenAI

from ..contracts.state_snapshot import StateSnapshot
from ..contracts.thread_state import ThreadState
from .state_analyzer_prompts import (
    STATE_ANALYZER_SYSTEM,
    STATE_ANALYZER_USER_TEMPLATE,
)
from ...config import config

logger = logging.getLogger(__name__)

STATE_ANALYZER_MODEL = "gpt-5-nano"

# ── Детерминированные словари ──────────────────────────────────────────

_SAFETY_KEYWORDS = frozenset([
    "суицид", "убить себя", "убью себя", "не хочу жить",
    "всё кончено", "всё бесполезно хочу умереть",
    "suicide", "kill myself", "end it all", "hurt myself",
    "не могу больше терпеть", "лучше бы меня не было",
])

_HYPER_KEYWORDS = frozenset([
    "паника", "паническая", "тревога", "тревожно", "не могу успокоиться",
    "сердце бьётся", "задыхаюсь", "срываюсь", "всё рушится",
    "panic", "anxiety", "can't calm", "freaking out",
])

_HYPO_KEYWORDS = frozenset([
    "ничего не чувствую", "пустота", "всё равно", "нет сил",
    "не могу встать", "апатия", "нет смысла", "безразличие",
    "numbness", "emptiness", "don't care", "no energy",
])

_CONTACT_PHRASES = frozenset([
    "просто хочу поговорить", "не надо советов", "хочу чтобы выслушали",
    "просто выслушай", "не нужно советов", "just want to talk",
    "no advice", "just listen",
])

_SOLUTION_PHRASES = frozenset([
    "как мне", "что делать", "помоги решить", "что посоветуешь",
    "дай совет", "как справиться с", "what should i do",
    "how do i", "help me fix",
])

_VENT_SIGNALS = frozenset([
    "я злюсь", "бесит", "это несправедливо", "ненавижу",
    "так обидно", "не могу простить", "i'm angry", "it's unfair",
])

_DEFENSIVE_SIGNALS = frozenset([
    "всё равно не поможет", "уже пробовал", "ничего не изменится",
    "бесполезно", "это не работает", "won't help", "already tried",
])


def _contains_any(text: str, keywords: frozenset) -> bool:
    lower = text.lower()
    return any(kw in lower for kw in keywords)


def _detect_safety(message: str) -> bool:
    return _contains_any(message, _SAFETY_KEYWORDS)


def _detect_nervous_state(message: str) -> tuple[str, float]:
    if _contains_any(message, _HYPER_KEYWORDS):
        return "hyper", 0.92
    if _contains_any(message, _HYPO_KEYWORDS):
        return "hypo", 0.88
    caps_ratio = sum(1 for c in message if c.isupper()) / max(len(message), 1)
    exclamations = message.count("!")
    if caps_ratio > 0.3 or exclamations >= 3:
        return "hyper", 0.80
    words = message.split()
    if len(words) < 5 and not message.endswith("?"):
        return "hypo", 0.65
    return "window", 0.70   # неопределённо — отправить в LLM


def _detect_intent(message: str) -> tuple[Optional[str], float]:
    if _contains_any(message, _CONTACT_PHRASES):
        return "contact", 0.93
    if _contains_any(message, _SOLUTION_PHRASES):
        return "solution", 0.88
    if _contains_any(message, _VENT_SIGNALS):
        return "vent", 0.85
    return None, 0.0   # неопределённо — отправить в LLM


def _detect_openness(message: str) -> tuple[Optional[str], float]:
    if _contains_any(message, _DEFENSIVE_SIGNALS):
        return "defensive", 0.85
    return None, 0.0


def _is_start_command(message: str) -> bool:
    return message.strip() in {"/start", "start", "начать", "привет", "hello"}


def _is_empty(message: str) -> bool:
    return not message.strip()


class StateAnalyzerAgent:
    """
    Анализирует сообщение пользователя и возвращает StateSnapshot.
    Гибридный подход: детерминированные правила + LLM для неоднозначных случаев.
    """

    def __init__(self, client: Optional[AsyncOpenAI] = None):
        self._client = client or AsyncOpenAI(api_key=config.openai_api_key)
        self._model = getattr(config, "state_analyzer_model", STATE_ANALYZER_MODEL)

    async def analyze(
        self,
        user_message: str,
        previous_thread: Optional[ThreadState] = None,
    ) -> StateSnapshot:
        try:
            # Граничные случаи
            if _is_empty(user_message):
                return self._default_snapshot()

            if _is_start_command(user_message):
                return self._onboarding_snapshot()

            # Уровень 1: Safety (безусловный приоритет)
            if _detect_safety(user_message):
                return StateSnapshot(
                    nervous_state="hyper",
                    intent="contact",
                    openness="collapsed",
                    ok_position="I-W-",
                    safety_flag=True,
                    confidence=0.99,
                )

            # Уровень 1: Детерминированный анализ
            nervous_state, nervous_conf = _detect_nervous_state(user_message)
            intent, intent_conf = _detect_intent(user_message)
            openness, openness_conf = _detect_openness(user_message)

            fast_confidence = (
                nervous_conf
                + (intent_conf if intent else 0.0)
                + (openness_conf if openness else 0.0)
            ) / 3

            # Уровень 2: LLM если быстрый уровень недостаточно уверен
            if fast_confidence < 0.75 or intent is None or openness is None:
                return await self._analyze_with_llm(
                    user_message=user_message,
                    previous_thread=previous_thread,
                    fast_nervous_state=nervous_state,
                    fast_intent=intent,
                    fast_openness=openness,
                )

            # Полностью детерминированный результат (редкий, но возможный случай)
            return StateSnapshot(
                nervous_state=nervous_state,
                intent=intent or "explore",
                openness=openness or "open",
                ok_position="I+W+",   # без LLM ok_position всегда дефолт
                safety_flag=False,
                confidence=round(fast_confidence, 3),
            )

        except Exception as exc:
            logger.error("[STATE_ANALYZER] analyze failed: %s", exc, exc_info=True)
            return self._default_snapshot()

    async def _analyze_with_llm(
        self,
        user_message: str,
        previous_thread: Optional[ThreadState],
        fast_nervous_state: str,
        fast_intent: Optional[str],
        fast_openness: Optional[str],
    ) -> StateSnapshot:
        previous_context = "нет" if previous_thread is None else (
            f"Тема нити: {previous_thread.core_direction}
"
            f"Фаза: {previous_thread.phase}
"
            f"Открытые петли: {previous_thread.open_loops}"
        )

        # Передаём детерминированные сигналы как подсказки в промпт
        hint = ""
        if fast_nervous_state != "window":
            hint += f"
Подсказка от детерминированного анализа: nervous_state скорее всего '{fast_nervous_state}'."
        if fast_intent:
            hint += f" intent скорее всего '{fast_intent}'."
        if fast_openness:
            hint += f" openness скорее всего '{fast_openness}'."

        user_prompt = STATE_ANALYZER_USER_TEMPLATE.format(
            user_message=user_message[:1000],
            previous_context=previous_context + hint,
        )

        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": STATE_ANALYZER_SYSTEM},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.1,
                max_tokens=200,
            )
            raw = response.choices[0].message.content
            data = json.loads(raw)

            return StateSnapshot(
                nervous_state=data.get("nervous_state", "window"),
                intent=data.get("intent", "explore"),
                openness=data.get("openness", "open"),
                ok_position=data.get("ok_position", "I+W+"),
                safety_flag=False,   # safety всегда из детерминированного уровня
                confidence=float(data.get("confidence", 0.75)),
            )

        except Exception as exc:
            logger.error("[STATE_ANALYZER] LLM call failed: %s", exc)
            return StateSnapshot(
                nervous_state=fast_nervous_state,
                intent=fast_intent or "explore",
                openness=fast_openness or "open",
                ok_position="I+W+",
                safety_flag=False,
                confidence=0.55,
            )

    @staticmethod
    def _default_snapshot() -> StateSnapshot:
        return StateSnapshot(
            nervous_state="window",
            intent="explore",
            openness="open",
            ok_position="I+W+",
            safety_flag=False,
            confidence=0.5,
        )

    @staticmethod
    def _onboarding_snapshot() -> StateSnapshot:
        return StateSnapshot(
            nervous_state="window",
            intent="contact",
            openness="open",
            ok_position="I+W+",
            safety_flag=False,
            confidence=0.9,
        )


state_analyzer_agent = StateAnalyzerAgent()
```

---

## 8. Обновление Orchestrator

`orchestrator.py` сейчас содержит заглушку. Добавить вызов State Analyzer:

```python
# multiagent/orchestrator.py — обновить метод run()

from .agents.state_analyzer import state_analyzer_agent
from .agents.thread_manager import thread_manager_agent
from .thread_storage import thread_storage

async def run(user_message: str, user_id: str) -> dict:

    # 1. Загрузить активную нить и архив
    current_thread = thread_storage.load_active(user_id)
    archived_threads = thread_storage.load_archived(user_id)

    # 2. State Analyzer  ←── PRD-018
    state_snapshot = await state_analyzer_agent.analyze(
        user_message=user_message,
        previous_thread=current_thread,
    )

    # 3. Thread Manager (уже реализован)
    updated_thread = await thread_manager_agent.update(
        user_message=user_message,
        state_snapshot=state_snapshot,
        user_id=user_id,
        current_thread=current_thread,
        archived_threads=archived_threads,
    )

    # 4. Сохранить ПЕРЕД генерацией ответа
    if updated_thread.relation_to_thread == "new_thread" and current_thread:
        thread_storage.archive_thread(current_thread, reason="new_thread")
    thread_storage.save_active(updated_thread)

    # 5–7: Memory + Writer + Validator (PRD-019, PRD-020)
    # Пока возвращаем заглушку
    return {
        "status": "ok",
        "answer": "[Writer not yet implemented]",
        "thread_id": updated_thread.thread_id,
        "phase": updated_thread.phase,
        "response_mode": updated_thread.response_mode,
        "debug": {
            "nervous_state": state_snapshot.nervous_state,
            "intent": state_snapshot.intent,
            "safety_flag": state_snapshot.safety_flag,
            "confidence": state_snapshot.confidence,
        },
    }
```

---

## 9. Обновление `agents/__init__.py`

```python
# multiagent/agents/__init__.py — добавить:

from .state_analyzer import state_analyzer_agent
from .thread_manager import thread_manager_agent

__all__ = [
    "state_analyzer_agent",
    "thread_manager_agent",
]
```

---

## 10. Обновление `feature_flags.py`

```python
# bot_agent/feature_flags.py — добавить:

STATE_ANALYZER_MODEL: str = os.getenv("STATE_ANALYZER_MODEL", "gpt-5-nano")
```

---

## 11. Fixtures для тестов

Файл `tests/multiagent/fixtures/state_analyzer_fixtures.json`:

```json
[
  {
    "id": "SA-F01",
    "message": "не могу больше, хочу умереть",
    "expected": {"safety_flag": true, "response_mode_override": "safe_override"}
  },
  {
    "id": "SA-F02",
    "message": "паника, не могу успокоиться, сердце бьётся",
    "expected": {"nervous_state": "hyper", "safety_flag": false}
  },
  {
    "id": "SA-F03",
    "message": "всё равно ничего не чувствую, просто пустота",
    "expected": {"nervous_state": "hypo", "safety_flag": false}
  },
  {
    "id": "SA-F04",
    "message": "просто хочу поговорить, не надо советов",
    "expected": {"intent": "contact", "safety_flag": false}
  },
  {
    "id": "SA-F05",
    "message": "что мне делать с этой ситуацией? дай совет",
    "expected": {"intent": "solution"}
  },
  {
    "id": "SA-F06",
    "message": "я так злюсь на него, это несправедливо!",
    "expected": {"intent": "vent", "nervous_state": "hyper"}
  },
  {
    "id": "SA-F07",
    "message": "всё равно не поможет, я уже всё пробовал",
    "expected": {"openness": "defensive"}
  },
  {
    "id": "SA-F08",
    "message": "/start",
    "expected": {"intent": "contact", "nervous_state": "window", "confidence": 0.9}
  },
  {
    "id": "SA-F09",
    "message": "",
    "expected": {"nervous_state": "window", "confidence": 0.5}
  },
  {
    "id": "SA-F10",
    "message": "хочу разобраться почему я так реагирую",
    "expected": {"intent": "clarify", "nervous_state": "window"}
  }
]
```

---

## 12. Тесты

### 12.1 test_state_analyzer.py — полный список

```
SA-01  SAFETY_RU — русские слова кризиса: safety_flag=True
SA-02  SAFETY_EN — английские слова кризиса: safety_flag=True
SA-03  SAFETY_OVERRIDE_MODE — при safety_flag=True: response_mode не зависит от TM
SA-04  SAFETY_NO_LLM — при safety_flag=True LLM НЕ вызывается (mock проверяет 0 вызовов)
SA-05  HYPER_KEYWORDS — слова тревоги: nervous_state="hyper"
SA-06  HYPO_KEYWORDS — слова апатии: nervous_state="hypo"
SA-07  CAPS_HYPER — 30%+ CAPS: nervous_state="hyper"
SA-08  SHORT_HYPO — < 5 слов без вопроса: nervous_state="hypo" или "window"
SA-09  CONTACT_INTENT — "просто хочу поговорить": intent="contact"
SA-10  SOLUTION_INTENT — "что мне делать": intent="solution"
SA-11  VENT_INTENT — "я злюсь": intent="vent"
SA-12  DEFENSIVE_OPENNESS — "всё равно не поможет": openness="defensive"
SA-13  START_COMMAND — "/start": onboarding_snapshot, confidence=0.9
SA-14  EMPTY_MESSAGE — "": default_snapshot, confidence=0.5
SA-15  LLM_CALLED_WHEN_AMBIGUOUS — неоднозначное сообщение: LLM вызывается
SA-16  LLM_NOT_CALLED_WHEN_CERTAIN — явные сигналы: LLM НЕ вызывается
SA-17  LLM_FALLBACK — LLM ошибка: возвращается snapshot с confidence≤0.6
SA-18  CONFIDENCE_RANGE — confidence всегда ∈ [0.0, 1.0]
SA-19  ALL_FIELDS_PRESENT — все поля StateSnapshot всегда присутствуют
SA-20  VALID_NERVOUS_VALUES — nervous_state всегда одно из {window,hyper,hypo}
SA-21  VALID_INTENT_VALUES — intent всегда одно из 5 допустимых значений
SA-22  VALID_OPENNESS_VALUES — openness всегда одно из 4 допустимых значений
SA-23  VALID_OK_POSITION — ok_position всегда одно из 4 допустимых значений
SA-24  PREVIOUS_THREAD_CONTEXT — передача previous_thread влияет на промпт
SA-25  LONG_MESSAGE_TRUNCATED — сообщение > 1000 символов: truncate до 1000
SA-26  ASYNC_METHOD — state_analyzer_agent.analyze() является корутиной
SA-27  SINGLETON_EXPORT — state_analyzer_agent импортируется из agents/__init__.py
SA-28  MODEL_FROM_CONFIG — используется модель из config, не хардкод
SA-29  FIXTURES_PASS — все 10 fixtures из state_analyzer_fixtures.json проходят
SA-30  INTEGRATION_WITH_TM — StateSnapshot из SA корректно принимается thread_manager_agent.update()
```

### 12.2 Регрессионные чеки

```
REG-01  pytest tests/multiagent/ — все тесты PRD-017 остаются зелёными
REG-02  pytest tests/test_feature_flags.py — флаги не нарушены
REG-03  MULTIAGENT_ENABLED=False → классический path без изменений
REG-04  state_analyzer.py не импортирует из adaptive_runtime/
REG-05  state_analyzer.py не импортирует route_resolver.py
REG-06  contracts/state_snapshot.py не изменён (проверить sha)
```

---

## 13. Acceptance Criteria (Definition of Done)

PRD-018 завершён когда:

- [ ] Созданы файлы: `agents/state_analyzer.py`, `agents/state_analyzer_prompts.py`
- [ ] Создан `tests/multiagent/fixtures/state_analyzer_fixtures.json` (10 fixtures)
- [ ] Создан `tests/multiagent/test_state_analyzer.py` (30 тестов)
- [ ] `state_snapshot.py` не изменён
- [ ] Все 30 тестов SA зелёные при LLM-мок
- [ ] Все тесты PRD-017 остаются зелёными (REG-01)
- [ ] Safety flag срабатывает детерминированно без LLM (SA-04)
- [ ] `orchestrator.py` обновлён с реальным вызовом State Analyzer
- [ ] `agents/__init__.py` экспортирует `state_analyzer_agent`
- [ ] `pytest tests/multiagent/ -q` — 100% pass (все тесты PRD-017 + PRD-018)

---

## 14. Что НЕ входит в PRD-018

| Что | PRD |
|---|---|
| Memory + Retrieval Agent | PRD-019 |
| Writer Agent / NEO | PRD-020 |
| Validator | PRD-021 |
| Полный Orchestrator | PRD-022 |
| Архивирование legacy | PRD-023 |
| Telegram Adapter | PRD-024 |

---

## 15. Важные замечания для IDE-агента

1. **`state_snapshot.py` — не трогать.** Thread Manager уже на него завязан.
2. **`thread_manager.py` — не трогать.** Он реализован хорошо и не требует изменений.
3. **Safety флаг — детерминированный, без LLM, без исключений.** Это критично для безопасности пользователей.
4. **Гибридный подход:** сначала быстрые правила, LLM только при неуверенности. Не переделывать в "только LLM" — это ухудшит скорость и предсказуемость.
5. **Модель:** `gpt-5-nano` через config, не хардкод.
6. **Все тесты через mock LLM** — не делать реальных вызовов в тестах.

---

*Конец PRD-018 · State Analyzer Agent*  
*Следующий документ: PRD-019 · Memory + Retrieval Agent (пишется после реализации PRD-018)*
