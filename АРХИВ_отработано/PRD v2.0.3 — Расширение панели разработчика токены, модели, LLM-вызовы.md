
# PRD v2.0.3 — Расширение панели разработчика: токены, модели, LLM-вызовы

**Проект:** bot_psychologist / bot_agent + web_ui  
**Версия:** 2.0.3  
**Дата:** 2026-03-03  
**Статус:** Ready for implementation  
**Приоритет:** Medium  

---

## 1. КОНТЕКСТ И ЦЕЛЬ

### 1.1 Текущее состояние
`InlineDebugTrace` отображает роутинг, чанки и память. Однако ряд
ценных данных уже существует в `api.types.ts` (`LLMCallTrace`,
`total_duration_ms`, `DebugTrace.llm_calls`), но не рендерится.
Данные о токенах, стоимости и моделях пайплайна отсутствуют вовсе.

### 1.2 Цель
Добавить в панель разработчика три новых блока:
1. **LLM Calls** — по каждому вызову: шаг, модель, токены, время
2. **Модели пайплайна** — какие модели задействованы в ответе
3. **Токены и стоимость** — за сообщение и нарастающий итог сессии

---

## 2. SCOPE ИЗМЕНЕНИЙ

### 2.1 Бэкенд — файлы для изменения

| Файл | Тип изменения |
|------|--------------|
| `bot_agent/api/models.py` (или аналог с Pydantic-схемами) | Добавить поля в `InlineTrace` |
| `bot_agent/response/response_generator.py` | Собирать `llm_calls` при генерации |
| `bot_agent/llm_answerer.py` | Возвращать `tokens_used`, `duration_ms`, `model` |
| `bot_agent/api/router.py` (или `main.py`) | Добавить поля в формирование `trace` |

### 2.2 Фронтенд — файлы для изменения

| Файл | Тип изменения |
|------|--------------|
| `web_ui/src/types/chat.types.ts` | Добавить поля в `InlineTrace` |
| `web_ui/src/components/chat/InlineDebugTrace.tsx` | Добавить 3 новых секции |

### 2.3 Файлы НЕ трогать
- `config.py` — не менять
- `response_formatter.py` — не менять
- `state_classifier.py` / `sd_classifier.py` — не менять
- `Message.tsx`, `MessageList.tsx`, `ChatWindow.tsx` — не менять
- Все страницы (`ChatPage`, `ProfilePage`, `SettingsPage`) — не менять

---

## 3. ДЕТАЛЬНЫЕ ТРЕБОВАНИЯ

---

### 3.1 БЭКЕНД: расширить `InlineTrace` / `DebugTrace`

#### 3.1.1 Найти Pydantic-модель `InlineTrace` на бэкенде
(может называться `InlineTrace`, `TraceData`, `BotTrace` — искать
в `api/models.py`, `api/schemas.py` или `bot_agent/models.py`)

Добавить в неё следующие поля:

```python
# === LLM Calls ===
llm_calls: list[LLMCallInfo] = Field(default_factory=list)

# === Models used ===
primary_model: str | None = None
classifier_model: str | None = None
embedding_model: str | None = None
reranker_model: str | None = None
reranker_enabled: bool = False

# === Tokens per message ===
tokens_prompt: int | None = None
tokens_completion: int | None = None
tokens_total: int | None = None

# === Session cumulative ===
session_tokens_total: int | None = None
session_cost_usd: float | None = None
session_turns: int | None = None
```


#### 3.1.2 Добавить вложенную модель `LLMCallInfo`

```python
class LLMCallInfo(BaseModel):
    step: str                        # "state_classifier", "sd_classifier", "answer"
    model: str                       # "gpt-4o-mini"
    tokens_prompt: int | None = None
    tokens_completion: int | None = None
    tokens_total: int | None = None
    duration_ms: int | None = None
    system_prompt_preview: str | None = None  # первые 200 символов
    response_preview: str | None = None       # первые 200 символов
```


#### 3.1.3 Заполнять `llm_calls` при генерации ответа

В `llm_answerer.py` — после каждого `openai.chat.completions.create()`
собирать данные из `response.usage` и замерять время:

