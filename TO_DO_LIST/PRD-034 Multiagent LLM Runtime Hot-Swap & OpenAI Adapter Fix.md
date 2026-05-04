# PRD-034 — Multiagent LLM Runtime Hot-Swap & OpenAI Adapter Fix

## 1. Название

**PRD-034: Починка мультиагентного LLM-runtime, hot-swap моделей из Web Admin и устранение тихих fallback’ов**

---

## 2. Контекст

После переделки Web Admin под новую мультиагентную систему бот перестал стабильно работать. Backend отвечает `200`, запросы доходят до мультиагентного runtime, карточки агентов в админке показывают вызовы, но поведение похоже на деградацию: бот может отвечать короткими fallback-фразами вроде:

```text id="va4nxb"
Я слышу тебя.
Я слышу тебя. Расскажи больше, если хочешь.
Сделай медленный вдох. Я рядом.
```

На скрине Web Admin видно, что модели агентов меняются через UI:

```text id="xnyxh9"
state_analyzer → gpt-5-nano
thread_manager → gpt-5-nano
writer → gpt-5-mini
```

В текущем `agent_llm_config.py` дефолты действительно такие: `state_analyzer` и `thread_manager` используют `gpt-5-nano`, а `writer` использует `gpt-5-mini` .

Проблема в том, что новые мультиагентные агенты вызывают LLM напрямую старым способом. Например, `writer_agent.py` вызывает `client.chat.completions.create(...)` с `temperature` и `max_tokens` . `state_analyzer.py` делает похожий прямой вызов через `chat.completions.create(...)`, включая `response_format`, `temperature` и `max_tokens` .

При этом в старом `llm_answerer.py` уже есть более правильная логика: для моделей, которые не поддерживают кастомную temperature, используется другой путь через Responses API и `max_output_tokens` . В `config.py` уже есть методы `supports_custom_temperature`, `get_token_param_name`, `get_reasoning_effort`, а `gpt-5*`, `o1`, `o3`, `o4` определены как модели, требующие особого режима .

---

## 3. Главная проблема

Сейчас Web Admin может показывать выбранную модель, но runtime агентов не гарантирует корректную работу, потому что:

```text id="b5pbb8"
1. gpt-5-mini/gpt-5-nano вызываются как обычные chat.completions-модели.
2. В LLM-запросы передаются параметры, которые для этих моделей могут быть неподходящими.
3. Ошибка LLM скрывается fallback-ответом.
4. Agent metrics в админке могут показывать errors: 0, даже если Writer внутри упал и вернул fallback.
5. Модель, temperature, max_tokens могут быть закэшированы в singleton-агенте при старте и не обновляться на следующем запросе.
```

---

## 4. Цель PRD-034

Сделать так, чтобы:

```text id="qx52gd"
1. Бот снова стабильно отвечал через мультиагентную систему.
2. WriterAgent и StateAnalyzerAgent корректно вызывали разные семейства моделей.
3. Модели, выбранные в Web Admin, применялись на следующем запросе без перезапуска сервера.
4. Temperature и token limits тоже читались динамически, если они редактируются через админку.
5. Ошибки LLM не скрывались полностью, а попадали в trace, metrics и Admin UI.
6. DebugTrace и MultiAgentTrace не ломались из-за несовместимых форматов.
```

---

## 5. Out of Scope

В рамках PRD-034 **не делать**:

```text id="focwd8"
1. Не удалять старую каскадную систему.
2. Не делать PRD-028 Legacy Cleanup.
3. Не переносить Thread Storage из JSON в БД.
4. Не внедрять Redis rate limiting.
5. Не переделывать CORS.
6. Не делать большой production-hardening.
7. Не переписывать всю админку.
```

PRD-034 — это точечный runtime-fix, чтобы бот снова работал, а модели в админке реально переключались.

---

# 6. Архитектурное решение

## 6.1. Ввести единый LLM adapter для мультиагентных агентов

Создать новый файл:

```text id="ng2p9b"
bot_psychologist/bot_agent/multiagent/agents/agent_llm_client.py
```

Этот файл должен стать единственным местом, где агенты решают:

```text id="dk5kvo"
какую модель вызвать;
через какой API вызвать;
какие параметры передавать;
как достать текст ответа;
как достать usage/tokens;
как записать api_mode.
```

---

