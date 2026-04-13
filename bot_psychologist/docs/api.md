# REST API (Phase 5)

## РќР°РІРёРіР°С†РёСЏ

- [РќР°Р·Р°Рґ Рє README](../README.md)
- [РћР±Р·РѕСЂ РїСЂРѕРµРєС‚Р°](./overview.md)
- [РђСЂС…РёС‚РµРєС‚СѓСЂР°](./architecture.md)
- [Bot Agent](./bot_agent.md)

---

## РћРїРёСЃР°РЅРёРµ Рё РЅР°Р·РЅР°С‡РµРЅРёРµ

**РќР°Р·РЅР°С‡РµРЅРёРµ РґРѕРєСѓРјРµРЅС‚Р°**: РџРѕР»РЅРѕРµ РѕРїРёСЃР°РЅРёРµ REST API Bot Psychologist, РІСЃРµС… endpoints, Р°СѓС‚РµРЅС‚РёС„РёРєР°С†РёРё Рё РїСЂРёРјРµСЂРѕРІ РёСЃРїРѕР»СЊР·РѕРІР°РЅРёСЏ.

**Р”Р»СЏ РєРѕРіРѕ**: Р Р°Р·СЂР°Р±РѕС‚С‡РёРєРё, РёРЅС‚РµРіСЂРёСЂСѓСЋС‰РёРµ API, frontend СЂР°Р·СЂР°Р±РѕС‚С‡РёРєРё.

**Р§С‚Рѕ СЃРѕРґРµСЂР¶РёС‚**:
- РћР±Р·РѕСЂ API
- РђСѓС‚РµРЅС‚РёС„РёРєР°С†РёСЏ
- Endpoints Phase 1-4
- РњРѕРґРµР»Рё Р·Р°РїСЂРѕСЃРѕРІ/РѕС‚РІРµС‚РѕРІ
- РџСЂРёРјРµСЂС‹ РёСЃРїРѕР»СЊР·РѕРІР°РЅРёСЏ

---

## РћР±Р·РѕСЂ API

### Р‘Р°Р·РѕРІС‹Р№ URL

```
http://localhost:8000/api/v1
```

### Р’РµСЂСЃРёСЏ

**v0.5.0** (Phase 5)

### Р¤РѕСЂРјР°С‚ РґР°РЅРЅС‹С…

- **Request**: JSON
- **Response**: JSON
- **Content-Type**: `application/json`

### Р”РѕРєСѓРјРµРЅС‚Р°С†РёСЏ

- **Swagger UI**: `http://localhost:8000/api/docs`
- **ReDoc**: `http://localhost:8000/api/redoc`
- **OpenAPI Schema**: `http://localhost:8000/api/openapi.json`

---

## РђСѓС‚РµРЅС‚РёС„РёРєР°С†РёСЏ

### API Keys

Р’СЃРµ endpoints (РєСЂРѕРјРµ `/health`) С‚СЂРµР±СѓСЋС‚ API РєР»СЋС‡ РІ Р·Р°РіРѕР»РѕРІРєРµ:

```
X-API-Key: your-api-key-here
```

### РџСЂРµРґСѓСЃС‚Р°РЅРѕРІР»РµРЅРЅС‹Рµ РєР»СЋС‡Рё

- **test-key-001**: Test Client (100 req/min)
- **dev-key-001**: Development (1000 req/min)

### Rate Limiting

Р›РёРјРёС‚ Р·Р°РїСЂРѕСЃРѕРІ Р·Р°РІРёСЃРёС‚ РѕС‚ С‚РёРїР° API РєР»СЋС‡Р°:
- **Test**: 100 Р·Р°РїСЂРѕСЃРѕРІ РІ РјРёРЅСѓС‚Сѓ
- **Development**: 1000 Р·Р°РїСЂРѕСЃРѕРІ РІ РјРёРЅСѓС‚Сѓ

РџСЂРё РїСЂРµРІС‹С€РµРЅРёРё Р»РёРјРёС‚Р° РІРѕР·РІСЂР°С‰Р°РµС‚СЃСЏ `429 Too Many Requests`.

---

## Endpoints

### Questions Endpoints

#### POST `/api/v1/questions/basic`

**Phase 1**: Р‘Р°Р·РѕРІС‹Р№ QA Р±РµР· Р°РґР°РїС‚Р°С†РёРё.

**Request**:
```json
{
  "query": "Р§С‚Рѕ С‚Р°РєРѕРµ РѕСЃРѕР·РЅР°РІР°РЅРёРµ?",
  "user_id": "user_123",
  "include_path": false,
  "include_feedback_prompt": false,
  "debug": false
}
```

