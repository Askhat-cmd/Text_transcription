# Dialogue Thread Lifecycle (Жизненный цикл нити диалога)

## Thread (Что такое нить)

Нить — это устойчивый смысловой контур разговора между пользователем и ботом.
Каждая нить хранит:
- текущую фазу диалога;
- направление (`core_direction`);
- открытые и закрытые петли;
- continuity score;
- relation текущего хода к нити.

Источник модели: `bot_agent/multiagent/contracts/thread_state.py`.

## Thread Phases (Фазы нити)

Допустимые фазы:
- `stabilize` — первичная стабилизация и безопасный контакт.
- `clarify` — уточнение запроса, контекста и целей.
- `explore` — углубление и исследование смыслов.
- `integrate` — сборка выводов и интеграция в практический шаг.

Фаза сохраняется в `ThreadState.phase` и обновляется в `ThreadManagerAgent`.

## Thread Manager Agent Role (Роль Thread Manager Agent)

Файл: `bot_agent/multiagent/agents/thread_manager.py`

Thread Manager детерминированно решает, как связать новый ход с историей:
- продолжить текущую нить;
- начать новую нить;
- вернуться к архивной нити;
- ветвить текущую.

Ключевые поля выхода:
- `thread_id`
- `phase`
- `relation_to_thread`
- `continuity_score`
- `response_mode`

## Continue vs New Thread (Продолжение vs новая нить)

Решение строится на комбинации:
- смысловой близости к текущей нити;
- признаков смены темы;
- safety-контекста;
- состояния пользователя.

`continuity_score` — численный индикатор непрерывности (`0.0..1.0`).
Низкий score и явная смена темы обычно ведут к `new_thread`.

## relation_to_thread (Отношение к нити)

Поддерживаемые значения:
- `continue` — сообщение продолжает текущую нить.
- `new_thread` — создается новая нить.
- `branch` — ответвление внутри текущей темы.
- `return_to_old` — возврат к ранее архивированной нити.

## Thread Storage (Хранение нитей)

Хранилище: `bot_agent/multiagent/thread_storage.py`

Формат:
- активные нити пользователя;
- архив нитей;
- метаданные по времени и причинам архивирования.

Путь к storage формируется стабильно относительно кода (без зависимости от текущей рабочей директории).

## Thread Archiving (Архивирование нитей)

Архивирование выполняется при переходах, где активная нить закрывается или вытесняется новой.
В архив записываются:
- `thread_id`
- `core_direction`
- петли (`open_loops`, `closed_loops`)
- финальная фаза
- причина архивирования
- timestamp

Контракт архивной нити: `ArchivedThread`.

## Scenario Examples (Примеры сценариев)

### When Thread Continues (Когда нить продолжается)
- пользователь задает уточняющий вопрос по той же теме;
- continuity score высокий;
- `relation_to_thread=continue`.

### When New Thread Is Created (Когда создаётся новая нить)
- пользователь резко меняет тему/контекст;
- continuity score низкий;
- `relation_to_thread=new_thread`.

### When Return Occurs (Когда происходит возврат)
- пользователь явно возвращается к раннему сюжету;
- находится релевантная архивная нить;
- `relation_to_thread=return_to_old`.

## Safety Flag Role (Роль флага безопасности)

Если `safety_active=True`, Thread Manager принудительно удерживает безопасный режим и не допускает рискованных переходов.
Это влияет на `phase` и `response_mode` (вплоть до `safe_override`).

## Checks and Tests (Проверки и тесты)

Рекомендуемые тесты:

```bash
pytest tests/multiagent/test_thread_manager.py -q
pytest tests/multiagent/test_thread_storage_persistence.py -q
pytest tests/multiagent/test_orchestrator_e2e.py -q
```
