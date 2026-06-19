from __future__ import annotations

from bot_agent.knowledge.semantic_card_loader import load_semantic_cards
from bot_agent.knowledge.semantic_card_payload_adapter import card_to_writer_payload_item
from bot_agent.multiagent.writer_kb_payload import (
    WriterKbPayloadConfig,
    build_writer_kb_payload,
)


def test_adapter_exposes_only_writer_safe_fields() -> None:
    card = load_semantic_cards()[0]

    item = card_to_writer_payload_item(card)

    assert item["chunk_id"].startswith("semantic_card:")
    assert item["writer_can_ignore"] is True
    assert "source_ref" not in item
    assert "safety_notes" not in item
    assert "raw" not in item
    assert item["content"] == card.core_thesis


def test_adapter_preserves_writer_kb_payload_contract() -> None:
    card = next(card for card in load_semantic_cards() if card.card_id == "program_imperfect_self_v1")
    item = card_to_writer_payload_item(card)
    config = WriterKbPayloadConfig(
        enabled=True,
        max_chunks=2,
        max_total_chars=2400,
        excerpt_target_chars=500,
        excerpt_max_chars=700,
        sentence_boundary=True,
        use_overlay_metadata=False,
    )

    payload = build_writer_kb_payload(
        semantic_hits=[],
        rag_for_writer=[item],
        overlay_items=[],
        config=config,
    )

    assert payload["schema_version"] == "writer_kb_payload_v1"
    assert payload["chunk_count"] == 1
    chunk = payload["chunks"][0]
    assert chunk["chunk_id"] == "semantic_card:program_imperfect_self_v1"
    assert chunk["writer_instruction"]
    assert chunk["quote_policy"] == "paraphrase_only"
    assert "source_ref" not in chunk

