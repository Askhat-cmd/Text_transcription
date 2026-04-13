# РўРµСЃС‚РёСЂРѕРІР°РЅРёРµ

## РќР°РІРёРіР°С†РёСЏ

- [РќР°Р·Р°Рґ Рє README](../README.md)
- [РћР±Р·РѕСЂ РїСЂРѕРµРєС‚Р°](./overview.md)
- [Р Р°Р·РІС‘СЂС‚С‹РІР°РЅРёРµ](./deployment.md)

---

## РћРїРёСЃР°РЅРёРµ Рё РЅР°Р·РЅР°С‡РµРЅРёРµ

**РќР°Р·РЅР°С‡РµРЅРёРµ РґРѕРєСѓРјРµРЅС‚Р°**: РћРїРёСЃР°С‚СЊ РїСЂРѕС†РµСЃСЃ С‚РµСЃС‚РёСЂРѕРІР°РЅРёСЏ РІСЃРµС… Phase РїСЂРѕРµРєС‚Р° Bot Psychologist.

**Р”Р»СЏ РєРѕРіРѕ**: Р Р°Р·СЂР°Р±РѕС‚С‡РёРєРё, QA РёРЅР¶РµРЅРµСЂС‹.

**Р§С‚Рѕ СЃРѕРґРµСЂР¶РёС‚**:
- РўРµСЃС‚РёСЂРѕРІР°РЅРёРµ Phase 1-4
- РўРµСЃС‚РёСЂРѕРІР°РЅРёРµ API (Phase 5)
- РўРµСЃС‚РёСЂРѕРІР°РЅРёРµ Web UI (Phase 6)
- РџСЂРёРјРµСЂС‹ С‚РµСЃС‚РѕРІ

---

## РўРµСЃС‚РёСЂРѕРІР°РЅРёРµ Phase 1-4

### Phase 1: Р‘Р°Р·РѕРІС‹Р№ QA

**Р¤Р°Р№Р»**: `tests/test_phase1.py`

**РўРµСЃС‚РёСЂСѓРµРјС‹Рµ С„СѓРЅРєС†РёРё**:
- `answer_question_basic(query: str)`

**РџСЂРёРјРµСЂ С‚РµСЃС‚Р°**:
```python
from bot_agent import answer_question_basic

result = answer_question_basic("Р§С‚Рѕ С‚Р°РєРѕРµ РѕСЃРѕР·РЅР°РІР°РЅРёРµ?")
assert result["status"] == "success"
assert len(result["answer"]) > 0
assert len(result["sources"]) > 0
```

**Р—Р°РїСѓСЃРє**:
```bash
python tests/test_phase1.py
```

---

### Legacy (архив): SAG-aware QA

**Р¤Р°Р№Р»**: `tests/test_phase2.py` (только для исторической совместимости, не active runtime)

**РўРµСЃС‚РёСЂСѓРµРјС‹Рµ С„СѓРЅРєС†РёРё**:
- `answer_question_sag_aware(query: str, user_level: str)`

**РџСЂРёРјРµСЂ С‚РµСЃС‚Р°**:
```python
from bot_agent import answer_question_sag_aware

result = answer_question_sag_aware(
    "РљР°Рє СЂР°Р·РІРёС‚СЊ РѕСЃРѕР·РЅР°РІР°РЅРёРµ?",
    user_level="beginner"
)
assert result["status"] == "success"
assert result["user_level"] == "beginner"
```

**Р—Р°РїСѓСЃРє**:
```bash
python tests/test_phase2.py
```

---

### Phase 3: Knowledge Graph Powered QA

**Р¤Р°Р№Р»**: `tests/test_phase3.py`

**РўРµСЃС‚РёСЂСѓРµРјС‹Рµ С„СѓРЅРєС†РёРё**:
- `answer_question_graph_powered(query: str, user_level: str)`

**РџСЂРёРјРµСЂ С‚РµСЃС‚Р°**:
```python
from bot_agent import answer_question_graph_powered

result = answer_question_graph_powered(
    "РљР°РєРёРµ РїСЂР°РєС‚РёРєРё РїРѕРјРѕРіР°СЋС‚ СЂР°Р·РІРёС‚СЊ РѕСЃРѕР·РЅР°РІР°РЅРёРµ?",
    user_level="intermediate"
)
assert result["status"] == "success"
assert "practices" in result.get("metadata", {})
```

**Р—Р°РїСѓСЃРє**:
```bash
python tests/test_phase3.py
```

---

### Phase 4: Adaptive QA

**Р¤Р°Р№Р»**: `tests/test_phase4.py`

**РўРµСЃС‚РёСЂСѓРµРјС‹Рµ С„СѓРЅРєС†РёРё**:
- `answer_question_adaptive(query: str, user_id: str)`

