<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# хорошо, напиши отдельный ПРД (PRD v1.0.1 ) для агента ИДЕ по исправлению данной проблемы с выбором моделей, до того как будет реализован основной ПРД. Сделай его максимально развернутым и подробным на профессиональном уровне.

Теперь у меня полная картина для написания PRD. Составляю документ.

***

# PRD v1.0.1 — Model Compatibility Fix: GPT-5 Series Support

**Репозиторий:** `Askhat-cmd/Text_transcription`
**Путь проекта:** `bot_psychologist/`
**Версия документа:** 1.0.1
**Дата:** 2026-03-01
**Статус:** `READY FOR AGENT`
**Приоритет:** `BLOCKER` — должен быть выполнен **до** реализации PRD v2.0 Admin Config Panel
**Автор:** Askhat

***

## 1. Контекст и предпосылки

### 1.1 Описание проблемы

При попытке переключить языковую модель с `gpt-4o-mini` на `gpt-5-mini` путём изменения переменной окружения в `.env` бот перестаёт функционировать. API возвращает ошибку:

```
openai.BadRequestError: Unsupported parameter: 'max_tokens' is not supported
with this model. Use 'max_completion_tokens' instead.
```

Дополнительно к этому были выявлены системные проблемы: отсутствие документации переменной `PRIMARY_MODEL` в `.env.example`, устаревшая версия библиотеки `openai`, и отсутствие валидации имени модели при старте.

### 1.2 Корневые причины (Root Causes)

| \# | Причина | Файл | Критичность |
| :-- | :-- | :-- | :-- |
| RC-1 | Параметр `max_tokens` не поддерживается в GPT-5 family — требуется `max_completion_tokens` | `bot_agent/llm_answerer.py` | **CRITICAL** |
| RC-2 | Имя env-переменной `PRIMARY_MODEL` отсутствует в `.env.example` | `.env.example` | **HIGH** |
| RC-3 | Минимальная версия `openai>=1.3.0` (ноябрь 2023) — слишком старая, не гарантирует совместимость с GPT-5 | `requirements_bot.txt` | **HIGH** |
| RC-4 | Нет валидации значения `LLM_MODEL` при старте — бот молча падает в рантайме вместо понятной ошибки при инициализации | `bot_agent/config.py` | **MEDIUM** |

### 1.3 Официальное поведение OpenAI API

Согласно официальной документации OpenAI [platform.openai.com/docs/models/gpt-5-mini], GPT-5 mini (model ID: `gpt-5-mini`, snapshot: `gpt-5-mini-2025-08-07`) **не принимает** параметр `max_tokens` в Chat Completions API. Все модели семейства GPT-5 и o-series (o3, o4-mini) требуют `max_completion_tokens`. Это подтверждается множеством репортов от команд LangChain, LiteLLM, DSPy, Vercel AI.

***

## 2. Цели (Goals)

- **G-1:** Бот корректно работает с моделями `gpt-5-mini`, `gpt-5`, `gpt-4o`, `gpt-4o-mini`, `gpt-4-turbo`
- **G-2:** При указании неизвестной модели в `.env` бот выдаёт понятную ошибку при старте, а не в рантайме
- **G-3:** Переменная `PRIMARY_MODEL` задокументирована в `.env.example` с примерами допустимых значений
- **G-4:** Зависимость `openai` обновлена до минимально безопасной версии
- **G-5:** Логика определения нужного параметра (`max_tokens` vs `max_completion_tokens`) инкапсулирована в одном месте и легко расширяется


## 3. Не-цели (Non-Goals)

- Не переписывать архитектуру LLMAnswerer
- Не добавлять поддержку Responses API (`/v1/responses`) — только Chat Completions
- Не реализовывать UI выбора модели (это задача PRD v2.0)
- Не мигрировать на новые модели принудительно — дефолт остаётся `gpt-4o-mini`

***

## 4. Технические требования

### 4.1 Файл: `bot_psychologist/requirements_bot.txt`

**Изменение:** Поднять минимальную версию `openai` с `>=1.3.0` до `>=1.54.0`.

Версия 1.54.0 — это минимально стабильная версия пакета `openai`, которая:

