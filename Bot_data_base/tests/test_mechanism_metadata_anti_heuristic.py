from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_new_mechanism_metadata_modules_do_not_contain_forbidden_runtime_routes() -> None:
    forbidden_patterns = {
        'if "мама" in user_message',
        'if "стыд" in user_message',
        'if "контроль" in user_message',
        'if "паника" in user_message',
        "depth_level = 3 if",
    }
    for relative_path in (
        "Bot_data_base/knowledge_governance/mechanism_metadata.py",
        "Bot_data_base/tools/run_mechanism_metadata_audit.py",
    ):
        lines = (REPO_ROOT / relative_path).read_text(encoding="utf-8").lower().splitlines()
        executable_lines = [line.strip() for line in lines if not line.strip().startswith(("'", '"'))]
        for line in executable_lines:
            assert line not in forbidden_patterns
