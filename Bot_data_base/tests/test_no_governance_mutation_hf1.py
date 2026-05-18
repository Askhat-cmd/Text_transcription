from __future__ import annotations

from tools import run_live_botdb_chroma_registry_audit_hf1 as runner


def test_no_governance_mutation_proof_flags():
    payload = runner._build_no_governance_mutation(
        source_prd="PRD-046.1.21-HF1",
        before_registry_hash="a",
        after_registry_hash="a",
        before_blocks_hash="b",
        after_blocks_hash="b",
        reindex_performed=True,
        cleanup_performed=False,
        expected_source_id="123__кузница_духа",
    )

    assert payload["all_blocks_merged_text_mutated"] is False
    assert payload["registry_focus_source_mutated"] is False
    assert payload["chroma_reindex_performed"] is True
    assert payload["focus_source_deleted"] is False
