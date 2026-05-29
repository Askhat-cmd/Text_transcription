from __future__ import annotations

import json
from pathlib import Path

from scripts.run_prd_047_8_mvp_free_dialogue_cases import (
    DEFAULT_DATASET,
    _run_direct,
    _validate_dataset,
)


def test_dataset_validation_passes_for_prd_047_8_cases() -> None:
    payload = json.loads(Path(DEFAULT_DATASET).read_text(encoding="utf-8-sig"))
    assert isinstance(payload, list)
    ok, errors, _coverage = _validate_dataset(payload)
    assert ok is True
    assert errors == []


def test_direct_mode_has_active_concept_inheritance_and_relaxed_writer() -> None:
    payload = json.loads(Path(DEFAULT_DATASET).read_text(encoding="utf-8-sig"))
    result = _run_direct(payload)
    assert result["summary"]["active_concept_inheritance_ok"] is True
    assert result["summary"]["writer_repair_and_expand_relaxed_ok"] is True