## 6.2. Правило выбора API

Использовать существующую логику из `config.py`:

```python id="xsw8rz"
config.supports_custom_temperature(model)
```

### Если `supports_custom_temperature(model) == True`

Использовать:

```text id="lpn1m9"
chat.completions.create
```

Для моделей:

```text id="ocm2b7"
gpt-4o-mini
gpt-4.1
gpt-4.1-mini
gpt-4.1-nano
```

Передавать:

```text id="j53t57"
messages
temperature
max_tokens
timeout
response_format, если задан
```

---

### Если `supports_custom_temperature(model) == False`

Использовать:

```text id="erej1s"
responses.create
```

Для моделей:

```text id="nfz9wt"
gpt-5.2
gpt-5.1
gpt-5
gpt-5-mini
gpt-5-nano
o1
o3
o4
```

Передавать:

```text id="rqrjfk"
input
max_output_tokens
reasoning, если задан config.get_reasoning_effort(model)
```

Не передавать:

```text id="rtjuta"
temperature
max_tokens
response_format
```

Для JSON-задач, например State Analyzer, требовать JSON через prompt:

```text id="jm8ms6"
Return ONLY a valid JSON object. No markdown. No explanation.
```

---

# 7. Новый файл: `agent_llm_client.py`

## 7.1. Требуемый интерфейс

```python id="tg4867"
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

@dataclass
class AgentLLMResult:
    text: str
    model: str
    api_mode: str  # "chat_completions" | "responses"
    tokens_prompt: Optional[int] = None
    tokens_completion: Optional[int] = None
    tokens_total: Optional[int] = None
    raw_response: Optional[Any] = None
```

Основная функция:

```python id="uv2zda"
async def create_agent_completion(
    *,
    client: Any,
    model: str,
    messages: list[dict[str, str]],
    temperature: float | None = None,
    max_tokens: int | None = None,
    timeout: float | None = None,
    response_format: dict | None = None,
    require_json: bool = False,
) -> AgentLLMResult:
    ...
```

---

## 7.2. Вспомогательная функция

Добавить:

```python id="nd12h3"
def messages_to_input(messages: list[dict[str, str]]) -> str:
    ...
```

Формат можно взять по смыслу из старого `llm_answerer.py`, где chat messages превращаются в plain text input для Responses API .

Пример:

```text id="zmwvfa"
SYSTEM:
...

USER:
...
```

---

## 7.3. Usage extraction

Adapter должен уметь доставать usage из обоих режимов.

### Для chat.completions

```text id="ugor2h"
prompt_tokens
completion_tokens
total_tokens
```

### Для responses

```text id="ytnh2j"
input_tokens
output_tokens
total_tokens
```

Если `total_tokens` отсутствует, вычислить:

```text id="p3j0lv"
tokens_total = tokens_prompt + tokens_completion
```

---

## 7.4. Ошибки

Adapter **не должен молча глотать ошибки**.

Он должен:

```text id="cfm99v"
1. Пробрасывать exception выше.
2. Давать агенту возможность записать ошибку в last_debug.
3. Не возвращать пустой успешный результат при ошибке API.
```

---

# 8. Изменения в `writer_agent.py`

## 8.1. Убрать кэширование активной модели при `__init__`

Сейчас агент сохраняет модель при создании:

```python id="messtd"
self._model = model or get_model_for_agent("writer")
```

Нужно заменить на:

```python id="b78u0f"
self._model_override = model
```

И добавить:

```python id="o6ooap"
def _resolve_model(self) -> str:
    return self._model_override or get_model_for_agent("writer")
```

---

## 8.2. Динамически читать runtime-настройки на каждый LLM-вызов

Сейчас `WriterAgent` также кэширует:

```text id="nqwgpq"
_timeout
_max_tokens
_temperature
```

Это мешает hot-swap, если Web Admin меняет temperature или token limit.

Нужно сделать динамический resolver:

```python id="z7sd9l"
def _resolve_runtime_settings(self) -> dict:
    return {
        "model": self._resolve_model(),
        "temperature": ...,
        "max_tokens": ...,
        "timeout": ...,
    }
```

Главное правило:

```text id="p6l08c"
На каждый новый запрос WriterAgent должен заново читать:
- active model
- temperature
- max_tokens
- timeout
```

---

## 8.3. Заменить прямой OpenAI-вызов на adapter

