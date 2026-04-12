# AUDIT: Neo Runtime Residual Legacy (SD-era)

- Дата: 2026-04-12
- Область аудита: `C:\My_practice\Text_transcription\bot_psychologist`
- Цель: найти следы SD/legacy-эпохи, неиспользуемые или конфликтующие с чистой Neo-системой.

## 1. Итог аудита

Текущее состояние: **Neo — основной runtime, но система пока не "чисто Neo"**.

Что подтверждено:
- Боевой путь действительно идет через `answer_question_adaptive`.
- SD-runtime в логике маршрутизации **фактически отключен** (через disable и strip).

Что осталось:
- В активных runtime-слоях сохранены **многочисленные compatibility-хвосты SD/legacy** (модели API, debug surface, admin controls, типы UI, метрики сессии, скрипты и тестовые хвосты).

Вывод: проект работает как Neo, но структурно несет заметный "двойной слой" (Neo + legacy compatibility).

---

## 2. Критичные остатки в активном runtime

### 2.1 `bot_agent/answer_adaptive.py` содержит SD-скелет в живом коде

Ключевые маркеры:
- `_sd_runtime_disabled()` возвращает `True`, но SD-структуры продолжают жить в пайплайне и trace:
  - `bot_agent/answer_adaptive.py:389`
- Stage `sd_classifier` все еще добавляется в `pipeline_stages` как skipped:
  - `bot_agent/answer_adaptive.py:1377`, `1381`
- В debug trace создаются поля `sd_classification/sd_detail/sd_level`, потом чистятся:
  - `bot_agent/answer_adaptive.py:1235`, `1415`, `1425`, `1441`
  - очистка: `bot_agent/answer_adaptive.py:581`, `598-600`, `1937`, `2983`, `3037`
- Сохраняется extraction SD из блоков (`_extract_block_sd`) даже при отключенном SD-runtime:
  - `bot_agent/answer_adaptive.py:644-671`

Оценка: **High** (избыточная сложность и риск регрессий).

### 2.2 API контракт и модели продолжают нести SD-поля

- `api/models.py`:
  - `ChunkTraceItem.sd_level`: `api/models.py:156`
  - `DebugTrace.sd_classification`: `api/models.py:256`
  - `DebugTrace.sd_detail`: `api/models.py:285`
  - `DebugTrace.sd_level`: `api/models.py:307`
- `api/routes.py`:
  - сбор/проброс SD в trace payload при не-disable: `api/routes.py:613-616`
  - chunk trace с `sd_level`: `api/routes.py:87-100`
  - strip-слой legacy-полей: `api/routes.py:111-127`, `142-147`

Оценка: **High** (контракт все еще "говорит" на SD-языке).

### 2.3 Debug/Session метрики продолжают SD-аналитику

- `api/debug_routes.py`:
  - `payload["sd_level"]`: `api/debug_routes.py:191`
  - `sd_distribution`: `api/debug_routes.py:313`, `322-324`
- `api/session_store.py`:
  - метрики `sd_distribution`: `api/session_store.py:127-129`

Оценка: **High** для цели "только Neo" (forensic SD слой остается видимым).

### 2.4 Конфиг/админка держат SD-регуляторы

- `bot_agent/config.py`:
  - `SD_CLASSIFIER_*`, `PROMPT_SD_OVERRIDES_BASE`, `PROMPT_MODE_OVERRIDES_SD`
  - `bot_agent/config.py:147-156`
- `bot_agent/runtime_config.py`:
  - те же ключи в editable runtime config: `313`, `318`, `337`, `342`, `834-843`
- `web_ui/src/components/admin/RoutingTab.tsx`:
  - SD controls в routing tab: `51`, `57`, `73`, `74`
- `web_ui/src/components/admin/AdminPanel.tsx`:
  - deprecated routing keys с SD-ключами: `34-39`

Оценка: **High** (операционная поверхность остается mixed-mode).

---

## 3. Существенные остатки в UI/trace слое

### 3.1 Debug UI явно показывает SD как активную сущность

- `web_ui/src/components/chat/InlineDebugTrace.tsx`:
  - SD level/detail в панелях: `114`, `177-204`
- `web_ui/src/components/debug/StatusBar.tsx`:
  - chip `SD: ...`: `31`, `42`
- `web_ui/src/components/debug/TraceHistory.tsx`:
  - label с SD: `10`
- `web_ui/src/components/debug/LLMPayloadPanel.tsx`:
  - `sd: ...`: `87`
- типы:
  - `web_ui/src/types/api.types.ts`: `84`, `181`, `210`, `232`, `255`
  - `web_ui/src/services/api.service.ts`: `115`, `173`, `189`, `231`, `270`

Оценка: **Medium-High** (UI все еще закрепляет SD-терминологию).

---

## 4. Legacy API-алиасы и фазовые хвосты

### 4.1 Старые endpoint-и сохранены как Neo-compat

