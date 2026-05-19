from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent.contracts.diagnostic_center_provider_backed_smoke_readiness_v1 import (
    ProviderBackedSmokeReadinessStatus,
)


def test_provider_backed_smoke_readiness_contract_defaults() -> None:
    payload = ProviderBackedSmokeReadinessStatus().to_dict()
    assert payload["final_status"] == "failed"
    assert payload["decision"] == "provider_backed_readiness_blocked"
    assert payload["provider_called"] is False
