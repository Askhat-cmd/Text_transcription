from __future__ import annotations

import json
from pathlib import Path

from scripts.run_prd_047_9_mvp_context_unclamp_cases import (
    DEFAULT_DATASET,
    _run_direct,
    _validate_dataset,
)


def test_dataset_validation_passes_for_prd_047_9_cases() -> None:
    payload = json.loads(Path(DEFAULT_DATASET).read_text(encoding="utf-8-sig"))
    assert isinstance(payload, list)
    ok, errors = _validate_dataset(payload)
    assert ok is True
    assert errors == []


def test_direct_mode_passes_core_checks() -> None:
    payload = json.loads(Path(DEFAULT_DATASET).read_text(encoding="utf-8-sig"))
    result = _run_direct(payload)
    assert result["checks"]["cases_passed"] is True
    assert result["checks"]["context_truncated"] is True
    assert result["checks"]["writer_catalog_has_3_items"] is True
