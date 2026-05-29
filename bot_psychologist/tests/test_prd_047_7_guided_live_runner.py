from __future__ import annotations

import json
from pathlib import Path

from bot_agent.live_testing import feedback_capture as fc
from scripts.run_prd_047_7_guided_live_feedback_smoke import (
    DEFAULT_SCENARIOS,
    _load_scenarios,
    _run_dry,
    _validate_scenarios,
)


def test_scenario_set_validation_passes_for_default_dataset() -> None:
    items = _load_scenarios(Path(DEFAULT_SCENARIOS))
    ok, errors, coverage = _validate_scenarios(items)
    assert ok is True
    assert errors == []
    assert len(items) >= 18
    assert coverage["ordinary_understanding"] >= 1


def test_scenario_validation_fails_on_missing_categories() -> None:
    items = [
        {
            "scenario_id": "x",
            "category": "ordinary_understanding",
            "user_prompt": "hello",
        }
        for _ in range(18)
    ]
    ok, errors, _coverage = _validate_scenarios(items)
    assert ok is False
    assert any("missing_required_category" in err for err in errors)


def test_dry_smoke_creates_sanitized_summary(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(fc, "LIVE_FEEDBACK_BASE_DIR", tmp_path / "live_feedback", raising=False)

    items = _load_scenarios(Path(DEFAULT_SCENARIOS))
    result = _run_dry(items)

    assert result["summary"] == "passed"
    assert int(result["records_created"]) >= 3
    assert result["raw_dialogue_saved"] is False
    assert result["sanitized_summary_created"] is True

    session_path = fc.get_session_storage_path("sample_session")
    assert session_path.exists()
    payload = json.loads(session_path.read_text(encoding="utf-8"))
    assert payload["feedback_count"] >= 3