В `_call_llm()` заменить:

```python id="c3jf04"
client.chat.completions.create(...)
```

на:

```python id="toc2ek"
result = await create_agent_completion(
    client=client,
    model=model,
    messages=[
        {"role": "system", "content": WRITER_SYSTEM},
        {"role": "user", "content": user_prompt},
    ],
    temperature=temperature,
    max_tokens=max_tokens,
    timeout=timeout,
)
```

---

## 8.4. Обновить `last_debug`

`last_debug` должен содержать:

```python id="upgt1l"
{
    "model": model,
    "api_mode": result.api_mode,
    "temperature": temperature,
    "max_tokens": max_tokens,
    "timeout": timeout,
    "system_prompt": WRITER_SYSTEM,
    "user_prompt": user_prompt,
    "llm_response": result.text,
    "tokens_prompt": result.tokens_prompt,
    "tokens_completion": result.tokens_completion,
    "tokens_total": result.tokens_total,
    "estimated_cost_usd": estimated_cost,
    "duration_ms": duration_ms,
    "error": None,
}
```

При ошибке:

```python id="csnjtn"
self.last_debug["error"] = str(exc)
self.last_debug["model"] = model
self.last_debug["api_mode"] = api_mode или "unknown"
```

---

## 8.5. Fallback не должен считаться полноценным успехом

Если Writer упал и вернул static fallback, в debug должно быть:

```text id="bqxo1b"
writer_error != null
writer_fallback_used = true
```

И в карточке агента `writer` error_count должен увеличиться.

---

# 9. Изменения в `state_analyzer.py`

## 9.1. Убрать кэширование активной модели

Сейчас `StateAnalyzerAgent` сохраняет модель при создании.

Нужно аналогично Writer:

```python id="x9jjmn"
self._model_override = model

def _resolve_model(self) -> str:
    return self._model_override or get_model_for_agent("state_analyzer")
```

---

## 9.2. Добавить `last_debug`

Сейчас у State Analyzer нет такого развитого debug-объекта, как у Writer.

Добавить:

```python id="aw1ysj"
self.last_debug: dict[str, Any] = {}
```

На каждый LLM-вызов записывать:

```python id="lg7ji0"
{
    "model": model,
    "api_mode": result.api_mode,
    "temperature": temperature,
    "max_tokens": max_tokens,
    "tokens_prompt": result.tokens_prompt,
    "tokens_completion": result.tokens_completion,
    "tokens_total": result.tokens_total,
    "raw_response": result.text,
    "error": None,
}
```

При ошибке:

```python id="o1tm5k"
"error": str(exc)
```

---

## 9.3. Перевести `_analyze_with_llm()` на adapter

Заменить прямой вызов:

```python id="lr7vwg"
client.chat.completions.create(...)
```

на:

```python id="psvzz8"
result = await create_agent_completion(
    client=client,
    model=model,
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ],
    temperature=0.1,
    max_tokens=240,
    response_format={"type": "json_object"},
    require_json=True,
)
```

Для `gpt-5*` adapter не должен передавать `response_format` напрямую, но должен усилить prompt-инструкцию.

---

## 9.4. Перевести `_llm_safety_check()` на adapter

Также заменить прямой вызов safety-check LLM.

Важно:

```text id="n77ph4"
Для safety-check достаточно короткого ответа YES/NO.
Для gpt-5* использовать responses.create.
Для обычных моделей использовать chat.completions.
```

---

# 10. Изменения в `orchestrator.py`

## 10.1. Пробросить debug Writer в общий trace

Сейчас orchestrator уже собирает `writer_debug` после Writer. Нужно добавить поля:

```python id="txbstn"
"writer_api_mode": writer_debug.get("api_mode"),
"writer_error": writer_debug.get("error"),
"writer_fallback_used": writer_debug.get("fallback_used"),
```

Также существующие поля сохранить:

```python id="bjmce4"
"model_used"
"model_temperature"
"model_max_tokens"
"tokens_prompt"
"tokens_completion"
"tokens_total"
```

---

## 10.2. Пробросить debug State Analyzer

После вызова State Analyzer добавить:

```python id="tbov3v"
state_debug = state_analyzer_agent.last_debug if isinstance(..., dict) else {}
```

В общий debug добавить:

```python id="tb3vh5"
"state_analyzer_model": state_debug.get("model"),
"state_analyzer_api_mode": state_debug.get("api_mode"),
"state_analyzer_error": state_debug.get("error"),
"state_analyzer_tokens_prompt": state_debug.get("tokens_prompt"),
"state_analyzer_tokens_completion": state_debug.get("tokens_completion"),
"state_analyzer_tokens_total": state_debug.get("tokens_total"),
```

---

## 10.3. Agent metrics должны видеть LLM-ошибки

Сейчас карточки в админке могут показывать:

```text id="b1a05l"
errors: 0
```

даже если агент вернул fallback.

Нужно:

```text id="ieoyg8"
Если writer_debug["error"] не пустой:
    _record_agent_metric(..., error=writer_debug["error"])

Если state_debug["error"] не пустой:
    _record_agent_metric(..., error=state_debug["error"])
```

Это критично для админки.

---

# 11. Изменения в Debug / API models

## 11.1. `MultiAgentTraceResponse`

Добавить в модели trace, если нужно:

```python id="dehczu"
writer_api_mode: Optional[str]
writer_error: Optional[str]
state_analyzer_api_mode: Optional[str]
state_analyzer_error: Optional[str]
```

Или, если не хочется менять Pydantic-модель, добавить эти поля в существующие вложенные trace-структуры.

---

## 11.2. Legacy `DebugTrace`

Последний коммит уже добавил нормализацию `semantic_hits_detail` для `DebugTrace` .

В рамках PRD-034:

```text id="v1y4aw"
1. Не удалять этот фикс.
2. Не переписывать его без необходимости.
3. Добавить тест, что multiagent semantic_hits_detail не ломает DebugTrace.
```

---

# 12. Изменения в Web Admin

## 12.1. Проверить, что модель применяется на следующий запрос

В админке уже есть надпись:

```text id="lx8dwk"
Изменения применяются к следующему запросу без перезапуска сервера.
```

После PRD-034 это должно стать правдой не только в UI, но и в runtime.

---

## 12.2. Показывать `api_mode`

В таблице последних trace или в карточке агента желательно показывать:

```text id="v6fr6v"
model: gpt-5-mini
api_mode: responses
```

или:

```text id="r4ruf3"
model: gpt-4o-mini
api_mode: chat_completions
```

---

## 12.3. Thread Manager не должен вводить в заблуждение

Сейчас `thread_manager` в коде фактически эвристический, а не LLM-агент. В `orchestrator.py` он прямо отмечается как:

```python id="x9skdz"
"thread_manager_model": "heuristic"
```



Поэтому в Web Admin нужно сделать одно из двух:

### Вариант A — оставить, но подписать

```text id="gl64ya"
thread_manager — heuristic, LLM model reserved for future use
```

### Вариант B — скрыть выбор модели

Скрыть model selector для `thread_manager`, пока он реально не вызывает LLM.

Рекомендация: **вариант A**, чтобы не ломать уже сделанную админку.

---

# 13. Тесты

## 13.1. Новый test file

Создать:

```text id="y3ohcp"
bot_psychologist/tests/multiagent/test_agent_llm_client.py
```

Покрыть:

```text id="mx84fb"
1. gpt-4o-mini → chat_completions
2. gpt-4.1-mini → chat_completions
3. gpt-5-mini → responses
4. gpt-5-nano → responses
5. chat_completions получает temperature и max_tokens
6. responses не получает temperature и max_tokens
7. responses получает max_output_tokens
8. usage корректно извлекается из chat.completions
9. usage корректно извлекается из responses
10. require_json для responses добавляет JSON-инструкцию в input
```

---

## 13.2. Обновить `test_writer_agent.py`

Сейчас тесты Writer проверяют старое поведение: например, что `max_tokens` и `temperature` передаются напрямую в `chat.completions` .

Нужно заменить эти проверки на две группы.

### Writer + gpt-4o-mini

```text id="ixc2jc"
- api_mode == "chat_completions"
- temperature передан
- max_tokens передан
- response не fallback
```

### Writer + gpt-5-mini

```text id="x3b3pp"
- api_mode == "responses"
- temperature НЕ передан
- max_tokens НЕ передан
- max_output_tokens передан
- response не fallback
```

---

## 13.3. Обновить `test_state_analyzer.py`

Добавить проверки:

### State Analyzer + gpt-4o-mini

```text id="tgj6ii"
- api_mode == "chat_completions"
- response_format передан
- JSON парсится
```

### State Analyzer + gpt-5-nano

```text id="qz80vn"
- api_mode == "responses"
- response_format НЕ передан напрямую
- JSON-инструкция есть в input
- JSON парсится
- StateSnapshot валидный
```

---

## 13.4. Главный hot-swap тест

Создать:

```text id="kiyvr6"
bot_psychologist/tests/multiagent/test_agent_hot_swap.py
```

Тест должен проверять именно то, что важно для Web Admin.

### Сценарий 1 — Writer model hot-swap

```text id="fbi23q"
1. Создать один instance WriterAgent.
2. set_model_for_agent("writer", "gpt-5-mini")
3. Выполнить write()
4. Проверить last_debug["model"] == "gpt-5-mini"
5. Проверить last_debug["api_mode"] == "responses"

6. Без пересоздания WriterAgent:
   set_model_for_agent("writer", "gpt-4o-mini")

7. Выполнить write() ещё раз.
8. Проверить last_debug["model"] == "gpt-4o-mini"
9. Проверить last_debug["api_mode"] == "chat_completions"
```

### Сценарий 2 — State Analyzer model hot-swap

```text id="n08i7e"
1. Создать один instance StateAnalyzerAgent.
2. set_model_for_agent("state_analyzer", "gpt-5-nano")
3. analyze()
4. api_mode == "responses"

5. Без пересоздания:
   set_model_for_agent("state_analyzer", "gpt-4o-mini")

6. analyze()
7. api_mode == "chat_completions"
```

---

## 13.5. Тест на отсутствие тихого fallback

Добавить тест:

```text id="m5c2rq"
Если LLM adapter падает:
1. Writer возвращает fallback пользователю.
2. writer.last_debug["error"] не пустой.
3. writer.last_debug["fallback_used"] == True.
4. Orchestrator debug содержит writer_error.
5. Agent metrics увеличивает error_count.
```

---

## 13.6. Тест на DebugTrace compatibility

Так как свежий коммит уже добавил `_normalize_semantic_hits_detail_for_debug_trace`, нужно добавить тест:

```text id="m3ezva"
Input:
[
  {
    "chunk_id": "abc",
    "score": 0.88,
    "content_preview": "preview",
    "content_full": "full text",
    "source": "memory"
  }
]

Expected:
[
  {
    "block_id": "abc",
    "score": 0.88,
    "text_preview": "preview",
    "source": "memory"
  }
]
```

---

# 14. Fake clients для тестов

Нужно сделать fake OpenAI client с двумя ветками:

```python id="ea5h1x"
fake_client.chat.completions.create(...)
fake_client.responses.create(...)
```

Fake должен сохранять calls:

```python id="h8yvoz"
chat_calls
responses_calls
```

Чтобы тест мог проверить:

```text id="noztr4"
- какой API реально был вызван;
- какие параметры были переданы;
- каких параметров не было.
```

---

# 15. Acceptance Criteria

PRD-034 считается выполненным, если:

```text id="se3d3t"
1. WriterAgent больше не вызывает gpt-5-mini через chat.completions + temperature + max_tokens.
2. StateAnalyzerAgent больше не вызывает gpt-5-nano через chat.completions + temperature + max_tokens.
3. gpt-5*, o-series идут через responses.create.
4. gpt-4o-mini/gpt-4.1* идут через chat.completions.
5. Модель Writer меняется из Web Admin на следующем запросе без перезапуска сервера.
6. Модель State Analyzer меняется из Web Admin на следующем запросе без перезапуска сервера.
7. Temperature и max_tokens/max_output_tokens читаются динамически на каждый запрос.
8. writer_error попадает в trace, если Writer упал.
9. state_analyzer_error попадает в trace, если State Analyzer упал.
10. Agent metrics error_count увеличивается при реальной LLM-ошибке.
11. DebugTrace не падает на semantic_hits_detail.
12. MultiAgentTrace показывает model и api_mode.
13. Бот возвращает нормальный ответ, а не постоянный static fallback.
14. Web Admin показывает актуальные agent metrics после запросов.
15. Все тесты из test matrix проходят.
```

---

# 16. Команды тестирования

Запустить обязательно:

```bash id="zvvn3y"
pytest tests/multiagent/test_agent_llm_client.py -q
pytest tests/multiagent/test_agent_hot_swap.py -q
pytest tests/multiagent/test_writer_agent.py -q
pytest tests/multiagent/test_state_analyzer.py -q
pytest tests/multiagent/test_orchestrator_e2e.py -q
pytest tests/multiagent -q
pytest tests/api -q
pytest tests/test_admin_agent_llm_config.py -q
pytest tests/test_admin_multiagent.py -q
```

Если есть отдельный тест на routes/common:

```bash id="bwm15w"
pytest tests/api/test_debug_trace.py -q
```

или добавить новый:

```bash id="hfrhll"
pytest tests/api/test_debug_trace_semantic_hits.py -q
```

---

# 17. Ручной smoke-check

После фикса запустить backend и web UI.

## 17.1. Проверка Writer на `gpt-5-mini`

В Web Admin выбрать:

```text id="zfo4wd"
writer → gpt-5-mini
```

Отправить в чат:

```text id="bn16cp"
Меня зовут Асхат. Я немного тревожусь и хочу разобраться, почему мне сложно начать разговор.
```

Ожидается:

```text id="t16cri"
1. Ответ не равен "Я слышу тебя."
2. Ответ не равен короткому static fallback.
3. В Admin Trace:
   writer model = gpt-5-mini
   writer api_mode = responses
   writer_error = null
4. Writer card:
   calls увеличился
   errors не увеличился
```

---

## 17.2. Проверка Writer на `gpt-4o-mini`

В Web Admin выбрать:

```text id="d0qzhz"
writer → gpt-4o-mini
```

Отправить новый запрос:

```text id="omdt6x"
А теперь помоги мне спокойно разложить это по шагам.
```

Ожидается:

```text id="n4dt2o"
1. Следующий запрос использует gpt-4o-mini без перезапуска.
2. writer api_mode = chat_completions
3. writer_error = null
4. Ответ нормальный.
```

---

## 17.3. Проверка State Analyzer

В Web Admin выбрать:

```text id="hvfaxv"
state_analyzer → gpt-5-nano
```

Отправить:

```text id="b4bvp1"
Мне тревожно, но я хочу понять, что происходит.
```

Ожидается:

```text id="nc67dv"
state_analyzer model = gpt-5-nano
state_analyzer api_mode = responses
state_analyzer_error = null
nervous_state определён
intent определён
```

Потом переключить:

```text id="duffb7"
state_analyzer → gpt-4o-mini
```

Отправить ещё запрос.

Ожидается:

```text id="t37x4u"
state_analyzer model = gpt-4o-mini
state_analyzer api_mode = chat_completions
```

---

# 18. Важные запреты для агента IDE

```text id="gqxfnp"
DO NOT:
1. Не удалять legacy cascade.
2. Не менять публичные API-контракты без необходимости.
3. Не переписывать всю Web Admin.
4. Не менять business logic Thread Manager.
5. Не считать thread_manager LLM-агентом, пока он реально не вызывает LLM.
6. Не скрывать LLM-ошибки полностью.
7. Не кэшировать active model в singleton-агентах.
8. Не передавать temperature в responses.create.
9. Не передавать max_tokens в responses.create.
10. Не передавать max_output_tokens в chat.completions.
```

---

# 19. Рекомендуемый порядок коммитов

## Commit 1

```text id="i0glis"
feat(multiagent): add agent LLM client adapter
```

Содержит:

```text id="h94okt"
agent_llm_client.py
tests/multiagent/test_agent_llm_client.py
```

---

## Commit 2

```text id="tpdrbd"
fix(writer): use agent LLM adapter and hot runtime settings
```

Содержит:

```text id="y66z25"
writer_agent.py
test_writer_agent.py
test_agent_hot_swap.py частично
```

---

## Commit 3

```text id="umx9dt"
fix(state-analyzer): use agent LLM adapter and dynamic model resolution
```

Содержит:

```text id="j86j19"
state_analyzer.py
test_state_analyzer.py
test_agent_hot_swap.py полностью
```

---

## Commit 4

```text id="s4qnfp"
feat(trace): expose multiagent LLM api mode and errors
```

Содержит:

```text id="u2w0tf"
orchestrator.py
debug_routes.py или models.py, если нужно
admin trace UI, если требуется
```

