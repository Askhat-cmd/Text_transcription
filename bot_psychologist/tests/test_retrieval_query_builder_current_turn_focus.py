from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from bot_agent.multiagent.retrieval_query_builder import build_retrieval_query


def test_standalone_knowledge_question_does_not_include_previous_user_query() -> None:
    payload = build_retrieval_query(
        user_message='а что такое "Программа несовершенное Я"?',
        previous_user_message="Что такое самореализация как она коррелируется с Нейросталкингом?",
        planner_query="программа несовершенное",
        max_chars=300,
    )
    assert payload["previous_user_query_included"] is False
    assert "самореализация" not in payload["executed_query"].lower()
    assert "нейросталкинг" not in payload["executed_query"].lower()


def test_c23_002_focuses_on_imperfect_self_topic() -> None:
    payload = build_retrieval_query(
        user_message='а что такое "Программа несовершенное Я"?',
        previous_user_message="Что такое самореализация как она коррелируется с Нейросталкингом?",
        planner_query="программа несовершенное",
        max_chars=300,
    )
    assert "программа" in payload["executed_query"].lower()
    assert "несовершенное" in payload["executed_query"].lower()
    assert "я" in payload["executed_query"].lower()


def test_c23_003_duplicate_long_query_dedupes() -> None:
    raw_query = (
        "расскажи о Пяти драйверах выживания: Драйвер 1: «Будь сильным», "
        "Драйвер 2: «Будь лучшим», Драйвер 3: «Радуй других», "
        "Драйвер 4: «Старайся сильнее», Драйвер 5: «Спеши» "
        "расскажи о Пяти драйверах выживания: Драйвер 1: «Будь сильным», "
        "Драйвер 2: «Будь лучшим», Драйвер 3: «Радуй других», "
        "Драйвер 4: «Старайся сильнее», Драйвер 5: «Спеши»"
    )
    payload = build_retrieval_query(
        user_message=raw_query,
        planner_query="пять драйверов выживания будь сильным будь лучшим радуй других старайся сильнее спеши",
        max_chars=300,
    )
    assert payload["dedupe_applied"] is True
    assert payload["duplicate_fragment_count"] >= 1
    assert payload["executed_query"].lower().count("пять") == 1


def test_truncation_never_cuts_mid_word() -> None:
    payload = build_retrieval_query(
        user_message=" ".join([f"драйвер_оченьдлинныйтокен_{i}" for i in range(20)]),
        max_chars=120,
    )
    assert payload["truncation_applied"] is True
    assert payload["query_truncated_mid_word"] is False


def test_elliptical_da_uses_last_offer_summary_not_previous_user_query() -> None:
    payload = build_retrieval_query(
        user_message="да",
        previous_user_message="Что такое самореализация?",
        last_assistant_offer_summary="Хочешь, объясню второй уровень - НеоСталкинг?",
        inherited_topic="НеоСталкинг",
        max_chars=300,
    )
    assert payload["previous_user_query_included"] is False
    assert payload["inherited_topic_used"] is True
    assert payload["current_turn_focus_status"] == "elliptical_contextualized"


def test_second_level_followup_can_use_inherited_topic() -> None:
    payload = build_retrieval_query(
        user_message="а второй уровень?",
        inherited_topic="НеоСталкинг",
        max_chars=300,
    )
    assert payload["inherited_topic_used"] is True
    assert "неосталкинг" in payload["executed_query"].lower()


def test_topic_switch_blocks_previous_topic_pollution() -> None:
    payload = build_retrieval_query(
        user_message="что такое пять драйверов выживания?",
        previous_user_message="Что такое Нейросталкинг?",
        inherited_topic="Нейросталкинг",
        max_chars=300,
    )
    assert "нейросталкинг" not in payload["executed_query"].lower()
    assert "драйвер" in payload["executed_query"].lower()


def test_planned_query_used_only_if_current() -> None:
    stale = build_retrieval_query(
        user_message='а что такое "Программа несовершенное Я"?',
        planner_query="самореализация нейросталкинг",
        max_chars=300,
    )
    fresh = build_retrieval_query(
        user_message='а что такое "Программа несовершенное Я"?',
        planner_query="программа несовершенное",
        max_chars=300,
    )
    assert stale["planner_query_used"] is False
    assert fresh["planner_query_used"] is True


def test_trace_contains_required_fields() -> None:
    payload = build_retrieval_query(
        user_message="что такое нейросталкинг?",
        planner_query="нейросталкинг",
        max_chars=300,
    )
    assert payload["schema_version"] == "retrieval_query_build_trace_v1"
    assert payload["primary_path"] == "current_turn_focus_v1"
    assert "executed_query" in payload
    assert "previous_user_query_inclusion_reason" in payload


def test_fallback_trace_is_marked_when_query_is_empty() -> None:
    payload = build_retrieval_query(
        user_message="   ",
        previous_user_message="что такое нейросталкинг",
        max_chars=300,
    )
    assert payload["fallback_used"] is True
    assert payload["legacy_query_builder_fallback"] is True
