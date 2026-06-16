from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_runtime_files_do_not_reference_prd_047_20_batch_eval_contracts() -> None:
    runtime_roots = [
        REPO_ROOT / "bot_psychologist" / "bot_agent" / "multiagent",
        REPO_ROOT / "bot_psychologist" / "api",
        REPO_ROOT / "Bot_data_base" / "api",
        REPO_ROOT / "Bot_data_base" / "storage",
    ]
    forbidden_tokens = {
        "mechanism_metadata_curated_batch_selection_v1",
        "mechanism_metadata_curated_batch_retrieval_eval_results_v1",
        "offline_curator_batch_1",
        "batch_1_overlay_shadow_lookup",
        "evaluation_only_overlay",
    }
    for root in runtime_roots:
        for path in root.rglob("*.py"):
            text = path.read_text(encoding="utf-8").lower()
            for token in forbidden_tokens:
                assert token not in text, f"{token} leaked into {path}"
