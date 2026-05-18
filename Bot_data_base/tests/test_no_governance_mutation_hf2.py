from __future__ import annotations

from pathlib import Path

from tools import run_live_chroma_runtime_binding_hf2 as runner


def test_no_governance_mutation_proof_hf2(tmp_path: Path):
    botdb = tmp_path
    (botdb / "data" / "processed").mkdir(parents=True, exist_ok=True)
    (botdb / "data").mkdir(parents=True, exist_ok=True)
    (botdb / "data" / "processed" / "all_blocks_merged.json").write_text("{}", encoding="utf-8")
    (botdb / "data" / "registry.json").write_text("{}", encoding="utf-8")
    (botdb / "config.yaml").write_text("x: 1", encoding="utf-8")

    before = {
        "all_blocks_merged": runner._sha256(botdb / "data" / "processed" / "all_blocks_merged.json"),
        "registry": runner._sha256(botdb / "data" / "registry.json"),
        "config": runner._sha256(botdb / "config.yaml"),
    }

    payload = runner._no_mutation_proof(botdb, before, rebind_performed=True, rebuild_performed=False)
    assert payload["all_blocks_merged_text_mutated"] is False
    assert payload["registry_focus_source_mutated"] is False
    assert payload["config_mutated"] is False
