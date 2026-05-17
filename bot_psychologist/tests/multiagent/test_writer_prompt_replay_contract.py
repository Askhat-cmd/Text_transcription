from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent.contracts.writer_prompt_replay_v1 import WriterPromptReplayResult


def test_replay_contract_forces_offline_only_guardrails() -> None:
    payload = WriterPromptReplayResult.from_dict(
        {
            "activation_mode": "runtime_active",
            "apply_to_writer_contract": True,
            "apply_to_writer_prompt": True,
            "apply_to_final_answer": True,
            "provider_called": True,
        }
    ).to_dict()

    assert payload["activation_mode"] == "offline_replay_only"
    assert payload["apply_to_writer_contract"] is False
    assert payload["apply_to_writer_prompt"] is False
    assert payload["apply_to_final_answer"] is False
    assert payload["provider_called"] is False
