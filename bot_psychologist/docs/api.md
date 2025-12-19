# REST API (Phase 5)

## Навигация

- [Назад к README](../README.md)
- [Обзор проекта](./overview.md)
- [Архитектура](./architecture.md)
- [Bot Agent](./bot_agent.md)

---

## Описание и назначение

**Назначение документа**: Полное описание REST API Bot Psychologist, всех endpoints, аутентификации и примеров использования.

**Для кого**: Разработчики, интегрирующие API, frontend разработчики.

**Что содержит**:
- Обзор API
- Аутентификация
- Endpoints Phase 1-4
- Модели запросов/ответов
- Примеры использования

---

## Обзор API

### Базовый URL

```
http://localhost:8000/api/v1
```

### Версия

**v0.5.0** (Phase 5)

### Формат данных

- **Request**: JSON
- **Response**: JSON
- **Content-Type**: `application/json`

### Документация

- **Swagger UI**: `http://localhost:8000/api/docs`
- **ReDoc**: `http://localhost:8000/api/redoc`
- **OpenAPI Schema**: `http://localhost:8000/api/openapi.json`

---

## Аутентификация

### API Keys

Все endpoints (кроме `/health`) требуют API ключ в заголовке:

```
X-API-Key: your-api-key-here
```

### Предустановленные ключи

- **test-key-001**: Test Client (100 req/min)
- **dev-key-001**: Development (1000 req/min)

### Rate Limiting

Лимит запросов зависит от типа API ключа:
- **Test**: 100 запросов в минуту
- **Development**: 1000 запросов в минуту

При превышении лимита возвращается `429 Too Many Requests`.

---

## Endpoints

### Questions Endpoints

#### POST `/api/v1/questions/basic`

**Phase 1**: Базовый QA без адаптации.

**Request**:
```json
{
  "query": "Что такое осознавание?",
  "user_id": "user_123",
  "user_level": "beginner",
  "include_path": false,
  "include_feedback_prompt": false,
  "debug": false
}
```

**Response**:
```json
{
  "status": "success",
  "answer": "Осознавание — это способность наблюдать...",
  "concepts": ["осознавание"],
  "sources": [
    {
      "block_id": "block_001",
      "title": "Что такое осознавание",
      "youtube_link": "https://youtube.com/watch?v=abc123&t=330s",
      "start": "00:05:30",
      "end": "00:08:15",
      "block_type": "concept_explanation",
      "complexity_score": 0.6
    }
  ],
  "metadata": {},
  "timestamp": "2024-01-01T12:00:00Z",
  "processing_time_seconds": 2.5
}
```

---

#### POST `/api/v1/questions/sag-aware`

**Phase 2**: SAG-aware QA с адаптацией по уровню.

**Request**:
```json
{
  "query": "Как развить осознавание?",
  "user_id": "user_123",
  "user_level": "beginner",
  "include_path": false,
  "include_feedback_prompt": false,
  "debug": false
}
```

**Response**: Аналогично `/basic`, но с адаптацией под уровень пользователя.

---

#### POST `/api/v1/questions/graph-powered`

**Phase 3**: Knowledge Graph Powered QA.

**Request**:
```json
{
  "query": "Какие практики помогают развить осознавание?",
  "user_id": "user_123",
  "user_level": "intermediate",
  "include_path": false,
  "include_feedback_prompt": false,
  "debug": false
}
```

**Response**: Аналогично `/basic`, но с практиками из Knowledge Graph в `metadata`.

---

#### POST `/api/v1/questions/adaptive`

**Phase 4**: Полностью адаптивный QA с анализом состояния и путями.

**Request**:
```json
{
  "query": "Хочу начать практиковать осознавание",
  "user_id": "user_123",
  "user_level": "beginner",
  "include_path": true,
  "include_feedback_prompt": true,
  "debug": false
}
```

