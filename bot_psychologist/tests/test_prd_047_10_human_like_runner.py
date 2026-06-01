from __future__ import annotations

import json
from pathlib import Path

from scripts.run_prd_047_10_human_like_eval import (
    DEFAULT_DATASET,
    REQUIRED_CASE_IDS,
    _run_direct,
    _validate_dataset,
)


def test_dataset_validation_passes_for_prd_047_10_cases() -> None:
    payload = json.loads(Path(DEFAULT_DATASET).read_text(encoding="utf-8-sig"))
    assert isinstance(payload, list)
    ok, errors = _validate_dataset(payload)
    assert ok is True
    assert errors == []


def test_direct_mode_executes_required_cases() -> None:
    payload = json.loads(Path(DEFAULT_DATASET).read_text(encoding="utf-8-sig"))
    result = _run_direct(payload)
    case_ids = {str(item.get("case_id", "")) for item in list(result.get("case_results", []) or [])}
    assert REQUIRED_CASE_IDS.issubset(case_ids)
    assert result["summary"]["cases_total"] >= len(REQUIRED_CASE_IDS)
