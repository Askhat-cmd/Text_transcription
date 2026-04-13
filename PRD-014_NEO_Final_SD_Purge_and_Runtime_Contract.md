# PRD-014_NEO_Final_SD_Purge_and_Runtime_Contract.md

## 1. Контекст

После серии миграций на NEO в активном runtime сохраняются SD/legacy-остатки (контракты API, поля памяти, совместимые ветки в движке, устаревшие docs). Это увеличивает сложность поддержки, создает риск расхождения поведения и мешает прозрачной диагностике в trace.

## 2. Цель

Довести активную систему `bot_psychologist` до состояния **NEO-only runtime contract**:
- без активных SD-эндпоинтов;
- без SD/user_level полей в API-контракте веб-чата;
- без SD-профиля в памяти диалога;
- без legacy-SD вычислений в основном пути ответа;
- с документацией, отражающей актуальную NEO-реальность.

## 3. Scope

### In Scope
- `bot_psychologist/api/*` (маршруты, модели, debug surface)
- `bot_psychologist/bot_agent/*` (answer runtime, memory, config flags)
- `bot_psychologist/web_ui/src/*` (API client/types/constants)
- `bot_psychologist/docs/*` (контрактные документы)
- tests: минимально достаточный набор под измененный контракт

### Out of Scope
- Telegram connector production hardening
- Chapter 8 (multi-agent + graph memory)
- Полная историческая чистка архива PRD/TASKLIST вне active runtime

## 4. Продуктовые требования

1. В API больше нет активного `/questions/sag-aware`.
2. В Web API-контракте для основного вопроса отсутствует `user_level`.
3. В runtime memory отсутствует `sd_profile` как активное поле состояния.
4. Trace/metadata не рассчитывают SD-классификацию в основном пути.
5. Документация API/тестов/данных не позиционирует SAG/SD как активный контур runtime.

## 5. Технические требования

1. Удалить/деактивировать legacy endpoint и связанные константы фронта.
2. Перевести `api.models.QuestionRequest` и цепочку вызовов на NEO-поля без `user_level`.
3. Упростить `conversation_memory`: убрать SD-profile state/methods, сохранить совместимость чтения старых снапшотов без падения.
4. Удалить SD-путь из `answer_adaptive` в части trace/debug/runtime metadata (NEO-диагностика остается).
5. Убрать SD config flags из runtime-конфига (или оставить только как no-op с явной деактивацией, если нужно для обратной совместимости тестов).

## 6. Критерии приемки

1. `rg` по активным директориям (`api`, `bot_agent`, `web_ui/src`) не находит активного `/questions/sag-aware`.
2. Отправка вопроса через web UI не включает `user_level`.
3. Trace блоки не содержат `sd_classification`, `sd_detail`, `sd_level` в runtime payload.
4. Smoke: веб-чат отвечает штатно, trace отображается без регрессии.
5. Таргетные тесты зеленые.

## 7. Тест-план

1. Backend unit/contract:
- tests на API request model/response contract
- tests на trace metadata cleanup (обновить под удаление SD ветки)

2. Frontend:
- tests `api.service`/stream contract (без `user_level`, без sag-aware)

3. Smoke manual:
- один диалог в web UI
- проверить ответ, trace, отсутствие SD-полей/терминов в runtime sections

## 8. Риски и смягчение

1. Риск: скрытая зависимость старых тестов на SD поля.
- Смягчение: обновить/переформулировать тесты в migration-guard стиле.

2. Риск: регрессия сериализации старой памяти.
- Смягчение: оставить tolerant-read старых полей без их дальнейшей записи.

3. Риск: ломка внешних интеграций на старом endpoint.
- Смягчение: вернуть 410/404 с явным сообщением в changelog (опционально).

## 9. Definition of Done

1. Кодовые изменения внесены по всем in-scope областям.
2. TASKLIST обновлен по шагам с чекбоксами и результатами.
3. Тесты/смоук выполнены и задокументированы.
4. Подготовлен короткий итог по дельте контракта.
