# PRD-024 · Multiagent .env Configuration + Smoke Test
## Мультиагентная система NEO — Эпоха №4, финал

---

**Документ:** PRD-024  
**Тип:** Конфигурация + первый живой прогон  
**Версия:** 1.0  
**Статус:** В разработке  
**Автор:** Askhat (соло)  
**Репозиторий:** github.com/Askhat-cmd/Text_transcription  
**Дата создания:** 2026-04-26  
**Зависимости:** PRD-017–023 ✅  

---

## 1. Контекст

### 1.1 Что нужно сделать

Система реализована, тесты зелёные (`164 passed`). Остался один шаг: добавить переменные окружения для мультиагентных моделей в `.env.example` и задокументировать что нужно прописать в реальном `.env` перед первым живым запуском.

**Telegram Adapter (`telegram_adapter/`) — вне скоупа PRD-024.** Это отдельный пакет по адресу `C:\My_practice\Text_transcription	elegram_adapter`. Подключение к реальному Telegram будет после полной отладки бота. PRD-024 касается только внутренней конфигурации системы.

### 1.2 Что уже есть в .env.example

В `.env.example` уже существуют:
- `PRIMARY_MODEL`, `CLASSIFIER_MODEL` — для основного LLM-пути
- `MULTIAGENT_ENABLED` — **отсутствует** (нужно добавить)
- Модели для мультиагентных агентов — **отсутствуют** (нужно добавить)
- `TELEGRAM_ENABLED=false`, `TELEGRAM_MODE=mock` — уже есть

---

## 2. Задача 1 — Обновить .env.example

### 2.1 Добавить секцию Multiagent в .env.example

Добавить новую секцию **после** блока `PRD Modernization Feature Flags`:

```dotenv
# ===== Multiagent System (PRD-017..023 / Epoch 4) =====
# Включить мультиагентный пайплайн вместо классического каскада.
# false = классический путь (answer_adaptive legacy), true = NEO multiagent.
MULTIAGENT_ENABLED=false

# Модель для State Analyzer Agent (PRD-018).
# Используется для LLM-классификации нервного состояния и интента.
# Recommended: gpt-4o-mini (дешево, быстро) или gpt-5-nano (если доступен).
# Fallback при недоступности: детерминированный путь внутри агента.
STATE_ANALYZER_MODEL=gpt-4o-mini

# Модель для Writer Agent / NEO (PRD-020).
# Генерирует финальный ответ пользователю.
# Recommended: gpt-4o-mini для production, gpt-5-mini для A/B-тестирования.
WRITER_MODEL=gpt-4o-mini

# Таймаут для LLM-вызовов мультиагентного пайплайна (секунды).
MULTIAGENT_LLM_TIMEOUT=30

# Максимальная длина ответа Writer Agent (токены).
MULTIAGENT_MAX_TOKENS=600

# Температура Writer Agent. 0.0 = детерминированный, 0.7 = креативный.
MULTIAGENT_TEMPERATURE=0.7
```

### 2.2 Что НЕ добавлять

- Не добавлять переменные для Memory Retrieval (он использует ChromaDB/существующий embedding стек)
- Не добавлять переменные для Thread Manager и Validator (детерминированные, без LLM)
- Не добавлять Telegram-переменные (уже есть)

---

## 3. Задача 2 — Проверить что агенты читают переменные

### 3.1 State Analyzer

В `state_analyzer.py` уже используется модель — проверить что она читается из env:

```python
# Должно быть:
import os
model = os.getenv("STATE_ANALYZER_MODEL", "gpt-4o-mini")
```

Если сейчас хардкод — заменить на `os.getenv`. Если уже читается из env или из `config.py` — подтвердить и не изменять.

### 3.2 Writer Agent

Аналогично для `writer_agent.py`:

```python
model = os.getenv("WRITER_MODEL", "gpt-4o-mini")
timeout = float(os.getenv("MULTIAGENT_LLM_TIMEOUT", "30"))
max_tokens = int(os.getenv("MULTIAGENT_MAX_TOKENS", "600"))
temperature = float(os.getenv("MULTIAGENT_TEMPERATURE", "0.7"))
```

Если уже есть — подтвердить. Если хардкод — заменить.

---

## 4. Задача 3 — Smoke Test

### 4.1 Создать test_multiagent_smoke.py

Это не unit-тест с моками. Это **конфигурационный smoke-тест** — проверяет что система правильно настроена для запуска.

```
tests/multiagent/test_multiagent_smoke.py
```

**Тесты:**

```
SM-01  ENV_MULTIAGENT_KEY_EXISTS — os.getenv("MULTIAGENT_ENABLED") существует как ключ в os.environ (даже если "false")
SM-02  STATE_ANALYZER_MODEL_READABLE — STATE_ANALYZER_MODEL читается, значение строка
SM-03  WRITER_MODEL_READABLE — WRITER_MODEL читается, значение строка  
SM-04  ORCHESTRATOR_IMPORTABLE — from bot_agent.multiagent.orchestrator import orchestrator — без ошибок
SM-05  ALL_AGENTS_IMPORTABLE — state_analyzer_agent, thread_manager_agent, memory_retrieval_agent, writer_agent, validator_agent — все импортируются без ошибок
SM-06  ALL_CONTRACTS_IMPORTABLE — StateSnapshot, ThreadState, MemoryBundle, WriterContract, ValidationResult — все импортируются
SM-07  FEATURE_FLAG_READABLE — feature_flags.is_enabled("MULTIAGENT_ENABLED") — не бросает исключений
SM-08  THREAD_STORAGE_INIT — thread_storage.load_active("smoke_test_user") — не бросает исключений, возвращает None или ThreadState
SM-09  TIMEOUT_VALUE_VALID — MULTIAGENT_LLM_TIMEOUT — если задан, то float > 0
SM-10  MAX_TOKENS_VALUE_VALID — MULTIAGENT_MAX_TOKENS — если задан, то int > 0
```