```python
import time

start = time.perf_counter()
response = client.chat.completions.create(...)
duration_ms = int((time.perf_counter() - start) * 1000)

call_info = LLMCallInfo(
    step=step_name,           # передавать как параметр
    model=response.model,     # реальное имя модели из ответа API
    tokens_prompt=response.usage.prompt_tokens if response.usage else None,
    tokens_completion=response.usage.completion_tokens if response.usage else None,
    tokens_total=response.usage.total_tokens if response.usage else None,
    duration_ms=duration_ms,
    system_prompt_preview=(system_prompt or "")[:200],
    response_preview=(answer_text or "")[:200],
)
```

Возвращать `call_info` из метода `generate_answer()` вместе с ответом
(добавить в возвращаемый `dict` ключ `llm_call_info`).

#### 3.1.4 Заполнять модели пайплайна

В точке формирования `trace` (router или orchestrator) добавить:

```python
from bot_agent.config import config

trace.primary_model = config.LLM_MODEL
trace.classifier_model = config.CLASSIFIER_MODEL
trace.embedding_model = config.EMBEDDING_MODEL
trace.reranker_model = config.VOYAGE_MODEL if config.VOYAGE_ENABLED else None
trace.reranker_enabled = config.VOYAGE_ENABLED
```


#### 3.1.5 Суммировать токены за сообщение

После сбора всех `llm_calls` посчитать итог:

```python
all_tokens = [c.tokens_total for c in trace.llm_calls if c.tokens_total]
if all_tokens:
    trace.tokens_total = sum(all_tokens)
    # Prompt и completion — из основного вызова ответа (step="answer")
    answer_call = next((c for c in trace.llm_calls if c.step == "answer"), None)
    if answer_call:
        trace.tokens_prompt = answer_call.tokens_prompt
        trace.tokens_completion = answer_call.tokens_completion
```


#### 3.1.6 Накопительные токены сессии

В session storage (или в памяти сессии) хранить накопленный счётчик:

```python
# При каждом ответе:
session.total_tokens += trace.tokens_total or 0
session.turns_count += 1

trace.session_tokens_total = session.total_tokens
trace.session_turns = session.turns_count
```


#### 3.1.7 Стоимость сессии (приблизительная)

Считать cost только для стандартных моделей:

```python
# Цены per 1M токенов (март 2026, openai.com/api/pricing)
COST_PER_1M: dict = {
    "gpt-4o-mini":           {"input": 0.15,  "output": 0.60},
    "gpt-4o":                {"input": 2.50,  "output": 10.00},
    "gpt-4-turbo":           {"input": 10.00, "output": 30.00},
    "gpt-4-turbo-preview":   {"input": 10.00, "output": 30.00},
    "gpt-5-mini":            {"input": 0.25,  "output": 2.00},
    "gpt-5-mini-2025-08-07": {"input": 0.25,  "output": 2.00},
    "gpt-5":                 {"input": 1.25,  "output": 10.00},
    "gpt-5-2025-08-07":      {"input": 1.25,  "output": 10.00},
}

# Расчёт (раздельно input/output):
model_key = config.LLM_MODEL.lower()
if model_key in COST_PER_1M:
    rates = COST_PER_1M[model_key]
    cost = (tokens_prompt / 1_000_000 * rates["input"] +
            tokens_completion / 1_000_000 * rates["output"])
    trace.session_cost_usd = round(session.cost + cost, 6)
else:
    trace.session_cost_usd = None  # не показывать "$0.00"
```

Если модель не в словаре — оставить `None` (не показывать "\$0.00").

---

### 3.2 ФРОНТЕНД: обновить тип `InlineTrace`

Файл: `web_ui/src/types/chat.types.ts`

Найти интерфейс `InlineTrace` и добавить поля:

```typescript
// === LLM Calls ===
llm_calls?: LLMCallInfo[];

// === Models ===
primary_model?: string;
classifier_model?: string;
embedding_model?: string;
reranker_model?: string | null;
reranker_enabled?: boolean;

// === Tokens per message ===
tokens_prompt?: number;
tokens_completion?: number;
tokens_total?: number;

// === Session cumulative ===
session_tokens_total?: number;
session_cost_usd?: number | null;
session_turns?: number;
```

