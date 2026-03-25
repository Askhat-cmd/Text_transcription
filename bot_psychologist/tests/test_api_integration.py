#!/usr/bin/env python3
"""
Тестовый скрипт для проверки интеграции bot_psychologist с Bot_data_base API
"""

import os
import sys
import requests
import pytest
from pathlib import Path

# Добавляем путь к bot_agent для импортов
sys.path.insert(0, str(Path(__file__).parent.parent))

from bot_agent.data_loader import data_loader
from bot_agent.config import config

def test_api_integration():
    try:
        requests.get("http://localhost:8003/api/registry/", timeout=2)
    except requests.exceptions.ConnectionError:
        pytest.skip("Bot_data_base API is not running (http://localhost:8003)")

    """Проверка работы KNOWLEDGE_SOURCE=api"""
    
    print("🔍 Тестирование интеграции bot_psychologist с Bot_data_base API")
    print("=" * 60)
    
    # Устанавливаем режим API
    os.environ["KNOWLEDGE_SOURCE"] = "api"
    os.environ["BOT_DB_URL"] = "http://localhost:8003"
    
    # Перезагружаем конфигурацию
    config.reload()
    
    print(f"✅ KNOWLEDGE_SOURCE = {config.KNOWLEDGE_SOURCE}")
    print(f"✅ BOT_DB_URL = {getattr(config, 'BOT_DB_URL', 'не установлен')}")
    
    try:
        # Проверяем загрузку данных
        print("\n📂 Загрузка данных через API...")
        data_loader._is_loaded = False  # Сброс кэша
        data_loader.load_all_data()
        
        blocks = data_loader.get_all_blocks()
        documents = data_loader.get_all_documents()
        
        print(f"✅ Загружено {len(blocks)} блоков")
        print(f"✅ Загружено {len(documents)} документов")
        
        if blocks:
            print(f"\n📊 Первый блок:")
            block = blocks[0]
            print(f"   ID: {block.block_id}")
            print(f"   Заголовок: {block.title[:50]}...")
            print(f"   Тип: {block.source_type}")
            print(f"   SD уровень: {block.sd_level}")
            print(f"   Сложность: {block.complexity_score}")
        
        # Проверка статистики
        stats = data_loader.get_stats()
        print(f"\n📈 Статистика:")
        for key, value in stats.items():
            print(f"   {key}: {value}")
            
        return True
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

if __name__ == "__main__":
    success = test_api_integration()
    if success:
        print("\n🎉 Интеграция успешно протестирована!")
    else:
        print("\n⚠️ Интеграция требует дополнительной настройки")