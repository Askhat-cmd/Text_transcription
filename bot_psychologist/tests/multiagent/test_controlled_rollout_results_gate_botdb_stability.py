from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_controlled_rollout_results_gate as gate  # noqa: E402


def test_controlled_rollout_results_gate_botdb_stability() -> None:
    preflight = gate.preflight_source(Path("TO_DO_LIST/logs/PRD-046.1.31"), Path("TO_DO_LIST/reports"))
    payload = gate.build_botdb_stability_gate(preflight["parsed"])
    assert payload["botdb_query_ok"] is True
    assert payload["botdb_semantic_fallback_used"] is False
    assert payload["botdb_stability_gate_passed"] is True
