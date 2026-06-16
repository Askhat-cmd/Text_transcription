from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_runtime_files_do_not_reference_prd_047_19_preflight_contract() -> None:
    runtime_roots = [
        REPO_ROOT / "bot_psychologist" / "bot_agent" / "multiagent",
        REPO_ROOT / "bot_psychologist" / "api",
        REPO_ROOT / "Bot_data_base" / "api",
        REPO_ROOT / "Bot_data_base" / "storage",
    ]
    forbidden_tokens = {
        "mechanism_metadata_dry_run_apply_plan_v1",
        "mechanism_metadata_apply_preflight_v1",
        "field_apply_map",
        "curated_overlay_preview",
        "apply_preflight_report",
        "accepted_fields -> runtime",
    }
    for root in runtime_roots:
        for path in root.rglob("*.py"):
            text = path.read_text(encoding="utf-8").lower()
            for token in forbidden_tokens:
                assert token not in text, f"{token} leaked into {path}"
