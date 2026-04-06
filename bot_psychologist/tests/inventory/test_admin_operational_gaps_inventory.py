from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_PATH = (
    REPO_ROOT
    / "bot_psychologist/tests/fixtures/admin_operational_surface_inventory_v1041_phase0.json"
)


def _load_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8-sig"))


def test_admin_operational_gaps_fixture_shape_v1041_phase0() -> None:
    payload = _load_fixture()
    assert payload.get("schema_version") == "10.4.1-phase0"
    sections = payload.get("ui_operational_gaps", {}).get("sections", [])
    assert isinstance(sections, list)
    assert sections, "ui_operational_gaps.sections must not be empty"


def test_admin_operational_gaps_sections_have_required_fields() -> None:
    payload = _load_fixture()
    sections = payload["ui_operational_gaps"]["sections"]
    required = {"name", "status", "file", "before_markers", "missing_markers"}
    for section in sections:
        assert required.issubset(set(section.keys())), f"Missing keys in section: {section}"
        assert section["status"] == "gap"
        assert isinstance(section["before_markers"], list) and section["before_markers"]
        assert isinstance(section["missing_markers"], list) and section["missing_markers"]


def test_admin_operational_gap_files_exist() -> None:
    payload = _load_fixture()
    for section in payload["ui_operational_gaps"]["sections"]:
        path = REPO_ROOT / section["file"]
        assert path.exists(), f"Missing file in inventory: {section['file']}"
