# Файл: bot_psychologist/test_voyage_api.py

import os
from dotenv import load_dotenv

def test_voyage_connection():
    """Проверка доступности Voyage AI API"""
    
    print("=" * 60)
    print("🧪 ДИАГНОСТИКА VOYAGE AI API")
    print("=" * 60)
    
    # Загрузка .env
    load_dotenv()
    api_key = os.getenv("VOYAGE_API_KEY")
    
    # Проверка 1: Ключ в .env
    print("\n1️⃣ Проверка API ключа в .env:")
    if not api_key:
        print("   ❌ VOYAGE_API_KEY не найден в .env")
        return
    
    print(f"   ✅ Ключ найден: {api_key[:10]}...{api_key[-4:]}")
    print(f"   Длина ключа: {len(api_key)} символов")
    
    # Проверка 2: Импорт модуля
    print("\n2️⃣ Проверка установки voyageai:")
    try:
        import voyageai
        print(f"   ✅ voyageai установлен (версия: {voyageai.__version__ if hasattr(voyageai, '__version__') else 'unknown'})")
    except ImportError as e:
        print(f"   ❌ voyageai не установлен: {e}")
        return
    
    # Проверка 3: Создание клиента
    print("\n3️⃣ Создание клиента Voyage:")
    try:
        client = voyageai.Client(api_key=api_key)
        print("   ✅ Клиент создан успешно")
    except Exception as e:
        print(f"   ❌ Ошибка создания клиента: {e}")
        return
    
    # Проверка 4: Тестовый rerank запрос
    print("\n4️⃣ Тестовый rerank запрос:")
    
    query = "Что такое осознанность?"
    documents = [
        "Осознанность - это практика присутствия в настоящем моменте",
        "Медитация помогает развить внимательность",
        "Вопросы и их природа в контексте осознавания"
    ]
    
    print(f"   Query: '{query}'")
    print(f"   Документов: {len(documents)}")
    
    try:
        # Используем правильный метод для rerank
        response = client.rerank(
            query=query,
            documents=documents,
            model="rerank-2",  # Или rerank-lite-1
            top_k=2
        )
        
        print("   ✅ Rerank запрос выполнен успешно!")
        print("\n   📊 Результаты:")
        
        for i, result in enumerate(response.results, 1):
            print(f"      [{i}] index={result.index} relevance_score={result.relevance_score:.4f}")
            print(f"          doc: {documents[result.index][:60]}...")
        
    except Exception as e:
        print(f"   ❌ Ошибка rerank запроса:")
        print(f"      Тип: {type(e).__name__}")
        print(f"      Сообщение: {str(e)}")
        
        # Дополнительная диагностика
        if "403" in str(e):
            print("\n   🚨 403 Forbidden - Возможные причины:")
            print("      1. Требуется VPN (IP из России/СНГ заблокирован)")
            print("      2. Ключ для другого API (embeddings вместо rerank)")
            print("      3. Ключ отозван или истёк")
        
        elif "401" in str(e):
            print("\n   🚨 401 Unauthorized - Неверный API ключ")
            print("      Проверьте правильность ключа в .env")
        
        elif "429" in str(e):
            print("\n   🚨 429 Too Many Requests - Превышен лимит")
            print("      Проверьте лимиты на dashboard.voyageai.com")
    
    print("\n" + "=" * 60)
    print("🏁 Диагностика завершена")
    print("=" * 60)


if __name__ == "__main__":
    test_voyage_connection()
