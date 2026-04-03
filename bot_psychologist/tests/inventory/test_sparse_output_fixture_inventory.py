from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_PATH = REPO_ROOT / "bot_psychologist/tests/fixtures/response_richness_baseline_v103.json"


def _load_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8-sig"))


def test_sparse_output_fixture_inventory_shape() -> None:
    payload = _load_fixture()
    assert payload.get("schema_version") == "10.3-phase0"
    queries = payload.get("queries")
    assert isinstance(queries, list) and len(queries) >= 5


def test_sparse_output_fixture_has_required_classes() -> None:
    payload = _load_fixture()
    classes = {item.get("class") for item in payload.get("queries", [])}
    required = {
        "pure_inform",
        "mixed_inform_personal",
        "first_turn_exploratory",
        "practice_start",
        "mixed_concept_application",
    }
    assert required.issubset(classes)
