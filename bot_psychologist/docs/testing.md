# Тестирование

## Навигация

- [Назад к README](../README.md)
- [Обзор проекта](./overview.md)
- [Развёртывание](./deployment.md)

---

## Описание и назначение

**Назначение документа**: Описать процесс тестирования всех Phase проекта Bot Psychologist.

**Для кого**: Разработчики, QA инженеры.

**Что содержит**:
- Тестирование Phase 1-4
- Тестирование API (Phase 5)
- Тестирование Web UI (Phase 6)
- Примеры тестов

---

## Тестирование Phase 1-4

### Phase 1: Базовый QA

**Файл**: `test_phase1.py`

**Тестируемые функции**:
- `answer_question_basic(query: str)`

**Пример теста**:
```python
from bot_agent import answer_question_basic

result = answer_question_basic("Что такое осознавание?")
assert result["status"] == "success"
assert len(result["answer"]) > 0
assert len(result["sources"]) > 0
```

**Запуск**:
```bash
python test_phase1.py
```

---

### Phase 2: SAG-aware QA

**Файл**: `test_phase2.py`

**Тестируемые функции**:
- `answer_question_sag_aware(query: str, user_level: str)`

**Пример теста**:
```python
from bot_agent import answer_question_sag_aware

result = answer_question_sag_aware(
    "Как развить осознавание?",
    user_level="beginner"
)
assert result["status"] == "success"
assert result["user_level"] == "beginner"
```

**Запуск**:
```bash
python test_phase2.py
```

---

### Phase 3: Knowledge Graph Powered QA

**Файл**: `test_phase3.py`

**Тестируемые функции**:
- `answer_question_graph_powered(query: str, user_level: str)`

**Пример теста**:
```python
from bot_agent import answer_question_graph_powered

result = answer_question_graph_powered(
    "Какие практики помогают развить осознавание?",
    user_level="intermediate"
)
assert result["status"] == "success"
assert "practices" in result.get("metadata", {})
```

**Запуск**:
```bash
python test_phase3.py
```

---

### Phase 4: Adaptive QA

**Файл**: `test_phase4.py`

**Тестируемые функции**:
- `answer_question_adaptive(query: str, user_id: str, user_level: str)`

**Пример теста**:
```python
from bot_agent import answer_question_adaptive

result = answer_question_adaptive(
    "Хочу начать практиковать осознавание",
    user_id="test_user_001",
    user_level="beginner"
)
assert result["status"] == "success"
assert "state_analysis" in result
assert "path_recommendation" in result
```

**Запуск**:
```bash
python test_phase4.py
```

---

## Тестирование API (Phase 5)

### Тестовый файл

**Файл**: `test_api.py`

**Используемые библиотеки**:
- `requests` — HTTP клиент
- `json` — работа с JSON

### Примеры тестов

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
        "query": "Что такое осознавание?",
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
        "query": "Хочу начать практиковать осознавание",
        "user_id": "test_user_001",
        "user_level": "beginner",
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

### Запуск тестов API

**Перед запуском**:
1. Запустите API сервер: `uvicorn api.main:app --reload`
2. Убедитесь, что API доступен: `http://localhost:8000/api/v1/health`

**Запуск**:
```bash
python test_api.py
```

---

## Тестирование Web UI (Phase 6)

### Unit тесты компонентов

**Пример теста React компонента**:

```typescript
import { render, screen } from '@testing-library/react';
import { ChatWindow } from './ChatWindow';

test('renders chat window', () => {
  render(<ChatWindow />);
  const inputElement = screen.getByPlaceholderText(/введите вопрос/i);
  expect(inputElement).toBeInTheDocument();
});
```

### E2E тесты

**Пример E2E теста**:

```typescript
import { test, expect } from '@playwright/test';

test('user can ask question and get answer', async ({ page }) => {
  await page.goto('http://localhost:5173');
  
  // Ввести вопрос
  await page.fill('[data-testid="chat-input"]', 'Что такое осознавание?');
  await page.click('[data-testid="send-button"]');
  
  // Дождаться ответа
  await page.waitForSelector('[data-testid="bot-message"]');
  
  // Проверить наличие ответа
  const answer = await page.textContent('[data-testid="bot-message"]');
  expect(answer).toBeTruthy();
});
```

---

## Интеграционные тесты

### Тест полного потока

```python
def test_full_flow():
    # 1. Задать вопрос через API
    response = requests.post(
        f"{API_URL}/questions/adaptive",
        headers=headers,
        json={
            "query": "Что такое осознавание?",
            "user_id": "test_user_001",
            "user_level": "beginner",
            "include_path": True
        }
    )
    assert response.status_code == 200
    
    # 2. Проверить ответ
    data = response.json()
    assert data["status"] == "success"
    
    # 3. Отправить обратную связь
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
    
    # 4. Проверить историю
    history_response = requests.post(
        f"{API_URL}/users/test_user_001/history",
        headers=headers
    )
    assert history_response.status_code == 200
    history_data = history_response.json()
    assert len(history_data["turns"]) > 0
```

---

## Тестирование компонентов Bot Agent

### Тест DataLoader

```python
from bot_agent.data_loader import data_loader

def test_data_loader():
    data_loader.load_all_data()
    assert len(data_loader.documents) > 0
    assert len(data_loader.all_blocks) > 0
```

### Тест Retriever

```python
from bot_agent.retriever import get_retriever

def test_retriever():
    retriever = get_retriever()
    retriever.build_index()
    results = retriever.retrieve("Что такое осознавание?")
    assert len(results) > 0
    assert all(score >= 0.1 for _, score in results)
```

### Тест GraphClient

```python
from bot_agent.graph_client import graph_client

def test_graph_client():
    graph_client.load_graphs_from_all_documents()
    assert len(graph_client.nodes) > 0
    assert len(graph_client.edges) > 0
    
    # Поиск узла
    nodes = graph_client.find_nodes_by_name("осознавание")
    assert len(nodes) > 0
    
    # Поиск практик
    practices = graph_client.find_practices_for_concept("осознавание")
    assert len(practices) > 0
```

### Тест StateClassifier

```python
from bot_agent.state_classifier import state_classifier

def test_state_classifier():
    analysis = state_classifier.classify_state(
        "Хочу начать практиковать осознавание",
        conversation_history=[]
    )
    assert analysis.primary_state in UserState
    assert 0 <= analysis.confidence <= 1
```

---

## Навигация

- [Обзор проекта](./overview.md)
- [Развёртывание](./deployment.md)
- [Конфигурация](./configuration.md)
