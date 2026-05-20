from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_controlled_rollout_execution as execution  # noqa: E402


def test_controlled_rollout_execution_source_gate() -> None:
    preflight = execution.preflight_source(
        reports_dir=Path("TO_DO_LIST/reports"),
        docs_dir=Path("docs"),
        source_dir=Path("TO_DO_LIST/logs/PRD-046.1.30"),
    )
    source_gate = execution.build_source_gate(preflight)
    assert preflight["ok"] is True
    assert source_gate["source_gate_passed"] is True

