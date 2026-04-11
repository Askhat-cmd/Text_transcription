# PRD-009: Устранение обрезки ответов бота — двойной источник
**Статус:** DRAFT  
**Приоритет:** КРИТИЧЕСКИЙ (P0)  
**Версия:** 1.0  
**Дата:** 2026-04-11  
**Автор анализа:** на основе bot.log, retrieval.log, Polotno-LLM, Chat-5.txt  

---

## 1. Контекст и постановка задачи

Пользователи наблюдают, что ответы бота в веб-чате значительно короче, чем полный
текст, генерируемый LLM (видимый в Полотне отладки). Проведено прямое сравнение
текста в Полотне ЛЛМ и текста, попавшего в веб-чат. Вывод однозначен:

> **LLM генерирует полный ответ. Обрезка происходит в pipeline ДО или ПОСЛЕ LLM,
> независимо от самой LLM.**

Обнаружены **два независимых механизма** обрезки, работающих одновременно.
Оба подтверждены доказательно — логами, текстом чата и дампом промпта из Полотна ЛЛМ.

---

## 2. Root Cause Analysis (RCA)

### BUG-A: Mojibake в полях промпта (кодировка UTF-8 / Windows-1252)

**Источник:** `Polotno-LLM-posledego-soobshcheniia-4.txt` (дамп промпта turn=9)  
**Severity:** P0 — критический, с непредсказуемым проявлением  

В дампе промпта зафиксированы нечитаемые поля:

```
РЕКОМЕНДАЦИЯ ПО ОТВЕТУ:
Р Р°Р·РІРёРІР°Р№ РёРЅС‚РµСЂРµСЃ...

КОНТЕКСТ ИЗ ПРОШЛЫХ СЕССИЙ:
РР· РїСЂРµРґС‹РґСѓС‰РёС… СЃРµСЃСЃРёР№:
- СЃРѕСЃС‚РѕСЏРЅРёРµ: overwhelmed
```

Это классический **mojibake**: UTF-8 кириллица, прочитанная как Latin-1/CP1252.

**Механизм:**
- Поля `РЕКОМЕНДАЦИЯ ПО ОТВЕТУ` и `КОНТЕКСТ ИЗ ПРОШЛЫХ СЕССИЙ` хранятся в
  SQLite или Redis в корректной UTF-8 кодировке
- При чтении и подстановке в строку промпта происходит неявная конвертация
  через платформенную кодировку (CP1252 на Windows)
- LLM получает нечитаемый мусор вместо инструкций по объёму ответа и
  контексту прошлых сессий
- Без этих инструкций — LLM генерирует минимально допустимый ответ
- Проблема **случайная**: зависит от того, есть ли эти поля в конкретном тёрне;
  на turn=0 (нет истории) — не проявляется

**Вероятное место бага:**  
`answer_adaptive.py` или `prompt_builder.py` — функция сборки строки промпта.  
Конкретно: чтение из БД или из файлов шаблонов без явного `encoding="utf-8"`.

---

### BUG-B: Маршруты `contact_hold`, `regulate`, `contact` — нет anti-brevity директив

**Источник:** `bot.log` (строки ROUTING + TASK_INSTRUCTION), `Chat-5.txt`  
**Severity:** P0 — системный, воспроизводится стабильно  

**Прямое сравнение из Chat-5.txt:**

| Вопрос пользователя | Маршрут | Символов в ответе |
|---|---|---|
| «Что ты можешь посоветовать?» | contact / regulate | 145 ✂️ |
| «Это повторяется уже третий раз» | contact | 145 ✂️ |
| «У меня тревога перед важной встречей» | regulate | 194 ✂️ |
| «Объясни мне что такое быть самим собой» | reflect | 858 ✅ |
| «Объясни мне что такое самореализация» | reflect | 646 ✅ |
| «Объясни мне что такое Здесь и Сейчас» | reflect | 636 ✅ |

**Причина диспропорции:**  
Маршрут `reflect` имеет в `TASK_INSTRUCTION` явные директивы:
```
- Избегай смысловой скупости.
- Не своди ответ к формату «одна мысль + один вопрос».
- Сначала кратко обозначь концепт, затем свяжи его с ситуацией пользователя.
- Добавь практический угол и мягкий вопрос-мост.
```

