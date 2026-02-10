

# PRODUCT REQUIREMENTS DOCUMENT (PRD)

# Telegram Bot Integration for Bot Psychologist v2.0

**Version:** 1.0
**Date:** 09.02.2026
**Author:** AI Agent (Cursor IDE)
**Target:** Integration Telegram Bot with existing FastAPI backend

***

## EXECUTIVE SUMMARY

Добавить Telegram-бот как дополнительный интерфейс к существующему `bot_psychologist` проекту. Бот будет работать параллельно с Web UI, используя общий FastAPI API-сервер и SessionManager для персистентной памяти.

**Ключевые цели:**

- ✅ Доступ через Telegram без необходимости браузера
- ✅ Персистентные диалоги с привязкой к `telegram_id`
- ✅ Команды управления контекстом (`/start`, `/new_topic`, `/delete_my_data`)
- ✅ GDPR compliance (полное удаление данных)
- ✅ Минимальные изменения в существующем коде

***

## 1. CURRENT STATE (ЧТО УЖЕ ЕСТЬ)

### 1.1 Архитектура проекта

```
bot_psychologist/
├── api/                    ✅ FastAPI сервер на :8000
│   ├── main.py
│   ├── routes.py          ← 12 REST endpoints
│   ├── models.py
│   └── auth.py
├── bot_agent/             ✅ Мозг бота (Phase 1-4)
│   ├── answer_adaptive.py ← Главная функция
│   ├── config.py
│   ├── conversation_memory.py
│   ├── storage/
│   │   └── session_manager.py ← SQLite persistence
│   └── ...
├── web_ui/                ✅ React UI на :5173
├── .env                   ✅ Конфигурация
└── requirements_bot.txt   ✅ Зависимости
```


### 1.2 Существующие endpoints (API)

Уже работают через HTTP:

```python
POST /api/v1/questions/adaptive       # Главный endpoint
GET  /api/v1/users/{user_id}/history  # История диалога
DELETE /api/v1/users/{user_id}/history # Очистка истории
DELETE /api/v1/users/{user_id}/gdpr-data # GDPR удаление
GET  /api/v1/users/{user_id}/session  # Статус сессии
GET  /api/v1/health                    # Health check
```


### 1.3 SessionManager (SQLite)

`bot_agent/storage/session_manager.py` уже умеет:[^1]

- Создавать сессии по `user_id`
- Сохранять всю историю диалога
- Хранить semantic embeddings
- Архивировать старые сессии (90/365 дней)
- Полностью удалять данные (GDPR)

**Схема БД:**

```sql
CREATE TABLE sessions (
    session_id TEXT PRIMARY KEY,
    user_id TEXT,  -- ← telegram_id сюда!
    working_state TEXT,
    conversation_summary TEXT,
    status TEXT DEFAULT 'active',
    created_at TIMESTAMP,
    last_active TIMESTAMP
);

CREATE TABLE conversation_turns (...);
CREATE TABLE semantic_embeddings (...);
```


***

## 2. TARGET STATE (ЧТО НУЖНО ДОБАВИТЬ)

### 2.1 Новые файлы

```
bot_psychologist/
├── telegram_bot.py        ← NEW! Telegram bot entry point
├── telegram/              ← NEW! Telegram-specific code
│   ├── __init__.py
│   ├── handlers.py        ← Обработчики команд/сообщений
│   └── utils.py           ← Утилиты (форматирование и т.д.)
├── .env                   ← ADD: TELEGRAM_BOT_TOKEN
└── requirements_telegram.txt ← ADD: pyTelegramBotAPI
```


### 2.2 Обновления существующих файлов

**`.env`** — добавить:

```bash
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_ENABLE_DEBUG=false
TELEGRAM_API_URL=http://localhost:8000
```

**`requirements_bot.txt`** или **`requirements_telegram.txt`**:

```
pyTelegramBotAPI==4.14.1
requests==2.31.0
python-dotenv==1.0.0  # уже есть
```


***

## 3. TELEGRAM BOT ARCHITECTURE

### 3.1 Схема взаимодействия

```
┌─────────────────┐
│  Пользователь   │
│   в Telegram    │
└────────┬────────┘
         │ text message
         ▼
┌─────────────────────────┐
│  telegram_bot.py         │  ← NEW! Long polling
│  (pyTelegramBotAPI)      │
└────────┬────────────────┘
         │ HTTP POST request
         ▼
┌─────────────────────────┐
│  FastAPI :8000           │  ← EXISTING
│  /api/v1/questions/adaptive │
└────────┬────────────────┘
         │ function call
         ▼
┌─────────────────────────┐
│  bot_agent/              │  ← EXISTING
│  answer_adaptive()       │
└────────┬────────────────┘
         │ read/write
         ▼
┌─────────────────────────┐
│  SQLite + ChromaDB       │  ← EXISTING
│  (session persistence)   │
└─────────────────────────┘
```


### 3.2 Флоу обработки сообщения

```python
# 1. Пользователь пишет в Telegram
message.text = "Как справиться с тревогой?"
telegram_id = message.from_user.id  # например 123456789

# 2. telegram_bot.py отправляет HTTP-запрос
response = requests.post(
    "http://localhost:8000/api/v1/questions/adaptive",
    json={
        "question": message.text,
        "user_id": str(telegram_id),  # ← user_id = telegram_id!
        "user_level": "intermediate"
    }
)

# 3. FastAPI вызывает answer_adaptive()
result = answer_adaptive(
    question=message.text,
    user_id=str(telegram_id)
)

# 4. SessionManager ищет/создаёт сессию по user_id
session = session_manager.load_session(str(telegram_id))

# 5. Генерация ответа через OpenAI
answer = result['answer']
mode = result['recommended_mode']
confidence = result['confidence_score']

# 6. Отправка в Telegram
bot.reply_to(message, answer)
```


***

## 4. DETAILED SPECIFICATION

### 4.1 telegram_bot.py (Entry Point)

**Назначение:** Главный файл запуска Telegram-бота.

```python
"""
Telegram Bot for Bot Psychologist
Entry point для Telegram интерфейса
"""

import os
import logging
from dotenv import load_dotenv
from telebot import TeleBot

from telegram.handlers import register_handlers

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Main entry point"""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN not found in .env")
    
    bot = TeleBot(token)
    register_handlers(bot)
    
    logger.info("🤖 Telegram bot started. Polling...")
    bot.infinity_polling()

if __name__ == "__main__":
    main()
```

**Запуск:**

```bash
cd bot_psychologist
python telegram_bot.py
```


***

### 4.2 telegram/handlers.py (Обработчики)

**Назначение:** Обработка команд и сообщений от пользователей.

