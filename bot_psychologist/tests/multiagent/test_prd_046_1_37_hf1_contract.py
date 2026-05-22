from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent.contracts.diagnostic_center_final_completion_hf1_v1 import (  # noqa: E402
    DiagnosticCenterFinalCompletionHF1Scorecard,
)


def test_prd_046_1_37_hf1_contract_defaults() -> None:
    payload = DiagnosticCenterFinalCompletionHF1Scorecard().to_dict()
    assert payload["schema_version"] == "diagnostic_center_actual_live_runtime_hf1_scorecard_v1"
    assert payload["final_status"] == "blocked"
    assert payload["decision"] == "blocked_runtime_readiness_after_hf1"
