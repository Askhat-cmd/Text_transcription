# PRD: Упрощение и оптимизация системы ретривала Bot Psychologist

**Версия:** 1.0
**Дата:** 24.03.2026
**Исполнитель:** Cursor IDE Agent 
**Проект:** `C:\My_practice\Text_transcription\bot_psychologist`

***

## ⚠️ ИНСТРУКЦИЯ АГЕНТУ — ЧИТАТЬ ПЕРВЫМ

Перед началом работы агент обязан:

1. **Создать файл задач** `PRD_TASKS.md` в корне проекта со списком всех тасков из этого PRD (чекбоксы). При каждом завершённом шаге — отмечать `[x]`. Это обеспечит возможность продолжить работу в новом чате.
2. **Создать ветку** `git checkout -b refactor/simplify-retrieval-pipeline`
3. **Сделать коммит** текущего состояния перед началом: `git add -A && git commit -m "checkpoint: before retrieval simplification"`
4. **После каждого этапа** делать коммит с понятным сообщением.
5. Если сессия прерывается — в следующем чате агент **первым делом читает** `PRD_TASKS.md` и продолжает с первого незакрытого таска.

***

## 1. Контекст и мотивация

### Текущее состояние

Система ретривала содержит 5 последовательных фильтров:

```
TF-IDF/API → SD-фильтр → Voyage Reranker → Stage-фильтр → Confidence cap → LLM
```

Анализ реальных логов показал:

- **Stage-фильтр** всегда возвращает 0 блоков (все блоки базы имеют complexity 0.56–0.78, порог 0.45) → всегда срабатывает аварийный fallback на топ-3
- **SD-фильтр** вырезает семантически релевантные блоки только потому что их SD-тег не совпадает с уровнем пользователя
- **Confidence scorer** режет количество блоков на основе `voyage_confidence`, который равен 0.0 при сбоях Voyage API
- Реально в LLM попадают блоки, отобранные **не по семантике, а по fallback-логике**


### Цель

Убрать жёсткие фильтры блоков. Оставить только семантический отбор. Передать задачу адаптации языка LLM через промпт.

### Принцип

> «Чем меньше жёстких правил в отборе блоков — тем точнее работает семантика. Задача системы — найти релевантные по смыслу блоки. Задача LLM — подать их правильным языком под пользователя.»

### Целевая схема

```
Запрос пользователя
    ↓
1. Semantic Search (API / TF-IDF fallback)   ← отбор по смыслу
    ↓
2. Voyage Reranker                            ← точная семантическая переупорядочка
    ↓
3. TOP-K = 3–5 блоков                        ← простой лимит
    ↓
4. LLM (SD-уровень + state — в промпте)      ← адаптация языка
```


***

## 2. Скоуп изменений

### Удалить полностью (код + логи + UI)

- `stage_filter.py` — весь модуль
- `sd_filter.py` — как фильтр блоков (файл удалить или полностью очистить логику фильтрации)
- Все вызовы `stage_filter` и `sd_filter` в `answer_adaptive.py` и других модулях
- Все упоминания `complexity_cap`, `stage`, `STAGE_FILTER` в логах (убрать log-строки)
- UI-элементы в веб-админке, связанные с этими фильтрами


### Оставить и адаптировать

- `sd_classifier.py` — классификатор SD-уровня **оставить**, убрать только его использование для фильтрации блоков
- SD-уровень и state — **передавать в LLM-промпт** как контекст
- `voyage_reranker.py` — оставить, убрать зависимость confidence от его результата
- TF-IDF — оставить как fallback при недоступности API
- FAST_PATH / CLARIFICATION — логику для приветствий оставить
- `confidence_scorer.py` — упростить: убрать `voyage_confidence` из формулы отсева блоков, оставить только для FAST_PATH-решения


### Не трогать

- `state_classifier.py` (curious/stagnant/confused/etc.)
- `conversation_memory.py`, `semantic_memory.py`
- `llm_answerer.py`
- `path_builder.py`, `graph_client.py`
- API-роуты, авторизация, UI (кроме удаления элементов Stage/SD-фильтра)

***

## 3. Этапы выполнения


***

### ЭТАП 0 — Подготовка и аудит

**Таски для `PRD_TASKS.md`:**