**Важно:** SM-01..SM-10 должны работать **без реального API-ключа**, без сети, без ChromaDB. Это проверка конфигурации, не функциональности.

---

## 5. Задача 4 — Чеклист первого живого запуска (документ)

Создать `bot_psychologist/docs/MULTIAGENT_LAUNCH_CHECKLIST.md`:

```markdown
# Чеклист первого живого запуска мультиагентной системы

## 1. Подготовка .env

- [ ] `OPENAI_API_KEY` — задан и действителен
- [ ] `MULTIAGENT_ENABLED=true` — выставлен
- [ ] `STATE_ANALYZER_MODEL=gpt-4o-mini` — выставлен
- [ ] `WRITER_MODEL=gpt-4o-mini` — выставлен
- [ ] `MULTIAGENT_LLM_TIMEOUT=30` — выставлен

## 2. Проверка конфигурации

- [ ] `pytest tests/multiagent/test_multiagent_smoke.py -v` → 10 passed
- [ ] `pytest tests/multiagent/ -q` → 164+ passed

## 3. Первый тестовый запрос

Вызвать вручную через Python REPL или скрипт:

```python
import asyncio
from bot_agent.multiagent.orchestrator import orchestrator

result = asyncio.run(orchestrator.run(
    query="Я чувствую тревогу перед важным событием",
    user_id="smoke_test_001"
))
print("Status:", result["status"])
print("Phase:", result["phase"])
print("Mode:", result["response_mode"])
print("Answer:", result["answer"][:200])
print("Debug:", result["debug"])
```

Ожидаемый результат:
- `status == "ok"`
- `answer` — непустой русский текст
- `validator_blocked == False`
- Нет исключений в логах

## 4. После успешного первого запроса

- [ ] Проверить логи (`logs/`) — нет ERROR, только DEBUG/INFO
- [ ] `validator_blocked` — `False` (ответ не заблокирован)
- [ ] `phase` — один из: `clarify`, `explore`, `stabilize`, `integrate`
- [ ] Записать результат в `CHANGELOG.md` как "Epoch 4: first live run"

## 5. Откат (если что-то не так)

- [ ] Выставить `MULTIAGENT_ENABLED=false` в `.env`
- [ ] Перезапустить бота — классический каскад работает без изменений
- [ ] Проблему логировать в issues проекта
```

---

## 6. Структура изменений

```
bot_psychologist/
├── .env.example                                    ← добавить секцию Multiagent
├── bot_agent/
│   └── multiagent/
│       └── agents/
│           ├── state_analyzer.py                   ← проверить/исправить чтение env
│           └── writer_agent.py                     ← проверить/исправить чтение env
├── docs/
│   └── MULTIAGENT_LAUNCH_CHECKLIST.md             ← [новый]
└── tests/
    └── multiagent/
        └── test_multiagent_smoke.py                ← [новый]
```

---

## 7. Тесты

### 7.1 Список тестов

```
SM-01..SM-10  test_multiagent_smoke.py (см. секцию 4.1)
```

### 7.2 Регрессионные чеки

```
REG-01  pytest tests/multiagent/ -q — 164+ passed (все PRD-017..023 зелёные)
REG-02  pytest tests/test_feature_flags.py -q — зелёный
REG-03  .env.example корректный (нет синтаксических ошибок)
REG-04  Без OPENAI_API_KEY — SM-тесты проходят (они не делают сетевых вызовов)
```

---

## 8. Acceptance Criteria

PRD-024 завершён когда:

- [ ] `.env.example` — секция Multiagent добавлена
- [ ] `state_analyzer.py` и `writer_agent.py` — читают модели из env (не хардкод)
- [ ] `tests/multiagent/test_multiagent_smoke.py` — создан, 10 тестов зелёные
- [ ] `docs/MULTIAGENT_LAUNCH_CHECKLIST.md` — создан
- [ ] `pytest tests/multiagent/ -q` → 174+ passed

---

## 9. Что НЕ входит в PRD-024

- Подключение `telegram_adapter/` к реальному Telegram — это отдельный этап после полной отладки
- Интеграция веб-админки с мультиагентным трейсом — PRD-025
- A/B тестирование старого vs нового пайплайна — PRD-026
- Никаких изменений в контрактах, агентах или оркестраторе

---

*Конец PRD-024 · Multiagent .env Configuration + Smoke Test*  
*После PRD-024 Эпоха №4 завершена. Следующие шаги: реальная отладка → PRD-025 (веб-админка трейс) → PRD-026 (A/B) → Telegram Adapter.*
