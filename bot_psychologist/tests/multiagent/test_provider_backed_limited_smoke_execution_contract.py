from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent.contracts.diagnostic_center_provider_backed_limited_smoke_execution_v1 import (
    ProviderBackedLimitedSmokeExecutionStatus,
)


def test_provider_backed_limited_smoke_execution_contract_defaults() -> None:
    payload = ProviderBackedLimitedSmokeExecutionStatus().to_dict()
    assert payload["final_status"] == "failed"
    assert payload["decision"] == "provider_backed_limited_smoke_failed"
    assert payload["provider_calls_performed"] == 0
