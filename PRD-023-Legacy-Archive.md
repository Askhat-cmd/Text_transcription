# PRD-023 · Legacy Archive + Cleanup
## Мультиагентная система NEO — Эпоха №4

---

**Документ:** PRD-023  
**Тип:** Технический долг / архивирование  
**Версия:** 1.0  
**Статус:** В разработке  
**Автор:** Askhat (соло)  
**Репозиторий:** github.com/Askhat-cmd/Text_transcription  
**Дата создания:** 2026-04-26  
**Зависимости:** PRD-017–022 ✅ (весь пайплайн реализован и работает)  

---

## 1. Контекст и назначение

### 1.1 Что произошло в Эпохе №4

За PRD-017 → PRD-022 в `bot_psychologist/bot_agent/multiagent/` выросла полноценная мультиагентная система:

```
multiagent/
├── agents/
│   ├── state_analyzer.py          (PRD-018)
│   ├── state_analyzer_prompts.py
│   ├── thread_manager.py          (PRD-017)
│   ├── thread_manager_prompts.py
│   ├── memory_retrieval.py        (PRD-019)
│   ├── memory_retrieval_config.py
│   ├── writer_agent.py            (PRD-020)
│   ├── writer_agent_prompts.py
│   ├── validator_agent.py         (PRD-021)
│   └── validator_agent_config.py
├── contracts/
│   ├── state_snapshot.py
│   ├── thread_state.py
│   ├── memory_bundle.py
│   ├── writer_contract.py
│   └── validation_result.py
├── orchestrator.py                (PRD-022)
└── thread_storage.py
```

`159 passed` в тестах. Writeback работает. E2E проверен. `answer_adaptive.py` подключён.

### 1.2 Что такое PRD-023

PRD-023 — это **аудит и архивирование кода который больше не нужен** после перехода на мультиагентный пайплайн. Задача не сломать ничего, а:
1. Найти устаревшие/дублирующие компоненты
2. Пометить их как deprecated (не удалять — могут понадобиться для rollback)
3. Добавить в README `multiagent/` документацию архитектуры
4. Убедиться что feature-flag rollback `MULTIAGENT_ENABLED=False` полностью работает

---

## 2. Задачи

### 2.1 Аудит устаревших компонентов

IDE-агент должен **самостоятельно прочитать** следующие файлы и определить что из них дублируется или заменено мультиагентным пайплайном:

**Файлы для аудита:**
- `bot_agent/answer_adaptive.py` — найти функции/классы которые теперь вызываются только через старый путь
- `bot_agent/route_resolver.py` (если существует) — проверить пересечение с Thread Manager
- `bot_agent/adaptive_runtime.py` (если существует) — проверить пересечение с Orchestrator
- `bot_agent/prompts/` или `bot_agent/prompt_builder.py` (если существуют) — проверить пересечение с Writer Agent

**Результат аудита** — добавить в начало каждого устаревшего модуля:

```python
# DEPRECATED since PRD-022 (Epoch 4).
# Replaced by: multiagent/agents/<agent>.py
# Kept for MULTIAGENT_ENABLED=False rollback path.
# Do not extend this module — extend the multiagent equivalent.
```

**Важно:** Ничего не удалять. Только помечать.

### 2.2 README для мультиагентной системы

Создать `bot_psychologist/bot_agent/multiagent/README.md` со следующей структурой:

```markdown
# NEO Multiagent System — Epoch 4

## Пайплайн

User Message → State Analyzer → Thread Manager → Memory+Retrieval → Writer → Validator → Answer

## Агенты

| Агент | Файл | Тип | PRD |
|---|---|---|---|
| State Analyzer | agents/state_analyzer.py | hybrid (det + nano LLM) | PRD-018 |
| Thread Manager | agents/thread_manager.py | deterministic | PRD-017 |
| Memory+Retrieval | agents/memory_retrieval.py | deterministic | PRD-019 |
| Writer / NEO | agents/writer_agent.py | LLM (gpt-5-mini) | PRD-020 |
| Validator | agents/validator_agent.py | deterministic | PRD-021 |

## Контракты

| Контракт | Описание |
|---|---|
| StateSnapshot | Результат State Analyzer: нервное состояние, интент, открытость |
| ThreadState | Активная нить разговора: фаза, режим ответа, петли |
| MemoryBundle | Сборка контекста: история, профиль, RAG-чанки |
| WriterContract | Входной контракт для Writer |
| ValidationResult | Результат Validator: заблокирован/чист/quality |

## Включение

Feature flag: `MULTIAGENT_ENABLED=True` в `.env` или через FeatureFlags.

## Тесты

`pytest bot_psychologist/tests/multiagent/ -q` → 159+ passed
```

### 2.3 Проверка rollback

Убедиться что при `MULTIAGENT_ENABLED=False`:
- `answer_adaptive.py` использует старый путь без ошибок
- Ни один тест старого пути не падает

Если что-то падает — исправить без изменения логики старого пути.

---

## 3. Структура изменений

```
bot_psychologist/
└── bot_agent/
    ├── multiagent/
    │   └── README.md                    ← [новый]
    ├── answer_adaptive.py               ← пометить deprecated-блоки (если есть)
    ├── route_resolver.py (если есть)    ← пометить deprecated (если есть)
    └── adaptive_runtime.py (если есть)  ← пометить deprecated (если есть)
```

---

## 4. Тесты

### 4.1 test_legacy_rollback.py

```
LR-01  ROLLBACK_FLAG_FALSE — MULTIAGENT_ENABLED=False: answer_adaptive не вызывает orchestrator
LR-02  ROLLBACK_NO_IMPORT_ERROR — MULTIAGENT_ENABLED=False: нет ImportError при импорте answer_adaptive
LR-03  README_EXISTS — файл multiagent/README.md существует
LR-04  README_AGENTS_TABLE — README содержит строки для всех 5 агентов
LR-05  DEPRECATED_COMMENTS — (если найдены устаревшие модули) они содержат DEPRECATED-комментарий
```

### 4.2 Регрессионные чеки

```
REG-01  pytest tests/multiagent/ — 159+ passed (без изменений)
REG-02  pytest tests/test_feature_flags.py — зелёный
REG-03  Ничего не удалено из рабочего кода
```

---

## 5. Acceptance Criteria

PRD-023 завершён когда:

- [ ] `multiagent/README.md` создан с таблицей агентов и контрактов
- [ ] Устаревшие модули (если найдены) помечены DEPRECATED-комментарием
- [ ] Rollback `MULTIAGENT_ENABLED=False` работает (LR-01, LR-02)
- [ ] `pytest tests/multiagent/ -q` → 159+ passed (регрессия не допускается)
- [ ] `pytest tests/multiagent/test_legacy_rollback.py -q` → 5 passed

---

## 6. Важные замечания для IDE-агента

1. **Ничего не удалять.** Deprecated-комментарий — только маркер для разработчика.
2. **Аудит — на основе реального кода.** Прочитать файлы перед тем как помечать. Не помечать то что не является дубликатом.
3. **README.md — минимальный и точный.** Только факты: агенты, контракты, флаг, тесты. Никаких философских описаний.
4. **test_legacy_rollback.py** — тесты лёгкие: проверка флага, проверка что README существует, проверка что нет ImportError.
5. **Если устаревших модулей нет** — LR-05 можно пропустить как N/A, это допустимо.

---

*Конец PRD-023 · Legacy Archive + Cleanup*  
*Следующий и финальный документ: PRD-024 · Telegram Adapter*