- Корректно обрабатывает `max_completion_tokens` для o-series и GPT-5
- Включает все актуальные типы и валидацию параметров
- Совместима с текущим кодом (без breaking changes для Chat Completions)

**Результирующий блок:**

```
# OpenAI API client
openai>=1.54.0
```


***

### 4.2 Файл: `bot_psychologist/.env.example`

**Изменение:** Добавить секцию `===== LLM Configuration =====` с документацией переменной `PRIMARY_MODEL` и всеми допустимыми значениями.

Добавить **после строки** `OPENAI_API_KEY="your_openai_api_key_here"`:

```bash
# ===== LLM Configuration =====
# Модель OpenAI, используемая ботом для генерации ответов.
# Env-переменная читается в: bot_agent/config.py → Config.LLM_MODEL
#
# Допустимые значения (Chat Completions API):
#   gpt-4o-mini        — быстрая, дешёвая, рекомендуется для продакшена (DEFAULT)
#   gpt-4o             — более точная, дороже
#   gpt-4-turbo        — устаревшая, поддерживается для совместимости
#   gpt-5-mini         — GPT-5 family: быстрая, cost-efficient (требует Tier 1+)
#   gpt-5              — GPT-5 family: флагман (требует Tier 1+)
#
# ВАЖНО: GPT-5 family использует max_completion_tokens вместо max_tokens.
#         Код бота определяет это автоматически по имени модели.
#
PRIMARY_MODEL=gpt-4o-mini
```


***

### 4.3 Файл: `bot_psychologist/bot_agent/config.py`

**Изменение 1:** Добавить константу `SUPPORTED_MODELS` — полный список допустимых значений.

**Изменение 2:** Добавить метод `get_token_param_name(model: str) -> str` — возвращает `"max_completion_tokens"` для GPT-5/o-series, `"max_tokens"` для остальных. Этот метод является **единственным местом** определения совместимости токенов в проекте.

**Изменение 3:** Добавить валидацию `LLM_MODEL` в метод `validate()`.

**Полный diff для `config.py`:**

В классе `Config` добавить после блока `# === LLM параметры ===`:

```python
# === LLM параметры ===
LLM_MODEL = os.getenv("PRIMARY_MODEL", "gpt-4o-mini")
LLM_TEMPERATURE = 0.7
LLM_MAX_TOKENS = 1500
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Полный список поддерживаемых моделей Chat Completions API.
# При добавлении новой модели — добавить сюда и в .env.example.
SUPPORTED_MODELS: tuple = (
    "gpt-4o-mini",
    "gpt-4o",
    "gpt-4-turbo",
    "gpt-4-turbo-preview",
    "gpt-5-mini",
    "gpt-5-mini-2025-08-07",
    "gpt-5",
    "gpt-5-2025-08-07",
)

# Префиксы моделей, требующих max_completion_tokens вместо max_tokens.
# GPT-5 family и o-series не принимают max_tokens (BadRequestError).
_MAX_COMPLETION_TOKENS_PREFIXES: tuple = (
    "gpt-5",
    "o1",
    "o3",
    "o4",
)

@classmethod
def get_token_param_name(cls, model: Optional[str] = None) -> str:
    """
    Определяет, какой параметр токенов использовать для данной модели.

    OpenAI GPT-5 family и o-series НЕ принимают 'max_tokens'.
    Они требуют 'max_completion_tokens'.

    GPT-4 и более старые модели принимают 'max_tokens'.

    Args:
        model: Имя модели. Если None — используется LLM_MODEL из конфига.

    Returns:
        "max_completion_tokens" для GPT-5/o-series
        "max_tokens" для остальных моделей

    Examples:
        >>> Config.get_token_param_name("gpt-5-mini")
        'max_completion_tokens'
        >>> Config.get_token_param_name("gpt-4o-mini")
        'max_tokens'
        >>> Config.get_token_param_name("o3-mini")
        'max_completion_tokens'
    """
    target = (model or cls.LLM_MODEL).lower()
    for prefix in cls._MAX_COMPLETION_TOKENS_PREFIXES:
        if target.startswith(prefix):
            return "max_completion_tokens"
    return "max_tokens"
```

В метод `validate()` добавить проверку модели:

```python
@classmethod
def validate(cls) -> bool:
    errors = []

    if not cls.OPENAI_API_KEY:
        errors.append("OPENAI_API_KEY не установлен в .env")

    if not cls.SAG_FINAL_DIR.exists():
        errors.append(f"Директория данных не найдена: {cls.SAG_FINAL_DIR}")

    # --- НОВАЯ ПРОВЕРКА ---
    if cls.LLM_MODEL not in cls.SUPPORTED_MODELS:
        errors.append(
            f"Неизвестная модель '{cls.LLM_MODEL}' задана в PRIMARY_MODEL. "
            f"Допустимые значения: {', '.join(cls.SUPPORTED_MODELS)}"
        )
    # ----------------------

    if errors:
        raise ValueError("❌ Ошибки конфигурации:\n" + "\n".join(f"  - {e}" for e in errors))

    return True
```

**Добавить импорт** в начало файла (если ещё нет):

```python
from typing import Optional
```


***

### 4.4 Файл: `bot_psychologist/bot_agent/llm_answerer.py`

Это **главное изменение**. Метод `generate_answer` передаёт `max_tokens=max_tokens` в `client.chat.completions.create(...)`. Для GPT-5 family это вызывает `BadRequestError`.

**Изменение:** Заменить хардкоденный параметр `max_tokens` на динамически определяемый через `Config.get_token_param_name()`.

**Изменить блок вызова API** внутри `generate_answer` (строка `response = self.client.chat.completions.create(...)`):

```python
# БЫЛО:
response = self.client.chat.completions.create(
    model=model,
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": context}
    ],
    temperature=temperature,
    max_tokens=max_tokens,
)

# СТАЛО:
# Определяем правильный параметр токенов для данной модели.
# GPT-5 и o-series требуют max_completion_tokens; GPT-4 и старше — max_tokens.
token_param = config.get_token_param_name(model)
logger.debug(f"📐 Используем параметр токенов: {token_param}={max_tokens} для модели {model}")

response = self.client.chat.completions.create(
    model=model,
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": context}
    ],
    temperature=temperature,
    **{token_param: max_tokens},
)
```

**Пояснение по `**{token_param: max_tokens}`:** Это стандартный Python-паттерн для передачи именованного аргумента с динамическим именем. OpenAI SDK принимает keyword arguments в `create()`, поэтому `**{"max_completion_tokens": 1500}` эквивалентно `max_completion_tokens=1500`. Это чистый, читаемый и расширяемый подход без `if/else` ветвлений в вызове API.

**Дополнительно:** Добавить логирование модели при инициализации клиента для быстрой диагностики:

```python
def _init_client(self):
    """Инициализация OpenAI клиента"""
    try:
        import openai
        self.client = openai.OpenAI(api_key=self.api_key)
        token_param = config.get_token_param_name()
        logger.info(
            f"✓ OpenAI клиент инициализирован | "
            f"модель: {config.LLM_MODEL} | "
            f"параметр токенов: {token_param}"
        )
    except ImportError:
        logger.error("❌ openai не установлен. Установите: pip install openai")
        raise
```


***

### 4.5 Файл: `bot_psychologist/bot_agent/config.py` — секция `info()`

Обновить метод `info()` для отображения параметра токенов в диагностике:

```python
@classmethod
def info(cls) -> str:
    token_param = cls.get_token_param_name()
    return f"""
╭─────────────────────────────────────────────╮
│ Bot Psychologist - Configuration            │
├─────────────────────────────────────────────┤
│ PROJECT_ROOT: {cls.PROJECT_ROOT}
│ DATA_ROOT:    {cls.DATA_ROOT}
│ SAG_FINAL:    {cls.SAG_FINAL_DIR}
│ LLM_MODEL:    {cls.LLM_MODEL}
│ TOKEN_PARAM:  {token_param}
│ TOP_K:        {cls.TOP_K_BLOCKS}
│ DEBUG:        {cls.DEBUG}
│ API_KEY:      {'✓ Set' if cls.OPENAI_API_KEY else '✗ Missing'}
╰─────────────────────────────────────────────╯
"""
```


***

## 5. Порядок выполнения агентом (Implementation Order)

