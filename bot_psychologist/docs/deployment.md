# Развёртывание

## Навигация

- [Назад к README](../README.md)
- [Обзор проекта](./overview.md)
- [Конфигурация](./configuration.md)

---

## Описание и назначение

**Назначение документа**: Описать процесс развёртывания Bot Psychologist для локальной разработки и production.

**Для кого**: Разработчики, DevOps инженеры.

**Что содержит**:
- Локальный запуск
- Production развёртывание
- Docker (опционально)
- Мониторинг и логирование

---

## Локальный запуск

### Предварительные требования

- Python 3.10+
- Node.js 18+ (для Web UI)
- Данные из `voice_bot_pipeline` (SAG v2.0 JSON файлы)

### Шаг 1: Установка зависимостей

```bash
cd bot_psychologist

# Python зависимости
pip install -r requirements_bot.txt
pip install -r api/requirements.txt

# Node.js зависимости (для Web UI)
cd web_ui
npm install
cd ..
```

### Шаг 2: Настройка переменных окружения

Создайте `.env` файл:

```bash
cp .env.example .env
# Отредактируйте .env и добавьте OPENAI_API_KEY
```

### Шаг 3: Проверка данных

Убедитесь, что данные доступны:

```bash
# Проверить наличие sag_final данных
ls ../voice_bot_pipeline/data/sag_final/
```

### Шаг 4: Запуск тестов

```bash
# Phase 1
python test_phase1.py

# Phase 2
python test_phase2.py

# Phase 3
python test_phase3.py

# Phase 4
python test_phase4.py
```

### Шаг 5: Запуск API сервера

```bash
cd api
uvicorn main:app --reload --port 8000
```

API будет доступен по адресу `http://localhost:8000`.

### Шаг 6: Запуск Web UI

```bash
cd web_ui
npm run dev
```

Web UI будет доступен по адресу `http://localhost:5173`.

---

## Production развёртывание

### Рекомендации

1. **Используйте процесс-менеджер**: systemd, supervisor, или PM2
2. **Настройте reverse proxy**: Nginx или Apache
3. **Используйте HTTPS**: SSL/TLS сертификаты
4. **Настройте мониторинг**: логирование, метрики, алерты
5. **Используйте секреты**: храните API ключи в секретах

### Systemd Service

Создайте файл `/etc/systemd/system/bot-psychologist-api.service`:

```ini
[Unit]
Description=Bot Psychologist API
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/app/bot_psychologist/api
Environment="PATH=/app/venv/bin"
ExecStart=/app/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

**Запуск**:
```bash
sudo systemctl enable bot-psychologist-api
sudo systemctl start bot-psychologist-api
```

### Nginx Reverse Proxy

Создайте файл `/etc/nginx/sites-available/bot-psychologist`:

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location / {
        root /app/bot_psychologist/web_ui/dist;
        try_files $uri $uri/ /index.html;
    }
}
```

**Активация**:
```bash
sudo ln -s /etc/nginx/sites-available/bot-psychologist /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## Docker развёртывание (опционально)

### Dockerfile для API

Создайте `Dockerfile` в `api/`:

```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Dockerfile для Web UI

Создайте `Dockerfile` в `web_ui/`:

```dockerfile
FROM node:18-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
```

### Docker Compose

Создайте `docker-compose.yml`:

```yaml
version: '3.8'

services:
  api:
    build: ./api
    ports:
      - "8000:8000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - DATA_ROOT=/app/data
    volumes:
      - ../voice_bot_pipeline/data:/app/data:ro
    restart: unless-stopped

  web:
    build: ./web_ui
    ports:
      - "80:80"
    depends_on:
      - api
    restart: unless-stopped
```

**Запуск**:
```bash
docker-compose up -d
```

---

## Мониторинг и логирование

### Логирование

Логи сохраняются в:
- `logs/bot_agent/bot_agent.log` — логи Bot Agent
- Консоль — логи API сервера

### Метрики

Рекомендуется добавить:
- Количество запросов
- Время обработки
- Ошибки
- Использование ресурсов

### Health Check

Используйте endpoint `/api/v1/health` для проверки состояния:

```bash
curl http://localhost:8000/api/v1/health
```

---

## Резервное копирование

### Данные для резервного копирования

1. **История диалогов**: `.cache_bot_agent/conversations/`
2. **Конфигурация**: `.env` (без секретов)
3. **Логи**: `logs/`

### Пример скрипта резервного копирования

```bash
#!/bin/bash
BACKUP_DIR="/backups/bot-psychologist"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Резервное копирование истории диалогов
tar -czf $BACKUP_DIR/conversations_$DATE.tar.gz .cache_bot_agent/conversations/

# Резервное копирование логов
tar -czf $BACKUP_DIR/logs_$DATE.tar.gz logs/

echo "Backup completed: $DATE"
```

---

## Обновление

### Обновление кода

```bash
# Остановить сервисы
sudo systemctl stop bot-psychologist-api

# Обновить код
git pull

# Обновить зависимости
pip install -r requirements_bot.txt
pip install -r api/requirements.txt

# Перезапустить сервисы
sudo systemctl start bot-psychologist-api
```

### Обновление данных

При обновлении данных из `voice_bot_pipeline`:

1. Обновите данные в `voice_bot_pipeline`
2. Перезапустите API сервер (данные загрузятся автоматически)

---

## Troubleshooting

### Проблема: API не запускается

**Решение**:
1. Проверьте переменные окружения: `python -c "from bot_agent.config import config; config.validate()"`
2. Проверьте наличие данных: `ls ../voice_bot_pipeline/data/sag_final/`
3. Проверьте логи: `tail -f logs/bot_agent/bot_agent.log`

### Проблема: Web UI не подключается к API

**Решение**:
1. Проверьте `VITE_API_URL` в `.env.local`
2. Проверьте CORS настройки в API
3. Проверьте доступность API: `curl http://localhost:8000/api/v1/health`

### Проблема: Медленные ответы

**Решение**:
1. Проверьте количество блоков в данных
2. Оптимизируйте `TOP_K_BLOCKS` в конфигурации
3. Используйте более быструю модель LLM

---

## Навигация

- [Обзор проекта](./overview.md)
- [Конфигурация](./configuration.md)
- [Тестирование](./testing.md)