**Response**:
```json
{
  "status": "success",
  "answer": "РћСЃРѕР·РЅР°РІР°РЅРёРµ вЂ” СЌС‚Рѕ СЃРїРѕСЃРѕР±РЅРѕСЃС‚СЊ РЅР°Р±Р»СЋРґР°С‚СЊ...",
  "concepts": ["РѕСЃРѕР·РЅР°РІР°РЅРёРµ"],
  "sources": [
    {
      "block_id": "block_001",
      "title": "Р§С‚Рѕ С‚Р°РєРѕРµ РѕСЃРѕР·РЅР°РІР°РЅРёРµ",
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

#### POST `/api/v1/questions/graph-powered`

**Phase 3**: Knowledge Graph Powered QA.

**Request**:
```json
{
  "query": "РљР°РєРёРµ РїСЂР°РєС‚РёРєРё РїРѕРјРѕРіР°СЋС‚ СЂР°Р·РІРёС‚СЊ РѕСЃРѕР·РЅР°РІР°РЅРёРµ?",
  "user_id": "user_123",
  "include_path": false,
  "include_feedback_prompt": false,
  "debug": false
}
```

**Response**: РђРЅР°Р»РѕРіРёС‡РЅРѕ `/basic`, РЅРѕ СЃ РїСЂР°РєС‚РёРєР°РјРё РёР· Knowledge Graph РІ `metadata`.

---

#### POST `/api/v1/questions/adaptive`

**Phase 4**: РџРѕР»РЅРѕСЃС‚СЊСЋ Р°РґР°РїС‚РёРІРЅС‹Р№ QA СЃ Р°РЅР°Р»РёР·РѕРј СЃРѕСЃС‚РѕСЏРЅРёСЏ Рё РїСѓС‚СЏРјРё.

**Request**:
```json
{
  "query": "РҐРѕС‡Сѓ РЅР°С‡Р°С‚СЊ РїСЂР°РєС‚РёРєРѕРІР°С‚СЊ РѕСЃРѕР·РЅР°РІР°РЅРёРµ",
  "user_id": "user_123",
  "include_path": true,
  "include_feedback_prompt": true,
  "debug": false
}
```

**Response**:
```json
{
  "status": "success",
  "answer": "РћС‚Р»РёС‡РЅРѕ, С‡С‚Рѕ РІС‹ С…РѕС‚РёС‚Рµ РЅР°С‡Р°С‚СЊ...",
  "state_analysis": {
    "primary_state": "committed",
    "confidence": 0.85,
    "emotional_tone": "motivated",
    "recommendations": [
      "РР·СѓС‡РёС‚СЊ Р±Р°Р·РѕРІС‹Рµ РєРѕРЅС†РµРїС‚С‹ РѕСЃРѕР·РЅР°РІР°РЅРёСЏ",
      "РќР°С‡Р°С‚СЊ СЃ РїСЂРѕСЃС‚С‹С… РїСЂР°РєС‚РёРє РјРµРґРёС‚Р°С†РёРё"
    ]
  },
  "path_recommendation": {
    "current_state": "committed",
    "target_state": "integrated",
    "key_focus": "СЂР°Р·РІРёС‚РёРµ Р±Р°Р·РѕРІРѕРіРѕ РѕСЃРѕР·РЅР°РІР°РЅРёСЏ",
    "steps_count": 5,
    "total_duration_weeks": 8,
    "first_step": {
      "step_number": 1,
      "title": "Р Р°Р·РІРёС‚РёРµ Р±Р°Р·РѕРІРѕРіРѕ РѕСЃРѕР·РЅР°РІР°РЅРёСЏ",
      "duration_weeks": 2,
      "practices": ["РјРµРґРёС‚Р°С†РёСЏ", "РґС‹С…Р°С‚РµР»СЊРЅС‹Рµ РїСЂР°РєС‚РёРєРё"],
      "key_concepts": ["РѕСЃРѕР·РЅР°РІР°РЅРёРµ", "РІРЅРёРјР°РЅРёРµ"]
    }
  },
  "feedback_prompt": "Р‘С‹Р» Р»Рё СЌС‚РѕС‚ РѕС‚РІРµС‚ РїРѕР»РµР·РµРЅ?",
  "concepts": ["РѕСЃРѕР·РЅР°РІР°РЅРёРµ", "РјРµРґРёС‚Р°С†РёСЏ"],
  "sources": [...],
  "conversation_context": "РџРѕР»СЊР·РѕРІР°С‚РµР»СЊ С…РѕС‡РµС‚ РЅР°С‡Р°С‚СЊ РїСЂР°РєС‚РёРєРѕРІР°С‚СЊ...",
  "metadata": {},
  "timestamp": "2024-01-01T12:00:00Z",
  "processing_time_seconds": 3.2
}
```

---

### User History Endpoints

#### POST `/api/v1/users/{user_id}/history`

РџРѕР»СѓС‡РёС‚СЊ РёСЃС‚РѕСЂРёСЋ РґРёР°Р»РѕРіР° РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ.

**Parameters**:
- `user_id` (path): ID РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ
- `last_n_turns` (query, default=10): РџРѕСЃР»РµРґРЅРёРµ N РѕР±РѕСЂРѕС‚РѕРІ (1-50)

**Response**:
```json
{
  "user_id": "user_123",
  "total_turns": 15,
  "turns": [
    {
      "timestamp": "2024-01-01T12:00:00Z",
      "user_input": "Р§С‚Рѕ С‚Р°РєРѕРµ РѕСЃРѕР·РЅР°РІР°РЅРёРµ?",
      "user_state": "curious",
      "bot_response": "РћСЃРѕР·РЅР°РІР°РЅРёРµ вЂ” СЌС‚Рѕ СЃРїРѕСЃРѕР±РЅРѕСЃС‚СЊ...",
      "blocks_used": 3,
      "concepts": ["РѕСЃРѕР·РЅР°РІР°РЅРёРµ"],
      "user_feedback": "positive",
      "user_rating": 5
    }
  ],
  "primary_interests": ["РѕСЃРѕР·РЅР°РІР°РЅРёРµ", "РјРµРґРёС‚Р°С†РёСЏ"],
  "average_rating": 4.5,
  "last_interaction": "2024-01-01T12:00:00Z"
}
```

---

### Feedback Endpoints

#### POST `/api/v1/feedback`

РћС‚РїСЂР°РІРёС‚СЊ РѕР±СЂР°С‚РЅСѓСЋ СЃРІСЏР·СЊ РЅР° РѕС‚РІРµС‚.

**Request**:
```json
{
  "user_id": "user_123",
  "turn_index": 0,
  "feedback": "positive",
  "rating": 5,
  "comment": "РћС‡РµРЅСЊ РїРѕРјРѕРіР»Рѕ!"
}
```

**Response**:
```json
{
  "status": "success",
  "message": "РћР±СЂР°С‚РЅР°СЏ СЃРІСЏР·СЊ СЃРѕС…СЂР°РЅРµРЅР°",
  "user_id": "user_123",
  "turn_index": 0
}
```

**Feedback Types**:
- `positive` вЂ” РѕС‚РІРµС‚ Р±С‹Р» РїРѕР»РµР·РµРЅ
- `negative` вЂ” РѕС‚РІРµС‚ РЅРµ РїРѕРјРѕРі
- `neutral` вЂ” РЅРµР№С‚СЂР°Р»СЊРЅР°СЏ РѕС†РµРЅРєР°

**Rating**: 1-5 Р·РІС‘Р·Рґ (РѕРїС†РёРѕРЅР°Р»СЊРЅРѕ)

---

### Statistics Endpoints

#### GET `/api/v1/stats`

РџРѕР»СѓС‡РёС‚СЊ РѕР±С‰СѓСЋ СЃС‚Р°С‚РёСЃС‚РёРєСѓ СЃРёСЃС‚РµРјС‹.

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

РџСЂРѕРІРµСЂРёС‚СЊ СЃС‚Р°С‚СѓСЃ СЃРµСЂРІРµСЂР° (РЅРµ С‚СЂРµР±СѓРµС‚ Р°СѓС‚РµРЅС‚РёС„РёРєР°С†РёРё).

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

## РњРѕРґРµР»Рё РґР°РЅРЅС‹С…

### Request Models

#### AskQuestionRequest
```python
{
  "query": str,                    # Р’РѕРїСЂРѕСЃ (3-500 СЃРёРјРІРѕР»РѕРІ)
  "user_id": str,                  # ID РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ (default: "default")
  "include_path": bool,            # Р’РєР»СЋС‡РёС‚СЊ РїСѓС‚СЊ (default: true)
  "include_feedback_prompt": bool, # Р’РєР»СЋС‡РёС‚СЊ Р·Р°РїСЂРѕСЃ РѕР±СЂР°С‚РЅРѕР№ СЃРІСЏР·Рё (default: true)
  "debug": bool                    # РћС‚Р»Р°РґРѕС‡РЅР°СЏ РёРЅС„РѕСЂРјР°С†РёСЏ (default: false)
}
```

#### FeedbackRequest
```python
{
  "user_id": str,                  # ID РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ
  "turn_index": int,               # РРЅРґРµРєСЃ С…РѕРґР° (0-based)
  "feedback": "positive" | "negative" | "neutral",
  "rating": int,                   # Р РµР№С‚РёРЅРі 1-5 (РѕРїС†РёРѕРЅР°Р»СЊРЅРѕ)
  "comment": str                   # РљРѕРјРјРµРЅС‚Р°СЂРёР№ (РѕРїС†РёРѕРЅР°Р»СЊРЅРѕ, max 500 СЃРёРјРІРѕР»РѕРІ)
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

## РџСЂРёРјРµСЂС‹ РёСЃРїРѕР»СЊР·РѕРІР°РЅРёСЏ

### cURL

#### Basic QA
```bash
curl -X POST "http://localhost:8000/api/v1/questions/basic" \
  -H "X-API-Key: test-key-001" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Р§С‚Рѕ С‚Р°РєРѕРµ РѕСЃРѕР·РЅР°РІР°РЅРёРµ?",
    "user_id": "user_123"
  }'
```

#### Adaptive QA
```bash
curl -X POST "http://localhost:8000/api/v1/questions/adaptive" \
  -H "X-API-Key: test-key-001" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "РҐРѕС‡Сѓ РЅР°С‡Р°С‚СЊ РїСЂР°РєС‚РёРєРѕРІР°С‚СЊ РѕСЃРѕР·РЅР°РІР°РЅРёРµ",
    "user_id": "user_123",
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
        "query": "Р§С‚Рѕ С‚Р°РєРѕРµ РѕСЃРѕР·РЅР°РІР°РЅРёРµ?",
        "user_id": "user_123"
    }
)
print(response.json())

# Adaptive QA
response = requests.post(
    f"{API_URL}/questions/adaptive",
    headers=headers,
    json={
        "query": "РҐРѕС‡Сѓ РЅР°С‡Р°С‚СЊ РїСЂР°РєС‚РёРєРѕРІР°С‚СЊ РѕСЃРѕР·РЅР°РІР°РЅРёРµ",
        "user_id": "user_123",
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
    query: "Р§С‚Рѕ С‚Р°РєРѕРµ РѕСЃРѕР·РЅР°РІР°РЅРёРµ?",
    user_id: "user_123"
  })
});

const data = await response.json();
console.log(data.answer);
```

---

## РћР±СЂР°Р±РѕС‚РєР° РѕС€РёР±РѕРє

### РљРѕРґС‹ СЃС‚Р°С‚СѓСЃРѕРІ

- **200 OK** вЂ” СѓСЃРїРµС€РЅС‹Р№ Р·Р°РїСЂРѕСЃ
- **400 Bad Request** вЂ” РЅРµРІР°Р»РёРґРЅС‹Рµ РґР°РЅРЅС‹Рµ Р·Р°РїСЂРѕСЃР°
- **403 Forbidden** вЂ” РЅРµРІР°Р»РёРґРЅС‹Р№ РёР»Рё РѕС‚СЃСѓС‚СЃС‚РІСѓСЋС‰РёР№ API РєР»СЋС‡
- **429 Too Many Requests** вЂ” РїСЂРµРІС‹С€РµРЅ rate limit
- **500 Internal Server Error** вЂ” РѕС€РёР±РєР° СЃРµСЂРІРµСЂР°

### Р¤РѕСЂРјР°С‚ РѕС€РёР±РєРё

```json
{
  "status": "error",
  "error": "РћРїРёСЃР°РЅРёРµ РѕС€РёР±РєРё",
  "detail": "Р”РµС‚Р°Р»Рё РѕС€РёР±РєРё (РѕРїС†РёРѕРЅР°Р»СЊРЅРѕ)",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

---

## Middleware

### CORS
Р Р°Р·СЂРµС€РµРЅС‹ origins:
- `http://localhost:3000`
- `http://localhost:8080`
- `http://127.0.0.1:3000`
- `http://127.0.0.1:8080`
- `*` (РІ production РѕРіСЂР°РЅРёС‡РёС‚СЊ)

### Trusted Host
Р Р°Р·СЂРµС€С‘РЅРЅС‹Рµ С…РѕСЃС‚С‹:
- `localhost`
- `127.0.0.1`
- `*.example.com`

### Р›РѕРіРёСЂРѕРІР°РЅРёРµ
Р’СЃРµ Р·Р°РїСЂРѕСЃС‹ Р»РѕРіРёСЂСѓСЋС‚СЃСЏ СЃ РІСЂРµРјРµРЅРµРј РІС‹РїРѕР»РЅРµРЅРёСЏ.

---

## РќР°РІРёРіР°С†РёСЏ

- [РћР±Р·РѕСЂ РїСЂРѕРµРєС‚Р°](./overview.md)
- [РђСЂС…РёС‚РµРєС‚СѓСЂР°](./architecture.md)
- [Bot Agent](./bot_agent.md)
- [Web UI](./web_ui.md)