- `/questions/basic`: `api/routes.py:204`
- `/questions/basic-with-semantic`: `api/routes.py:248`
- `/questions/sag-aware`: `api/routes.py:277`
- `/questions/graph-powered`: `api/routes.py:314`
- Логи `NEO_COMPAT`: `api/routes.py:230`, `260`, `296`, `334`

Это валидный compatibility слой, но для "чистой Neo" — технический долг.

### 4.2 Признаки старой фазовой модели в API description

- `api/main.py` в описании все еще есть формулировки Phase 1/2/3:
  - `api/main.py:111-113`
- Комментарий `legacy + v1` для admin router:
  - `api/main.py:210`

Оценка: **Medium** (документационный/операционный шум).

---

## 5. Скрипты, тесты и инфраструктурный legacy-хвост

### 5.1 Скрипты с SD-зависимостями / старым контрактом

- `scripts/bootstrap_eval_sets.py` импортирует `bot_agent.sd_classifier`:
  - `scripts/bootstrap_eval_sets.py:314`
- `scripts/eval_retrieval.py` и `scripts/eval_reranker_usage.py` передают `sd_level` в retriever:
  - `scripts/eval_retrieval.py:43`, `63`
  - `scripts/eval_reranker_usage.py:56`, `79`

Оценка: **Medium** (не боевой путь, но создает ложную "живость" SD).

### 5.2 Набор тестов содержит отключенные/устаревшие сценарии

`pytest.ini` отключает legacy-тесты:
- `tests/test_phase1.py`, `test_phase2.py`, `test_phase3.py`,
- `test_fast_detector.py`, `test_sd_classifier.py`, `test_sd_integration.py`, `test_full_dialogue_pipeline.py`
- строки: `pytest.ini:6-12`

Часть из них ссылается на удаленные модули (`bot_agent.answer_basic`, `bot_agent.sd_classifier`):
- `tests/test_phase1.py:27`
- `tests/test_fast_detector.py:11`
- `tests/test_sd_classifier.py:7`
- `tests/test_sd_integration.py:12`
- `tests/test_full_dialogue_pipeline.py:7`

Оценка: **Medium** (шума много, поддерживаемость ниже).

---

## 6. Физически сохраненные legacy-артефакты

### 6.1 Legacy code/prompts в репозитории

Присутствует директория:
- `bot_agent/legacy/python/*`
- `bot_agent/legacy/prompts/*`

(полный список файлов зафиксирован отдельно в выводе аудита shell).

### 6.2 Legacy SD-конфиг

- `config/sd_classification.yaml` существует и содержит SD матрицы.

### 6.3 README/docs содержат крупный исторический слой

- `README.md` содержит большой legacy-раздел и ссылки на неактуальные runtime-сущности,
  включая `bot_agent/sd_classifier.py` и `bot_agent/user_level_adapter.py`.

Оценка: **Medium** (документация не соответствует цели "только Neo").

---

## 7. Что уже хорошо (подтверждено)

- SD-runtime выключен по флагам по умолчанию:
  - `bot_agent/feature_flags.py:20`, `23`
- В ответах/trace есть strip-механизмы legacy-полей:
  - `api/routes.py:111-127`, `142-147`
  - `bot_agent/answer_adaptive.py:571-600`
- Legacy Python runtime вынесен в архивную папку `bot_agent/legacy/` (не primary import path).

---

## 8. Рекомендованный план очистки до "чисто Neo"

### Phase A (Runtime code purge, приоритет P0)
- Удалить SD-структуры из `answer_adaptive` (включая `SDClassificationResult`, `sd_classifier` stage, `_extract_block_sd` в runtime trace-контуре).
- Упростить trace-аномалии и метаданные: убрать SD-only ветки и strip как временную прокладку.

### Phase B (API/Schema/Web contract purge, P0)
- Удалить SD-поля из `api/models.py` (`sd_level`, `sd_classification`, `sd_detail` в trace-моделях).
- Убрать SD-поля из `api/debug_routes.py` / `api/session_store.py` метрик.
- Очистить UI-типы и debug-компоненты от SD-визуализации.

### Phase C (Admin/config surface cleanup, P1)
- Убрать `SD_CLASSIFIER_*`, `PROMPT_SD_OVERRIDES_BASE`, `PROMPT_MODE_OVERRIDES_SD` из editable config.
- Упростить `RoutingTab` до Neo routing taxonomy без SD controls.

### Phase D (Tests/scripts/docs cleanup, P1)
- Удалить или перенести в архив отключенные legacy-тесты.
- Очистить `scripts/*` от зависимостей на `bot_agent.sd_classifier` и `sd_level` аргументов.
- Переписать README/docs в "Neo-first" формате (исторический раздел в архив).

### Phase E (Optional compatibility reduction, P2)
- Решить судьбу Neo-compat endpoint-ов `/questions/basic*|sag-aware|graph-powered`.
- При отсутствии внешних потребителей — удалить.

---

## 9. Заключение

Проект уже в Neo-режиме по факту исполнения, но архитектурно сохраняет **много compatibility-наследия SD-эпохи**. 
Для цели "чистая система исключительно на NEO" требуется целевая зачистка active runtime/API/UI/contracts + test/doc/script слоя.

