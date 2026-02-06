# test_api.py
"""
Тесты для Bot Psychologist API (Phase 5)

Запуск:
1. Запустить сервер: python api/main.py
2. Запустить тесты: python test_api.py
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8001"
API_KEY = "test-key-001"


def get_headers():
    """Заголовки с API ключом"""
    return {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    }


def print_separator(title: str):
    """Печать разделителя"""
    print("\n" + "=" * 100)
    print(f"TEST: {title}")
    print("=" * 100)


def test_health_check():
    """Проверка здоровья"""
    print_separator("Health Check")
    
    response = requests.get(f"{BASE_URL}/api/v1/health")
    result = response.json()
    
    print(f"Status Code: {response.status_code}")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert result["status"] == "healthy", f"Expected healthy, got {result['status']}"
    
    print("[OK] PASSED")
    return True


def test_root_endpoint():
    """Проверка корневого endpoint"""
    print_separator("Root Endpoint")
    
    response = requests.get(f"{BASE_URL}/")
    result = response.json()
    
    print(f"Status Code: {response.status_code}")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    assert response.status_code == 200
    assert result["name"] == "Bot Psychologist API"
    assert result["version"] == "0.5.0"
    
    print("[OK] PASSED")
    return True


def test_api_info():
    """Проверка информации об API"""
    print_separator("API Info")
    
    response = requests.get(f"{BASE_URL}/api/v1/info")
    result = response.json()
    
    print(f"Status Code: {response.status_code}")
    print(f"Phases: {list(result.get('phases', {}).keys())}")
    print(f"Endpoints: {list(result.get('endpoints', {}).keys())}")
    
    assert response.status_code == 200
    assert "phase_1" in result.get("phases", {})
    assert "adaptive" in result.get("endpoints", {})
    
    print("[OK] PASSED")
    return True


def test_adaptive_question():
    """Тест адаптивного вопроса (Phase 4)"""
    print_separator("Adaptive Question (Phase 4)")
    
    payload = {
        "query": "Что такое осознавание?",
        "user_id": "api_test_user_001",
        "user_level": "beginner",
        "include_path": True,
        "include_feedback_prompt": True,
        "debug": False
    }
    
    print(f"Request: {payload['query']}")
    
    response = requests.post(
        f"{BASE_URL}/api/v1/questions/adaptive",
        json=payload,
        headers=get_headers()
    )
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"State: {result.get('state_analysis', {}).get('primary_state')}")
        print(f"Processing time: {result.get('processing_time_seconds')}s")
        print(f"Answer preview: {result.get('answer', '')[:200]}...")
        print(f"Sources count: {len(result.get('sources', []))}")
        print(f"Concepts: {result.get('concepts', [])[:5]}")
    else:
        print(f"Error: {response.text}")
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    
    print("[OK] PASSED")
    return True


def test_basic_question():
    """Тест базового вопроса (Phase 1)"""
    print_separator("Basic Question (Phase 1)")
    
    payload = {
        "query": "Как медитировать?",
        "user_id": "api_test_user_002"
    }
    
    print(f"Request: {payload['query']}")
    
    response = requests.post(
        f"{BASE_URL}/api/v1/questions/basic",
        json=payload,
        headers=get_headers()
    )
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"Processing time: {result.get('processing_time_seconds')}s")
        print(f"Answer preview: {result.get('answer', '')[:200]}...")
    else:
        print(f"Error: {response.text}")
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    
    print("[OK] PASSED")
    return True


def test_user_history():
    """Тест истории пользователя"""
    print_separator("User History")
    
    user_id = "api_test_user_001"
    
    response = requests.post(
        f"{BASE_URL}/api/v1/users/{user_id}/history",
        params={"last_n_turns": 5},
        headers=get_headers()
    )
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"User ID: {result.get('user_id')}")
        print(f"Total turns: {result.get('total_turns')}")
        print(f"Primary interests: {result.get('primary_interests')}")
        print(f"Average rating: {result.get('average_rating')}")
    else:
        print(f"Error: {response.text}")
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    
    print("[OK] PASSED")
    return True


def test_feedback():
    """Тест отправки обратной связи"""
    print_separator("Feedback")
    
    payload = {
        "user_id": "api_test_user_001",
        "turn_index": 0,
        "feedback": "positive",
        "rating": 5,
        "comment": "Очень полезно!"
    }
    
    print(f"Feedback: {payload['feedback']}, Rating: {payload['rating']}")
    
    response = requests.post(
        f"{BASE_URL}/api/v1/feedback",
        json=payload,
        headers=get_headers()
    )
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"Error: {response.text}")
    
    # Может вернуть 400 если turn_index не существует
    assert response.status_code in [200, 400], f"Expected 200 or 400, got {response.status_code}"
    
    print("[OK] PASSED")
    return True


def test_statistics():
    """Тест статистики"""
    print_separator("Statistics")
    
    response = requests.get(
        f"{BASE_URL}/api/v1/stats",
        headers=get_headers()
    )
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"Total users: {result.get('total_users')}")
        print(f"Total questions: {result.get('total_questions')}")
        print(f"Average time: {result.get('average_processing_time')}s")
        print(f"Top states: {result.get('top_states')}")
    else:
        print(f"Error: {response.text}")
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    
    print("[OK] PASSED")
    return True


def test_invalid_api_key():
    """Тест с невалидным API ключом"""
    print_separator("Invalid API Key (Expect 403)")
    
    headers = {"X-API-Key": "invalid-key-12345"}
    
    response = requests.get(
        f"{BASE_URL}/api/v1/stats",
        headers=headers
    )
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 403:
        result = response.json()
        print(f"Error detail: {result.get('detail')}")
    
    assert response.status_code == 403, f"Expected 403, got {response.status_code}"
    
    print("[OK] PASSED (403 expected)")
    return True


def test_missing_api_key():
    """Тест без API ключа"""
    print_separator("Missing API Key (Expect 403)")
    
    response = requests.get(f"{BASE_URL}/api/v1/stats")
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 403:
        result = response.json()
        print(f"Error detail: {result.get('detail')}")
    
    assert response.status_code == 403, f"Expected 403, got {response.status_code}"
    
    print("[OK] PASSED (403 expected)")
    return True


def run_all_tests():
    """Запуск всех тестов"""
    print("\n" + "=" * 100)
    print("BOT PSYCHOLOGIST API - PHASE 5 TESTING")
    print(f"Started at: {datetime.now().isoformat()}")
    print("=" * 100)
    
    tests = [
        ("Health Check", test_health_check),
        ("Root Endpoint", test_root_endpoint),
        ("API Info", test_api_info),
        ("Adaptive Question", test_adaptive_question),
        ("Basic Question", test_basic_question),
        ("User History", test_user_history),
        ("Feedback", test_feedback),
        ("Statistics", test_statistics),
        ("Invalid API Key", test_invalid_api_key),
        ("Missing API Key", test_missing_api_key),
    ]
    
    passed = 0
    failed = 0
    errors = []
    
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except AssertionError as e:
            failed += 1
            errors.append((name, str(e)))
            print(f"[FAIL] FAILED: {e}")
        except requests.exceptions.ConnectionError:
            failed += 1
            errors.append((name, "Connection refused - is the server running?"))
            print("[FAIL] FAILED: Connection refused - is the server running?")
        except Exception as e:
            failed += 1
            errors.append((name, str(e)))
            print(f"[ERR] ERROR: {e}")
    
    # Summary
    print("\n" + "=" * 100)
    print("TEST SUMMARY")
    print("=" * 100)
    print(f"Total: {len(tests)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    
    if errors:
        print("\nErrors:")
        for name, error in errors:
            print(f"  - {name}: {error}")
    
    if failed == 0:
        print("\n" + "=" * 100)
        print("ALL TESTS PASSED!")
        print("=" * 100)
    else:
        print("\n" + "=" * 100)
        print(f"SOME TESTS FAILED ({failed}/{len(tests)})")
        print("=" * 100)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)


