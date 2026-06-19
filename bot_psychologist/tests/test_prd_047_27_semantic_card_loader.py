from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest

from bot_agent.knowledge.semantic_card_loader import load_semantic_cards, validate_semantic_cards


def test_loader_returns_unique_valid_cards() -> None:
    cards = load_semantic_cards()
    ids = [card.card_id for card in cards]

    assert len(ids) == len(set(ids))
    assert all(card.writer_can_ignore for card in cards)


def test_validator_rejects_duplicate_ids() -> None:
    cards = [card.to_dict() for card in load_semantic_cards()[:2]]
    cards[1]["card_id"] = cards[0]["card_id"]

    errors = validate_semantic_cards(cards)

    assert any(error.startswith("duplicate_card_id:") for error in errors)


def test_validator_rejects_practice_without_explicit_policy() -> None:
    card = load_semantic_cards()[0].to_dict()
    card["card_id"] = "bad_practice_v1"
    card["chunk_type"] = "practice"
    card["practice_policy"] = "no_practice_unless_requested"

    errors = validate_semantic_cards([card])

    assert any("practice_card_requires_explicit_policy" in error for error in errors)


def test_loader_raises_on_invalid_file() -> None:
    temp_dir = Path(__file__).resolve().parents[1] / ".tmp_test_artifacts" / f"semantic_card_loader_{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    invalid = temp_dir / "cards.json"
    invalid.write_text('{"cards":[{"card_id":"x"}]}', encoding="utf-8")

    with pytest.raises(ValueError):
        load_semantic_cards(invalid)