```python
"""
Telegram handlers for bot commands and messages
"""

import os
import logging
import requests
from typing import Dict

logger = logging.getLogger(__name__)

# URL FastAPI backend
API_URL = os.getenv("TELEGRAM_API_URL", "http://localhost:8000")

# In-memory хранилище активных пользователей (в production → Redis)
active_users: Dict[str, bool] = {}


def register_handlers(bot):
    """Регистрация всех handlers"""
    
    @bot.message_handler(commands=['start'])
    def cmd_start(message):
        """
        Команда /start
        Начать новый диалог или продолжить существующий
        """
        telegram_id = str(message.from_user.id)
        username = message.from_user.first_name or "друг"
        
        logger.info(f"📱 /start from {telegram_id} ({username})")
        
        # Проверить существующую сессию через API
        try:
            response = requests.get(
                f"{API_URL}/api/v1/users/{telegram_id}/session",
                timeout=5
            )
            session_data = response.json()
            
            if session_data.get("exists"):
                # Сессия существует
                turns = session_data.get("total_turns", 0)
                bot.reply_to(
                    message,
                    f"С возвращением, {username}! 👋\n\n"
                    f"У нас уже {turns} сообщений в истории.\n"
                    f"Продолжим разговор? Или /new_topic для новой темы."
                )
            else:
                # Новая сессия
                bot.reply_to(
                    message,
                    f"Привет, {username}! 👋\n\n"
                    f"Я бот-психолог на базе лекций по осознаванию.\n"
                    f"Расскажи, что тебя беспокоит?\n\n"
                    f"📌 Команды:\n"
                    f"/new_topic - начать новую тему\n"
                    f"/history - показать историю\n"
                    f"/delete_my_data - удалить все мои данные (GDPR)"
                )
            
            active_users[telegram_id] = True
            
        except requests.RequestException as e:
            logger.error(f"❌ API error: {e}")
            bot.reply_to(
                message,
                "⚠️ Ошибка подключения к серверу. Попробуй позже."
            )
    
    
    @bot.message_handler(commands=['new_topic'])
    def cmd_new_topic(message):
        """
        Команда /new_topic
        Сбросить контекст и начать новый диалог
        """
        telegram_id = str(message.from_user.id)
        logger.info(f"🔄 /new_topic from {telegram_id}")
        
        try:
            # Удалить историю через API
            response = requests.delete(
                f"{API_URL}/api/v1/users/{telegram_id}/history",
                timeout=5
            )
            
            if response.status_code == 200:
                bot.reply_to(
                    message,
                    "✅ Контекст сброшен!\n\n"
                    "Начинаем с чистого листа. О чём хочешь поговорить?"
                )
            else:
                bot.reply_to(message, "⚠️ Не удалось сбросить контекст.")
        
        except requests.RequestException as e:
            logger.error(f"❌ API error: {e}")
            bot.reply_to(message, "⚠️ Ошибка подключения к серверу.")
    
    
    @bot.message_handler(commands=['history'])
    def cmd_history(message):
        """
        Команда /history
        Показать последние 5 сообщений из истории
        """
        telegram_id = str(message.from_user.id)
        logger.info(f"📋 /history from {telegram_id}")
        
        try:
            response = requests.post(
                f"{API_URL}/api/v1/users/{telegram_id}/history",
                params={"last_n_turns": 5},
                timeout=10
            )
            
            if response.status_code != 200:
                bot.reply_to(message, "История пуста или недоступна.")
                return
            
            data = response.json()
            turns = data.get("turns", [])
            
            if not turns:
                bot.reply_to(message, "История диалога пуста.")
                return
            
            # Форматировать историю
            history_text = "📋 **Последние сообщения:**\n\n"
            for i, turn in enumerate(turns[-5:], 1):
                user_input = turn.get("user_input", "")[:80]
                history_text += f"{i}. Ты: {user_input}...\n"
            
            history_text += f"\n\nВсего сообщений: {data.get('total_turns', 0)}"
            
            bot.reply_to(message, history_text, parse_mode="Markdown")
        
        except requests.RequestException as e:
            logger.error(f"❌ API error: {e}")
            bot.reply_to(message, "⚠️ Ошибка получения истории.")
    
    
    @bot.message_handler(commands=['delete_my_data'])
    def cmd_delete_data(message):
        """
        Команда /delete_my_data
        GDPR: полное удаление данных пользователя
        """
        telegram_id = str(message.from_user.id)
        logger.info(f"🗑️ /delete_my_data from {telegram_id}")
        
        # Подтверждение
        bot.reply_to(
            message,
            "⚠️ **ВНИМАНИЕ!**\n\n"
            "Это удалит ВСЕ твои данные навсегда:\n"
            "- Историю диалогов\n"
            "- Semantic embeddings\n"
            "- Персональные пути\n"
            "- SQLite records\n\n"
            "Отправь 'УДАЛИТЬ' для подтверждения.",
            parse_mode="Markdown"
        )
        
        # Ждём подтверждения
        bot.register_next_step_handler(message, confirm_delete_data)
    
    
    def confirm_delete_data(message):
        """Подтверждение удаления данных"""
        telegram_id = str(message.from_user.id)
        
        if message.text.strip().upper() != "УДАЛИТЬ":
            bot.reply_to(message, "Удаление отменено.")
            return
        
        try:
            response = requests.delete(
                f"{API_URL}/api/v1/users/{telegram_id}/gdpr-data",
                timeout=10
            )
            
            if response.status_code == 200:
                if telegram_id in active_users:
                    del active_users[telegram_id]
                
                bot.reply_to(
                    message,
                    "🗑️ Все твои данные удалены.\n\n"
                    "Отправь /start для начала нового диалога."
                )
            else:
                bot.reply_to(message, "⚠️ Ошибка удаления данных.")
        
        except requests.RequestException as e:
            logger.error(f"❌ API error: {e}")
            bot.reply_to(message, "⚠️ Ошибка удаления данных.")
    
    
    @bot.message_handler(func=lambda m: True)
    def handle_message(message):
        """
        Обработка всех текстовых сообщений
        Главный диалоговый handler
        """
        telegram_id = str(message.from_user.id)
        user_text = message.text
        
        # Проверка активности пользователя
        if telegram_id not in active_users:
            bot.reply_to(
                message,
                "Отправь /start чтобы начать диалог."
            )
            return
        
        logger.info(f"💬 Message from {telegram_id}: {user_text[:50]}...")
        
        # Показать "печатает..."
        bot.send_chat_action(message.chat.id, 'typing')
        
        try:
            # Отправить запрос в FastAPI
            response = requests.post(
                f"{API_URL}/api/v1/questions/adaptive",
                json={
                    "question": user_text,
                    "user_id": telegram_id,
                    "user_level": "intermediate",  # или из профиля
                    "include_path": False,
                    "include_feedback_prompt": False,
                    "debug": False
                },
                timeout=30
            )
            
            if response.status_code != 200:
                bot.reply_to(
                    message,
                    f"⚠️ Ошибка сервера: {response.status_code}"
                )
                return
            
            data = response.json()
            answer = data.get("answer", "Извини, не смог обработать.")
            mode = data.get("recommended_mode", "UNKNOWN")
            confidence = data.get("confidence_score", 0)
            
            # Форматировать ответ
            footer = f"\n\n_[{mode} | ⭐️{confidence:.2f}]_"
            
            # Отправить ответ
            bot.reply_to(
                message,
                answer + footer,
                parse_mode="Markdown"
            )
            
            logger.info(f"✅ Answered to {telegram_id} ({mode}, {confidence:.2f})")
        
        except requests.Timeout:
            bot.reply_to(
                message,
                "⏱️ Превышено время ожидания. Попробуй ещё раз."
            )
        except requests.RequestException as e:
            logger.error(f"❌ API error: {e}")
            bot.reply_to(
                message,
                "⚠️ Ошибка соединения с сервером."
            )
        except Exception as e:
            logger.error(f"❌ Unexpected error: {e}")
            bot.reply_to(
                message,
                "❌ Произошла ошибка. Попробуй ещё раз."
            )
```


