from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent.contracts.diagnostic_center_limited_smoke_consolidation_v1 import (
    LimitedSmokeConsolidationStatusV1,
)


def test_limited_smoke_consolidation_contract_defaults() -> None:
    payload = LimitedSmokeConsolidationStatusV1().to_dict()
    assert payload["final_status"] == "blocked"
    assert payload["decision"] == "blocker_requires_hotfix"
    assert payload["provider_cycles_total"] == 0