Маршруты `contact_hold`, `contact`, `regulate`, `stabilize` — этих директив **не имеют**.
LLM правомерно интерпретирует отсутствие требований к объёму как разрешение
написать 1–2 предложения.

**Историческая справка:**  
До внедрения NEO система использовала SD-классификацию с явными фильтрами минимальной
длины ответа на каждый маршрут. В NEO эти фильтры были заменены на TASK_INSTRUCTION
директивы — но директивы добавили только для маршрута `reflect`, забыв про остальные.
Это объясняет, почему чат «прекрасно работал» до NEO.

---

## 3. Scope изменений

| Файл | Тип изменения |
|---|---|
| `bot_agent/prompt_builder.py` | Fix кодировки при чтении данных из БД и файлов |
| `bot_agent/answer_adaptive.py` | Verify encoding при сборке контекста сессии |
| Шаблоны `TASK_INSTRUCTION` / `route_config.py` | Добавить anti-brevity блок для маршрутов contact/regulate/stabilize |
| `tests/test_encoding.py` | Новый файл — тесты кодировки |
| `tests/test_response_length.py` | Новый файл — тесты минимальной длины ответов |
| `tests/test_output_completeness.py` | Новый файл — тест совпадения stream и debug payload |

---

## 4. Технические требования

### 4.1 Fix-A — Устранение Mojibake (P0, ~40 мин)

**Место:** `prompt_builder.py` и/или `answer_adaptive.py`

**Требование:**  
Все поля, читаемые из SQLite или Redis и подставляемые в промпт, должны явно
декодироваться как UTF-8. Никакой неявной конвертации строк через платформенную кодировку.

```python
# БЫЛО (некорректно — платформенная кодировка CP1252 на Windows):
context_str = db.get("diag_context")

# СТАЛО (корректно):
raw = db.get("diag_context")
context_str = raw.decode("utf-8") if isinstance(raw, bytes) else raw
```

**Дополнительно:** Все вызовы `open()` для шаблонных файлов `.txt` / `.md` — обязателен
явный `encoding="utf-8"`:

```python
# БЫЛО:
with open("templates/diag_algorithm.txt") as f:   # платформенная кодировка

# СТАЛО:
with open("templates/diag_algorithm.txt", encoding="utf-8") as f:
```

**Критерий выполнения:**  
В Полотне ЛЛМ поля `РЕКОМЕНДАЦИЯ ПО ОТВЕТУ` и `КОНТЕКСТ ИЗ ПРОШЛЫХ СЕССИЙ`
отображаются читаемым русским текстом без мусорных символов.

---

### 4.2 Fix-B — Anti-brevity директивы для маршрутов contact/regulate (P0, ~30 мин)

**Место:** генерация `TASK_INSTRUCTION` в `route_config.py` или `prompt_builder.py`

**Требование:** Для маршрутов `contact_hold`, `contact`, `regulate`, `stabilize`
добавить следующий блок в `TASK_INSTRUCTION`:

```
ТРЕБОВАНИЯ К ОБЪЁМУ:
- Минимальный ответ: 3 содержательных предложения.
- Не сводить ответ к одному наблюдению + вопросу.
- После признания состояния пользователя — дать практическое наблюдение
  или связь с предыдущим контекстом диалога.
- Запрещено: ответ из 1–2 коротких предложений без развёртки.
- Максимальный ответ для contact-маршрутов: 600 символов (без перегрузки).
```

**Критерий выполнения:**  
Ответы на «У меня тревога», «Что посоветуешь?», «Это повторяется»
содержат ≥ 3 предложения и ≥ 250 символов.

---

## 5. Тест-план

### TEST-A1: Mojibake — визуальная проверка промпта

**Тип:** ручной  
**Предусловие:** Сессия с историей ≥ 3 тёрна

**Шаги:**
1. Открыть сессию с историей (≥ 3 тёрна)
2. Отправить любой вопрос
3. Открыть Полотно ЛЛМ → секция `РЕКОМЕНДАЦИЯ ПО ОТВЕТУ`