***

### 4.3 telegram/utils.py (Утилиты)

**Назначение:** Вспомогательные функции для форматирования.

```python
"""
Telegram utility functions
"""

def format_mode_emoji(mode: str) -> str:
    """Вернуть эмодзи для режима"""
    emojis = {
        "PRESENCE": "🧘",
        "CLARIFICATION": "🤔",
        "VALIDATION": "💝",
        "THINKING": "🤯",
        "INTERVENTION": "💡",
        "INTEGRATION": "🌟"
    }
    return emojis.get(mode, "🤖")


def format_confidence_stars(confidence: float) -> str:
    """Вернуть звёзды для confidence"""
    stars = int(confidence * 5)
    return "⭐" * stars + "☆" * (5 - stars)


def truncate_text(text: str, max_length: int = 4096) -> str:
    """
    Обрезать текст до max_length (Telegram limit)
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."
```


***

## 5. INSTALLATION \& SETUP

### 5.1 Создание Telegram бота

1. **Открой Telegram**, найди [@BotFather](https://t.me/BotFather)
2. Напиши `/newbot`
3. Придумай имя: `Bot Psychologist`
4. Придумай username: `bot_psychologist_bot` (должен быть уникальным)
5. BotFather даст токен:

```
1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
```


### 5.2 Установка зависимостей

```bash
cd bot_psychologist
pip install pyTelegramBotAPI==4.14.1 requests==2.31.0
```

Или создай `requirements_telegram.txt`:

```
pyTelegramBotAPI==4.14.1
requests==2.31.0
```

```bash
pip install -r requirements_telegram.txt
```


### 5.3 Конфигурация .env

Добавь в `bot_psychologist/.env`:

```bash
# ===== TELEGRAM BOT =====
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_API_URL=http://localhost:8000
TELEGRAM_ENABLE_DEBUG=false

# ===== EXISTING CONFIG =====
OPENAI_API_KEY=sk-proj-...
DATA_ROOT=../voice_bot_pipeline/data
BOT_DB_PATH=data/bot_sessions.db
# ... остальное
```


***

## 6. RUNNING THE BOT

### 6.1 Запуск двух процессов

**Терминал 1** — FastAPI сервер:

```bash
cd bot_psychologist/api
uvicorn main:app --reload --port 8000 --host 0.0.0.0
```

**Терминал 2** — Telegram бот:

```bash
cd bot_psychologist
python telegram_bot.py
```

Вывод:

```
2026-02-09 12:45:00 - INFO - 🤖 Telegram bot started. Polling...
```


### 6.2 Проверка работы

1. Открой Telegram
2. Найди своего бота: `@bot_psychologist_bot`
3. Напиши `/start`
4. Задай вопрос: "Как справиться с тревогой?"
5. Получи ответ через 3-10 секунд

***

## 7. FEATURE SPECIFICATION

### 7.1 Команды бота

| Команда | Описание | Пример |
| :-- | :-- | :-- |
| `/start` | Начать диалог или продолжить существующий | `/start` |
| `/new_topic` | Сбросить контекст и начать новую тему | `/new_topic` |
| `/history` | Показать последние 5 сообщений | `/history` |
| `/delete_my_data` | GDPR: удалить все данные | `/delete_my_data` → `УДАЛИТЬ` |

### 7.2 Флоу работы

**Сценарий 1: Новый пользователь**

```
1. Пользователь → /start
2. Бот → "Привет! Расскажи, что тебя беспокоит?"
3. Пользователь → "Меня беспокоит работа"
4. Бот → [Ответ через answer_adaptive]
5. SessionManager создаёт session в SQLite
```

**Сценарий 2: Возвращающийся пользователь**

```
1. Пользователь → /start
2. Бот проверяет GET /api/v1/users/{telegram_id}/session
3. Бот → "С возвращением! У нас уже 15 сообщений."
4. Пользователь → "Я снова переживаю"
5. Бот → [Ответ с учётом истории]
```

**Сценарий 3: Сброс контекста**

```
1. Пользователь → /new_topic
2. Бот → DELETE /api/v1/users/{telegram_id}/history
3. SessionManager очищает turns, embeddings
4. Бот → "✅ Контекст сброшен!"
```

**Сценарий 4: GDPR удаление**

```
1. Пользователь → /delete_my_data
2. Бот → "⚠️ ВНИМАНИЕ! Отправь 'УДАЛИТЬ' для подтверждения."
3. Пользователь → "УДАЛИТЬ"
4. Бот → DELETE /api/v1/users/{telegram_id}/gdpr-data
5. SessionManager удаляет из SQLite + JSON + semantic cache
6. Бот → "🗑️ Все данные удалены."
```


### 7.3 Форматирование ответов

**Базовый ответ:**

```
[Текст ответа от OpenAI]

[VALIDATION | ⭐️0.78]
```

**С эмодзи режима:**

```
💝 [Текст ответа]

[VALIDATION | ⭐️⭐️⭐️⭐️☆]
```

**Длинные ответы** обрезаются до 4096 символов (лимит Telegram).

***

## 8. ERROR HANDLING

### 8.1 Типы ошибок

| Ошибка | Причина | Ответ пользователю |
| :-- | :-- | :-- |
| API недоступен | FastAPI не запущен | "⚠️ Ошибка подключения к серверу" |
| Timeout | OpenAI > 30 секунд | "⏱️ Превышено время ожидания" |
| 500 Internal Error | Ошибка в bot_agent | "❌ Произошла ошибка" |
| No /start | Пользователь не активирован | "Отправь /start чтобы начать" |

### 8.2 Логирование

Все ошибки логируются:

```python
logger.error(f"❌ API error: {e}")
logger.info(f"💬 Message from {telegram_id}: {user_text[:50]}...")
logger.info(f"✅ Answered to {telegram_id} ({mode}, {confidence:.2f})")
```

Логи пишутся в stdout и могут быть перенаправлены в файл:

```bash
python telegram_bot.py > telegram_bot.log 2>&1
```


***

## 9. DEPLOYMENT CONSIDERATIONS

### 9.1 Production Checklist

- [ ] Заменить `active_users` (dict) на Redis для multi-instance
- [ ] Настроить webhook вместо polling для production
- [ ] Добавить rate limiting (защита от спама)
- [ ] Настроить systemd service для автозапуска
- [ ] Настроить мониторинг (Prometheus + Grafana)
- [ ] Включить SSL для webhook (если используется)
- [ ] Backup SQLite базы каждые 24 часа


### 9.2 Systemd Service (Linux)

Создай `/etc/systemd/system/telegram-bot.service`:

```ini
[Unit]
Description=Bot Psychologist Telegram Bot
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/bot_psychologist
ExecStart=/usr/bin/python3 telegram_bot.py
Restart=always
RestartSec=10
Environment="PYTHONUNBUFFERED=1"

[Install]
WantedBy=multi-user.target
```

Активация:

```bash
sudo systemctl daemon-reload
sudo systemctl enable telegram-bot
sudo systemctl start telegram-bot
sudo systemctl status telegram-bot
```


### 9.3 Webhook (для production)

**Вместо polling** можно использовать webhook:

```python
# В telegram_bot.py
from flask import Flask, request

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    json_str = request.get_data().decode('UTF-8')
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return '', 200

if __name__ == "__main__":
    # Set webhook
    bot.remove_webhook()
    bot.set_webhook(url="https://your-domain.com/webhook")
    app.run(host='0.0.0.0', port=8443)
```

Требует:

- SSL сертификат
- Публичный домен
- Nginx reverse proxy

***

## 10. TESTING STRATEGY

### 10.1 Unit Tests

Создай `tests/test_telegram_handlers.py`:

```python
import unittest
from unittest.mock import Mock, patch
from telegram.handlers import register_handlers

class TestTelegramHandlers(unittest.TestCase):
    
    def setUp(self):
        self.bot = Mock()
        register_handlers(self.bot)
    
    @patch('telegram.handlers.requests.get')
    def test_start_command_new_user(self, mock_get):
        """Тест /start для нового пользователя"""
        mock_get.return_value.json.return_value = {"exists": False}
        
        message = Mock()
        message.from_user.id = 123456
        message.from_user.first_name = "Test"
        
        # Call handler
        self.bot.message_handler.calls[^0](message)
        
        # Assert
        self.bot.reply_to.assert_called()
    
    # ... другие тесты
```


### 10.2 Integration Tests

```bash
# Тест полного флоу
curl -X POST http://localhost:8000/api/v1/questions/adaptive \
  -H "Content-Type: application/json" \
  -d '{"question": "Test", "user_id": "test_telegram_123"}'
```


### 10.3 Manual Testing Checklist

- [ ] `/start` создаёт новую сессию
- [ ] Повторный `/start` продолжает сессию
- [ ] Сообщения сохраняются в SQLite
- [ ] `/new_topic` очищает историю
- [ ] `/history` показывает последние сообщения
- [ ] `/delete_my_data` требует подтверждение
- [ ] Подтверждение "УДАЛИТЬ" удаляет данные
- [ ] Ошибки API обрабатываются gracefully
- [ ] Timeout 30 секунд работает
- [ ] Длинные ответы обрезаются

***

## 11. PERFORMANCE CONSIDERATIONS

### 11.1 Метрики

| Метрика | Target | Измерение |
| :-- | :-- | :-- |
| Время ответа | < 10 сек | 95 percentile |
| API latency | < 3 сек | Среднее |
| OpenAI latency | < 5 сек | Среднее |
| Memory per user | < 5 MB | SQLite + cache |
| Concurrent users | 100+ | Одновременно |

### 11.2 Оптимизации

**Кеширование:**

```python
# В telegram/handlers.py
from functools import lru_cache

@lru_cache(maxsize=128)
def get_user_level(telegram_id: str) -> str:
    """Кешировать user_level"""
    # ... запрос к API
```

**Connection pooling:**

```python
session = requests.Session()
adapter = HTTPAdapter(pool_connections=10, pool_maxsize=20)
session.mount('http://', adapter)
```


***

## 12. SECURITY

### 12.1 Угрозы

- **Injection attacks**: Пользователь отправляет SQL/code
- **Rate limiting**: Спам сообщениями
- **Token leak**: `.env` попадает в git
- **GDPR violations**: Данные не удаляются


### 12.2 Защита

**1. Валидация input:**

```python
def sanitize_input(text: str) -> str:
    """Очистить input от опасных символов"""
    # Удалить SQL keywords
    dangerous = ["DROP", "DELETE", "INSERT", "UPDATE", "SELECT"]
    for word in dangerous:
        text = text.replace(word, "")
    return text[:500]  # Max 500 символов
```

**2. Rate limiting:**

```python
from collections import defaultdict
from time import time

user_last_message = defaultdict(float)
RATE_LIMIT_SECONDS = 3

def check_rate_limit(telegram_id: str) -> bool:
    now = time()
    if now - user_last_message[telegram_id] < RATE_LIMIT_SECONDS:
        return False
    user_last_message[telegram_id] = now
    return True
```

**3. .gitignore:**

```
.env
*.db
*.log
__pycache__/
```


***

## 13. MONITORING \& ANALYTICS

### 13.1 Метрики для мониторинга

```python
# В telegram/handlers.py
from prometheus_client import Counter, Histogram

telegram_messages_total = Counter(
    'telegram_messages_total',
    'Total messages received'
)

telegram_response_time = Histogram(
    'telegram_response_time_seconds',
    'Response time in seconds'
)

@telegram_messages_total.count_exceptions()
def handle_message(message):
    with telegram_response_time.time():
        # ... обработка
```


### 13.2 Дашборд (Grafana)

**Метрики:**

- Total messages per hour
- Average response time
- Error rate (HTTP 500)
- Active users (unique telegram_id)
- Top states (VALIDATION, PRESENCE, etc.)

***

## 14. FUTURE ENHANCEMENTS

### 14.1 Phase 2 Features

- [ ] **Inline кнопки**: "Подробнее", "Примеры", "Практики"
- [ ] **Голосовые сообщения**: Транскрипция через Whisper API
- [ ] **Отложенные напоминания**: "Как прошёл день?"
- [ ] **Персональные пути**: Показ прогресса в боте
- [ ] **Мультиязычность**: Определение языка автоматически
- [ ] **Групповые чаты**: Бот в групповых диалогах
- [ ] **Admin панель**: Web UI для статистики


### 14.2 Inline Keyboards (пример)

```python
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

markup = InlineKeyboardMarkup()
markup.row(
    InlineKeyboardButton("📖 Подробнее", callback_data="more_info"),
    InlineKeyboardButton("🧘 Практики", callback_data="practices")
)

bot.reply_to(message, answer, reply_markup=markup)
```


***

## 15. APPENDIX

### 15.1 Файловая структура (итоговая)

```
bot_psychologist/
├── telegram_bot.py                 # Entry point
├── telegram/
│   ├── __init__.py
│   ├── handlers.py                 # Команды и сообщения
│   └── utils.py                    # Утилиты
├── api/                            # Existing
│   ├── main.py
│   ├── routes.py
│   ├── models.py
│   └── auth.py
├── bot_agent/                      # Existing
│   ├── answer_adaptive.py
│   ├── conversation_memory.py
│   ├── storage/
│   │   └── session_manager.py
│   └── ...
├── .env                            # + TELEGRAM_BOT_TOKEN
├── requirements_telegram.txt       # NEW
├── README_telegram.md              # NEW: документация
└── tests/
    └── test_telegram_handlers.py   # NEW: тесты
```


### 15.2 Размеры кода (оценка)

| Файл | LOC (lines of code) |
| :-- | :-- |
| telegram_bot.py | 30 |
| telegram/handlers.py | 250 |
| telegram/utils.py | 50 |
| requirements_telegram.txt | 3 |
| **TOTAL** | **~330 LOC** |

### 15.3 Время разработки (estimate)

| Задача | Время |
| :-- | :-- |
| Создание бота у @BotFather | 5 мин |
| Написание telegram_bot.py | 10 мин |
| Написание telegram/handlers.py | 60 мин |
| Написание telegram/utils.py | 15 мин |
| Тестирование | 30 мин |
| Документация | 20 мин |
| **TOTAL** | **~2.5 часа** |

### 15.4 Ссылки

- [pyTelegramBotAPI docs](https://github.com/eternnoir/pyTelegramBotAPI)
- [Telegram Bot API](https://core.telegram.org/bots/api)
- [FastAPI docs](https://fastapi.tiangolo.com/)
- [BotFather](https://t.me/BotFather)

***

## ACCEPTANCE CRITERIA

✅ Telegram-бот подключён к @BotFather
✅ Команды `/start`, `/new_topic`, `/history`, `/delete_my_data` работают
✅ Сообщения сохраняются в SQLite через SessionManager
✅ Ответы генерируются через answer_adaptive() API
✅ GDPR compliance: полное удаление данных
✅ Логирование всех событий
✅ Обработка ошибок (API unavailable, timeout)
✅ Документация и тесты

***

## SIGN-OFF

**Prepared by:** AI Agent (Cursor IDE)
**Date:** 09.02.2026
**Status:** READY FOR IMPLEMENTATION
**Estimated complexity:** LOW (использует существующую инфраструктуру)
**Estimated time:** 2-3 часа для базовой версии

***

**Next steps:**

1. Создать бота у @BotFather
2. Добавить токен в `.env`
3. Создать `telegram_bot.py` и `telegram/handlers.py`
4. Запустить FastAPI + Telegram bot
5. Протестировать основные команды
6. Deploy в production (опционально)
<span style="display:none">[^2]</span>

<div align="center">⁂</div>

[^1]: PRODUCT-REQUIREMENTS-DOCUMENT-PRD-v2.0.md

[^2]: image.jpg

