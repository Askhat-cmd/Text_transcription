from __future__ import annotations

from tools.controlled_candidate_apply import build_apply_preflight


def _candidate_block(block_id: str) -> dict:
    return {
        "id": block_id,
        "source": "book:123__кузница_духа",
        "text": "safe",
        "metadata": {
            "governance": {
                "chunk_type": "theory",
                "allowed_use": ["writer_context"],
                "safety_flags": ["not_for_direct_quote"],
            },
            "chunking_quality": {"mixed_intent_severity": "none"},
        },
    }


def test_preflight_passes_for_ready_candidate(monkeypatch) -> None:
    monkeypatch.setattr("tools.controlled_candidate_apply._contains_active_legacy_sd", lambda: False)
    gate = {
        "status": "passed",
        "candidate_ready_for_apply": True,
        "mixed_intent_unresolved_count": 0,
        "mixed_intent_split_required_count": 0,
        "direct_practice_misclassified_count": 0,
        "unsafe_practice_suggestion_count": 0,
    }
    blocks = [_candidate_block("b1"), _candidate_block("b2")]
    registry = [
        {"source_id": "123__кузница_духа", "status": "done", "blocks_count": 2},
        {"source_id": "test", "status": "archived", "blocks_count": 0},
    ]
    preflight = build_apply_preflight(
        source_prd="PRD-046.0.8.1",
        hf2_gate=gate,
        candidate_blocks=blocks,
        production_blocks=blocks,
        registry_records=registry,
        chroma_probe={"collection_count": 2},
        expected_candidate_blocks=2,
    )
    assert preflight["passed"] is True
    assert preflight["blockers"] == []
    assert preflight["candidate_blocks_count"] == 2


def test_preflight_blocks_when_gate_not_ready(monkeypatch) -> None:
    monkeypatch.setattr("tools.controlled_candidate_apply._contains_active_legacy_sd", lambda: False)
    gate = {"status": "candidate_needs_governance_calibration", "candidate_ready_for_apply": False}
    blocks = [_candidate_block("b1")]
    registry = [{"source_id": "123__кузница_духа", "status": "done", "blocks_count": 1}]
    preflight = build_apply_preflight(
        source_prd="PRD-046.0.8.1",
        hf2_gate=gate,
        candidate_blocks=blocks,
        production_blocks=[],
        registry_records=registry,
        chroma_probe={"collection_count": 0},
        expected_candidate_blocks=1,
    )
    assert preflight["passed"] is False
    assert "hf2_gate_not_passed" in preflight["blockers"]
    assert "hf2_candidate_ready_false" in preflight["blockers"]