**Ожидаемый результат (после фикса):**
```
РЕКОМЕНДАЦИЯ ПО ОТВЕТУ:
Развивай интерес пользователя к теме...
```

**Текущий (баг):**
```
Р Р°Р·РІРёРІР°Р№ РёРЅС‚РµСЂРµСЃ...
```

---

### TEST-A2: Mojibake — автотест кодировки

**Тип:** автоматический  
**Файл:** `tests/test_encoding.py`

```python
import pytest
from bot_agent.prompt_builder import build_prompt


def test_prompt_no_mojibake():
    """Промпт не должен содержать mojibake-последовательности."""
    prompt = build_prompt(
        query="тест",
        session_context={"recommendation": "Развивай интерес"},
        past_sessions=[{"state": "overwhelmed"}, {"state": "curious"}]
    )
    # Mojibake паттерны: латинские буквы Р, С перед кириллицей
    assert "РёРЅС‚" not in prompt, "Найден mojibake в промпте"
    assert "РїСЂРµ" not in prompt, "Найден mojibake в промпте"
    assert "Р°Р·"  not in prompt, "Найден mojibake в промпте"


def test_past_sessions_readable():
    """Контекст прошлых сессий должен читаться как кириллица или ASCII."""
    from bot_agent.conversation_memory import load_past_context
    ctx = load_past_context(user_id="test_user")
    if ctx:
        is_cyrillic = any(0x0400 <= ord(c) <= 0x04FF for c in ctx)
        is_ascii    = ctx.isascii()
        assert is_cyrillic or is_ascii, (
            "Контекст не содержит ни кириллицы ни ASCII — вероятно mojibake"
        )


def test_template_files_utf8():
    """Все шаблонные файлы должны открываться без ошибок в UTF-8."""
    import os, glob
    templates = glob.glob("bot_agent/templates/**/*.txt", recursive=True)
    templates += glob.glob("bot_agent/templates/**/*.md", recursive=True)
    for path in templates:
        try:
            with open(path, encoding="utf-8") as f:
                f.read()
        except UnicodeDecodeError as e:
            pytest.fail(f"Файл {path} содержит не-UTF-8 данные: {e}")
```

---

### TEST-B1: Anti-brevity — минимальная длина ответов (автотест)

**Тип:** автоматический  
**Файл:** `tests/test_response_length.py`

```python
import pytest
from bot_agent.answer_adaptive import get_adaptive_response

SHORT_QUERIES = [
    "У меня тревога перед важной встречей.",
    "Это повторяется уже третий раз.",
    "Что ты можешь посоветовать?",
    "Мне плохо.",
    "Я не знаю что делать.",
]


@pytest.mark.parametrize("query", SHORT_QUERIES)
def test_contact_regulate_min_length(query, test_session_with_history):
    """Ответы на коротких маршрутах должны быть >= 250 символов."""
    response = get_adaptive_response(
        user_id=test_session_with_history,
        query=query
    )
    assert len(response["answer"]) >= 250, (
        f"Ответ слишком короткий ({len(response['answer'])} символов) "
        f"для запроса: '{query}'"
    )


@pytest.mark.parametrize("query", SHORT_QUERIES)
def test_contact_regulate_min_sentences(query, test_session_with_history):
    """Ответ должен содержать минимум 3 предложения."""
    response = get_adaptive_response(
        user_id=test_session_with_history,
        query=query
    )
    text = response["answer"].replace("!", ".").replace("?", ".")
    sentences = [s.strip() for s in text.split(".") if s.strip()]
    assert len(sentences) >= 3, (
        f"Ответ содержит только {len(sentences)} предложений для: '{query}'"
    )
```

---

### TEST-B2: Паритет маршрутов — соотношение длин

**Тип:** автоматический  
**Файл:** `tests/test_response_length.py` (продолжение)

```python
def test_reflect_vs_contact_parity(test_session_with_history):
    """
    Разрыв в длине ответов между маршрутами reflect и contact
    не должен превышать 3x.
    """
    reflect_response = get_adaptive_response(
        user_id=test_session_with_history,
        query="Объясни мне что такое тревога"
    )
    contact_response = get_adaptive_response(
        user_id=test_session_with_history,
        query="У меня тревога"
    )

    ratio = len(reflect_response["answer"]) / max(len(contact_response["answer"]), 1)
    assert ratio <= 3.0, (
        f"Ответ reflect в {ratio:.1f}x длиннее contact — "
        f"слишком большое расхождение (reflect={len(reflect_response['answer'])}, "
        f"contact={len(contact_response['answer'])})"
    )
```

