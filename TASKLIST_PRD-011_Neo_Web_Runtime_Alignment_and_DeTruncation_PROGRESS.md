# TASKLIST: PRD-011 Neo Web Runtime Alignment & DeTruncation

Статус: In Progress
Дата старта: 2026-04-12
PRD: `PRD-011_Neo_Web_Runtime_Alignment_and_DeTruncation.md`

## Checklist

- [x] T0. Создать PRD-011 в корне проекта.
- [x] T1. Создать progress tasklist в корне проекта.
- [x] T2. Исправить SSE done-контракт (`answer` + backward compatibility).
- [x] T3. Обновить фронтовый SSE parser приоритизации финального текста (`answer` first).
- [x] T4. Убрать default mode-clip для обычных ответов (де-транкейшн политика).
- [x] T5. Согласовать prompt-слой (base + mode + stack assets) без конфликтов краткости.
- [x] T6. Обновить/добавить тесты под новый контракт и политику длины.
- [x] T7. Прогнать целевой набор backend тестов.
- [x] T8. Прогнать целевой набор frontend тестов.
- [x] T9. Зафиксировать результаты и остаточные риски.

## Progress Log

- 2026-04-12 14:26: Созданы PRD и tasklist, старт реализации.
- 2026-04-12 14:42: Реализован dual-key done payload (`answer` + `answer_fallback`) в `adaptive-stream`.
- 2026-04-12 14:43: Обновлен frontend SSE parser: приоритет `answer`, fallback на `answer_fallback`.
- 2026-04-12 14:46: В `response_formatter` отключен default mode-char clip для обычных ответов; оставлены explicit brevity + hard-cap.
- 2026-04-12 14:50: Приведен к согласованному виду prompt-контур web-рантайма (base + templates + active prompts).
- 2026-04-12 14:57: Backend тесты: `29 passed`.
- 2026-04-12 14:57: Frontend тесты: `18 passed`.
- 2026-04-12 14:58: Live smoke API/SSE: `done` содержит `answer` и `answer_fallback`, длина ответа 1142 символа, `trace` event и `llm-payload` endpoint работают.

## Exit Criteria

- [x] `adaptive-stream` done payload стабильно содержит `answer`.
- [x] Ответы не обрезаются искусственно при обычном запросе.
- [x] Тесты backend/frontend из PRD проходят.
- [x] Веб-чат и trace сохраняют работоспособность.

## Residual Risks

- На production/high-load может потребоваться дополнительная калибровка `hard_max_chars` под UX и лимиты транспортного слоя.
- В проекте накоплено много исторических PRD/TASKLIST файлов и перемещений (archive/move), это организационный риск для дальнейших миграций и ревью.
