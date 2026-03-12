# 🚀 Инструкция по запуску Bot_data_base

Полное руководство по установке, настройке и запуску системы подготовки базы знаний.

---

## 📋 Оглавление

1. [Требования](#-требования)
2. [Быстрый старт](#-быстрый-старт-3-команды)
3. [Пошаговая установка](#-пошаговая-установка)
4. [Настройка переменных окружения](#-настройка-переменных-окружения)
5. [Запуск сервера](#-запуск-сервера)
6. [Web UI](#-web-ui)
7. [API Endpoints](#-api-endpoints)
8. [Примеры использования](#-примеры-использования)
9. [Устранение проблем](#-устранение-проблем)

---

## 🛠 Требования

| Компонент | Версия | Обязательно |
|-----------|--------|-------------|
| **Python** | 3.10+ | ✅ Да |
| **OpenAI API Key** | — | ✅ Да (для SD-разметки) |
| **YouTube Data API** | — | ❌ Нет (опционально) |

---

## ⚡ Быстрый старт (3 команды)

```bash
cd Bot_data_base

# 1. Установка зависимостей
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

# 2. Настройка .env (отредактируйте файл)
copy .env.example .env

# 3. Запуск сервера
.\.venv\Scripts\python.exe -m uvicorn api.main:app --reload --port 8001
```

**Готово!** Откройте http://localhost:8003

---

## 📖 Пошаговая установка

### Шаг 1: Создание виртуального окружения

```bash
cd Bot_data_base

# Создание venv
python -m venv .venv

# Активация (Windows)
.\.venv\Scripts\activate

# Активация (Linux/Mac)
source .venv/bin/activate
```

### Шаг 2: Установка зависимостей

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Шаг 3: Настройка .env

```bash
copy .env.example .env
```

Отредактируйте `.env` и укажите минимум:
```env
OPENAI_API_KEY=sk-proj-...
API_HOST=0.0.0.0
API_PORT=8001
```

---

## 🖥 Запуск сервера

### Режим разработки (auto-reload)

```bash
.\.venv\Scripts\activate
python -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8003
```

### Production режим

```bash
.\.venv\Scripts\activate
python -m uvicorn api.main:app --host 0.0.0.0 --port 8003 --workers 4
```

---

## 🌐 Web UI

После запуска сервера доступны следующие страницы:

| Страница | URL | Описание |
|----------|-----|----------|
| **Dashboard** | http://localhost:8003/ | Общая статистика, последние источники |
| **Добавить YouTube** | http://localhost:8003/youtube | Форма для обработки YouTube видео |
| **Загрузить книгу** | http://localhost:8003/books | Загрузка книг (MD/TXT) |
| **Реестр источников** | http://localhost:8003/registry | Управление источниками |
| **API Docs** | http://localhost:8003/docs | Swagger документация |

### Прогресс обработки YouTube

1. ⏳ Queued — в очереди
2. ⬇️ Downloading — загрузка субтитров
3. ✂️ Chunking — разбиение на блоки
4. 🏷️ SD Labeling — SD-разметка
5. 🔧 Normalizing — нормализация
6. 📤 Exporting — экспорт JSON
7. 📚 Indexing — индексация в ChromaDB
8. ✅ Done — готово

---

## 🔌 API Endpoints

### YouTube

```bash
curl -X POST http://localhost:8003/api/ingest/youtube ^
  -H "Content-Type: application/json" ^
  -d "{\"url\": \"https://www.youtube.com/watch?v=VIDEO_ID\", \"author\": \"Саламат Сарсекенов\", \"author_id\": \"salamat\"}"
```

### Books

```bash
curl -X POST http://localhost:8003/api/ingest/books ^
  -F "title=Название книги" ^
  -F "author=Автор" ^
  -F "author_id=author_slug" ^
  -F "file=@/path/to/book.md"
```

### Registry

```bash
# Получить все источники
curl http://localhost:8003/api/registry/sources

# Удалить источник
curl -X DELETE http://localhost:8003/api/registry/sources/{source_id}
```

### Status

```bash
# Статистика базы данных
curl http://localhost:8003/api/status/stats
```

---

## 🔧 Устранение проблем

### Ошибка: "No module named 'fastapi'"

```bash
.\.venv\Scripts\activate
pip install -r requirements.txt
```

### Ошибка: "OPENAI_API_KEY not set"

Проверьте `.env` файл:
```env
OPENAI_API_KEY=sk-proj-...
```

### Порт 8003 занят

```bash
# Запуск на другом порту
python -m uvicorn api.main:app --reload --port 8004

# Или найти и убить процесс (Windows)
netstat -ano | findstr :8003
taskkill /PID {PID} /F
```

### ChromaDB ошибка инициализации

```bash
# Удалить старую БД
rmdir /s /q data\chroma_db

# Перезапустить сервер
```

### SD-разметка не работает

```bash
# Проверить OPENAI_API_KEY в .env
# Проверить логи
tail -f logs/pipeline.log

# Временное отключение
SD_LABELING_ENABLED=false
```

---

## 📊 Мониторинг

### Логи

```bash
# Просмотр логов в реальном времени
tail -f logs/pipeline.log
```

### Тесты

```bash
# Запуск тестов
python -m pytest tests/ -v --tb=short
```

---

## 📝 Лицензия

Private — для внутреннего использования

---

**Последнее обновление:** 11 марта 2026 г.
