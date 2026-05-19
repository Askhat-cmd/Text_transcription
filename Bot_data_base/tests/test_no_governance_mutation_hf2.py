from __future__ import annotations

from tools import run_botdb_live_recovery_hf2 as runner


def test_no_governance_mutation_proof_hf2(tmp_path):
    payload = runner._build_no_governance_mutation_proof(
        before_hashes={"all_blocks_merged": "a", "registry": "b", "config": "c"},
        after_hashes={"all_blocks_merged": "a", "registry": "b", "config": "c"},
        focus_before=[{"source_id": "123__кузница_духа", "blocks_count": 247}],
        focus_after=[{"source_id": "123__кузница_духа", "blocks_count": 247}],
        cleanup_result={"registry_zero_block_test_archive_rows_removed": True},
        output_dir=tmp_path,
    )
    assert payload["all_blocks_merged_text_mutated"] is False
    assert payload["focus_source_registry_mutated"] is False
    assert payload["focus_source_deleted"] is False
    assert payload["config_mutated"] is False