```
[ ] 0.1 Создать PRD_TASKS.md с полным чеклистом
[ ] 0.2 Создать ветку refactor/simplify-retrieval-pipeline
[ ] 0.3 Сделать checkpoint-коммит
[ ] 0.4 Запустить существующие тесты: cd tests && python -m pytest -v --tb=short > tests_before.txt
[ ] 0.5 Сохранить tests_before.txt как baseline
[ ] 0.6 Составить карту всех файлов, затронутых изменениями (grep -r "stage_filter\|sd_filter\|complexity_cap" --include="*.py" -l)
[ ] 0.7 Зафиксировать найденные файлы в PRD_TASKS.md
```

**Критерий готовности:** есть baseline тестов, есть список файлов для изменений, ветка создана.

***

### ЭТАП 1 — Удаление Stage-фильтра

#### 1.1 Удаление модуля

```
[ ] 1.1 Удалить файл bot_agent/retrieval/stage_filter.py
[ ] 1.2 Найти все импорты: grep -r "stage_filter\|StageFilter\|complexity_cap" --include="*.py"
[ ] 1.3 Удалить все импорты stage_filter из найденных файлов
[ ] 1.4 В answer_adaptive.py удалить блок вызова stage_filter (обычно секция после rerank)
[ ] 1.5 Убедиться что после удаления пайплайн: initial → SD → rerank → cap → LLM
```


#### 1.2 Удаление из логов

```
[ ] 1.6 Найти все log-строки с STAGE_FILTER, complexity_cap: grep -rn "STAGE_FILTER\|complexity_cap\|stage_filter" --include="*.py"
[ ] 1.7 Удалить найденные logger.info/warning строки
```


#### 1.3 Удаление из веб-админки

```
[ ] 1.8 Найти UI-компоненты: grep -r "stage\|complexity" в frontend/ или static/ (JS/HTML/JSX файлы)
[ ] 1.9 Удалить элементы Stage-фильтра из трейс-панели (секция в Pipeline Timeline)
[ ] 1.10 Удалить из Config Snapshot отображение stage-параметров
[ ] 1.11 Проверить что в трейсе нет строк "Stage фильтр: skip/active"
```


#### 1.4 Тест этапа

```
[ ] 1.12 Запустить: python -m pytest tests/ -k "retrieval or filter" -v
[ ] 1.13 Сделать тестовый запрос через API: POST /api/v1/questions/adaptive-stream с тестовым query
[ ] 1.14 Убедиться в логах: нет строк STAGE_FILTER, пайплайн доходит до LLM
[ ] 1.15 Коммит: git commit -m "feat: remove stage_filter module and all references"
```


***

### ЭТАП 2 — Рефакторинг SD-фильтра

#### 2.1 Удаление фильтрующей логики

```
[ ] 2.1 Найти sd_filter.py в bot_agent/retrieval/
[ ] 2.2 Удалить файл sd_filter.py (или очистить содержимое до пустого модуля с комментарием "deprecated")
[ ] 2.3 В answer_adaptive.py найти блок [SD_FILTER] / after_sd_filter
[ ] 2.4 Удалить вызов sd_filter — блоки после initial retrieval идут напрямую в reranker
[ ] 2.5 Удалить импорт sd_filter
[ ] 2.6 Удалить log-строки: SD_FILTER, "After SD filter", SD_COMPAT, allowed=
[ ] 2.7 В sd_classifier.py — оставить всё как есть (классификатор нужен)
```


#### 2.2 Передача SD-уровня в промпт

```
[ ] 2.8 В answer_adaptive.py найти место, где формируется контекст для LLM
[ ] 2.9 Убедиться что sd_level и user_state передаются в prompt_builder или llm_answerer
[ ] 2.10 В системном промпте (system_prompt) добавить секцию:
        "Уровень пользователя по Спиральной Динамике: {sd_level}
         Текущее состояние: {user_state}
         Адаптируй язык, глубину и примеры под этот уровень."
[ ] 2.11 Проверить что sd_level присутствует в LLM Calls → System Prompt в трейсе
```


#### 2.3 Удаление из UI

```
[ ] 2.12 В трейс-панели: убрать строку "SD фильтр: skip/active" из Pipeline Timeline
[ ] 2.13 Оставить отображение SD-уровня пользователя (SD: BLUE · 0.85) — это полезная информация
[ ] 2.14 В Config Snapshot убрать параметры SD_CONFIDENCE_THRESHOLD если они использовались только для фильтра
```


#### 2.4 Тест этапа

