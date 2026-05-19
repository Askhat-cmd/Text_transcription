from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_second_provider_backed_smoke as gate
from bot_agent.multiagent.contracts.diagnostic_center_second_provider_backed_smoke_v1 import (
    SecondProviderBackedSmokeStatusV1,
)


def test_second_provider_backed_smoke_contract_defaults() -> None:
    payload = SecondProviderBackedSmokeStatusV1().to_dict()
    assert payload["final_status"] == "failed"
    assert payload["decision"] == "hotfix_required"
    assert payload["provider_calls_performed"] == 0
    assert gate.CONTRACT_PAYLOAD["provider_budget_max_calls"] == 6