Добавить новый интерфейс `LLMCallInfo` в тот же файл:

```typescript
export interface LLMCallInfo {
  step: string;
  model: string;
  tokens_prompt?: number | null;
  tokens_completion?: number | null;
  tokens_total?: number | null;
  duration_ms?: number | null;
  system_prompt_preview?: string | null;
  response_preview?: string | null;
}
```


---

### 3.3 ФРОНТЕНД: добавить секции в `InlineDebugTrace.tsx`

#### 3.3.1 Секция "⚡ LLM Вызовы"

Добавить новую `<details>` секцию после блока "Чанки в ответ",
перед блоком "Контекст памяти":

```tsx
{/* LLM Calls */}
{trace.llm_calls && trace.llm_calls.length > 0 && (
  <details>
    <summary className="cursor-pointer font-semibold
                        text-slate-600 dark:text-slate-400 py-1 select-none">
      ⚡ LLM Вызовы ({trace.llm_calls.length})
    </summary>
    <div className="mt-2 space-y-2">
      {trace.llm_calls.map((call, idx) => (
        <details key={idx}
          className="rounded-lg border border-slate-200
                     dark:border-slate-700 bg-white dark:bg-slate-800">
          <summary className="cursor-pointer px-3 py-2
                              flex items-center gap-2 text-xs select-none
                              hover:bg-slate-50 dark:hover:bg-slate-700/50">
            <span className="font-mono font-semibold
                             text-slate-700 dark:text-slate-300 w-28 truncate">
              {call.step}
            </span>
            <span className="text-sky-600 dark:text-sky-400 font-medium">
              {call.model}
            </span>
            {call.tokens_total != null && (
              <span className="ml-auto text-slate-500">
                🪙 {call.tokens_total.toLocaleString()} tok
              </span>
            )}
            {call.duration_ms != null && (
              <span className="text-slate-400">
                ⏱ {call.duration_ms}ms
              </span>
            )}
          </summary>
          <div className="px-3 py-2 border-t border-slate-200
                          dark:border-slate-700 space-y-2">
            {/* Tokens breakdown */}
            {(call.tokens_prompt != null || call.tokens_completion != null) && (
              <div className="flex gap-4 text-[11px]">
                <span className="text-slate-400">
                  prompt: <b className="text-slate-600 dark:text-slate-300">
                    {call.tokens_prompt ?? '—'}
                  </b>
                </span>
                <span className="text-slate-400">
                  completion: <b className="text-slate-600 dark:text-slate-300">
                    {call.tokens_completion ?? '—'}
                  </b>
                </span>
              </div>
            )}
            {/* Previews */}
            {call.system_prompt_preview && (
              <div>
                <p className="text-[10px] text-slate-400 uppercase
                              tracking-wide mb-0.5">
                  System prompt (preview)
                </p>
                <p className="font-mono text-[10px] text-slate-500
                              dark:text-slate-400 whitespace-pre-wrap
                              bg-slate-50 dark:bg-slate-900 rounded p-1.5">
                  {call.system_prompt_preview}
                </p>
              </div>
            )}
            {call.response_preview && (
              <div>
                <p className="text-[10px] text-slate-400 uppercase
                              tracking-wide mb-0.5">
                  Response (preview)
                </p>
                <p className="font-mono text-[10px] text-slate-500
                              dark:text-slate-400 whitespace-pre-wrap
                              bg-slate-50 dark:bg-slate-900 rounded p-1.5">
                  {call.response_preview}
                </p>
              </div>
            )}
          </div>
        </details>
      ))}
    </div>
  </details>
)}
```


#### 3.3.2 Секция "🤖 Модели пайплайна"

Добавить после блока "⚡ LLM Вызовы":

