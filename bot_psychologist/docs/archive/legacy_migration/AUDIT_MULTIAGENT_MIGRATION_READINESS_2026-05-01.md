# AUDIT Multiagent Migration Readiness — 2026-05-01

## Audit Scope (Область аудита)
Проверка фактической готовности проекта к полному удалению каскадного (legacy/adaptive) рантайма после перехода на мультиагентную архитектуру.

Проверены слои:
- backend runtime (API entrypoints, bot runtime, feature flags)
- debug/trace pipeline
- admin/web surfaces
- тестовые контракты и инвентарные фикстуры

## What Was Checked (Что проверено)
- Поиск runtime-точек входа и переключателей (`MULTIAGENT_ENABLED`, legacy-маркеры).
- Проверка фактической связки `api -> answer_adaptive -> multiagent|cascade`.
- Проверка тест-контрактов на требуемое legacy-поведение.
- Целевой тест-прогон:
  - `tests/multiagent/test_orchestrator_e2e.py`
  - `tests/test_multiagent_trace.py`
  - `tests/e2e/test_legacy_fallback_when_flag_off.py`
  - `tests/inventory/test_runtime_legacy_touchpoints_map.py`

Результат тест-прогона: **29 passed**.

## Current Architecture Picture (Факт) (Текущая архитектурная картина)

### 1) Runtime entrypoint всё ещё через фасад `answer_adaptive`
- `bot_psychologist/api/routes/chat.py` вызывает `answer_question_adaptive(...)`.
- `bot_psychologist/api/telegram_adapter/service.py` также вызывает `answer_question_adaptive(...)`.

### 2) Внутри `answer_adaptive` есть branch + fallback
- `bot_psychologist/bot_agent/answer_adaptive.py`:
  - при `MULTIAGENT_ENABLED=true` выполняется `multiagent.orchestrator.run_sync(...)`;
  - при ошибке/не-ok результата — fallback в каскадный runtime (classic adaptive pipeline).

Вывод: мультиагент не является единственным runtime-контуром, а работает через совместимый фасад.

### 3) Legacy-контур физически активен как кодовая зависимость
Активно присутствуют и подключены:
- `bot_psychologist/bot_agent/adaptive_runtime/*` (20 модулей)
- `bot_psychologist/bot_agent/state_classifier.py`
- `bot_psychologist/bot_agent/route_resolver.py`
- `bot_psychologist/bot_agent/decision/*`
- `bot_psychologist/bot_agent/response/*`

### 4) Админка и API явно держат legacy-режимы
- `bot_psychologist/api/admin_routes.py`:
  - `pipeline_mode`: `full_multiagent | hybrid | legacy_adaptive`
  - логика `_compute_env_pipeline_mode()`
- `bot_psychologist/web_ui/src/components/admin/OrchestratorTab.tsx` и типы также содержат `legacy_adaptive`.

### 5) Trace/metadata ещё содержит переходный слой очистки legacy-полей
- `bot_psychologist/api/routes/common.py` и `bot_psychologist/api/debug_routes.py` используют
  `_strip_legacy_trace_fields`, `_strip_legacy_runtime_metadata`.
- Это признак, что система проектно рассчитана на coexistence с legacy payload.

### 6) Тесты фиксируют и требуют legacy-совместимость
- `bot_psychologist/tests/e2e/test_legacy_fallback_when_flag_off.py` — проверяет живой fallback legacy-пути.
- `bot_psychologist/tests/inventory/test_runtime_legacy_touchpoints_map.py` + fixture `runtime_legacy_touchpoints_v102.json` — фиксируют legacy-touchpoints как контракт.
- Есть дополнительные тесты/фикстуры legacy inventory/map.

### 7) Конфиги по умолчанию не полностью multiagent-first
- `bot_psychologist/.env`: `MULTIAGENT_ENABLED=true` (локально включено)
- `bot_psychologist/.env.example`: `MULTIAGENT_ENABLED=false` (по умолчанию путь всё ещё legacy-first)

## Verdict (Вердикт)

## Is Project Ready for Full Legacy Removal Now? (Готов ли проект к полному удалению каскадной системы сейчас?)
**Нет, не готов.**

Причина: каскадный runtime остаётся частью рабочего контура (entrypoint + fallback + тест-контракт + admin режимы + trace sanitization).

## Migration Stage Assessment (Оценка стадии миграции)
- Мультиагентный контур: **реально рабочий**.
- Архитектура перехода: **гибридная (coexistence)**.
- Готовность к hard purge legacy: **низкая/средняя**, пока не удалены блокеры ниже.

## Critical Blockers Before Legacy Removal (Критические блокеры перед удалением legacy)
1. Убрать fallback из `answer_adaptive` (или полностью убрать `answer_adaptive` из runtime-path).
2. Перевести API entrypoint на прямой `multiagent orchestrator`.
3. Удалить `legacy_adaptive` и `hybrid` режимы из admin/web contracts.
4. Удалить/переписать тесты и fixtures, требующие legacy-touchpoints.
5. Обновить `.env.example` на multiagent-first (без legacy pipeline defaults).
6. Удалить/переписать trace sanitizers, когда legacy поля больше не могут появляться.

## Minimum Safe Purge Plan (Recommended) (Минимальный безопасный план purge)
1. **Cutover PR**: API/Telegram entrypoints -> только multiagent orchestrator.
2. **Contract PR**: убрать `legacy_adaptive/hybrid` из admin/web типов и endpoint payload.
3. **Trace PR**: новый контракт без `_strip_legacy_*` слоя.
4. **Tests PR**: удалить legacy inventory fixtures/tests, заменить на multiagent invariants.
5. **Cleanup PR**: физически удалить `adaptive_runtime` и неиспользуемые legacy-модули после зелёного полного прогона.

## Additional Observation (Доп. наблюдение)
В нескольких файлах есть признаки mojibake (битая кодировка в комментариях/docstrings). Это не блокирует миграцию как архитектуру, но ухудшает поддерживаемость и обзор trace/docs.
