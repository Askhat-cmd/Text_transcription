# Text Transcription - Монорепозиторий проектов

Монорепозиторий, содержащий два связанных проекта для работы с транскрипцией и обработкой YouTube-лекций для создания AI-ботов.


## Важные пункты (2026-03-19)

- `bot_psychologist` подключён к `Bot_data_base` по HTTP: используйте `KNOWLEDGE_SOURCE=api` и `BOT_DB_URL=http://localhost:8003`.
- В логах старта бота должны быть строки `KNOWLEDGE_SOURCE=api` и `DB API url=http://localhost:8003`.
- `Bot_data_base /api/query` должен использовать эмбеддинги запроса той же модели, что и коллекция (иначе будет mismatch dimension и 503).
- Voyage rerank зависит от venv конкретного подпроекта: в `Bot_data_base` нужен пакет `voyageai`, иначе в логах будет `voyageai не установлен, rerank отключён`.

## 📁 Структура проектов

### 🎬 voice_bot_pipeline
**Полнофункциональный пайплайн для подготовки данных из YouTube-лекций**

- Обработка YouTube-видео и извлечение субтитров
- Структурированная генерация данных (SAG v2.0)
- Векторная база данных (ChromaDB)
- Граф знаний (Knowledge Graph)
- Система экстракторов знаний (5 этапов)
- Управление видео-реестром

**Документация:** [voice_bot_pipeline/README.md](voice_bot_pipeline/README.md)

### 🤖 bot_psychologist
**Супер-Умный Бот-Психолог на базе данных voice_bot_pipeline**

- AI-ассистент, работающий поверх данных SAG v2.0
- Семантический поиск по блокам и граф-сущностям
- Ответы с отсылками к конкретным видео и таймкодам
- Рекомендации практик через граф знаний

**Документация:** [bot_psychologist/README.md](bot_psychologist/README.md)

## 🔗 Связь между проектами

`bot_psychologist` использует данные, сгенерированные `voice_bot_pipeline`:
- Данные из `voice_bot_pipeline/data/sag_final/`
- Векторная база данных из `voice_bot_pipeline/data/chromadb/`
- Knowledge Graph для семантического поиска

---

## 🧬 SD-разметка (Спиральная Динамика)

**SD-разметка** — система автоматической классификации блоков контента по уровням Спиральной Динамики (Spiral Dynamics). Позволяет боту адаптировать ответы под уровень сознания пользователя.

### Уровни SD

| Уровень | Цвет | Описание | Доля в базе |
|---------|------|----------|-------------|
| **BEIGE** | 🟤 | Выживание, базовые страхи | 0.5% |
| **PURPLE** | 🟣 | Традиции, семья, коллектив | 0.5% |
| **RED** | 🔴 | Сила, власть, эго-центризм | 1.2% |
| **BLUE** | 🔵 | Правила, долг, дисциплина | 1.4% |
| **ORANGE** | 🟠 | Успех, цели, эффективность | 1.7% |
| **GREEN** | 🟢 | Чувства, эмпатия, принятие | 56.1% |
| **YELLOW** | 🟡 | Паттерны, системы, интеграция | 25.4% |
| **TURQUOISE** | 🔷 | Единство, холизм | 13.2% |

### Как работает SD-разметка

1. **voice_bot_pipeline** — каждый блок получает `sd_metadata` через LLM-классификацию:
   ```json
   {
     "sd_metadata": {
       "sd_level": "GREEN",
       "sd_secondary": "YELLOW",
       "complexity_score": 6,
       "emotional_tone": "validating",
       "requires_prior_concepts": true,
       "reasoning": "Текст ориентирован на читателя...",
       "author_id": "salamat",
       "labeled_by": "sd_labeler_v1"
     }
   }
   ```

2. **bot_psychologist** — при ответе фильтрует блоки по SD-совместимости:
   - Пользователь с GREEN-уровнем получает GREEN/YELLOW-контент
   - RED-контент фильтруется для GREEN-пользователя

### Запуск SD-разметки

```bash
cd voice_bot_pipeline

# Разметка всех файлов
python scripts/sd_labeler_cli.py --input data/sag_final/

# Тестовый запуск (dry-run)
python scripts/sd_labeler_cli.py --input data/sag_final/ --limit 3 --dry-run

# Переразметка существующих
python scripts/sd_labeler_cli.py --input data/sag_final/ --overwrite
```

### Статистика разметки

- **Всего блоков:** 1280
- **Процент размеченных:** 100%
- **Скрипт разметки:** `voice_bot_pipeline/scripts/sd_labeler_cli.py`
- **Интеграция в боте:** `bot_psychologist/bot_agent/retrieval/sd_filter.py`

### Документация

- PRD: `PRD v2 Фикс SD-разметки и фильтрации.md`
- SD-классификатор: `bot_psychologist/bot_agent/sd_classifier.py`
- SD-фильтр: `bot_psychologist/bot_agent/retrieval/sd_filter.py`

## 🚀 Быстрый старт

### 1. Настройка voice_bot_pipeline

```bash
cd voice_bot_pipeline
pip install -r requirements.txt
# Настройте .env файл с API ключами
python pipeline_orchestrator.py --help
```

### 2. Настройка bot_psychologist

```bash
cd bot_psychologist
pip install -r requirements_bot.txt
# Настройте .env файл
python test_phase1.py  # Тестирование Phase 1
```

## 📋 Требования

- Python 3.10+
- OpenAI API Key (для обработки текста)
- YouTube Data API Key (опционально, для метаданных)
- ChromaDB (устанавливается автоматически)

## 📂 Структура репозитория

```
Text_transcription/
├── voice_bot_pipeline/      # Проект 1: Pipeline обработки данных
│   ├── data/                # Обработанные данные
│   ├── text_processor/      # Обработка текста
│   ├── vector_db/           # Векторная БД
│   └── ...
├── bot_psychologist/        # Проект 2: AI-бот
│   ├── bot_agent/          # Код бота
│   ├── Docs_for_make_tasks/ # Документация
│   └── ...
├── АРХИВ_отработано/        # Архивная документация
└── README.md                # Этот файл
```

## 🔄 Workflow разработки

1. **Обработка видео** → `voice_bot_pipeline` генерирует структурированные данные
2. **Индексация** → Данные индексируются в векторную БД и Knowledge Graph
3. **Использование ботом** → `bot_psychologist` использует данные для ответов

## 📝 Лицензия

Private — для внутреннего использования

## 👤 Автор

Askhat-cmd
