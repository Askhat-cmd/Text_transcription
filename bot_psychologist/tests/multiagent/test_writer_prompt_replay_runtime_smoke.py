from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_writer_prompt_replay_eval as runner


def test_runtime_smoke_replay_offline_only_and_no_apply_flags() -> None:
    cases = runner._run_runtime_smoke()
    assert len(cases) >= 3
    for item in cases:
        assert item["status"] == "ok"
        assert item["answer_exists"] is True
        assert item["replay_exists"] is True
        assert item["activation_mode"] == "offline_replay_only"
        assert item["apply_to_writer_contract"] is False
        assert item["apply_to_writer_prompt"] is False
        assert item["apply_to_final_answer"] is False
        assert item["provider_called"] is False
