from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_runtime_files_do_not_reference_prd_047_18_review_contract() -> None:
    runtime_roots = [
        REPO_ROOT / "bot_psychologist" / "bot_agent" / "multiagent",
        REPO_ROOT / "bot_psychologist" / "api",
        REPO_ROOT / "Bot_data_base" / "api",
        REPO_ROOT / "Bot_data_base" / "storage",
    ]
    forbidden_tokens = {
        "mechanism_metadata_review_decision_v1",
        "mechanism_metadata_curated_overlay_preview_v1",
        "mechanism_metadata_review_queue_v1",
        "safe_to_apply_to_live_metadata",
        "curated_overlay_preview",
    }
    for root in runtime_roots:
        for path in root.rglob("*.py"):
            text = path.read_text(encoding="utf-8").lower()
            for token in forbidden_tokens:
                assert token not in text, f"{token} leaked into {path}"
