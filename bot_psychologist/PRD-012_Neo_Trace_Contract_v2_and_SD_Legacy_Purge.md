# PRD-012: Neo Trace Contract v2 + SD Legacy Purge

- Дата: 2026-04-12
- Проект: `bot_psychologist`
- Статус: Draft for approval (готов к старту после твоего "старт")
- Основание: `AUDIT_NEO_SD_LEGACY_CLEANUP_2026-04-12.md` + предоставленные скрины трейса

## 1) Контекст и проблема

Текущий runtime уже работает в Neo-парадигме, но trace-контракт и debug UI остаются гибридными (Neo + SD-legacy). Из-за этого:

- в trace/UI видны SD-поля и SD-метрики (`SD уровень`, `SD classifier skip`, `SD distribution`, `SD_CONFIDENCE_THRESHOLD`),
- backend хранит и пробрасывает compatibility-ветки,
- операторская диагностика перегружена и местами концептуально смешана,
- "Полотно LLM" полезно, но не структурировано как двухуровневая диагностика (быстрый обзор + глубокий разбор).

Цель этого PRD: довести debug/trace слой до состояния **чисто Neo**, сохранив полную наблюдаемость того, что летит в LLM.

## 2) Подтвержденные решения

Решения по ответам владельца и архитектурным выборам:

1. SD-поля из API-трейса удаляются полностью, без периода совместимости для новых ответов.
2. Исторические trace-данные не мигрируются. Для старых записей применяется read-sanitize при чтении (SD поля скрываются в выдаче).
3. Верхняя "быстрая" панель trace фиксируется на 8 сигналах Neo (см. раздел 5).
4. "Полотно LLM" доступно только для `dev-key-001` и по умолчанию свернуто.
5. Полный system prompt не показывается сразу: по умолчанию только preview, полный текст через явное раскрытие.
6. `Session Dashboard` остается, но полностью без SD-метрик.
7. `Config Snapshot` показывает только Neo-runtime параметры, SD-ключи удаляются.
8. Термин `Classifier` в UI переименуется в Neo-термин `State Router Model`.
9. Экспорт трейса переводится на схему `trace_contract_version = "v2"`.
10. В рамках PRD выполняется и контрактная чистка, и физическая зачистка legacy-остатков SD (в активном проекте).
11. Вводится двухрежимная диагностика: `Simple` (по умолчанию) и `Deep` (полный инженерный разбор), оба режима с сворачиваемыми секциями.
12. Telegram-коннектор и Chapter 8 (multi-agent/graph memory) — вне scope.

## 3) Цели

- Удалить SD-наследие из active trace/runtime/UI-contract.
- Сохранить и улучшить наблюдаемость API→LLM пайплайна.
- Сделать trace одновременно простым для ежедневной отладки и глубоким для forensic-анализа.
- Упростить дальнейшую поддержку: один канонический Neo-контракт без dual-mode.

## 4) Не в scope

- Реализация Telegram runtime.
- Реализация multi-agent/graph-memory главы (Chapter 8).
- Изменение бизнес-логики ответов, не связанной с trace/legacy cleanup.

## 5) Целевой Neo Trace Contract v2

Обязательные поля v2 верхнего уровня:

- `trace_contract_version` (`"v2"`)
- `session_id`
- `turn_number`
- `recommended_mode`
- `user_state`
- `decision_rule_id` (string)
- `confidence_score`
- `confidence_level`
- `total_duration_ms`
- `tokens_prompt`
- `tokens_completion`
- `tokens_total`
- `estimated_cost_usd`
- `chunks_retrieved[]`
- `chunks_after_filter[]`
- `llm_calls[]`
- `pipeline_stages[]`
- `anomalies[]`
- `context_mode`
- `hybrid_query_preview`
- `hybrid_query_text`
- `memory_turns`
- `summary_length`
- `semantic_hits`
- `config_snapshot` (Neo-only keys)

Удаляемые SD/legacy поля из v2:

- `sd_level`
- `sd_classification`
- `sd_detail`
- `sd_confidence_threshold`
- любые SD-distribution структуры
- UI-чипы/лейблы, завязанные на SD

## 6) Быстрая панель trace (Simple mode)

Фиксированный набор из 8 чипов:

1. `MODE`
2. `STATE`
3. `RULE`
4. `CHUNKS` (after/cap)
5. `HITS`
6. `TOKENS`
7. `LLM` (latency)
8. `WARN` (count)

Принципы:

- без SD-терминов,
- без перегруза деталями,
- клик по карточке раскрывает deep-секции.

## 7) Deep mode (полная инженерная диагностика)

Секции (все `details`, сворачиваемые):

- Routing & State
- Pipeline Timeline
- Retrieval (chunks in response + all chunks)
- LLM Calls
- Memory Context
- Models/Tokens/Cost
- Anomalies
- Session Dashboard
- Trace History
- Config Snapshot
- LLM Canvas

`LLM Canvas`:

- dev-only,
- default collapsed,
- preview-first,
- full prompt/manual expand,
- copy/export доступны,
- fallback-safe при недоступности blob.

## 8) Этапы реализации

### Этап A — Контракт backend (P0)

