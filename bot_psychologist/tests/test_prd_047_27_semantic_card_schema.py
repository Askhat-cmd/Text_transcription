from __future__ import annotations

from bot_agent.knowledge.semantic_card_loader import load_semantic_cards
from bot_agent.knowledge.semantic_chunk_card import (
    CHUNK_TYPES,
    PRACTICE_POLICIES,
    QUOTE_POLICIES,
    SEMANTIC_CHUNK_CARD_SCHEMA_VERSION,
)


REQUIRED_BASE_IDS = {
    "program_imperfect_self",
    "five_survival_drivers",
    "be_strong_driver",
    "be_best_driver",
    "please_others_driver",
    "try_harder_driver",
    "hurry_up_driver",
    "control_as_safety",
    "fact_vs_interpretation",
    "panic_control_support",
    "one_bounded_practice_not_self_improvement_whip",
    "neurostalking_basic_lens",
}


def test_pilot_pack_contains_required_semantic_cards() -> None:
    cards = load_semantic_cards()

    assert 10 <= len(cards) <= 20
    base_ids = {card.card_id.removesuffix("_v1") for card in cards}
    assert REQUIRED_BASE_IDS <= base_ids


def test_pilot_cards_follow_schema_contract() -> None:
    cards = load_semantic_cards()

    for card in cards:
        assert card.schema_version == SEMANTIC_CHUNK_CARD_SCHEMA_VERSION
        assert card.chunk_type in CHUNK_TYPES
        assert card.quote_policy in QUOTE_POLICIES
        assert card.practice_policy in PRACTICE_POLICIES
        assert card.writer_can_ignore is True
        assert card.core_thesis
        assert card.writer_instruction
        assert card.allowed_use

