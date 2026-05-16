from __future__ import annotations

from review.post_apply_quality_gate import build_data_consistency_gate


def _block(block_id: str) -> dict:
    return {
        "id": block_id,
        "source": "book:123__кузница_духа",
        "text": "safe",
        "metadata": {
            "source_id": "123__кузница_духа",
            "governance": {
                "chunk_type": "theory",
                "allowed_use": ["writer_context"],
                "safety_flags": ["not_for_direct_quote"],
            },
        },
    }


def test_data_consistency_passes_for_expected_state() -> None:
    blocks_payload = {"blocks": [_block("b1"), _block("b2"), _block("b3")]}
    registry_payload = [{"source_id": "123__кузница_духа", "status": "done", "blocks_count": 3}]
    apply_result = {
        "apply_summary": {
            "text_changed_count": 0,
            "chunk_type_changed_count": 0,
            "allowed_use_changed_count": 0,
            "safety_flags_changed_count": 0,
            "source_id_changed_count": 0,
            "block_id_changed_count": 0,
            "governance_invariant_violations": 0,
        }
    }
    gate = build_data_consistency_gate(
        blocks_payload=blocks_payload,
        registry_payload=registry_payload,
        apply_result_payload=apply_result,
        expected_blocks_total=3,
        expected_source_id="123__кузница_духа",
    )
    assert gate["data_consistency_passed"] is True
    assert gate["governance_present_rate"] == 1.0
    assert gate["allowed_use_present_rate"] == 1.0
    assert gate["safety_flags_present_rate"] == 1.0


def test_data_consistency_fails_on_authority_mutation_counters() -> None:
    blocks_payload = {"blocks": [_block("b1")]}
    registry_payload = [{"source_id": "123__кузница_духа", "status": "done", "blocks_count": 1}]
    apply_result = {
        "apply_summary": {
            "text_changed_count": 1,
            "chunk_type_changed_count": 0,
            "allowed_use_changed_count": 0,
            "safety_flags_changed_count": 0,
            "source_id_changed_count": 0,
            "block_id_changed_count": 0,
            "governance_invariant_violations": 0,
        }
    }
    gate = build_data_consistency_gate(
        blocks_payload=blocks_payload,
        registry_payload=registry_payload,
        apply_result_payload=apply_result,
        expected_blocks_total=1,
        expected_source_id="123__кузница_духа",
    )
    assert gate["data_consistency_passed"] is False