- В `api/models.py` удалить SD-поля из `DebugTrace`, `ChunkTraceItem`, `ConfigSnapshot`, `LLMPayloadTrace`.
- В `api/routes.py` убрать SD сборку/strip ветки из trace payload.
- В `api/debug_routes.py` убрать SD из payload и метрик.
- В `api/session_store.py` убрать `sd_distribution` агрегацию.
- Добавить поле `trace_contract_version="v2"`.
- Сохранить безопасный sanitize старых trace при чтении debug endpoints.

### Этап B — Frontend trace UI (P0)

- Обновить `web_ui/src/types/api.types.ts` под v2.
- `StatusBar.tsx`: заменить SD-чип на RULE/TOKENS.
- `InlineDebugTrace.tsx`: удалить SD карточки/детали; привести секции к Neo.
- `SessionDashboard.tsx` и `useSessionTrace.ts`: убрать SD метрики, добавить Neo KPI.
- `TraceHistory.tsx`: формат `#turn · mode · state`.
- `ConfigSnapshot.tsx`: только Neo поля.
- `LLMPayloadPanel.tsx`: убрать SD-поле, оставить Neo-поля + strict collapsible UX.
- Переименовать `Classifier` -> `State Router Model`.

### Этап C — Админка и runtime-config surface (P1)

- Удалить SD routing controls из `RoutingTab.tsx`.
- Удалить deprecated SD keys из admin effective/schema payload.
- Убрать SD config keys из `config.py`/`runtime_config.py`, если они не участвуют в Neo runtime.
- Проверить что feature-flags не содержат operational SD-toggles в активном контуре.

### Этап D — Физическая зачистка legacy (P1)

- Удалить неиспользуемые SD-скрипты/тесты/конфиги из active пути `bot_psychologist`.
- Удалить/переписать SD references в docs и README в части runtime/trace.
- Сохранить только Neo-актуальные документы и контракты.

### Этап E — Контрактные проверки и стабилизация (P0)

- Обновить/добавить тесты API-contract и UI rendering.
- Прогнать smoke: web chat + dev trace + llm payload + export json.
- Зафиксировать regression guard на отсутствие SD-полей.

## 9) Тест-план

### Backend

- Unit: trace builder возвращает `trace_contract_version=v2`.
- Unit: debug payload не содержит `sd_*` ключей.
- Unit: sanitize старого trace удаляет SD поля.
- Unit: session metrics без `sd_distribution`.
- Contract: `/api/v1/questions/adaptive` (debug=true) -> trace v2 schema.
- Contract: `/api/v1/questions/adaptive-stream` -> `trace` SSE event по v2.
- Contract: `/api/debug/session/{id}/llm-payload` flat/structured без SD.

### Frontend

- Component: `StatusBar` рендерит 8 Neo-chip метрик.
- Component: `SessionDashboard` без SD блоков.
- Component: `TraceHistory` не рендерит SD.
- Component: `ConfigSnapshot` без SD threshold.
- Component: `LLMPayloadPanel` скрыт по умолчанию, раскрывается и грузит payload.
- API parsing tests: обработка trace v2 + SSE trace event.

### E2E / Manual

- dev-key session: trace виден, все секции сворачиваются.
- Simple mode читаем, Deep mode содержит полный forensic-объем.
- "Полотно LLM" показывает полный путь API->LLM (preview + full expand).
- Export JSON содержит `trace_contract_version=v2` и не содержит SD полей.

## 10) Чек-лист выполнения

- [ ] Утвержден v2-контракт trace.
- [ ] Backend trace/debug endpoints очищены от SD.
- [ ] Frontend debug UI полностью Neo.
- [ ] Session metrics и history Neo-only.
- [ ] LLM Canvas dev-only + collapsed-by-default.
- [ ] Админка очищена от SD routing controls.
- [ ] Legacy SD файлы/ссылки удалены из active проекта.
- [ ] Автотесты и smoke-тесты зеленые.
- [ ] Документация обновлена под Neo-only runtime.

## 11) Критерии приемки (Definition of Done)

- В ответах чата и debug trace отсутствуют `sd_*` поля.
- В UI нет ни одного SD-термина в runtime trace/admin routing.
- Trace JSON экспортируется в схеме `v2`.
- Вкладка "Полотно LLM" информативна, сворачиваема, dev-only, без утечки SD.
- Regression тесты покрывают запрет возврата SD-полей.
- Runtime поведение бота не деградировало (ответы, routing, memory, retrieval).

## 12) Риски и контроль

- Риск: поломка совместимости старых trace-объектов в UI.
  Митигатор: sanitize-on-read + defensive parsing в UI.

- Риск: скрытая зависимость от SD-ключей в admin/runtime_config.
  Митигатор: поэтапное удаление с grep-аудитом + targeted tests.

- Риск: потеря диагностической глубины после упрощения.
  Митигатор: двухуровневая модель Simple/Deep + обязательный LLM Canvas.

## 13) Артефакты после реализации

- Обновленный контракт trace v2 (код + тесты).
- Обновленный UI trace/debug.
- Обновленный tasklist прогресса по этапам.
- Обновленный audit appendix с "before/after" подтверждением очистки.