Агент должен выполнять изменения строго в следующем порядке — каждый шаг зависит от предыдущего:

**Шаг 1** — `requirements_bot.txt`
Поднять `openai>=1.3.0` → `openai>=1.54.0`. Независимое изменение, выполняется первым.

**Шаг 2** — `.env.example`
Добавить секцию `===== LLM Configuration =====` с документацией `PRIMARY_MODEL`.

**Шаг 3** — `bot_agent/config.py`

- Добавить `SUPPORTED_MODELS`, `_MAX_COMPLETION_TOKENS_PREFIXES`
- Добавить метод `get_token_param_name()`
- Добавить импорт `from typing import Optional`
- Расширить метод `validate()`
- Обновить метод `info()`

**Шаг 4** — `bot_agent/llm_answerer.py`

- Исправить вызов `client.chat.completions.create()`: заменить `max_tokens=max_tokens` на `**{token_param: max_tokens}`
- Добавить `logger.debug` перед вызовом API
- Обновить `_init_client()` с логированием параметра токенов

***

## 6. Smoke-тесты (Acceptance Criteria)

После реализации агент или разработчик должен проверить следующие сценарии:

### Тест 1: Дефолтная конфигурация не сломана

```bash
# В .env: PRIMARY_MODEL не задан (или PRIMARY_MODEL=gpt-4o-mini)
python -c "from bot_agent.config import config; print(config.get_token_param_name())"
# Ожидаемый вывод: max_tokens
```


### Тест 2: GPT-5-mini корректно определяется

```bash
python -c "from bot_agent.config import Config; print(Config.get_token_param_name('gpt-5-mini'))"
# Ожидаемый вывод: max_completion_tokens
```


### Тест 3: o-series корректно определяется

```bash
python -c "from bot_agent.config import Config; print(Config.get_token_param_name('o3-mini'))"
# Ожидаемый вывод: max_completion_tokens
```


### Тест 4: Валидация при неизвестной модели

```bash
# Установить в .env: PRIMARY_MODEL=gpt-99-ultra-pro
python -c "from bot_agent.config import config; config.validate()"
# Ожидаемый вывод: ValueError с сообщением о недопустимой модели и списком допустимых
```


### Тест 5: Логирование при старте

```bash
# Установить в .env: PRIMARY_MODEL=gpt-5-mini
python -c "from bot_agent.llm_answerer import LLMAnswerer; LLMAnswerer()"
# В логах должна быть строка:
# ✓ OpenAI клиент инициализирован | модель: gpt-5-mini | параметр токенов: max_completion_tokens
```


### Тест 6: (если есть реальный API-ключ с доступом к gpt-5-mini)

```bash
# Установить в .env: PRIMARY_MODEL=gpt-5-mini
python -c "
from bot_agent.llm_answerer import LLMAnswerer
from bot_agent.data_loader import Block
b = Block(document_title='test', title='test', content='test content',
          start='0:00', end='1:00', youtube_link='', summary='test', score=1.0)
a = LLMAnswerer()
r = a.generate_answer('Привет, это тест', [b])
print(r['error'])  # Должно быть None
print(r['model_used'])  # Должно быть gpt-5-mini
"
```


***

## 7. Ограничения безопасности (Out-of-Scope Guards)

- **Не изменять** системные промпты (`prompt_system_base.md` и т.д.)
- **Не изменять** файлы `answer_adaptive.py`, `answer_basic.py`, `answer_graph_powered.py` — они используют `config.LLM_MODEL` напрямую через `llm_answerer`, изменений не требуют
- **Не изменять** `api/routes.py`, `api/models.py` — это задача PRD v2.0
- **Не удалять** дефолтное значение `"gpt-4o-mini"` в `os.getenv("PRIMARY_MODEL", "gpt-4o-mini")` — дефолт должен оставаться

***

## 8. Связь с PRD v2.0

После выполнения данного PRD, в PRD v2.0 (Admin Config Panel) необходимо использовать список `Config.SUPPORTED_MODELS` как источник истины для поля `options` в `EDITABLE_CONFIG`:

```python
# В bot_agent/runtimeconfig.py (PRD v2.0, шаг 4)
"LLM_MODEL": {
    "type": "select",
    "options": list(Config.SUPPORTED_MODELS),  # ← читать из Config, не хардкодить
    "group": "llm",
    "label": "GPT модель",
},
```

Это гарантирует, что Admin Panel и конфиг всегда синхронизированы.

***

## 9. Итоговый список изменений

| Файл | Тип изменения | Суть |
| :-- | :-- | :-- |
| `requirements_bot.txt` | UPDATE | `openai>=1.3.0` → `openai>=1.54.0` |
| `.env.example` | UPDATE | Добавить секцию с `PRIMARY_MODEL`, документацией и примерами |
| `bot_agent/config.py` | UPDATE | `SUPPORTED_MODELS`, `get_token_param_name()`, расширить `validate()`, обновить `info()` |
| `bot_agent/llm_answerer.py` | UPDATE | `max_tokens=` → `**{token_param: max_tokens}`, логирование |

**Итого: 4 файла, 0 новых файлов, 0 удалений.**
<span style="display:none">[^1][^10][^11][^12][^13][^14][^15][^16][^17][^18][^19][^2][^20][^21][^22][^23][^24][^25][^26][^27][^28][^29][^3][^30][^31][^32][^33][^34][^35][^36][^37][^4][^5][^6][^7][^8][^9]</span>

<div align="center">⁂</div>

[^1]: https://github.com/orgs/community/discussions/169881

[^2]: https://github.com/stanfordnlp/dspy/issues/8612

[^3]: https://github.com/sinaptik-ai/pandas-ai/issues/1684

[^4]: https://github.com/BerriAI/litellm/issues/13381

[^5]: https://github.com/bytedance/UI-TARS-desktop/issues/1192

[^6]: https://github.com/orgs/community/discussions/168107

[^7]: https://github.com/n8n-io/n8n/issues/18132

[^8]: https://github.com/langchain4j/langchain4j/issues/3511

[^9]: https://github.com/langchain-ai/langchain/discussions/32577

[^10]: https://github.com/orgs/community/discussions/169565

[^11]: https://github.com/vercel/ai/issues/7863

[^12]: https://github.com/BerriAI/litellm/pull/13386

[^13]: https://github.com/microsoft/semantic-kernel/issues/12865

[^14]: https://github.com/marketplace/models/azure-openai/gpt-5-mini

[^15]: https://github.com/anomalyco/opencode/issues/1735

[^16]: https://biss.pensoft.net/article/181968/

[^17]: http://arxiv.org/pdf/2403.05530.pdf

[^18]: http://arxiv.org/pdf/2402.09615.pdf

[^19]: https://arxiv.org/pdf/2305.15334.pdf

[^20]: http://arxiv.org/pdf/2405.15729.pdf

[^21]: https://arxiv.org/pdf/2406.09834v3.pdf

[^22]: https://arxiv.org/pdf/2310.15556.pdf

[^23]: https://arxiv.org/pdf/2307.16789.pdf

[^24]: https://linkinghub.elsevier.com/retrieve/pii/S095058492300191X

[^25]: https://developers.openai.com/api/docs/models/gpt-5-mini

[^26]: https://community.openai.com/t/what-is-going-on-with-the-gpt-5-api/1338030

[^27]: https://community.openai.com/t/gpt-5-responses-api-hundreds-of-calls-return-empty-completion-content-while-chat-works/1365210

[^28]: https://github.com/openai/openai-python/issues/2546

[^29]: https://www.cometapi.com/pl/models/openai/gpt-5-mini/

[^30]: https://developers.openai.com/api/docs/guides/latest-model/

[^31]: https://help.openai.com/en/articles/5072518-controlling-the-length-of-openai-model-responses

[^32]: https://openrouter.ai/openai/gpt-5-mini

[^33]: https://docs.aimlapi.com/api-references/text-models-llm/openai/gpt-5

[^34]: https://developers.openai.com/api/docs/models

[^35]: https://docs.aimlapi.com/api-references/text-models-llm/openai/gpt-5-mini

[^36]: https://developers.openai.com/api/docs/models/gpt-5

[^37]: https://learn.microsoft.com/en-us/azure/ai-foundry/openai/how-to/reasoning?view=foundry-classic