```tsx
{/* Pipeline Models */}
{(trace.primary_model || trace.classifier_model) && (
  <details>
    <summary className="cursor-pointer font-semibold
                        text-slate-600 dark:text-slate-400 py-1 select-none">
      🤖 Модели пайплайна
    </summary>
    <div className="mt-2 grid grid-cols-2 gap-2">
      {trace.primary_model && (
        <div className="rounded-lg bg-white dark:bg-slate-800 px-3 py-2">
          <p className="text-[10px] text-slate-400 uppercase tracking-wide">
            Primary (ответ)
          </p>
          <p className="font-mono font-semibold text-sky-600 dark:text-sky-400
                        text-[11px] truncate">
            {trace.primary_model}
          </p>
        </div>
      )}
      {trace.classifier_model && (
        <div className="rounded-lg bg-white dark:bg-slate-800 px-3 py-2">
          <p className="text-[10px] text-slate-400 uppercase tracking-wide">
            Classifier
          </p>
          <p className="font-mono font-semibold text-violet-600
                        dark:text-violet-400 text-[11px] truncate">
            {trace.classifier_model}
          </p>
        </div>
      )}
      {trace.embedding_model && (
        <div className="rounded-lg bg-white dark:bg-slate-800 px-3 py-2">
          <p className="text-[10px] text-slate-400 uppercase tracking-wide">
            Embedding
          </p>
          <p className="font-mono font-semibold text-emerald-600
                        dark:text-emerald-400 text-[11px] truncate">
            {trace.embedding_model}
          </p>
        </div>
      )}
      <div className="rounded-lg bg-white dark:bg-slate-800 px-3 py-2">
        <p className="text-[10px] text-slate-400 uppercase tracking-wide">
          Reranker
        </p>
        <p className="font-mono font-semibold text-[11px] truncate
                      text-slate-700 dark:text-slate-300">
          {trace.reranker_enabled
            ? (trace.reranker_model ?? 'enabled')
            ```
            : <span className="text-slate-400">off</span>
            ```
          }
        </p>
      </div>
    </div>
  </details>
)}
```


#### 3.3.3 Секция "🪙 Токены и стоимость"

Добавить после "🤖 Модели пайплайна":

```tsx
{/* Tokens & Cost */}
{(trace.tokens_total != null || trace.session_tokens_total != null) && (
  <details>
    <summary className="cursor-pointer font-semibold
                        text-slate-600 dark:text-slate-400 py-1 select-none">
      🪙 Токены и стоимость
    </summary>
    <div className="mt-2 space-y-2">
      {/* Per message */}
      {trace.tokens_total != null && (
        <div className="rounded-lg bg-white dark:bg-slate-800 px-3 py-2">
          <p className="text-[10px] text-slate-400 uppercase
                        tracking-wide mb-1">
            Это сообщение
          </p>
          <div className="flex gap-4 text-xs">
            <span className="text-slate-500">
              prompt: <b className="text-slate-700 dark:text-slate-200">
                {trace.tokens_prompt?.toLocaleString() ?? '—'}
              </b>
            </span>
            <span className="text-slate-500">
              completion: <b className="text-slate-700 dark:text-slate-200">
                {trace.tokens_completion?.toLocaleString() ?? '—'}
              </b>
            </span>
            <span className="text-slate-500">
              total: <b className="text-amber-600 dark:text-amber-400 font-bold">
                {trace.tokens_total.toLocaleString()}
              </b>
            </span>
          </div>
        </div>
      )}

      {/* Session cumulative */}
      {trace.session_tokens_total != null && (
        <div className="rounded-lg bg-white dark:bg-slate-800 px-3 py-2">
          <p className="text-[10px] text-slate-400 uppercase
                        tracking-wide mb-1">
            Сессия (нарастающий итог)
          </p>
          <div className="flex gap-4 text-xs items-center">
            <span className="text-slate-500">
              токены: <b className="text-slate-700 dark:text-slate-200 font-bold">
                {trace.session_tokens_total.toLocaleString()}
              </b>
            </span>
            {trace.session_turns != null && (
              <span className="text-slate-500">
                сообщений: <b className="text-slate-700 dark:text-slate-200">
                  {trace.session_turns}
                </b>
              </span>
            )}
            {trace.session_cost_usd != null && (
              <span className="ml-auto font-bold text-emerald-600
                               dark:text-emerald-400">
                ≈ ${trace.session_cost_usd.toFixed(4)}
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  </details>
)}
```