---

### TEST-C: Регрессия — стриминговый ответ совпадает с полным (автотест)

**Тип:** автоматический (интеграционный)  
**Файл:** `tests/test_output_completeness.py`

```python
import httpx
import pytest


def test_streamed_answer_matches_full_answer(test_session):
    """
    Текст, полученный через adaptive-stream SSE,
    должен совпадать с полным ответом из debug/llm-payload.
    """
    # Шаг 1: отправить вопрос через stream
    streamed_chunks = []
    with httpx.stream(
        "POST",
        "http://localhost:8000/api/v1/questions/adaptive-stream",
        json={"query": "Объясни мне что такое тревога", "user_id": test_session},
        timeout=60
    ) as r:
        for line in r.iter_lines():
            if line.startswith("data:"):
                chunk = line[5:].strip()
                if chunk and chunk != "[DONE]":
                    streamed_chunks.append(chunk)

    streamed_text = "".join(streamed_chunks)

    # Шаг 2: получить полный ответ из debug payload
    payload_resp = httpx.get(
        f"http://localhost:8000/api/debug/session/{test_session}/llm-payload"
    )
    full_text = payload_resp.json().get("last_answer", "")

    # Сравниваем (допуск: пробелы)
    assert streamed_text.strip() == full_text.strip(), (
        f"Стриминговый ответ ОБРЕЗАН!\n"
        f"Stream:  {len(streamed_text)} символов\n"
        f"Full:    {len(full_text)} символов\n"
        f"Разница: {len(full_text) - len(streamed_text)} символов"
    )
```

---

## 6. Критерии приёмки (Definition of Done)

- [ ] **TEST-A1** — Полотно ЛЛМ показывает `РЕКОМЕНДАЦИЯ ПО ОТВЕТУ` без mojibake
- [ ] **TEST-A2** — `test_prompt_no_mojibake` → PASS
- [ ] **TEST-A2** — `test_past_sessions_readable` → PASS
- [ ] **TEST-A2** — `test_template_files_utf8` → PASS
- [ ] **TEST-B1** — Все 5 коротких запросов дают ответ ≥ 250 символов
- [ ] **TEST-B1** — Все 5 коротких запросов дают ≥ 3 предложения
- [ ] **TEST-B2** — Соотношение длин reflect/contact ≤ 3.0x
- [ ] **TEST-C**  — Стриминговый ответ совпадает с full debug payload
- [ ] **Ручная** — «У меня тревога» → ответ ≥ 250 символов в веб-чате
- [ ] **Ручная** — Полотно ЛЛМ, тёрн с историей → кириллица читаемая во всех полях

---

## 7. Что НЕ входит в этот PRD

- Изменение логики маршрутизации (какой маршрут присваивается)
- Изменение модели LLM или её параметров токенов
- Исправление SSE done-event (отдельный PRD-007)
- Увеличение top_k retrieval (отдельная задача)
- Изменение warmup-контекста на turn=0

---

## 8. Риски и митигация

| Риск | Вероятность | Митигация |
|---|---|---|
| Fix кодировки сломает другие поля промпта | Средняя | Покрыть тестами ВСЕ поля промпта через TEST-A2 |
| Anti-brevity сделает contact-ответы слишком длинными | Низкая | Добавить максимум 600 символов для contact-маршрутов |
| Mojibake только на Windows (не на Linux prod) | Высокая | Проверить prod-окружение, добавить `encoding="utf-8"` везде явно |
| TEST-C ненадёжен при нестабильном SSE | Средняя | Добавить retry-логику (3 попытки) в тест |

---

## 9. Связанные задачи

| ID | Описание | Статус |
|---|---|---|
| PRD-007 | SSE done-event перезаписывает буфер | Выполнен (верификация) |
| PRD-008 | Усечение через route rules | Предыдущий черновик, заменён этим PRD |