```
[ ] 2.15 python -m pytest tests/ -k "sd or classifier" -v
[ ] 2.16 Тестовый запрос с query про сложную тему — убедиться что блоки с любым SD-тегом попадают в LLM
[ ] 2.17 Проверить трейс: нет "After SD filter", SD-уровень виден в промпте
[ ] 2.18 Коммит: git commit -m "feat: remove sd_filter, pass sd_level to LLM prompt"
```


***

### ЭТАП 3 — Упрощение Confidence Scorer

#### 3.1 Анализ текущей формулы

Текущий confidence = сумма 5 компонентов:

- `local_similarity` — релевантность TF-IDF
- `voyage_confidence` — уверенность Voyage
- `delta_top1_top2` — разрыв между лучшим и вторым блоком
- `state_match` — совпадение состояния
- `question_clarity` — ясность вопроса

```
[ ] 3.1 Открыть confidence_scorer.py
[ ] 3.2 Убрать из формулы confidence "voyage_confidence" как отдельный множитель
        (он не должен занулять общий score при сбое Voyage)
[ ] 3.3 Переработать формулу: confidence теперь = local_similarity + delta_top1_top2 + state_match + question_clarity
[ ] 3.4 Убедиться что FAST_PATH порог (low=0.40) остаётся — он нужен для приветствий
[ ] 3.5 Confidence cap на количество блоков: упростить до фиксированного TOP-K из конфига,
        не зависящего от confidence level (убрать "medium→3, low→2" логику)
[ ] 3.6 Удалить log-строки CONFIDENCE_CAP с разбивкой по уровням
[ ] 3.7 Оставить одну строку: [CONFIDENCE] score=X level=Y → FAST_PATH: yes/no
```


#### 3.2 Фиксированный TOP-K

```
[ ] 3.8 В конфиге (config.py или .env) убедиться есть параметр RETRIEVAL_TOP_K (текущий = 3)
[ ] 3.9 Поменять значение на 5 (оптимально для баланса качества и стоимости)
[ ] 3.10 В answer_adaptive.py финальный срез блоков: blocks[:config.RETRIEVAL_TOP_K]
[ ] 3.11 В веб-админке (вкладка "Поиск") поле "Кол-во блоков для контекста (TOP-K)" установить = 5
```


#### 3.3 Тест этапа

```
[ ] 3.12 python -m pytest tests/ -k "confidence" -v
[ ] 3.13 Тестовый запрос: убедиться что в трейсе "To LLM" = 5 блоков (не 0 как раньше)
[ ] 3.14 Тестовый запрос с приветствием: FAST_PATH всё ещё срабатывает
[ ] 3.15 Коммит: git commit -m "feat: simplify confidence scorer, fixed TOP-K=5"
```


***

### ЭТАП 4 — Оптимизация Voyage Reranker

```
[ ] 4.1 Открыть voyage_reranker.py
[ ] 4.2 Убедиться что TOP-K после rerank = 5 (а не 1 как в текущей конфигурации — это баг в админке)
[ ] 4.3 При fallback (403/timeout): оставлять блоки в исходном порядке TF-IDF, не менять их количество
[ ] 4.4 Убрать логику "reranked top_k=2 (voyage_active=True)" при ошибке Voyage —
        при ошибке писать явно: [VOYAGE] fallback, порядок сохранён
[ ] 4.5 В конфиге: VOYAGE_TOP_K = 5 (синхронно с RETRIEVAL_TOP_K)
[ ] 4.6 В веб-админке: "Voyage TOP-K после ранжирования" = 5
```

```
[ ] 4.7 Интеграционный тест Voyage:
        python -c "from bot_agent.retrieval.voyage_reranker import VoyageReranker; r = VoyageReranker(); print(r.test_connection())"
[ ] 4.8 Тестовый запрос с реальным вопросом — убедиться в логах: [VOYAGE] rerank success, top_k=5
[ ] 4.9 Коммит: git commit -m "fix: voyage reranker top_k=5, fix fallback logging"
```


***

### ЭТАП 5 — Обновление тестов

```
[ ] 5.1 Запустить все тесты: python -m pytest tests/ -v --tb=short > tests_after.txt
[ ] 5.2 Сравнить с baseline: diff tests_before.txt tests_after.txt
[ ] 5.3 Найти тесты, которые тестировали Stage-фильтр → удалить или переписать
[ ] 5.4 Найти тесты, которые тестировали SD-фильтр блоков → удалить или переписать
[ ] 5.5 Найти тесты confidence_scorer → обновить под новую формулу
```