---

## Commit 5

```text id="i60fvj"
test(trace): cover semantic hits debug compatibility
```

Содержит:

```text id="i7n0ok"
тест на _normalize_semantic_hits_detail_for_debug_trace
```

---

# 20. Rollback Plan

Если после PRD-034 бот не работает:

```text id="a2rpyd"
1. Не продолжать PRD-028 Legacy Cleanup.
2. Не удалять старую систему.
3. Проверить writer_error и state_analyzer_error в trace.
4. Временно поставить writer → gpt-4o-mini и state_analyzer → gpt-4o-mini.
5. Если на gpt-4o-mini работает, а на gpt-5-mini нет — проблема в responses adapter.
6. Если не работает ни на одной модели — проблема в agent runtime/config/admin persistence.
7. Откатить только commit PRD-034, не трогая свежий trace-fix commit 0e37389.
```

---

# 21. Definition of Done

PRD-034 закрыт только если выполнено всё:

```text id="sltmfe"
1. Бот отвечает нормальным содержательным ответом.
2. Writer можно переключить gpt-5-mini ↔ gpt-4o-mini без перезапуска.
3. State Analyzer можно переключить gpt-5-nano ↔ gpt-4o-mini без перезапуска.
4. Trace показывает фактическую модель и api_mode.
5. Ошибки LLM видны в trace и agent metrics.
6. DebugTrace больше не падает.
7. Все тесты зелёные.
8. В Web Admin карточки агентов показывают честные calls/errors.
9. Thread Manager явно обозначен как heuristic/no LLM call или не вводит в заблуждение.
10. PRD-028 Legacy Cleanup не начат до стабилизации PRD-034.
```

---

# 22. Короткое задание для вставки агенту IDE

```text id="aal27r"
Выполни PRD-034: Multiagent LLM Runtime Hot-Swap & OpenAI Adapter Fix.

Главная цель: бот должен снова нормально отвечать, а модели в Web Admin должны применяться на следующем запросе без перезапуска сервера.

Проблема:
Web Admin уже позволяет выбрать модели агентов, например state_analyzer=gpt-5-nano и writer=gpt-5-mini. Но WriterAgent и StateAnalyzerAgent вызывают эти модели напрямую через chat.completions с temperature/max_tokens. Для gpt-5* нужно использовать responses.create + max_output_tokens, без temperature/max_tokens. Из-за этого агенты могут падать в тихий fallback.

Сделай:
1. Создай bot_agent/multiagent/agents/agent_llm_client.py.
2. Adapter должен выбирать:
   - supports_custom_temperature(model)=True → chat.completions
   - supports_custom_temperature(model)=False → responses.create
3. Для responses.create не передавай temperature и max_tokens, используй max_output_tokens.
4. Для chat.completions используй temperature и max_tokens.
5. Переведи writer_agent.py на adapter.
6. Переведи state_analyzer.py на adapter.
7. Не кэшируй active model в singleton-агентах. Модель должна читаться через get_model_for_agent(...) на каждом LLM-вызове.
8. Temperature/max_tokens/timeout тоже должны читаться динамически на каждый запрос, если они управляются из админки.
9. Добавь writer_api_mode, writer_error, state_analyzer_api_mode, state_analyzer_error в debug/trace.
10. Ошибки Writer/StateAnalyzer должны увеличивать agent metrics error_count.
11. Thread Manager сейчас heuristic/no LLM call. Не делать вид, что его модель реально влияет на runtime, пока он не вызывает LLM.
12. Не трогай PRD-028 Legacy Cleanup.
13. Не перетирай свежий фикс semantic_hits_detail в chat.py/common.py. Добавь тест на него.

Тесты:
- test_agent_llm_client.py
- test_agent_hot_swap.py
- обновить test_writer_agent.py
- обновить test_state_analyzer.py
- добавить тест на DebugTrace semantic_hits_detail compatibility

Acceptance:
- writer gpt-5-mini → responses
- writer gpt-4o-mini → chat_completions
- state_analyzer gpt-5-nano → responses
- state_analyzer gpt-4o-mini → chat_completions
- смена модели в Web Admin применяется на следующем запросе без перезапуска
- бот отвечает нормальным ответом, не постоянным fallback
- trace показывает model/api_mode/error
- tests/multiagent и tests/api проходят
```
