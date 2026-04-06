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


def test_trace_surface_baseline_fixture_shape() -> None:
    payload = _load_fixture()
    trace_surface = payload.get("trace_surface_baseline", {})
    assert trace_surface.get("status") == "placeholder"
    blocks = trace_surface.get("required_blocks", [])
    assert isinstance(blocks, list)
    assert blocks, "required_blocks must not be empty"


def test_trace_surface_baseline_contains_required_operational_blocks() -> None:
    payload = _load_fixture()
    blocks = set(payload["trace_surface_baseline"]["required_blocks"])
    expected = {
        "turn_header",
        "diagnostics_snapshot",
        "routing_decision",
        "retrieval_pipeline",
        "prompt_stack_summary",
        "output_validation",
        "memory_update",
        "flags_anomalies",
    }
    assert expected.issubset(blocks)
