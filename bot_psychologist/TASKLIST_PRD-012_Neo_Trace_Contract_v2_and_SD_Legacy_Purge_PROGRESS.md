# TASKLIST PRD-012: Neo Trace Contract v2 + SD Legacy Purge

- PRD: `PRD-012_Neo_Trace_Contract_v2_and_SD_Legacy_Purge.md`
- Дата старта: 2026-04-12
- Статус: In progress (implementation complete, pending commit/push confirmation)

## 0) Prep

- [x] Подтвердить freeze scope (только `bot_psychologist`).
- [x] Зафиксировать baseline smoke (web chat + trace + llm payload).
- [x] Зафиксировать baseline grep по `sd_` в active runtime/UI.

## 1) Backend Trace Contract v2

- [x] Удалить SD поля из pydantic trace моделей (`api/models.py`).
- [x] Упростить trace builder в `api/routes.py` до Neo-only.
- [x] Удалить SD из `api/debug_routes.py` llm payload/structured payload.
- [x] Удалить SD из session metrics (`api/session_store.py`, `api/debug_routes.py`).
- [x] Добавить `trace_contract_version="v2"`.
- [x] Добавить sanitize-on-read для старых trace объектов.

Проверки:

- [x] `/api/v1/questions/adaptive` (debug=true) возвращает trace v2 без SD.
- [x] `/api/v1/questions/adaptive-stream` trace event в схеме v2.
- [x] `/api/debug/session/{id}/llm-payload` без SD полей.

## 2) Frontend Trace Alignment

- [x] Обновить `web_ui/src/types/api.types.ts` под v2.
- [x] Обновить `StatusBar` на 8 Neo chip метрик.
- [x] Убрать SD блоки в `InlineDebugTrace`.
- [x] Обновить `TraceHistory` на формат `#turn · mode · state`.
- [x] Обновить `SessionDashboard` на Neo-only KPI.
- [x] Обновить `ConfigSnapshot` (без SD).
- [x] Обновить `LLMPayloadPanel` (dev-only, default collapsed, no SD).
- [x] Переименовать `Classifier` -> `State Router Model`.

Проверки:

- [x] В UI trace отсутствуют SD термины.
- [x] Все deep-секции сворачиваются/раскрываются.
- [x] Полотно LLM сохраняет полную наблюдаемость API->LLM.

## 3) Admin + Runtime Config Cleanup

- [x] Удалить SD controls из `RoutingTab`.
- [x] Удалить deprecated SD keys из admin schema/effective payload.
- [x] Удалить SD config ключи из активного runtime config surface.

Проверки:

- [x] Admin routing вкладка Neo-only.
- [x] Runtime effective endpoints не возвращают SD runtime controls.

## 4) Legacy Physical Purge

- [x] Удалить/архивировать неиспользуемые SD скрипты в active пути.
- [x] Удалить/обновить устаревшие SD тесты.
- [x] Удалить/обновить SD ссылки в README/docs.

Проверки:

- [x] `rg -n -i "sd_|\\bsd\\b|user_level_adapter|decision_gate|prompt_sd_|DISABLE_SD_RUNTIME|DISABLE_USER_LEVEL_ADAPTER|ENABLE_FAST_SD_DETECTOR|PROMPT_MODE_OVERRIDES_SD|PROMPT_SD_OVERRIDES_BASE" README.md docs .env.example` не находит совпадений.

## 5) Tests & Regression Guard

- [x] Добавить/обновить backend unit/contract tests для trace v2.
- [x] Добавить/обновить frontend component/API parsing tests.
- [x] Прогнать целевые smoke сценарии.

Проверки:

- [x] Все тесты зеленые.
- [x] Нет регрессий в ответах, routing, memory, retrieval.

## 6) Release Readiness

- [x] Обновить changelog/документацию по trace v2.
- [x] Подготовить отчет "before/after" по cleanup.
- [ ] Подготовить commit/push пакет после подтверждения.

## Final DoD

- [x] Операционные trace/runtime/UI контракты очищены от SD-наследия.
- [x] Полная и удобная наблюдаемость API->LLM сохранена.
- [x] Export trace JSON в версии `v2`.
- [x] Стабильный web chat runtime после cleanup.
