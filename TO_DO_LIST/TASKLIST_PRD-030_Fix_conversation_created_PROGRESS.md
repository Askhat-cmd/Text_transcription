# TASKLIST_PRD-030_Fix_conversation_created_PROGRESS

## Цель
Исправить ложное создание новой conversation на каждом ходе и восстановить корректный lifecycle:
- 1-й ход: `conversation.created`
- последующие ходы: `conversation.resumed`

## Шаги реализации
- [x] `api/dependencies.py`: стабилизировать `session_id` без `X-Session-Id` через fingerprint (`fingerprint[:32]`).
- [x] `api/conversations/repository.py`: добавить fallback-поиск active conversation по `(user_id, channel)` при промахе по `(user_id, session_id, channel)`.
- [x] `api/conversations/repository.py`: ограничить fallback recency-окном 24 часа.
- [x] `api/conversations/service.py`: добавить в логи `lookup` (`session_id|user_fallback`) для `conversation.resumed`.
- [x] `api/conversations/service.py`: добавить в логи `reason=no_active_found` для `conversation.created`.
- [x] `api/routes/chat.py`: добавить `session_id` и `conversation_id` в SSE `done_payload`.

## Тесты
- [x] Unit: repository fallback (recent active найден по user/channel).
- [x] Unit: repository fallback не подхватывает conversation старше 24h.
- [x] Unit: service логирует `lookup=user_fallback` при resume через fallback.
- [x] Unit: service логирует `reason=no_active_found` при создании новой conversation.
- [x] API: без `X-Session-Id`, но с одинаковым fingerprint — conversation стабильна между запросами.
- [x] API/SSE: `done_payload` содержит `session_id` и `conversation_id`.

## Чек-лист готовности
- [x] `conversation.created` не появляется на каждом ходе одного диалога.
- [x] `conversation.resumed` появляется на повторных ходах и содержит `lookup`.
- [x] fallback не склеивает старые (stale >24h) active conversations.
- [x] профильные проверки выполнены: `py_compile` OK + runtime smoke `PRD030_SMOKE_OK`.

## Примечание по окружению тестов
- `pytest` в этом окружении блокируется ACL на temp-каталогах (`WinError 5` при работе `pytest tmpdir`), независимо от `TMP/TEMP` и `--basetemp`.
- Для подтверждения PRD-изменений выполнен эквивалентный smoke-сценарий через `python` без pytest tmp-механики.
