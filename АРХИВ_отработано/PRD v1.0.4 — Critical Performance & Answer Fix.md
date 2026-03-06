

***

## Реальная картина из логов

### Что теперь работает ✅

```
08:57:17 | ✅ Состояние определено: curious (уверенность: 0.90)  ← PRD v1.0.3 сработал
08:57:23 | ✅ SD уровень: BLUE (conf=0.32, method=llm)            ← PRD v1.0.3 сработал
```

Классификаторы больше не возвращают fallback — LLM даёт реальные ответы.[^1]

### Что сломано ❌ — 4 новых бага

**БАГ-01 [BLOCKER]: Главный текст ответа пуст в UI**

На обоих скриншотах видно: бот показывает только path-блок + "Хотите узнать что-то ещё по этой теме?" — без текста ответа. Retrieval работает, 3 блока прошли в LLM, `status=200`, но сам текстовый ответ в UI отсутствует.[^2][^3][^1]

**БАГ-02 [BLOCKER]: Первый запрос занимает 81 секунду → таймаут на фронте 60s**

```
08:57:02 — POST start
08:57:07 — Data loading done (5s, cold)
08:57:17 — state_classifier done (10s)
08:57:23 — sd_classifier done (6s)
08:57:32 — TF-IDF retrieval done (9s, cold build)
           ← ПРОПАСТЬ 31 секунда (необъяснима!)
08:58:03 — Voyage reranking (1s)
08:58:23 — response ready = 81.07s
```

Фронтенд таймаутит через 60s → `Ошибка: timeout of 60000ms exceeded`. Второй запрос: 28s (всё прогрето).[^3][^1]

**БАГ-03 [HIGH]: Классификаторы работают 10-24 секунды каждый запрос**

`state_classifier` с `gpt-5-mini` занимает **10-14 секунд** на каждый запрос вместо 1-2 секунд с `gpt-4o-mini`. `sd_classifier` — ещё **6-10 секунд**. Итого 16-24 секунды только на классификацию до retrieval.[^1]

**БАГ-04 [MEDIUM]: SD confidence всегда ниже порога → все теги-блоки удаляются**

```
SD уровень: BLUE (conf=0.32) → conservative fallback: BLUE→RED
SD_FILTER: 5 → 0 filtered (все 5 блоков tagged=GREEN/YELLOW, не подходят)
Fallback: добавлено 3 untagged blocks
```

Персонализация не работает — SD-фильтр выкидывает все подходящие блоки.[^4]

***

# PRD v1.0.4 — Critical Performance \& Answer Fix

**Репозиторий:** `Askhat-cmd/Text_transcription`
**Версия:** 1.0.4
**Дата:** 2026-03-03
**Статус:** `READY FOR AGENT`
**Приоритет:** `BLOCKER`
**Зависимость:** PRD v1.0.3 выполнен (commit `482b797`)

***

## Цели (Goals)

- **G-1:** Бот генерирует и отображает полный текстовый ответ (не только path-блок)
- **G-2:** Первый запрос укладывается в 60-секундный таймаут фронтенда
- **G-3:** Классификаторы не тратят 10-14 секунд на каждый вызов
- **G-4:** Обратная совместимость с `gpt-4o-mini` сохранена


## Не-цели (Non-Goals)

- Не изменять алгоритм SD-фильтрации (отдельный PRD)
- Не переписывать `llm_answerer.py` — только диагностировать причину пустого ответа
- Не трогать `response_format` из PRD v1.0.3

***

## Технические изменения

### Изменение 1: `llm_answerer.py` — ДИАГНОСТИКА + защита от пустого ответа

**Файл:** `bot_psychologist/bot_agent/llm_answerer.py`

Агент должен:

1. Найти место где `response.choices[^0].message.content` извлекается из ответа gpt-5-mini
2. Добавить явный debug-лог с длиной ответа ДО возврата
3. Добавить защиту на пустой `content` аналогично PRD v1.0.2
```python
# Найти строку похожую на:
content = response.choices[^0].message.content

# СТАЛО — добавить логирование и защиту:
content = (response.choices[^0].message.content or "").strip()
logger.debug(f"[LLM_ANSWERER] raw content length={len(content)} model={self.model}")

if not content:
    logger.warning(f"[LLM_ANSWERER] ⚠️ gpt-5-mini вернул пустой ответ, проверь max_completion_tokens и reasoning")
    # Вернуть минимальный fallback вместо пустой строки
    content = "Расскажите подробнее о своём вопросе — я готов помочь разобраться."
```

**Важно:** агент должен СНАЧАЛА прочитать файл, найти точное место, и только потом вносить изменение.

***

### Изменение 2: `config.py` — Разделение моделей: CLASSIFIER vs MAIN

**Файл:** `bot_psychologist/bot_agent/config.py`

Добавить новую переменную окружения `CLASSIFIER_MODEL` для использования быстрой модели в классификаторах:

```python
# В классе Config найти где определяется LLM_MODEL и добавить РЯДОМ:

LLM_MODEL: str = os.getenv("PRIMARY_MODEL", "gpt-4o-mini")
# НОВОЕ: отдельная лёгкая модель для быстрых классификаций (state + SD)
# По умолчанию берёт ту же модель, но можно переопределить в .env
CLASSIFIER_MODEL: str = os.getenv("CLASSIFIER_MODEL", "gpt-4o-mini")
```

**Логика:** `LLM_MODEL=gpt-5-mini` используется только для основного ответа. `CLASSIFIER_MODEL=gpt-4o-mini` — для классификаторов. Если `CLASSIFIER_MODEL` не задан в `.env`, берётся `gpt-4o-mini` (быстрый и дешёвый). Пользователь может задать `.env`:

```
PRIMARY_MODEL=gpt-5-mini
CLASSIFIER_MODEL=gpt-4o-mini
```


***

### Изменение 3: `state_classifier.py` — Использовать `CLASSIFIER_MODEL`

**Файл:** `bot_psychologist/bot_agent/state_classifier.py`

Найти инициализацию модели в `StateClassifier.__init__` или `_classify_by_llm`:

```python
# БЫЛО (использует основную LLM_MODEL — gpt-5-mini):
"model": config.LLM_MODEL,

# СТАЛО (использует быструю CLASSIFIER_MODEL — gpt-4o-mini):
"model": config.CLASSIFIER_MODEL,
```

И обновить параметр токенов:

```python
token_param = config.get_token_param_name(config.CLASSIFIER_MODEL)
```


***

### Изменение 4: `sd_classifier.py` — Использовать `CLASSIFIER_MODEL`

**Файл:** `bot_psychologist/bot_agent/sd_classifier.py`

В `SDClassifier.__init__`:

```python
# БЫЛО:
self.model = model or config.LLM_MODEL or str(_SD_SETTINGS.get("model", "gpt-4o-mini"))

# СТАЛО:
self.model = model or config.CLASSIFIER_MODEL or str(_SD_SETTINGS.get("model", "gpt-4o-mini"))
```


***

### Изменение 5: Frontend — Увеличить таймаут запроса

**Файл:** найти в директории `frontend/` или `web/` файл где задаётся timeout HTTP-запроса к API (скорее всего `axios` конфиг или `fetch` с `timeout`).

Найти строку вида:

```javascript
timeout: 60000  // или 60_000 или "60s"
```

Изменить:

```javascript
// БЫЛО:
timeout: 60000

// СТАЛО:
timeout: 120000   // 2 минуты — достаточно для gpt-5-mini холодного старта
```

**Если frontend не в этом репозитории**, агент должен сообщить путь к файлу где нужно это изменить.

***

## Порядок выполнения

```
Шаг 1 → Прочитать llm_answerer.py, найти точное место извлечения content
Шаг 2 → llm_answerer.py: добавить лог + fallback на пустой content
Шаг 3 → config.py: добавить CLASSIFIER_MODEL переменную
Шаг 4 → state_classifier.py: заменить LLM_MODEL → CLASSIFIER_MODEL
Шаг 5 → sd_classifier.py: заменить LLM_MODEL → CLASSIFIER_MODEL
Шаг 6 → Frontend: найти timeout и увеличить до 120000
Шаг 7 → Один коммит со всеми изменениями
```


***

## Acceptance Criteria

### Тест 1: Главный текст ответа присутствует

```
# Должно быть (в логах):
DEBUG | llm_answerer | [LLM_ANSWERER] raw content length=450 model=gpt-5-mini

# UI: над блоком "Источники" должен быть параграф текста длиннее 50 символов
```


### Тест 2: Классификаторы работают быстро

```
# Должно быть:
INFO | state_classifier | ✅ Состояние определено: curious (уверенность: 0.90)
# Время вызова: < 3 секунд (gpt-4o-mini быстрее gpt-5-mini в 5-10 раз)

# Не должно быть:
# 14 секунд ожидания до получения состояния
```


### Тест 3: Первый запрос не таймаутит

```
# Не должно быть в UI:
"Ошибка: timeout of 60000ms exceeded"

# Должно быть: ответ пусть за 80-90 секунд, но без ошибки
```


### Тест 4: Логи показывают CLASSIFIER_MODEL

```
INFO | bot_agent.state_classifier | model=gpt-4o-mini  ← быстрый классификатор
INFO | bot_agent.llm_answerer     | модель: gpt-5-mini ← основной LLM
```


***

## Ограничения для агента

- **Не изменять** промпты классификаторов
- **Не изменять** логику `response_format` из PRD v1.0.3
- **Не трогать** retrieval pipeline, voyage reranker, stage filter
- **Прочитать файлы перед редактированием** — особенно `llm_answerer.py`, точное место неизвестно
- Если `CLASSIFIER_MODEL` уже существует в `config.py` — не дублировать, только обновить

