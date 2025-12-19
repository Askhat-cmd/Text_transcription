# Конфигурация

## Навигация

- [Назад к README](../README.md)
- [Обзор проекта](./overview.md)
- [Развёртывание](./deployment.md)

---

## Описание и назначение

**Назначение документа**: Описать все настройки конфигурации проекта Bot Psychologist, переменные окружения и параметры.

**Для кого**: Разработчики, настраивающие проект, DevOps инженеры.

**Что содержит**:
- Переменные окружения
- Конфигурация Bot Agent
- Конфигурация API
- Конфигурация Web UI
- Примеры конфигурационных файлов

---

## Переменные окружения

### .env файл

Создайте файл `.env` в корне `bot_psychologist/`:

```env
# OpenAI API
OPENAI_API_KEY=sk-proj-...
PRIMARY_MODEL=gpt-4o-mini

# Данные
DATA_ROOT=../voice_bot_pipeline/data

# Отладка
DEBUG=False

# API (для Phase 5)
API_HOST=0.0.0.0
API_PORT=8000

# Web UI (для Phase 6)
VITE_API_URL=http://localhost:8000/api/v1
VITE_API_KEY=test-key-001
```

### Обязательные переменные

- **OPENAI_API_KEY** — ключ OpenAI API (обязательно)
- **DATA_ROOT** — путь к данным `voice_bot_pipeline` (по умолчанию: `../voice_bot_pipeline/data`)

### Опциональные переменные

- **PRIMARY_MODEL** — модель LLM (по умолчанию: `gpt-4o-mini`)
- **DEBUG** — режим отладки (по умолчанию: `False`)
- **API_HOST** — хост API сервера (по умолчанию: `0.0.0.0`)
- **API_PORT** — порт API сервера (по умолчанию: `8000`)

---

## Конфигурация Bot Agent

### Config (`bot_agent/config.py`)

**Пути к данным**:
```python
PROJECT_ROOT = Path(__file__).parent.parent  # bot_psychologist/
DATA_ROOT = Path(os.getenv("DATA_ROOT", "../voice_bot_pipeline/data"))
SAG_FINAL_DIR = DATA_ROOT / "sag_final"
```

**Параметры поиска**:
```python
TOP_K_BLOCKS = 5                    # Количество релевантных блоков
MIN_RELEVANCE_SCORE = 0.1          # Минимальный порог релевантности (0-1)
```

**LLM параметры**:
```python
LLM_MODEL = os.getenv("PRIMARY_MODEL", "gpt-4o-mini")
LLM_TEMPERATURE = 0.7              # Температура генерации (0-1)
LLM_MAX_TOKENS = 1500              # Максимальная длина ответа
```

**Кэширование**:
```python
ENABLE_CACHING = True
CACHE_DIR = PROJECT_ROOT / ".cache_bot_agent"
```

**Логи**:
```python
LOG_DIR = PROJECT_ROOT / "logs" / "bot_agent"
```

---

## Конфигурация API

### FastAPI (`api/main.py`)

**CORS**:
```python
allow_origins=[
    "http://localhost:3000",
    "http://localhost:8080",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8080",
    "*"  # TODO: в production ограничить
]
```

**Trusted Host**:
```python
allowed_hosts=["localhost", "127.0.0.1", "*.example.com"]
```

### API Keys (`api/auth.py`)

**Предустановленные ключи**:
```python
{
    "test-key-001": {
        "name": "Test Client",
        "rate_limit": 100  # requests per minute
    },
    "dev-key-001": {
        "name": "Development",
        "rate_limit": 1000
    }
}
```

**Добавление нового ключа**:
```python
api_key_manager.add_api_key(
    key="your-key-here",
    name="Your Client",
    rate_limit=500
)
```

---

## Конфигурация Web UI

### Vite (`web_ui/vite.config.ts`)

```typescript
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  }
})
```

### Tailwind CSS (`web_ui/tailwind.config.js`)

```javascript
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
```

### Переменные окружения (`web_ui/.env.local`)

```env
VITE_API_URL=http://localhost:8000/api/v1
VITE_API_KEY=test-key-001
```

---

## Примеры конфигурационных файлов

### .env.example

```env
# OpenAI API
OPENAI_API_KEY=sk-proj-...
PRIMARY_MODEL=gpt-4o-mini

# Данные
DATA_ROOT=../voice_bot_pipeline/data

# Отладка
DEBUG=False

# API
API_HOST=0.0.0.0
API_PORT=8000
```

### web_ui/.env.example

```env
VITE_API_URL=http://localhost:8000/api/v1
VITE_API_KEY=test-key-001
```

---

## Проверка конфигурации

### Валидация Bot Agent

```python
from bot_agent.config import config

try:
    config.validate()
    print("✅ Конфигурация валидна")
except ValueError as e:
    print(f"❌ Ошибка конфигурации: {e}")
```

### Информация о конфигурации

```python
from bot_agent.config import config

print(config.info())
```

Вывод:
```
╭─────────────────────────────────────────────╮
│ Bot Psychologist - Configuration            │
├─────────────────────────────────────────────┤
│ PROJECT_ROOT: /path/to/bot_psychologist
│ DATA_ROOT:    /path/to/voice_bot_pipeline/data
│ SAG_FINAL:    /path/to/sag_final
│ LLM_MODEL:    gpt-4o-mini
│ TOP_K:        5
│ DEBUG:        False
│ API_KEY:      ✓ Set
╰─────────────────────────────────────────────╯
```

---

## Production конфигурация

### Рекомендации

1. **API Keys**: Используйте сильные ключи, храните в секретах
2. **CORS**: Ограничьте разрешённые origins
3. **Rate Limiting**: Настройте лимиты для production
4. **Logging**: Настройте централизованное логирование
5. **Monitoring**: Добавьте мониторинг и алерты

### Пример production .env

```env
# OpenAI API
OPENAI_API_KEY=sk-proj-...  # Из секретов

# Данные
DATA_ROOT=/app/data

# Отладка
DEBUG=False

# API
API_HOST=0.0.0.0
API_PORT=8000

# Security
ALLOWED_ORIGINS=https://yourdomain.com
TRUSTED_HOSTS=yourdomain.com
```

---

## Навигация

- [Обзор проекта](./overview.md)
- [Развёртывание](./deployment.md)
- [Тестирование](./testing.md)