**Response**:
```json
{
  "status": "success",
  "answer": "Отлично, что вы хотите начать...",
  "state_analysis": {
    "primary_state": "committed",
    "confidence": 0.85,
    "emotional_tone": "motivated",
    "recommendations": [
      "Изучить базовые концепты осознавания",
      "Начать с простых практик медитации"
    ]
  },
  "path_recommendation": {
    "current_state": "committed",
    "target_state": "integrated",
    "key_focus": "развитие базового осознавания",
    "steps_count": 5,
    "total_duration_weeks": 8,
    "first_step": {
      "step_number": 1,
      "title": "Развитие базового осознавания",
      "duration_weeks": 2,
      "practices": ["медитация", "дыхательные практики"],
      "key_concepts": ["осознавание", "внимание"]
    }
  },
  "feedback_prompt": "Был ли этот ответ полезен?",
  "concepts": ["осознавание", "медитация"],
  "sources": [...],
  "conversation_context": "Пользователь хочет начать практиковать...",
  "metadata": {},
  "timestamp": "2024-01-01T12:00:00Z",
  "processing_time_seconds": 3.2
}
```

---

### User History Endpoints

#### POST `/api/v1/users/{user_id}/history`

Получить историю диалога пользователя.

**Parameters**:
- `user_id` (path): ID пользователя
- `last_n_turns` (query, default=10): Последние N оборотов (1-50)

**Response**:
```json
{
  "user_id": "user_123",
  "total_turns": 15,
  "turns": [
    {
      "timestamp": "2024-01-01T12:00:00Z",
      "user_input": "Что такое осознавание?",
      "user_state": "curious",
      "bot_response": "Осознавание — это способность...",
      "blocks_used": 3,
      "concepts": ["осознавание"],
      "user_feedback": "positive",
      "user_rating": 5
    }
  ],
  "primary_interests": ["осознавание", "медитация"],
  "average_rating": 4.5,
  "last_interaction": "2024-01-01T12:00:00Z"
}
```

---

### Feedback Endpoints

#### POST `/api/v1/feedback`

Отправить обратную связь на ответ.

**Request**:
```json
{
  "user_id": "user_123",
  "turn_index": 0,
  "feedback": "positive",
  "rating": 5,
  "comment": "Очень помогло!"
}
```

**Response**:
```json
{
  "status": "success",
  "message": "Обратная связь сохранена",
  "user_id": "user_123",
  "turn_index": 0
}
```

**Feedback Types**:
- `positive` — ответ был полезен
- `negative` — ответ не помог
- `neutral` — нейтральная оценка

**Rating**: 1-5 звёзд (опционально)

---

### Statistics Endpoints

#### GET `/api/v1/stats`

Получить общую статистику системы.

**Response**:
```json
{
  "total_users": 150,
  "total_questions": 1250,
  "average_processing_time": 2.8,
  "top_states": {
    "curious": 450,
    "committed": 320,
    "practicing": 280
  },
  "top_interests": [],
  "feedback_stats": {},
  "timestamp": "2024-01-01T12:00:00Z"
}
```

---

### Health Check

#### GET `/api/v1/health`

Проверить статус сервера (не требует аутентификации).

**Response**:
```json
{
  "status": "healthy",
  "version": "0.5.0",
  "timestamp": "2024-01-01T12:00:00Z",
  "modules": {
    "bot_agent": true,
    "conversation_memory": true,
    "state_classifier": true,
    "path_builder": true,
    "api": true
  }
}
```

---

## Модели данных

### Request Models

#### AskQuestionRequest
```python
{
  "query": str,                    # Вопрос (3-500 символов)
  "user_id": str,                  # ID пользователя (default: "default")
  "user_level": "beginner" | "intermediate" | "advanced",
  "include_path": bool,            # Включить путь (default: true)
  "include_feedback_prompt": bool, # Включить запрос обратной связи (default: true)
  "debug": bool                    # Отладочная информация (default: false)
}
```

