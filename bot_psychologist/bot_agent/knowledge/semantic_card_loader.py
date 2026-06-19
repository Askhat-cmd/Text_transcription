"""Load and validate the local semantic cards pilot pack."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .semantic_chunk_card import SemanticChunkCard, validate_semantic_card_payload


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def default_cards_path() -> Path:
    return repo_root() / "bot_psychologist" / "knowledge_packs" / "semantic_cards_pilot_v1" / "cards.json"


def load_semantic_cards(path: Path | None = None) -> list[SemanticChunkCard]:
    target = path or default_cards_path()
    payload = json.loads(target.read_text(encoding="utf-8"))
    raw_cards = payload.get("cards", payload) if isinstance(payload, dict) else payload
    if not isinstance(raw_cards, list):
        raise ValueError("cards_payload_must_be_list")
    errors = validate_semantic_cards(raw_cards)
    if errors:
        raise ValueError(";".join(errors))
    return [SemanticChunkCard.from_dict(dict(item)) for item in raw_cards]


def validate_semantic_cards(raw_cards: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(raw_cards):
        if not isinstance(item, dict):
            errors.append(f"card_{index}_not_object")
            continue
        card_id = str(item.get("card_id", "") or "").strip()
        if card_id in seen:
            errors.append(f"duplicate_card_id:{card_id}")
        if card_id:
            seen.add(card_id)
        for error in validate_semantic_card_payload(item):
            errors.append(f"{card_id or index}:{error}")
    return errors


__all__ = ["default_cards_path", "load_semantic_cards", "repo_root", "validate_semantic_cards"]

