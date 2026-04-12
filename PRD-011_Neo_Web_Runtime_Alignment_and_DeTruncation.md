# PRD-011: Neo Web Runtime Alignment & DeTruncation

## 1. Контекст

По результатам аудита `AUDIT_NEO_MINDBOT_SYSTEM_2026-04-12.md` в active runtime обнаружены ключевые проблемы:
- ответы могут становиться короче ожидаемого из-за конфликтов промптов и пост-форматирования;
- SSE done-контракт расходится между backend и тестами (`answer_fallback` vs `answer`);
- в prompt-контуре есть внутренние конфликтующие инструкции по краткости;
- текущая отладка ведётся в Web Chat (Telegram и Chapter 8 пока вне текущего цикла).

## 2. Область работ (Scope)

### In-Scope
- Backend/Frontend контракт стриминга для Web Chat.
- Политика форматирования длины ответа (де-транкейшн).
- Согласование active prompt stack и базового system prompt без внутренних конфликтов.
- Тесты backend/frontend на целостность ответа и контракта.

### Out-of-Scope
- Telegram connector.
- Chapter 8 (`multi-agent`, `graph memory`) из `Neo MindBot.md`.

## 3. Цели

1. Гарантировать, что в Web Chat доезжает полный текст ответа без искусственной «экономии».
2. Устранить SSE-контрактный дрейф для события `done`.
3. Согласовать промпт-правила с логикой NEO для web-режима (без взаимоисключающих директив).
4. Сохранить работоспособность dev-trace и админки.

## 4. Нефункциональные требования

- Изменения должны быть обратно-совместимы для текущего Web UI.
- Тесты backend/frontend должны проходить после изменений.
- Логи/trace не должны деградировать по объёму ключевой диагностики.

## 5. Технический план

### Phase A — SSE Contract Hardening (P0)
- Backend `adaptive-stream` done payload должен содержать стандартный ключ `answer`.
- Для совместимости временно оставить `answer_fallback`.
- Frontend parser должен приоритизировать `answer`, затем fallback.

### Phase B — DeTruncation Policy (P0)
- Убрать жёсткий mode-based char clipping как default поведение.
- Оставить авто-укорочение только при явном запросе краткости.
- Ввести только аварийный hard-cap (защита от экстремально длинных ответов).

### Phase C — Prompt Consistency (P1)
- Убрать конфликтующие директивы «не давай ответ/только вопрос» в активном web-контуре.
- Обновить mode directives на «полнота по запросу, без искусственного сжатия».
- Уточнить prompt-stack assets для согласованной логики: контакт → контекст → действие.

### Phase D — Regression Safety (P1)
- Прогон unit/integration тестов backend по SSE/validator/prompt stack.
- Прогон frontend stream parser/useChat тестов.
- Проверка, что trace/done payload не ломают отрисовку debug-панели.

## 6. Критерии приемки (Acceptance Criteria)

1. `done` событие SSE содержит `answer` (и совместимый `answer_fallback`).
2. При обычном запросе без маркеров «кратко/коротко» ответ не обрезается mode-лимитом.
3. Frontend корректно финализирует ответ из `answer`/streamed text без потери хвоста.
4. Backend тесты целевого набора проходят (кроме заранее известных внешних нестабильностей).
5. Frontend стрим-тесты проходят.

## 7. План тестирования

### Backend
- `python -m pytest tests/test_sse_payload.py -q`
- `python -m pytest tests/test_response_formatter.py -q`
- `python -m pytest tests/test_output_validator_neo.py tests/unit/test_prompt_stack_order.py tests/unit/test_route_resolver_rules.py -q`

### Frontend
- `npm run test -- src/services/api.stream.test.ts src/hooks/useChat.test.ts --run`

### Smoke (ручной)
- Web Chat: длинный запрос без «кратко» должен вернуть развёрнутый ответ.
- Dev trace: payload и «полотно ЛЛМ» доступны, вкладки без ошибок fetch.

## 8. Риски и смягчения

- Риск: слишком длинные ответы могут ухудшить UX.
  - Митигация: аварийный hard-cap + постепенная калибровка через runtime config.

- Риск: старые клиенты ждут `answer_fallback`.
  - Митигация: dual-key совместимость (`answer` + `answer_fallback`).

- Риск: prompt-изменения затронут стиль слишком резко.
  - Митигация: scoped web-oriented wording и regression тесты.

## 9. Артефакты

- PRD: `PRD-011_Neo_Web_Runtime_Alignment_and_DeTruncation.md`
- Tasklist progress: `TASKLIST_PRD-011_Neo_Web_Runtime_Alignment_and_DeTruncation_PROGRESS.md`