#### FeedbackRequest
```python
{
  "user_id": str,                  # ID пользователя
  "turn_index": int,               # Индекс хода (0-based)
  "feedback": "positive" | "negative" | "neutral",
  "rating": int,                   # Рейтинг 1-5 (опционально)
  "comment": str                   # Комментарий (опционально, max 500 символов)
}
```

### Response Models

#### AnswerResponse (Phase 1-3)
```python
{
  "status": str,
  "answer": str,
  "concepts": List[str],
  "sources": List[SourceResponse],
  "metadata": Dict[str, Any],
  "timestamp": str,
  "processing_time_seconds": float
}
```

#### AdaptiveAnswerResponse (Phase 4)
```python
{
  "status": str,
  "answer": str,
  "state_analysis": StateAnalysisResponse,
  "path_recommendation": Optional[PathRecommendationResponse],
  "feedback_prompt": str,
  "concepts": List[str],
  "sources": List[SourceResponse],
  "conversation_context": str,
  "metadata": Dict[str, Any],
  "timestamp": str,
  "processing_time_seconds": float
}
```

---

## Примеры использования

### cURL

#### Basic QA
```bash
curl -X POST "http://localhost:8000/api/v1/questions/basic" \
  -H "X-API-Key: test-key-001" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Что такое осознавание?",
    "user_id": "user_123"
  }'
```

#### Adaptive QA
```bash
curl -X POST "http://localhost:8000/api/v1/questions/adaptive" \
  -H "X-API-Key: test-key-001" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Хочу начать практиковать осознавание",
    "user_id": "user_123",
    "user_level": "beginner",
    "include_path": true
  }'
```

#### Feedback
```bash
curl -X POST "http://localhost:8000/api/v1/feedback" \
  -H "X-API-Key: test-key-001" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_123",
    "turn_index": 0,
    "feedback": "positive",
    "rating": 5
  }'
```

### Python

```python
import requests

API_URL = "http://localhost:8000/api/v1"
API_KEY = "test-key-001"

headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

# Basic QA
response = requests.post(
    f"{API_URL}/questions/basic",
    headers=headers,
    json={
        "query": "Что такое осознавание?",
        "user_id": "user_123"
    }
)
print(response.json())

# Adaptive QA
response = requests.post(
    f"{API_URL}/questions/adaptive",
    headers=headers,
    json={
        "query": "Хочу начать практиковать осознавание",
        "user_id": "user_123",
        "user_level": "beginner",
        "include_path": True
    }
)
print(response.json()["state_analysis"])
print(response.json()["path_recommendation"])
```

### JavaScript/TypeScript

```typescript
const API_URL = "http://localhost:8000/api/v1";
const API_KEY = "test-key-001";

// Basic QA
const response = await fetch(`${API_URL}/questions/basic`, {
  method: "POST",
  headers: {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
  },
  body: JSON.stringify({
    query: "Что такое осознавание?",
    user_id: "user_123"
  })
});

const data = await response.json();
console.log(data.answer);
```

---

## Обработка ошибок

### Коды статусов

- **200 OK** — успешный запрос
- **400 Bad Request** — невалидные данные запроса
- **403 Forbidden** — невалидный или отсутствующий API ключ
- **429 Too Many Requests** — превышен rate limit
- **500 Internal Server Error** — ошибка сервера

### Формат ошибки

```json
{
  "status": "error",
  "error": "Описание ошибки",
  "detail": "Детали ошибки (опционально)",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

---

## Middleware

### CORS
Разрешены origins:
- `http://localhost:3000`
- `http://localhost:8080`
- `http://127.0.0.1:3000`
- `http://127.0.0.1:8080`
- `*` (в production ограничить)

### Trusted Host
Разрешённые хосты:
- `localhost`
- `127.0.0.1`
- `*.example.com`

### Логирование
Все запросы логируются с временем выполнения.

---

## Навигация

- [Обзор проекта](./overview.md)
- [Архитектура](./architecture.md)
- [Bot Agent](./bot_agent.md)
- [Web UI](./web_ui.md)
