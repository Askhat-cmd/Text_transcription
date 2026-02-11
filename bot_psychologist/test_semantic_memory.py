# bot_psychologist/test_semantic_memory.py
"""
Тестирование Semantic Memory
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from bot_agent.conversation_memory import get_conversation_memory
from bot_agent.config import config


def test_semantic_memory():
    print("=" * 60)
    print("ТЕСТ SEMANTIC MEMORY")
    print("=" * 60)

    print(f"Semantic Memory: {'ON' if config.ENABLE_SEMANTIC_MEMORY else 'OFF'}")
    print(f"Conversation Summary: {'ON' if config.ENABLE_CONVERSATION_SUMMARY else 'OFF'}")
    print(f"Embedding Model: {config.EMBEDDING_MODEL}")
    print()

    memory = get_conversation_memory("test_semantic_user")
    memory.clear()

    turns = [
        ("Что такое осознавание?", "Осознавание — это способность замечать мысли и ощущения."),
        ("Как медитировать правильно?", "Начните с 5 минут наблюдения за дыханием."),
        ("Как справляться со стрессом?", "Полезно возвращаться к дыханию и телесным ощущениям."),
        ("Почему я теряю фокус?", "Фокус может снижаться из-за усталости и перегруза."),
        ("Как укрепить концентрацию?", "Регулярные короткие практики помогают тренировать внимание."),
    ]

    print("Adding test turns...")
    for user_input, bot_response in turns:
        memory.add_turn(
            user_input=user_input,
            bot_response=bot_response,
            blocks_used=0,
            concepts=["осознавание", "дыхание", "концентрация"]
        )
        print(f"  OK: {user_input[:50]}...")

    print(f"\nTotal turns in memory: {len(memory.turns)}")

    if memory.semantic_memory:
        stats = memory.semantic_memory.get_stats()
        print("\nSemantic Memory stats:")
        print(f"  • Эмбеддингов создано: {stats.get('total_embeddings')}")
        print(f"  • Модель: {stats.get('model_name')}")
        print(f"  • Размер на диске: {stats.get('embeddings_size_mb', 0):.2f} MB")

        query = "Как практиковать осознанность при стрессе?"
        print(f"\nQuery: {query}")
        similar = memory.semantic_memory.search_similar_turns(
            query=query,
            top_k=2,
            min_similarity=0.5
        )
        if similar:
            print("Found relevant past turns:")
            for turn_emb, score in similar:
                print(f"  [{score:.3f}] Обмен #{turn_emb.turn_index}: {turn_emb.user_input[:60]}...")
        else:
            print("No relevant turns found")
    else:
        print("\nSemantic memory disabled or not initialized")

    print("\n" + "=" * 60)
    print("ПОЛНЫЙ КОНТЕКСТ ДЛЯ LLM")
    print("=" * 60)
    test_question = "Как начать практиковать медитацию, если у меня стресс?"
    full_context = memory.get_adaptive_context_for_llm(test_question)

    print("\nContext components:")
    print(f"  • Short-term: {len(full_context.get('short_term', ''))} символов")
    print(f"  • Semantic: {len(full_context.get('semantic', ''))} символов")
    print(f"  • Summary: {len(full_context.get('summary', ''))} символов")
    print(f"  • ИТОГО: {sum(len(v) for v in full_context.values())} символов")

    if full_context.get("summary"):
        print("\n--- SUMMARY ---")
        print(full_context["summary"][:200] + ("..." if len(full_context["summary"]) > 200 else ""))

    if full_context.get("semantic"):
        print("\n--- SEMANTIC (первые 300 символов) ---")
        print(full_context["semantic"][:300] + "...")

    if full_context.get("short_term"):
        print("\n--- SHORT-TERM (первые 300 символов) ---")
        print(full_context["short_term"][:300] + "...")

    print("\n" + "=" * 60)
    print("Cleaning up test data...")
    memory.clear()
    print("Test finished!")


if __name__ == "__main__":
    try:
        test_semantic_memory()
    except Exception as exc:
        print(f"\nERROR: {exc}")
