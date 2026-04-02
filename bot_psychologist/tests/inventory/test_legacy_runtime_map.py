from __future__ import annotations

import json
import os
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_PATH = REPO_ROOT / "bot_psychologist/tests/fixtures/legacy_runtime_map.json"
NEO_ENABLED = os.getenv("NEO_MINDBOT_ENABLED", "false").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


@pytest.mark.skipif(
    NEO_ENABLED,
    reason="Legacy runtime inventory is not authoritative when Neo MindBot pipeline is enabled.",
)
def test_legacy_runtime_map_fixture_is_consistent() -> None:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8-sig"))
    assert payload.get("schema_version") == "1.0"

    for ep in payload["entrypoints"]:
        file_path = REPO_ROOT / ep["file"]
        assert file_path.exists(), f"Missing file for entrypoint: {ep['name']}"

        text = _read_text(file_path)
        assert ep["symbol"] in text, f"Missing symbol {ep['symbol']} in {ep['file']}"
        if "route" in ep:
            assert ep["route"] in text, f"Missing route {ep['route']} in {ep['file']}"


@pytest.mark.skipif(
    NEO_ENABLED,
    reason="Legacy runtime inventory is not authoritative when Neo MindBot pipeline is enabled.",
)
def test_legacy_runtime_dependencies_are_present_in_mapped_files() -> None:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8-sig"))
    patterns = {
        "sd_classifier": ["sd_classifier"],
        "sd_level": ["sd_level"],
        "user_level_adapter": ["user_level_adapter", "UserLevelAdapter"],
        "decision_gate": ["DecisionGate", "decision_gate"],
        "prompt_overlays": ["mode_prompt_override", "sd_overlay", "_load_sd_prompt"],
    }

    for dep_name, files in payload["legacy_runtime_dependencies"].items():
        assert dep_name in patterns, f"No pattern rules for dependency: {dep_name}"

        for rel_path in files:
            file_path = REPO_ROOT / rel_path
            assert file_path.exists(), f"Missing mapped file: {rel_path}"
            text = _read_text(file_path)
            assert any(p in text for p in patterns[dep_name]), (
                f"Dependency marker for '{dep_name}' was not found in {rel_path}"
            )
