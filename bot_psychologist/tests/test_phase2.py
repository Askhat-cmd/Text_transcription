# test_phase2.py
"""
Тестирование Phase 2 - SAG v2.0 Aware QA Bot
=============================================

Проверка функциональности Phase 2:
- Адаптация ответов под уровень пользователя
- Извлечение концептов и связей
- Семантический анализ
"""

import sys
import io
from pathlib import Path

def _configure_console_encoding():
    # Avoid touching sys.std* during pytest collection/capture.
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add project root to path for package imports
sys.path.insert(0, str(Path(__file__).parent))

# Import from bot_agent package
from bot_agent import answer_question_sag_aware


def print_separator(char="=", length=80):
    """Print a separator line"""
    print(char * length)


def print_result(result: dict, show_full_answer: bool = True):
    """
    Форматированный вывод результата Phase 2.
    """
    print(f"\n📊 Status: {result['status']}")
    print(f"⏱️  Processing time: {result['processing_time_seconds']}s")
    print(f"👤 User level: {result['user_level']}")
    
    # Metadata
    if result.get('metadata'):
        meta = result['metadata']
        print(f"📦 Blocks used: {meta.get('blocks_used', 'N/A')}")
        print(f"🔗 Semantic links: {meta.get('semantic_links', 0)}")
        if meta.get('model_used'):
            print(f"🤖 Model: {meta.get('model_used')}")
        if meta.get('tokens_used'):
            print(f"📈 Tokens: {meta.get('tokens_used')}")
    
    # Answer
    if show_full_answer:
        print(f"\n💬 ОТВЕТ:\n{'-' * 40}")
        print(result.get('answer', 'Нет ответа'))
        print('-' * 40)
    else:
        answer = result.get('answer', '')
        preview = answer[:300] + "..." if len(answer) > 300 else answer
        print(f"\n💬 ОТВЕТ (preview):\n{preview}")
    
    # Concepts
    concepts = result.get('concepts', [])
    if concepts:
        print(f"\n🔑 КОНЦЕПТЫ ({len(concepts)}):")
        for concept in concepts:
            print(f"  • {concept}")
    
    # Relations
    relations = result.get('relations', [])
    if relations:
        print(f"\n🔗 СВЯЗИ ({len(relations)}):")
        for rel in relations[:5]:  # Показываем первые 5
            print(f"  • {rel['from']} → {rel['to']} ({rel['type']})")
            if rel.get('context'):
                print(f"    Контекст: {rel['context'][:50]}...")
    
    # Sources
    sources = result.get('sources', [])
    if sources:
        print(f"\n📚 ИСТОЧНИКИ ({len(sources)} блоков):")
        for i, src in enumerate(sources[:3], 1):  # Показываем первые 3
            print(f"\n  [{i}] {src['title']}")
            print(f"      Лекция: {src['document_title']}")
            print(f"      Тип: {src.get('block_type', 'N/A')}, "
                  f"Сложность: {src.get('complexity_score', 'N/A')}")
            print(f"      🎬 {src['youtube_link']}")
    
    # Debug info
    if result.get('debug'):
        print(f"\n🔧 DEBUG INFO:")
        debug = result['debug']
        for key, value in debug.items():
            if isinstance(value, dict):
                print(f"  {key}:")
                for k, v in value.items():
                    print(f"    {k}: {v}")
            else:
                print(f"  {key}: {value}")


def run_test(query: str, level: str, test_num: int, total: int, debug: bool = False):
    """
    Запустить один тест.
    """
    print_separator()
    print(f"ТЕСТ {test_num}/{total}")
    print_separator()
    print(f"\n📋 Вопрос: {query}")
    print(f"📊 Уровень: {level}")
    
    try:
        result = answer_question_sag_aware(query, user_level=level, debug=debug)
        print_result(result, show_full_answer=True)
        return result['status'] == 'success'
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """
    Основной тестовый скрипт Phase 2.
    """
    print_separator("=")
    print("🧪 ТЕСТИРОВАНИЕ PHASE 2 - SAG v2.0 AWARE QA BOT")
    print_separator("=")
    
    # Тестовые комбинации (вопрос, уровень)
    test_cases = [
        ("Что такое осознавание?", "beginner"),
        ("Как работает разотождествление?", "intermediate"),
        ("Как связаны паттерны с сознанием?", "advanced"),
        ("Какие практики развивают осознавание?", "beginner"),
    ]
    
    total = len(test_cases)
    success_count = 0
    
    for i, (query, level) in enumerate(test_cases, 1):
        success = run_test(query, level, i, total, debug=True)
        if success:
            success_count += 1
        print()
    
    # Итоги
    print_separator("=")
    print("📊 ИТОГИ ТЕСТИРОВАНИЯ")
    print_separator("=")
    print(f"\n✅ Успешно: {success_count}/{total}")
    print(f"❌ Неуспешно: {total - success_count}/{total}")
    
    if success_count == total:
        print("\n🎉 Все тесты прошли успешно!")
    else:
        print("\n⚠️ Некоторые тесты не прошли. Проверьте логи.")
    
    print_separator("=")
    print("✅ ТЕСТИРОВАНИЕ PHASE 2 ЗАВЕРШЕНО")
    print_separator("=")
    
    return success_count == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)


