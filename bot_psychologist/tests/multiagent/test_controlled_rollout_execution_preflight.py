from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_controlled_rollout_execution as execution  # noqa: E402


def test_controlled_rollout_execution_preflight(tmp_path: Path) -> None:
    cohort = {
        "allowlisted_operator_ids": ["pilot_runtime_operator_001"],
    }
    botdb = {
        "gate_passed": True,
        "botdb_live_reachable": True,
        "registry_source_count": 1,
        "dashboard_chroma_count": 247,
        "dashboard_chroma_status": "ok",
        "query_endpoint_status": 200,
        "semantic_fallback_used": False,
        "botdb_circuit_open": False,
    }
    payload = execution.build_preflight(
        cohort_policy=cohort,
        botdb_gate=botdb,
        output_dir=tmp_path,
        provider_budget_max=12,
    )
    assert payload["preflight_passed"] is True
    assert payload["allowlist_explicitly_set"] is True

