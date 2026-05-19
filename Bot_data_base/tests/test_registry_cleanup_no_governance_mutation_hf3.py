from __future__ import annotations

from tools import run_registry_focus_only_cleanup_hf3 as hf3


def test_no_governance_mutation_proof_allows_registry_non_focus_removal():
    payload = hf3.build_no_mutation_proof(
        before_hashes={"registry": "a", "all_blocks": "x", "config": "y"},
        after_hashes={"registry": "b", "all_blocks": "x", "config": "y"},
        focus_before=[{"source_id": "123__кузница_духа", "blocks_count": 247}],
        focus_after=[{"source_id": "123__кузница_духа", "blocks_count": 247}],
        chroma_focus_before=247,
        chroma_focus_after=247,
    )
    assert payload["registry_non_focus_rows_removed"] is True
    assert payload["no_governance_mutation_proof_passed"] is True