**РџСЂРёРјРµСЂ С‚РµСЃС‚Р°**:
```python
from bot_agent import answer_question_adaptive

result = answer_question_adaptive(
    "РҐРѕС‡Сѓ РЅР°С‡Р°С‚СЊ РїСЂР°РєС‚РёРєРѕРІР°С‚СЊ РѕСЃРѕР·РЅР°РІР°РЅРёРµ",
    user_id="test_user_001"
)
assert result["status"] == "success"
assert "state_analysis" in result
assert "path_recommendation" in result
```

**Р—Р°РїСѓСЃРє**:
```bash
python tests/test_phase4.py
```

---

## РўРµСЃС‚РёСЂРѕРІР°РЅРёРµ API (Phase 5)

### РўРµСЃС‚РѕРІС‹Р№ С„Р°Р№Р»

**Р¤Р°Р№Р»**: `tests/test_api.py`

**РСЃРїРѕР»СЊР·СѓРµРјС‹Рµ Р±РёР±Р»РёРѕС‚РµРєРё**:
- `requests` вЂ” HTTP РєР»РёРµРЅС‚
- `json` вЂ” СЂР°Р±РѕС‚Р° СЃ JSON

### РџСЂРёРјРµСЂС‹ С‚РµСЃС‚РѕРІ

#### Basic QA Endpoint

```python
import requests

API_URL = "http://localhost:8000/api/v1"
API_KEY = "test-key-001"

headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

response = requests.post(
    f"{API_URL}/questions/basic",
    headers=headers,
    json={
        "query": "Р§С‚Рѕ С‚Р°РєРѕРµ РѕСЃРѕР·РЅР°РІР°РЅРёРµ?",
        "user_id": "test_user_001"
    }
)

assert response.status_code == 200
data = response.json()
assert data["status"] == "success"
assert len(data["answer"]) > 0
```

#### Adaptive QA Endpoint

```python
response = requests.post(
    f"{API_URL}/questions/adaptive",
    headers=headers,
    json={
        "query": "РҐРѕС‡Сѓ РЅР°С‡Р°С‚СЊ РїСЂР°РєС‚РёРєРѕРІР°С‚СЊ РѕСЃРѕР·РЅР°РІР°РЅРёРµ",
        "user_id": "test_user_001",
        "include_path": True
    }
)

assert response.status_code == 200
data = response.json()
assert "state_analysis" in data
assert "path_recommendation" in data
```

#### Feedback Endpoint

```python
response = requests.post(
    f"{API_URL}/feedback",
    headers=headers,
    json={
        "user_id": "test_user_001",
        "turn_index": 0,
        "feedback": "positive",
        "rating": 5
    }
)

assert response.status_code == 200
data = response.json()
assert data["status"] == "success"
```

#### User History Endpoint

```python
response = requests.post(
    f"{API_URL}/users/test_user_001/history",
    headers=headers,
    params={"last_n_turns": 10}
)

assert response.status_code == 200
data = response.json()
assert "turns" in data
```

#### Health Check

```python
response = requests.get(f"{API_URL}/health")
assert response.status_code == 200
data = response.json()
assert data["status"] == "healthy"
```

### Р—Р°РїСѓСЃРє С‚РµСЃС‚РѕРІ API

**РџРµСЂРµРґ Р·Р°РїСѓСЃРєРѕРј**:
1. Р—Р°РїСѓСЃС‚РёС‚Рµ API СЃРµСЂРІРµСЂ: `uvicorn api.main:app --reload`
2. РЈР±РµРґРёС‚РµСЃСЊ, С‡С‚Рѕ API РґРѕСЃС‚СѓРїРµРЅ: `http://localhost:8000/api/v1/health`

**Р—Р°РїСѓСЃРє**:
```bash
python tests/test_api.py
```

---

## РўРµСЃС‚РёСЂРѕРІР°РЅРёРµ Web UI (Phase 6)

### Unit С‚РµСЃС‚С‹ РєРѕРјРїРѕРЅРµРЅС‚РѕРІ

**РџСЂРёРјРµСЂ С‚РµСЃС‚Р° React РєРѕРјРїРѕРЅРµРЅС‚Р°**:

```typescript
import { render, screen } from '@testing-library/react';
import { ChatWindow } from './ChatWindow';

test('renders chat window', () => {
  render(<ChatWindow />);
  const inputElement = screen.getByPlaceholderText(/РІРІРµРґРёС‚Рµ РІРѕРїСЂРѕСЃ/i);
  expect(inputElement).toBeInTheDocument();
});
```

### E2E С‚РµСЃС‚С‹

**РџСЂРёРјРµСЂ E2E С‚РµСЃС‚Р°**:

```typescript
import { test, expect } from '@playwright/test';

test('user can ask question and get answer', async ({ page }) => {
  await page.goto('http://localhost:5173');
  
  // Р’РІРµСЃС‚Рё РІРѕРїСЂРѕСЃ
  await page.fill('[data-testid="chat-input"]', 'Р§С‚Рѕ С‚Р°РєРѕРµ РѕСЃРѕР·РЅР°РІР°РЅРёРµ?');
  await page.click('[data-testid="send-button"]');
  
  // Р”РѕР¶РґР°С‚СЊСЃСЏ РѕС‚РІРµС‚Р°
  await page.waitForSelector('[data-testid="bot-message"]');
  
  // РџСЂРѕРІРµСЂРёС‚СЊ РЅР°Р»РёС‡РёРµ РѕС‚РІРµС‚Р°
  const answer = await page.textContent('[data-testid="bot-message"]');
  expect(answer).toBeTruthy();
});
```

---

## РРЅС‚РµРіСЂР°С†РёРѕРЅРЅС‹Рµ С‚РµСЃС‚С‹

### РўРµСЃС‚ РїРѕР»РЅРѕРіРѕ РїРѕС‚РѕРєР°

```python
def test_full_flow():
    # 1. Р—Р°РґР°С‚СЊ РІРѕРїСЂРѕСЃ С‡РµСЂРµР· API
    response = requests.post(
        f"{API_URL}/questions/adaptive",
        headers=headers,
        json={
            "query": "Р§С‚Рѕ С‚Р°РєРѕРµ РѕСЃРѕР·РЅР°РІР°РЅРёРµ?",
            "user_id": "test_user_001",
            "include_path": True
        }
    )
    assert response.status_code == 200
    
    # 2. РџСЂРѕРІРµСЂРёС‚СЊ РѕС‚РІРµС‚
    data = response.json()
    assert data["status"] == "success"
    
    # 3. РћС‚РїСЂР°РІРёС‚СЊ РѕР±СЂР°С‚РЅСѓСЋ СЃРІСЏР·СЊ
    feedback_response = requests.post(
        f"{API_URL}/feedback",
        headers=headers,
        json={
            "user_id": "test_user_001",
            "turn_index": 0,
            "feedback": "positive",
            "rating": 5
        }
    )
    assert feedback_response.status_code == 200
    
    # 4. РџСЂРѕРІРµСЂРёС‚СЊ РёСЃС‚РѕСЂРёСЋ
    history_response = requests.post(
        f"{API_URL}/users/test_user_001/history",
        headers=headers
    )
    assert history_response.status_code == 200
    history_data = history_response.json()
    assert len(history_data["turns"]) > 0
```

---

## РўРµСЃС‚РёСЂРѕРІР°РЅРёРµ РєРѕРјРїРѕРЅРµРЅС‚РѕРІ Bot Agent

### РўРµСЃС‚ DataLoader

```python
from bot_agent.data_loader import data_loader

def test_data_loader():
    data_loader.load_all_data()
    assert len(data_loader.documents) > 0
    assert len(data_loader.all_blocks) > 0
```

### РўРµСЃС‚ Retriever

```python
from bot_agent.retriever import get_retriever

def test_retriever():
    retriever = get_retriever()
    retriever.build_index()
    results = retriever.retrieve("Р§С‚Рѕ С‚Р°РєРѕРµ РѕСЃРѕР·РЅР°РІР°РЅРёРµ?")
    assert len(results) > 0
    assert all(score >= 0.1 for _, score in results)
```

### РўРµСЃС‚ GraphClient

```python
from bot_agent.graph_client import graph_client

def test_graph_client():
    graph_client.load_graphs_from_all_documents()
    assert len(graph_client.nodes) > 0
    assert len(graph_client.edges) > 0
    
    # РџРѕРёСЃРє СѓР·Р»Р°
    nodes = graph_client.find_nodes_by_name("РѕСЃРѕР·РЅР°РІР°РЅРёРµ")
    assert len(nodes) > 0
    
    # РџРѕРёСЃРє РїСЂР°РєС‚РёРє
    practices = graph_client.find_practices_for_concept("РѕСЃРѕР·РЅР°РІР°РЅРёРµ")
    assert len(practices) > 0
```

### РўРµСЃС‚ StateClassifier

```python
from bot_agent.state_classifier import state_classifier

def test_state_classifier():
    analysis = state_classifier.classify_state(
        "РҐРѕС‡Сѓ РЅР°С‡Р°С‚СЊ РїСЂР°РєС‚РёРєРѕРІР°С‚СЊ РѕСЃРѕР·РЅР°РІР°РЅРёРµ",
        conversation_history=[]
    )
    assert analysis.primary_state in UserState
    assert 0 <= analysis.confidence <= 1
```

---

## РќР°РІРёРіР°С†РёСЏ

- [РћР±Р·РѕСЂ РїСЂРѕРµРєС‚Р°](./overview.md)
- [Р Р°Р·РІС‘СЂС‚С‹РІР°РЅРёРµ](./deployment.md)
- [РљРѕРЅС„РёРіСѓСЂР°С†РёСЏ](./configuration.md)