---

## 4. ИТОГОВАЯ СТРУКТУРА `InlineDebugTrace` ПОСЛЕ ИЗМЕНЕНИЙ

```
🔍 [CLARIFICATION] rule_id  conf: 0.13  SD: GREEN  ✓0 ✕0
│
├── 📊 Роутинг и оркестрация   ← существующий (не трогать)
├── ✓ Чанки в ответ (N)        ← существующий (не трогать)
├── ✕ Отсеянные чанки (N)      ← существующий (не трогать)
├── ⚡ LLM Вызовы (N)          ← НОВЫЙ
├── 🤖 Модели пайплайна        ← НОВЫЙ
├── 🪙 Токены и стоимость      ← НОВЫЙ
└── 🧠 Контекст памяти         ← существующий (не трогать)
```


---

## 5. ЧТО НЕ ТРОГАТЬ

1. Существующие секции `InlineDebugTrace.tsx` — только добавлять,
не изменять уже рабочие блоки.
2. `config.py` — не изменять, только читать значения.
3. `response_formatter.py` — не трогать.
4. `Message.tsx` — не трогать.
5. `api.types.ts` — не трогать (там уже есть `LLMCallTrace`,
тип `InlineTrace` живёт в `chat.types.ts`).

---

## 6. ТЕСТИРОВАНИЕ

### 6.1 Компиляция

```bash
cd bot_psychologist/web_ui
npm run lint
npm run build
```

Ожидаемый результат: 0 ошибок TypeScript.

### 6.2 Бэкенд

```bash
cd bot_psychologist
python -c "
from bot_agent.config import config
print('Models:', config.LLM_MODEL, config.CLASSIFIER_MODEL)
print('Voyage enabled:', config.VOYAGE_ENABLED)
"
```


### 6.3 Функциональный тест в браузере (dev-режим)

**Тест 1 — Блок LLM Вызовы:**

- [ ] Отправить сообщение в dev-режиме
- [ ] В трейсе появился блок "⚡ LLM Вызовы"
- [ ] Видно минимум 1 вызов (step="answer" или аналог)
- [ ] В каждом вызове: модель, токены, время
- [ ] При раскрытии вызова виден preview промпта и ответа

**Тест 2 — Блок Модели:**

- [ ] Блок "🤖 Модели пайплайна" появился
- [ ] Primary model совпадает с `PRIMARY_MODEL` в `.env`
- [ ] Classifier model показан
- [ ] Reranker показывает "off" если `VOYAGE_ENABLED=False`

**Тест 3 — Блок Токены:**

- [ ] Блок "🪙 Токены и стоимость" появился
- [ ] prompt + completion + total за сообщение отображаются
- [ ] После нескольких сообщений — нарастающий итог сессии растёт
- [ ] Стоимость "≈ \$X.XXXX" отображается (или не отображается
если модель не в словаре цен)

**Тест 4 — Регрессия:**

- [ ] Обычный (user) вход — новые блоки не видны
- [ ] Существующие блоки трейса работают как раньше
- [ ] Console браузера: нет ошибок

---

## 7. DEFINITION OF DONE

- [ ] Бэкенд: `LLMCallInfo` модель добавлена в схемы
- [ ] Бэкенд: `llm_calls` заполняется при каждом LLM-вызове
- [ ] Бэкенд: поля моделей пайплайна передаются в `trace`
- [ ] Бэкенд: `tokens_prompt/completion/total` заполняются
- [ ] Бэкенд: `session_tokens_total`, `session_cost_usd`,
`session_turns` накапливаются per session
- [ ] Фронт: `InlineTrace` тип обновлён в `chat.types.ts`
- [ ] Фронт: 3 новых секции добавлены в `InlineDebugTrace.tsx`
- [ ] `npm run lint` — 0 ошибок
- [ ] `npm run build` — успешная сборка
- [ ] Все тесты раздела 6.3 пройдены
- [ ] Обычный (user) режим не затронут

```
```