```
[ ] 5.6 Написать новый интеграционный тест: test_retrieval_pipeline_simplified.py
        Сценарий 1: Запрос с работающим Voyage → 5 блоков в LLM, нет STAGE_FILTER в логах
        Сценарий 2: Запрос при недоступном Voyage → TF-IDF fallback, всё равно 5 блоков
        Сценарий 3: Приветствие → FAST_PATH срабатывает, 0 блоков, CLARIFICATION mode
        Сценарий 4: SD-уровень передаётся в промпт, не используется для фильтрации
```

```
[ ] 5.7 Написать unit-тест для упрощённого confidence_scorer: test_confidence_scorer_simple.py
        - voyage_confidence не влияет на итоговый score при 0
        - FAST_PATH включается при score < 0.40
        - FAST_PATH НЕ включается при осмысленном вопросе с score > 0.40
```

```
[ ] 5.8 Запустить финально: python -m pytest tests/ -v
[ ] 5.9 Все тесты зелёные или явно помечены xfail с объяснением
[ ] 5.10 Коммит: git commit -m "test: update tests for simplified retrieval pipeline"
```


***

### ЭТАП 6 — Финальная проверка и документация

#### 6.1 Сквозной smoke-тест

```
[ ] 6.1 Запустить Bot_data_base: cd Bot_data_base && python -m uvicorn api.main:app --port 8003
[ ] 6.2 Запустить бота: cd bot_psychologist && python -m uvicorn api.main:app --port 8000
[ ] 6.3 Отправить 3 тестовых сообщения через UI:
        - "Привет!" → ожидаем FAST_PATH, CHUNKS: 0
        - "Хочу понять свой паттерн избегания..." → ожидаем CHUNKS: 5, нет STAGE_FILTER
        - Развёрнутый личный запрос → ожидаем SD-уровень виден в промпте, 5 блоков
[ ] 6.4 В трейсе проверить Pipeline Timeline:
        ✅ Классификатор состояния
        ✅ SD классификатор  
        ✅ Retrieval
        ❌ SD фильтр — НЕТ (удалён)
        ❌ Stage фильтр — НЕТ (удалён)
        ✅ Rerank
        ✅ LLM
        ✅ Форматирование
```


#### 6.2 Обновление документации

```
[ ] 6.5 Обновить README.md: убрать упоминание Stage-фильтра и SD-фильтра как фильтров блоков
[ ] 6.6 Добавить в README раздел "Архитектура ретривала" с новой схемой
[ ] 6.7 Обновить CHANGELOG.md: v0.6.0 — simplified retrieval pipeline
```


#### 6.3 Финальный коммит

```
[ ] 6.8 git add -A
[ ] 6.9 git commit -m "refactor: simplified retrieval pipeline v0.6.0 — remove stage/sd filters"
[ ] 6.10 Создать PR: refactor/simplify-retrieval-pipeline → main
[ ] 6.11 В описании PR указать: что удалено, что упрощено, ссылка на PRD_TASKS.md
```


***

## 4. Ожидаемый результат

### До

```
Пайплайн: TF-IDF → SD-фильтр → Voyage → Stage-фильтр → Confidence cap → LLM
Реально в LLM: 0–3 блока по fallback-логике, без семантики
```


### После

```
Пайплайн: Semantic Search → Voyage Reranker → TOP-5 → LLM
Реально в LLM: 5 семантически релевантных блоков
```


### Метрики успеха

- В трейсе нет строк `STAGE_FILTER`, `SD_FILTER`, `complexity_cap`
- `To LLM` в трейсе стабильно = 5 (не 0 с fallback)
- SD-уровень виден в `SYSTEM PROMPT (PREVIEW)` в LLM Calls
- Все тесты зелёные
- Время ответа не хуже текущего (≤ 30 сек)

***

## 5. Риски и ограничения

| Риск | Вероятность | Митигация |
| :-- | :-- | :-- |
| Voyage API снова недоступен без VPN | Средняя | TF-IDF fallback остаётся, тест сценария 2 |
| Удалённые тесты скрывали реальные баги | Низкая | Новые интеграционные тесты покрывают всё |
| SD-уровень в промпте не влияет на ответ | Низкая | Проверить качество ответа вручную |
| Bot_data_base 503 при тестах | Высокая | Тесты должны мокировать API или запускаться с поднятой базой |


***

*Агент: после прочтения этого PRD — первым действием создай `PRD_TASKS.md` с полным чеклистом всех тасков выше. Затем этап 0. Не переходи к следующему этапу без коммита предыдущего.*

