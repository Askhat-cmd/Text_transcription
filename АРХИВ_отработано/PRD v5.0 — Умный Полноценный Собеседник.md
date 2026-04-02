# PRD v5.0 — Умный Полноценный Собеседник

### Бот-психолог: Admin Panel + Routing Control + Prompt Priority + Free Mode

**Версия:** 5.0
**Ветка:** `feat/v0.7-smart-bot`
**Дата:** 2026-03-31
**Репозиторий:** [Askhat-cmd/Text_transcription / bot_psychologist](https://github.com/Askhat-cmd/Text_transcription/tree/main/bot_psychologist)
**Стек:** Python / FastAPI (бэкенд) · React + TypeScript + Vite + TailwindCSS (фронтенд `web_ui`)

***

## 0. Контекст и главная цель

Бот должен стать **полноценным развёрнутым собеседником** без искусственных ограничений токенов. Все ключевые параметры поведения управляются через Admin Panel (`localhost:3000/admin`) **без перезапуска сервера**. Архитектура pipeline (классификаторы, маршрутизация) остаётся нетронутой — добавляется только уровень конфигурируемости и **иерархия приоритетов промптов** поверх неё.

**Четыре задачи этого PRD:**

- **Блок A** — Расширить Admin Panel: исправить `Failed to fetch`, добавить недостающие параметры, связать с реальными бэкенд-параметрами
- **Блок B** — Добавить вкладку «Маршрутизация» для управления pipeline-фильтрами через UI
- **Блок C** — Убрать хардкод `max_tokens`, реализовать `FREE_CONVERSATION_MODE` и `MAX_TOKENS_SOFT_CAP`
- **Блок D** — Реализовать иерархию приоритетов промптов в `path_builder.py` (устранение противоречий на уровне кода)

**Главный инвариант — НЕ ТРОГАТЬ логику следующих файлов:**

```
bot_psychologist/bot_agent/answer_adaptive.py
bot_psychologist/bot_agent/state_classifier.py
bot_psychologist/bot_agent/sd_classifier.py
(path_builder.py — ТОЛЬКО добавить ветку FREE_CONVERSATION_MODE и функцию приоритетов, не переписывать существующую логику)
```


***

## 1. Блок A — Admin Panel: расширение и исправление

### 1.1 Текущие проблемы (диагностика)

| Проблема | Файл | Симптом |
| :-- | :-- | :-- |
| Вкладка «Промпты» не работает | `api/routes.py` | `Failed to fetch` |
| `max_tokens` задан хардкодом | `bot_agent/llm_answerer.py` | Игнорирует UI-настройки |
| Voyage TOP-K сохраняется как override | `runtime_config.py` | Баг \#3, значение 3 вместо дефолта 5 |
| `CONFIDENCE_CAP_*` нет в UI | `web_ui` | Нет полей в интерфейсе |
| Runtime вкладка — только 2 чекбокса | `web_ui` | Нет статуса системы |

### 1.2 Новые и исправленные бэкенд-эндпоинты

**Файл:** `bot_psychologist/api/routes.py`

Агенту выполнить: найти существующие admin-роуты и **дополнить** их следующими эндпоинтами (не удалять существующие):

```python
# ─── Конфигурация ───────────────────────────────────────────────────────────
GET  /api/v1/admin/config              # Вернуть все runtime параметры как JSON по группам
POST /api/v1/admin/config              # Принять dict {group: {key: value}}, обновить runtime_config
GET  /api/v1/admin/config/schema       # Вернуть схему параметров (тип, мин, макс, дефолт, nullable)

# ─── Промпты ────────────────────────────────────────────────────────────────
GET  /api/v1/admin/prompts             # Список всех .md файлов с именем и содержимым
GET  /api/v1/admin/prompts/{name}      # Содержимое одного промпта по имени файла без расширения
PUT  /api/v1/admin/prompts/{name}      # Обновить содержимое (hot-reload, без перезапуска)
POST /api/v1/admin/prompts/{name}/reset # Сбросить к .default.md снимку

# ─── Данные и статус ─────────────────────────────────────────────────────────
POST /api/v1/admin/reload-data         # Вызвать data_loader.reload()
GET  /api/v1/admin/status              # DEGRADED_MODE, DATA_SOURCE, BLOCKS_LOADED, VERSION
```

**Реализация GET /api/v1/admin/config/schema** — пример ответа, который фронтенд использует для динамического рендеринга формы:

```json
{
  "llm": {
    "MAX_TOKENS": {"type": "int_or_null", "min": 256, "max": 16000, "default": null, "nullable": true, "label": "Лимит токенов"},
    "MAX_TOKENS_SOFT_CAP": {"type": "int", "min": 1024, "max": 16000, "default": 8192, "label": "Мягкий лимит (защита от бесконечного ответа)"},
    "TEMPERATURE": {"type": "float", "min": 0.0, "max": 1.5, "default": 0.7},
    "MODEL": {"type": "enum", "options": ["gpt-4o", "gpt-4o-mini", "gpt-5-mini"], "default": "gpt-5-mini"},
    "STREAMING": {"type": "bool", "default": true}
  },
  "retrieval": {
    "TOP_K": {"type": "int", "min": 1, "max": 20, "default": 9},
    "VOYAGE_TOP_K": {"type": "int", "min": 1, "max": 10, "default": 5},
    "CONFIDENCE_CAP_HIGH": {"type": "int", "min": 1, "max": 10, "default": 7},
    "CONFIDENCE_CAP_MEDIUM": {"type": "int", "min": 1, "max": 10, "default": 5},
    "CONFIDENCE_CAP_LOW": {"type": "int", "min": 1, "max": 10, "default": 3},
    "MIN_SCORE_THRESHOLD": {"type": "float", "min": 0.0, "max": 1.0, "default": 0.1}
  },
  "routing": {
    "FREE_CONVERSATION_MODE": {"type": "bool", "default": false, "label": "Режим свободного собеседника"},
    "FAST_DETECTOR_ENABLED": {"type": "bool", "default": true},
    "FAST_DETECTOR_CONFIDENCE_THRESHOLD": {"type": "float", "min": 0.0, "max": 1.0, "default": 0.80},
    "STATE_CLASSIFIER_CONFIDENCE_THRESHOLD": {"type": "float", "min": 0.0, "max": 1.0, "default": 0.65},
    "SD_CLASSIFIER_CONFIDENCE_THRESHOLD": {"type": "float", "min": 0.0, "max": 1.0, "default": 0.65},
    "DECISION_GATE_RULE_THRESHOLD": {"type": "float", "min": 0.0, "max": 1.0, "default": 0.75},
    "PROMPT_SD_OVERRIDES_BASE": {"type": "bool", "default": true},
    "PROMPT_MODE_OVERRIDES_SD": {"type": "bool", "default": true}
  }
}
```


### 1.3 Исправление вкладки «Промпты» — горячая перезагрузка

Промпты — это `.md` файлы в `bot_agent/`. При PUT эндпоинт **перезаписывает файл на диске**. `path_builder.py` читает файлы при каждом вызове (или из кэша, который сбрасывается при записи).

Дополнительно: при запуске сервера агент должен создать снимки дефолтных промптов, если они ещё не существуют:

```python
# В startup-хуке FastAPI (main.py или lifespan)
PROMPT_FILES = [
    "prompt_system_base", "prompt_sd_green", "prompt_sd_yellow",
    "prompt_sd_orange", "prompt_sd_red", "prompt_sd_blue", "prompt_sd_purple",
    "prompt_system_level_beginner", "prompt_system_level_intermediate",
    "prompt_system_level_advanced"
]

for name in PROMPT_FILES:
    src = PROMPTS_DIR / f"{name}.md"
    dst = PROMPTS_DIR / f"{name}.default.md"
    if src.exists() and not dst.exists():
        shutil.copy2(src, dst)
        logger.info(f"[STARTUP] Created default snapshot: {name}.default.md")
```


### 1.4 Расширение вкладки «Runtime»

Добавить в UI следующие read-only индикаторы и кнопку:

```
┌─────────────────────────────────────────────────────┐
│ Статус системы                                      │
│ ─────────────────────────────────────────────────  │
│ Режим данных:     [API / JSON_FALLBACK / DEGRADED]  │
│ Блоков в памяти:  [^142]                             │
│ DEGRADED_MODE:    [●ОК / ●Активен]                  │
│ Версия:           [v0.7.0]                          │
│                                                     │
│            [ 🔄 Перезагрузить базу знаний ]         │
└─────────────────────────────────────────────────────┘
```

`GET /api/v1/admin/status` возвращает:

```json
{
  "degraded_mode": false,
  "data_source": "api",
  "blocks_loaded": 142,
  "version": "0.7.0"
}
```


### 1.5 Требования к фронтенду (Блок A)

**Файл для поиска агентом:** `bot_psychologist/web_ui/src/` — найти файл AdminPage или admin компонент.

Изменения в UI:

1. **Вкладка LLM** — добавить чекбокс «Без ограничений токенов»:
```typescript
const [unlimitedTokens, setUnlimitedTokens] = useState(config.llm.MAX_TOKENS === null);

// При сохранении:
const maxTokensValue = unlimitedTokens ? null : tokenInputValue;

// Показывать поле MAX_TOKENS_SOFT_CAP всегда (это защитный потолок)
```

2. **Вкладка Поиск** — добавить поля `CONFIDENCE_CAP_HIGH`, `CONFIDENCE_CAP_MEDIUM`, `CONFIDENCE_CAP_LOW`, `MIN_SCORE_THRESHOLD`. Убедиться что `VOYAGE_TOP_K` сохраняется без override-бага.
3. **Вкладка Промпты** — подключить к `GET/PUT /api/v1/admin/prompts`. Добавить кнопку «Сбросить к дефолту» для каждого промпта.
4. **Вкладка Runtime** — добавить статус-индикаторы и кнопку «Перезагрузить базу».

***

## 2. Блок B — Новая вкладка «Маршрутизация»

### 2.1 Новые параметры в `runtime_config.py`

**Файл:** `bot_psychologist/bot_agent/runtime_config.py`

Добавить в соответствующую секцию (не удалять существующие параметры):

```python
# ─── Routing pipeline controls ───────────────────────────────────────────────
FAST_DETECTOR_ENABLED: bool = True
FAST_DETECTOR_CONFIDENCE_THRESHOLD: float = 0.80
FAST_DETECTOR_SKIP_DOWNSTREAM: bool = True  # пропускать state+sd классификаторы при срабатывании

STATE_CLASSIFIER_ENABLED: bool = True        # read-only toggle (UI показывает предупреждение)
STATE_CLASSIFIER_CONFIDENCE_THRESHOLD: float = 0.65

SD_CLASSIFIER_ENABLED: bool = True           # read-only toggle (UI показывает предупреждение)
SD_CLASSIFIER_CONFIDENCE_THRESHOLD: float = 0.65

DECISION_GATE_RULE_THRESHOLD: float = 0.75
DECISION_GATE_LLM_ROUTER_ENABLED: bool = True

# Иерархия приоритетов в path_builder
PROMPT_SD_OVERRIDES_BASE: bool = True        # SD-промпт перекрывает base там, где пересекаются
PROMPT_MODE_OVERRIDES_SD: bool = True        # mode-директива перекрывает SD-промпт

# ─── FREE_CONVERSATION_MODE ──────────────────────────────────────────────────
FREE_CONVERSATION_MODE: bool = False
# Мягкий защитный потолок токенов (применяется только в FREE mode как защита от обрыва стрима)
MAX_TOKENS_SOFT_CAP: int = 8192
```


### 2.2 Изменения в `fast_detector.py`

**Файл:** `bot_psychologist/bot_agent/fast_detector.py`

Обернуть основную логику в проверку флага:

```python
from bot_agent import runtime_config as rc

class FastDetector:
    def detect(self, text: str) -> Optional[str]:
        if not rc.FAST_DETECTOR_ENABLED:
            return None  # всегда пропускаем в State Classifier
        
        result = self._run_detection(text)
        if result and result.confidence < rc.FAST_DETECTOR_CONFIDENCE_THRESHOLD:
            return None  # не уверены — пропускаем дальше
        return result
    
    # ... существующая логика _run_detection без изменений
```


### 2.3 UI: файл `RoutingTab.tsx`

**Создать файл:** `bot_psychologist/web_ui/src/components/admin/RoutingTab.tsx`

Верстка вкладки — вертикальная схема pipeline:

```
┌──────────────────────────────────────────────────────────────┐
│ 🧠 РЕЖИМ СВОБОДНОГО СОБЕСЕДНИКА                    [  ВКЛ  ] │
│ Бот отвечает без ограничивающих директив и без max_tokens    │
└──────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────┐
│ ⚡ Слой 1: Fast Detector                           [  ВКЛ  ] │
│  Порог уверенности: [────●──────] 0.80                       │
│  Пропускать слои 2–3 при срабатывании: [✓]                   │
└──────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────┐
│ 🟢 Слой 2: State Classifier                        [  ВКЛ  ] │
│  ⚠ Отключение влияет на качество психологической поддержки   │
│  Порог уверенности: [──────●────] 0.65                       │
└──────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────┐
│ 🟡 Слой 3: SD Classifier                           [  ВКЛ  ] │
│  ⚠ Отключение влияет на качество психологической поддержки   │
│  Порог уверенности: [──────●────] 0.65                       │
└──────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────┐
│ 🟠 Слой 4: Decision Gate                           [  ВКЛ  ] │
│  Rule threshold:      [────●────────] 0.75                   │
│  LLM Router при конфликте: [✓]                               │
└──────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────┐
│ 🔴 Слой 5: Path Builder — Приоритет промптов                 │
│  SD-промпт перекрывает base:        [✓]                      │
│  mode-директива перекрывает SD:     [✓]                      │
└──────────────────────────────────────────────────────────────┘
```

**Важно для агента:** при попытке выключить слои 2 (`State Classifier`) или 3 (`SD Classifier`) — показывать модальное предупреждение:

```typescript
const handleLayerToggle = (layer: 'state' | 'sd', value: boolean) => {
  if (!value) {
    setConfirmModal({
      open: true,
      message: "Отключение этого слоя снижает качество психологической поддержки. Продолжить?",
      onConfirm: () => updateConfig(layer + '_classifier_enabled', false)
    });
    return;
  }
  updateConfig(layer + '_classifier_enabled', value);
};
```


***

## 3. Блок C — Устранение хардкода токенов и Free Mode

### 3.1 Задание агенту: поиск и замена

Выполнить grep по кодовой базе:

```bash
grep -rn "max_tokens" bot_psychologist/bot_agent/
grep -rn "max_length" bot_psychologist/bot_agent/
grep -rn "\"brevity\"" bot_psychologist/bot_agent/
```

Для каждого найденного вхождения:

- Хардкод числа в вызове OpenAI API → заменить на логику из п. 3.2
- Хардкод числа в других местах → заменить на `rc.MAX_TOKENS`
- Строки в промптах (`"отвечай кратко"`) → **не трогать**


### 3.2 Финальная логика `llm_answerer.py`

**Файл:** `bot_psychologist/bot_agent/llm_answerer.py`

Найти метод построения параметров API-вызова и привести к следующему виду:

```python
from bot_agent import runtime_config as rc

def _build_api_params(self, messages: list) -> dict:
    params = {
        "model": rc.MODEL,
        "messages": messages,
    }

    # Температура не применяется к reasoning-моделям
    if not self._is_reasoning_model(rc.MODEL):
        params["temperature"] = rc.TEMPERATURE

    # Логика max_tokens:
    # 1. FREE_CONVERSATION_MODE=True + MAX_TOKENS=None → передаём только soft cap как защиту
    # 2. FREE_CONVERSATION_MODE=True + MAX_TOKENS задан → игнорируем MAX_TOKENS, используем soft cap
    # 3. FREE_CONVERSATION_MODE=False + MAX_TOKENS=None → не передаём max_tokens вообще
    # 4. FREE_CONVERSATION_MODE=False + MAX_TOKENS задан → передаём MAX_TOKENS
    if rc.FREE_CONVERSATION_MODE:
        params["max_tokens"] = rc.MAX_TOKENS_SOFT_CAP  # защита от обрыва стрима
    elif rc.MAX_TOKENS is not None:
        params["max_tokens"] = rc.MAX_TOKENS
    # else: max_tokens не передаётся

    if rc.STREAMING:
        params["stream"] = True

    return params
```

**Смысл `MAX_TOKENS_SOFT_CAP`:** в режиме свободного собеседника при стриминге модель не получает жёсткого лимита пользователя, но технически ограничена `8192` для защиты от обрыва соединения или зависания.

***

## 4. Блок D — Иерархия приоритетов промптов (устранение противоречий)

Это самый важный блок для достижения главной цели. Проблема: `level=beginner` говорит «упрощай», а `mode=THINKING` говорит «углубляйся» — LLM выбирает «безопасный» нейтральный средний ответ.

### 4.1 Принцип иерархии

```
mode_directive  (наивысший приоритет — что делать сейчас)
      ↓ перекрывает пересечения ↓
sd_prompt       (контекст пользователя — его уровень SD)
      ↓ перекрывает пересечения ↓
system_base     (базовые принципы психолога)
      ↓ дополняется ↓
level_prompt    (только то, что НЕ перекрыто выше)
```


### 4.2 Изменения в `path_builder.py`

**Файл:** `bot_psychologist/bot_agent/path_builder.py`

Добавить **в начало** метода сборки системного промпта (не переписывать существующую логику, добавить ветку):

```python
from bot_agent import runtime_config as rc

def build_system_prompt(self, mode: str, sd_level: str, user_level: str,
                        knowledge_blocks: list, history: list) -> str:
    
    # ─── Ветка FREE_CONVERSATION_MODE ─────────────────────────────────────
    if rc.FREE_CONVERSATION_MODE:
        return self._build_free_mode_prompt(sd_level, knowledge_blocks, history)
    
    # ─── Стандартная сборка с иерархией приоритетов ───────────────────────
    base = self._load_prompt("prompt_system_base")
    sd_instructions = self._load_prompt(f"prompt_sd_{sd_level.lower()}")
    level_instructions = self._load_prompt(f"prompt_system_level_{user_level}")
    mode_directive = self._get_mode_directive(mode)
    context_blocks = self._format_knowledge_blocks(knowledge_blocks)
    
    if rc.PROMPT_SD_OVERRIDES_BASE and rc.PROMPT_MODE_OVERRIDES_SD:
        # Применяем иерархию: mode > sd > base
        # base идёт первым как основа, sd дополняет и при конфликте перекрывает,
        # mode_directive идёт последним и имеет абсолютный приоритет
        system = (
            f"{base}\n\n"
            f"## Контекст уровня пользователя (SD):\n{sd_instructions}\n\n"
            f"## Директива режима (ПРИОРИТЕТ — перекрывает всё выше при конфликте):\n{mode_directive}\n\n"
        )
        # level_instructions добавляется ТОЛЬКО если не конфликтует с mode_directive
        if not self._conflicts_with_mode(level_instructions, mode):
            system += f"## Стиль подачи:\n{level_instructions}\n\n"
    else:
        # Старая конкатенация (если флаги выключены)
        system = f"{base}\n\n{sd_instructions}\n\n{mode_directive}\n\n{level_instructions}\n\n"
    
    system += f"## База знаний:\n{context_blocks}"
    return system

def _build_free_mode_prompt(self, sd_level: str, knowledge_blocks: list, history: list) -> str:
    """Промпт для режима свободного собеседника — без ограничивающих директив."""
    base = self._load_prompt("prompt_system_base")
    sd_context = self._load_prompt(f"prompt_sd_{sd_level.lower()}")
    context_blocks = self._format_knowledge_blocks(knowledge_blocks)
    
    return (
        f"{base}\n\n"
        f"## Контекст (SD-уровень пользователя для понимания, не как ограничение):\n{sd_context}\n\n"
        f"## База знаний:\n{context_blocks}\n\n"
        f"Отвечай настолько полно и развёрнуто, насколько этого требует вопрос. "
        f"Не ограничивай себя в длине. Приводи примеры из базы знаний."
    )

def _conflicts_with_mode(self, level_text: str, mode: str) -> bool:
    """Определяет, конфликтует ли level_instructions с текущим mode."""
    EXPANDING_MODES = {"THINKING", "INTEGRATION", "VALIDATION"}
    RESTRICTING_KEYWORDS = ["кратко", "упрощай", "не перегружай", "один вопрос"]
    
    if mode in EXPANDING_MODES:
        return any(kw in level_text.lower() for kw in RESTRICTING_KEYWORDS)
    return False
```


***

## 5. Порядок выполнения и коммиты

Агент выполняет задачи строго в следующем порядке. Тесты пишутся **параллельно** с каждым Fix, не в конце:

```
[Fix C + Test]  llm_answerer: параметризовать max_tokens, добавить FREE_CONVERSATION_MODE,
                MAX_TOKENS_SOFT_CAP. Тест: tests/test_llm_answerer.py

[Fix D + Test]  path_builder: добавить иерархию приоритетов и FREE ветку.
                Тест: tests/test_path_builder.py

[Fix B1 + Test] runtime_config: добавить routing параметры и FREE_CONVERSATION_MODE.
                Тест: tests/test_routing_config.py

[Fix B2]        fast_detector: обернуть в FAST_DETECTOR_ENABLED флаг.

[Fix A1 + Test] api/routes: добавить /admin/config, /admin/config/schema, /admin/status.
                Тест: tests/test_admin_api.py (часть 1)

[Fix A2 + Test] api/routes: добавить /admin/prompts CRUD.
                Тест: tests/test_admin_api.py (часть 2)

[Fix A3]        api/routes: добавить /admin/reload-data.
                Startup-хук: создание .default.md снимков.

[UI A]          web_ui: починить вкладку Промпты, добавить чекбокс токенов,
                поля CONFIDENCE_CAP_*, обновить Runtime вкладку.

[UI B]          web_ui: создать RoutingTab.tsx с pipeline-схемой и модальными
                предупреждениями для слоёв 2–3.

[Test-Regress]  Прогнать полный suite: pytest tests/ --tb=short

[Docs]          CHANGELOG: v0.7.0 entry
```

**Ветка:** `feat/v0.7-smart-bot` → PR в `main`

***

## 6. Полные тесты

### 6.1 `tests/test_llm_answerer.py`

```python
import pytest
from unittest.mock import patch, MagicMock
from bot_agent import runtime_config as rc
from bot_agent.llm_answerer import LLMAnswerer


@pytest.fixture(autouse=True)
def reset_config():
    """Сбрасывать конфиг до дефолта перед каждым тестом."""
    rc.FREE_CONVERSATION_MODE = False
    rc.MAX_TOKENS = None
    rc.MAX_TOKENS_SOFT_CAP = 8192
    rc.TEMPERATURE = 0.7
    rc.MODEL = "gpt-5-mini"
    rc.STREAMING = False
    yield


class TestMaxTokensLogic:

    def test_free_mode_uses_soft_cap(self):
        """FREE_CONVERSATION_MODE=True → max_tokens = MAX_TOKENS_SOFT_CAP."""
        rc.FREE_CONVERSATION_MODE = True
        rc.MAX_TOKENS = None
        params = LLMAnswerer()._build_api_params([])
        assert params.get("max_tokens") == 8192

    def test_free_mode_ignores_explicit_max_tokens(self):
        """В FREE mode MAX_TOKENS=2000 игнорируется, используется soft cap."""
        rc.FREE_CONVERSATION_MODE = True
        rc.MAX_TOKENS = 2000
        params = LLMAnswerer()._build_api_params([])
        assert params.get("max_tokens") == rc.MAX_TOKENS_SOFT_CAP
        assert params.get("max_tokens") != 2000

    def test_normal_mode_null_tokens_no_param(self):
        """FREE=False, MAX_TOKENS=None → max_tokens не передаётся совсем."""
        rc.FREE_CONVERSATION_MODE = False
        rc.MAX_TOKENS = None
        params = LLMAnswerer()._build_api_params([])
        assert "max_tokens" not in params

    def test_normal_mode_explicit_tokens_applied(self):
        """FREE=False, MAX_TOKENS=2000 → max_tokens=2000."""
        rc.FREE_CONVERSATION_MODE = False
        rc.MAX_TOKENS = 2000
        params = LLMAnswerer()._build_api_params([])
        assert params.get("max_tokens") == 2000

    def test_soft_cap_configurable(self):
        """MAX_TOKENS_SOFT_CAP можно изменить — и это применяется в FREE mode."""
        rc.FREE_CONVERSATION_MODE = True
        rc.MAX_TOKENS_SOFT_CAP = 4096
        params = LLMAnswerer()._build_api_params([])
        assert params.get("max_tokens") == 4096

    def test_temperature_skipped_for_reasoning_model(self):
        """Для reasoning-модели temperature не передаётся."""
        rc.MODEL = "gpt-5-mini"
        params = LLMAnswerer()._build_api_params([])
        assert "temperature" not in params

    def test_temperature_present_for_standard_model(self):
        """Для gpt-4o температура передаётся."""
        rc.MODEL = "gpt-4o"
        rc.TEMPERATURE = 0.8
        params = LLMAnswerer()._build_api_params([])
        assert params.get("temperature") == 0.8

    def test_streaming_flag_adds_stream_param(self):
        """STREAMING=True → stream=True в params."""
        rc.STREAMING = True
        params = LLMAnswerer()._build_api_params([])
        assert params.get("stream") is True
```


### 6.2 `tests/test_path_builder.py`

```python
import pytest
from bot_agent import runtime_config as rc
from bot_agent.path_builder import PathBuilder


@pytest.fixture(autouse=True)
def reset_config():
    rc.FREE_CONVERSATION_MODE = False
    rc.PROMPT_SD_OVERRIDES_BASE = True
    rc.PROMPT_MODE_OVERRIDES_SD = True
    yield


class TestFreeConversationMode:

    def test_free_mode_no_restricting_directives(self):
        """FREE mode: промпт не содержит ограничивающих директив."""
        rc.FREE_CONVERSATION_MODE = True
        builder = PathBuilder()
        prompt = builder.build_system_prompt(
            mode="PRESENCE", sd_level="GREEN", user_level="beginner",
            knowledge_blocks=[], history=[]
        )
        restricting = ["задай один вопрос", "не перегружай", "отвечай кратко"]
        for phrase in restricting:
            assert phrase not in prompt.lower(), f"Найдена ограничивающая директива: '{phrase}'"

    def test_free_mode_contains_expansion_instruction(self):
        """FREE mode: промпт содержит инструкцию отвечать развёрнуто."""
        rc.FREE_CONVERSATION_MODE = True
        builder = PathBuilder()
        prompt = builder.build_system_prompt(
            mode="THINKING", sd_level="BLUE", user_level="advanced",
            knowledge_blocks=[], history=[]
        )
        assert "полно" in prompt.lower() or "развёрн" in prompt.lower()

    def test_free_mode_includes_sd_as_context_not_restriction(self):
        """FREE mode: SD-промпт включается как контекст, а не ограничение."""
        rc.FREE_CONVERSATION_MODE = True
        builder = PathBuilder()
        prompt = builder.build_system_prompt(
            mode="THINKING", sd_level="RED", user_level="beginner",
            knowledge_blocks=[], history=[]
        )
        assert len(prompt) > 100  # промпт не пустой
        assert "RED" in prompt or "red" in prompt.lower() or builder._load_prompt("prompt_sd_red")[:20] in prompt


class TestPromptPriorityHierarchy:

    def test_mode_directive_appears_after_sd(self):
        """Иерархия: mode_directive идёт после SD-инструкций в тексте."""
        rc.FREE_CONVERSATION_MODE = False
        rc.PROMPT_MODE_OVERRIDES_SD = True
        builder = PathBuilder()
        prompt = builder.build_system_prompt(
            mode="THINKING", sd_level="GREEN", user_level="intermediate",
            knowledge_blocks=[], history=[]
        )
        # Директива режима должна быть позиционирована ПОСЛЕ SD
        sd_text = builder._load_prompt("prompt_sd_green")
        mode_text = builder._get_mode_directive("THINKING")
        if sd_text[:20] in prompt and mode_text[:20] in prompt:
            assert prompt.index(mode_text[:20]) > prompt.index(sd_text[:20])

    def test_level_beginner_excluded_in_thinking_mode(self):
        """beginner-инструкции с ограничивающими словами не попадают при mode=THINKING."""
        rc.FREE_CONVERSATION_MODE = False
        rc.PROMPT_MODE_OVERRIDES_SD = True
        builder = PathBuilder()
        level_text = builder._load_prompt("prompt_system_level_beginner")
        
        if builder._conflicts_with_mode(level_text, "THINKING"):
            prompt = builder.build_system_prompt(
                mode="THINKING", sd_level="GREEN", user_level="beginner",
                knowledge_blocks=[], history=[]
            )
            # Конфликтующие фразы не должны присутствовать
            restricting = ["кратко", "упрощай", "не перегружай"]
            conflicting_found = [p for p in restricting if p in level_text.lower() and p in prompt.lower()]
            assert len(conflicting_found) == 0

    def test_conflicts_with_mode_detection(self):
        """_conflicts_with_mode корректно определяет конфликт."""
        builder = PathBuilder()
        assert builder._conflicts_with_mode("Отвечай кратко и не перегружай", "THINKING") is True
        assert builder._conflicts_with_mode("Отвечай кратко и не перегружай", "PRESENCE") is False
        assert builder._conflicts_with_mode("Будь внимателен к деталям", "THINKING") is False
```


### 6.3 `tests/test_routing_config.py`

```python
import pytest
from bot_agent import runtime_config as rc


@pytest.fixture(autouse=True)
def reset_routing():
    rc.FREE_CONVERSATION_MODE = False
    rc.FAST_DETECTOR_ENABLED = True
    rc.FAST_DETECTOR_CONFIDENCE_THRESHOLD = 0.80
    rc.STATE_CLASSIFIER_ENABLED = True
    rc.STATE_CLASSIFIER_CONFIDENCE_THRESHOLD = 0.65
    rc.SD_CLASSIFIER_ENABLED = True
    rc.SD_CLASSIFIER_CONFIDENCE_THRESHOLD = 0.65
    rc.PROMPT_SD_OVERRIDES_BASE = True
    rc.PROMPT_MODE_OVERRIDES_SD = True
    yield


class TestFastDetectorConfig:

    def test_fast_detector_disabled_returns_none(self):
        """FAST_DETECTOR_ENABLED=False → detect() всегда возвращает None."""
        rc.FAST_DETECTOR_ENABLED = False
        from bot_agent.fast_detector import FastDetector
        detector = FastDetector()
        result = detector.detect("всё хорошо, я справляюсь")
        assert result is None

    def test_fast_detector_low_confidence_returns_none(self):
        """Если уверенность ниже порога — fast detector пропускает."""
        rc.FAST_DETECTOR_CONFIDENCE_THRESHOLD = 0.99
        from bot_agent.fast_detector import FastDetector
        detector = FastDetector()
        # Любой реальный запрос, который раньше мог сработать — теперь не должен
        result = detector.detect("мне немного грустно")
        assert result is None


class TestRuntimeConfigHotReload:

    def test_free_mode_toggle_immediate(self):
        """FREE_CONVERSATION_MODE меняется в runtime без перезапуска."""
        assert rc.FREE_CONVERSATION_MODE is False
        rc.FREE_CONVERSATION_MODE = True
        assert rc.FREE_CONVERSATION_MODE is True

    def test_all_routing_params_have_defaults(self):
        """Все routing параметры существуют и имеют корректный тип."""
        assert isinstance(rc.FAST_DETECTOR_ENABLED, bool)
        assert isinstance(rc.FAST_DETECTOR_CONFIDENCE_THRESHOLD, float)
        assert isinstance(rc.STATE_CLASSIFIER_ENABLED, bool)
        assert isinstance(rc.STATE_CLASSIFIER_CONFIDENCE_THRESHOLD, float)
        assert isinstance(rc.SD_CLASSIFIER_ENABLED, bool)
        assert isinstance(rc.SD_CLASSIFIER_CONFIDENCE_THRESHOLD, float)
        assert isinstance(rc.PROMPT_SD_OVERRIDES_BASE, bool)
        assert isinstance(rc.PROMPT_MODE_OVERRIDES_SD, bool)
        assert isinstance(rc.FREE_CONVERSATION_MODE, bool)
        assert isinstance(rc.MAX_TOKENS_SOFT_CAP, int)
```


### 6.4 `tests/test_admin_api.py`

```python
import pytest
import shutil
from pathlib import Path
from unittest.mock import patch
from bot_agent import runtime_config as rc

ADMIN_HEADERS = {"X-Admin-Token": "test-admin-secret"}


class TestAdminConfigEndpoints:

    def test_get_config_returns_all_groups(self, client):
        r = client.get("/api/v1/admin/config", headers=ADMIN_HEADERS)
        assert r.status_code == 200
        data = r.json()
        assert "llm" in data
        assert "retrieval" in data
        assert "routing" in data

    def test_get_config_schema_has_all_groups(self, client):
        r = client.get("/api/v1/admin/config/schema", headers=ADMIN_HEADERS)
        assert r.status_code == 200
        schema = r.json()
        assert "llm" in schema
        assert "retrieval" in schema
        assert "routing" in schema
        assert "FREE_CONVERSATION_MODE" in schema["routing"]
        assert "MAX_TOKENS" in schema["llm"]

    def test_post_config_updates_runtime(self, client):
        r = client.post("/api/v1/admin/config",
                        json={"llm": {"MAX_TOKENS": None}},
                        headers=ADMIN_HEADERS)
        assert r.status_code == 200
        assert rc.MAX_TOKENS is None

    def test_post_config_free_mode_hot_reload(self, client):
        client.post("/api/v1/admin/config",
                    json={"routing": {"FREE_CONVERSATION_MODE": True}},
                    headers=ADMIN_HEADERS)
        assert rc.FREE_CONVERSATION_MODE is True

    def test_post_config_max_tokens_soft_cap(self, client):
        client.post("/api/v1/admin/config",
                    json={"llm": {"MAX_TOKENS_SOFT_CAP": 4096}},
                    headers=ADMIN_HEADERS)
        assert rc.MAX_TOKENS_SOFT_CAP == 4096

    def test_get_status_returns_required_fields(self, client):
        r = client.get("/api/v1/admin/status", headers=ADMIN_HEADERS)
        assert r.status_code == 200
        data = r.json()
        assert "degraded_mode" in data
        assert "data_source" in data
        assert "blocks_loaded" in data
        assert "version" in data

    def test_reload_data_calls_data_loader(self, client):
        from bot_agent import data_loader
        with patch.object(data_loader, 'reload') as mock_reload:
            r = client.post("/api/v1/admin/reload-data", headers=ADMIN_HEADERS)
            assert r.status_code == 200
            mock_reload.assert_called_once()


class TestAdminPromptsEndpoints:

    def test_get_prompts_returns_all_md_files(self, client):
        r = client.get("/api/v1/admin/prompts", headers=ADMIN_HEADERS)
        assert r.status_code == 200
        names = [p["name"] for p in r.json()]
        assert "prompt_system_base" in names
        assert "prompt_sd_green" in names
        assert "prompt_sd_red" in names
        assert "prompt_sd_blue" in names

    def test_get_single_prompt_returns_content(self, client):
        r = client.get("/api/v1/admin/prompts/prompt_sd_green", headers=ADMIN_HEADERS)
        assert r.status_code == 200
        data = r.json()
        assert "content" in data
        assert len(data["content"]) > 0

    def test_put_prompt_updates_content(self, client):
        new_content = "# Test\nОтвечай развёрнуто и полно без ограничений."
        r = client.put("/api/v1/admin/prompts/prompt_sd_green",
                       json={"content": new_content},
                       headers=ADMIN_HEADERS)
        assert r.status_code == 200
        r2 = client.get("/api/v1/admin/prompts/prompt_sd_green", headers=ADMIN_HEADERS)
        assert r2.json()["content"] == new_content

    def test_reset_prompt_restores_default(self, client, tmp_prompts_dir):
        """Сброс промпта возвращает содержимое из .default.md снимка."""
        client.put("/api/v1/admin/prompts/prompt_sd_green",
                   json={"content": "CHANGED"},
                   headers=ADMIN_HEADERS)
        r = client.post("/api/v1/admin/prompts/prompt_sd_green/reset",
                        headers=ADMIN_HEADERS)
        assert r.status_code == 200
        r2 = client.get("/api/v1/admin/prompts/prompt_sd_green", headers=ADMIN_HEADERS)
        assert r2.json()["content"] != "CHANGED"

    def test_prompts_endpoint_not_returns_failed_to_fetch(self, client):
        """Ключевой тест: эндпоинт промптов отвечает без ошибок."""
        r = client.get("/api/v1/admin/prompts", headers=ADMIN_HEADERS)
        assert r.status_code == 200
        assert r.json() is not None
```


***

## 7. Definition of Done

| \# | Критерий | Как проверить |
| :-- | :-- | :-- |
| 1 | Вкладка «Промпты» не показывает `Failed to fetch` | `:3000/admin` → Промпты → список загружен |
| 2 | Чекбокс «Без ограничений» работает и сохраняется | Включить → отправить вопрос → в логах нет `max_tokens` |
| 3 | `FREE_CONVERSATION_MODE=true` даёт развёрнутые ответы | Включить → задать вопрос → ответ 3+ абзаца без обрыва |
| 4 | `MAX_TOKENS_SOFT_CAP` работает как защита в FREE mode | Лог API-вызова содержит `max_tokens: 8192` при FREE mode |
| 5 | Вкладка «Маршрутизация» показывает 5 слоёв | `:3000/admin` → Маршрутизация → 5 карточек отрисованы |
| 6 | Предупреждение при отключении слоёв 2–3 | Попробовать выключить → появляется модальное окно |
| 7 | Кнопка «Перезагрузить базу» работает | Нажать → в логах `[DATA_LOADER] reload triggered` |
| 8 | Промпт-противоречие устранено (`THINKING` + `beginner`) | Задать философский вопрос → ответ развёрнутый, не «безопасный средний» |
| 9 | `.default.md` снимки созданы при старте | `ls bot_agent/*.default.md` → 10 файлов |
| 10 | Все новые тесты green, регрессия не сломана | `pytest tests/ --tb=short` → 0 failed |

