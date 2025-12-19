# Bot Psychologist

**Супер-Умный Бот-Психолог** — AI-ассистент на базе данных `voice_bot_pipeline`.

## Описание

Специализированный AI-бот-психолог, который:
- Работает поверх готовых данных SAG v2.0 JSON + Knowledge Graph
- Использует все слои структуры: блоки, граф-сущности, семантические связи
- Отвечает на вопросы с отсылками к конкретным видео и таймкодам

## Структура проекта

```
bot_psychologist/
├── .taskmaster/           # TaskMaster — система управления задачами
│   ├── tasks/             # JSON файлы с задачами
│   └── config.json        # Конфигурация TaskMaster
├── Docs_for_make_tasks/   # Документация и спецификации
│   ├── PRD*.md            # Product Requirements Document
│   ├── Phase_1.md         # Детали Phase 1
│   ├── Phase_2.md         # Детали Phase 2
│   └── Phase_3.md         # Детали Phase 3
├── bot_agent/             # (будет создан) Основной код бота
├── .env.example           # Пример переменных окружения
├── .gitignore             # Git ignore
└── README.md              # Этот файл
```

## Фазы разработки

| Фаза | Название | Описание |
|------|----------|----------|
| Phase 1 | Семантический QA | Базовый поиск по блокам и ответы с таймкодами |
| Phase 2 | SAG v2.0 Aware | Учёт уровня пользователя, концептов, связей |
| Phase 3 | Knowledge Graph | Рекомендация практик через граф знаний |
| Phase 4 | Диагностика | Распознавание состояний и маршруты трансформации |

## Текущий статус

**Phase 1** — в процессе планирования (задачи созданы в TaskMaster)

## Команды TaskMaster

```bash
# Просмотр всех задач
cd bot_psychologist
npx task-master list --with-subtasks

# Следующая задача
npx task-master next

# Изменить статус задачи
npx task-master set-status --id=1 --status=in-progress
```

## Требования

- Python 3.10+
- OpenAI API Key
- Данные из `voice_bot_pipeline/data/sag_final/`

## Лицензия

Private — для внутреннего использования

