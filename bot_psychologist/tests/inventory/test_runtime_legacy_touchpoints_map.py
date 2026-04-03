from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_PATH = REPO_ROOT / "bot_psychologist/tests/fixtures/runtime_legacy_touchpoints_v102.json"


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def test_runtime_legacy_touchpoints_fixture_shape() -> None:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    assert payload.get("schema_version") == "10.2-phase0"
    assert isinstance(payload.get("entrypoints"), list) and payload["entrypoints"]
    assert isinstance(payload.get("legacy_touchpoints"), dict) and payload["legacy_touchpoints"]


def test_runtime_legacy_entrypoints_exist() -> None:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    for ep in payload["entrypoints"]:
        file_path = REPO_ROOT / ep["file"]
        assert file_path.exists(), f"Missing file for entrypoint: {ep['name']}"
        text = _read_text(file_path)
        assert ep["symbol"] in text, f"Missing symbol {ep['symbol']} in {ep['file']}"
        if "route" in ep:
            assert ep["route"] in text, f"Missing route {ep['route']} in {ep['file']}"


def test_runtime_legacy_touchpoints_are_present_in_baseline() -> None:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    for touchpoint_name, spec in payload["legacy_touchpoints"].items():
        file_path = REPO_ROOT / spec["file"]
        assert file_path.exists(), f"Missing touchpoint file: {touchpoint_name}"
        text = _read_text(file_path)
        for pattern in spec["patterns"]:
            assert pattern in text, (
                f"Expected baseline marker '{pattern}' for '{touchpoint_name}' "
                f"was not found in {spec['file']}"
            )
