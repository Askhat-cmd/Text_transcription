from __future__ import annotations

from pathlib import Path
import sys

CURRENT_FILE = Path(__file__).resolve()
BOT_PSYCHOLOGIST_ROOT = CURRENT_FILE.parents[2]
if str(BOT_PSYCHOLOGIST_ROOT) not in sys.path:
    sys.path.insert(0, str(BOT_PSYCHOLOGIST_ROOT))

from bot_agent.multiagent.contracts.creator_live_behavior_hf4_v1 import HF4Scorecard, PRD_ID  # noqa: E402


def test_hf4_contract_defaults() -> None:
    payload = HF4Scorecard().to_dict()
    assert payload["schema_version"] == "creator_live_behavior_hf4_scorecard_v1"
    assert payload["prd_id"] == PRD_ID
    assert payload["final_status"] == "blocked"
    assert payload["decision"] == "hf4_blocked_example_request_routing_failed"

