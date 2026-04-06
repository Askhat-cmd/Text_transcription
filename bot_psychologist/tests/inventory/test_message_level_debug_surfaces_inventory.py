from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_PATH = REPO_ROOT / "bot_psychologist/tests/fixtures/admin_boundary_inventory_v105_phase0.json"


def _load_debug_surfaces() -> list[str]:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8-sig"))
    return payload["boundary_inventory"]["message_level_debug_surfaces"]


def test_message_level_debug_inventory_contains_required_forensic_surfaces() -> None:
    surfaces = set(_load_debug_surfaces())
    required = {
        "trace_debug_tab",
        "last_diagnostics_snapshot",
        "recent_traces",
        "turn_retrieval_breakdown",
        "turn_validation_breakdown",
        "turn_memory_update",
        "turn_prompt_participation",
        "turn_anomalies",
    }
    assert required.issubset(surfaces)


def test_message_level_debug_inventory_not_empty() -> None:
    surfaces = _load_debug_surfaces()
    assert isinstance(surfaces, list)
    assert len(surfaces) >= 6
