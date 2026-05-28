from __future__ import annotations

import json
from pathlib import Path


DATASET_PATH = (
    Path(__file__).resolve().parents[1]
    / "tests"
    / "evaluation"
    / "prd_047_2_kernel_quality_cases.json"
)


def test_dataset_exists() -> None:
    assert DATASET_PATH.exists()


def test_dataset_has_minimum_cases_and_unique_ids() -> None:
    payload = json.loads(DATASET_PATH.read_text(encoding="utf-8-sig"))
    assert isinstance(payload, list)
    assert len(payload) >= 12
    ids = [str(item.get("id", "")) for item in payload if isinstance(item, dict)]
    assert len(ids) == len(set(ids))


def test_dataset_groups_and_required_fields() -> None:
    payload = json.loads(DATASET_PATH.read_text(encoding="utf-8-sig"))
    groups = {str(item.get("group", "")) for item in payload if isinstance(item, dict)}
    assert len(groups) >= 3

    for item in payload:
        assert isinstance(item, dict)
        assert str(item.get("id", "")).strip()
        assert str(item.get("query", "")).strip()
        assert isinstance(item.get("expected", {}), dict)


def test_dataset_has_forbidden_fragments_for_relevant_cases() -> None:
    payload = json.loads(DATASET_PATH.read_text(encoding="utf-8-sig"))
    relevant = [
        item
        for item in payload
        if isinstance(item, dict)
        and isinstance(item.get("expected", {}), dict)
        and (
            item.get("expected", {}).get("should_not_include_any")
            or item.get("expected", {}).get("must_not_external_surveillance")
            or item.get("expected", {}).get("must_not_quote_source")
        )
    ]
    assert len(relevant) >= 6
