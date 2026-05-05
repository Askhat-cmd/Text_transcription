from __future__ import annotations

import inspect
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.answer_adaptive import answer_question_adaptive


def test_answer_adaptive_public_shim_has_no_silent_legacy_fallback() -> None:
    source = inspect.getsource(answer_question_adaptive)
    assert "fallback to classic runtime" not in source
    assert "_runtime_prepare_adaptive_run_context" not in source
    assert "run_multiagent_adaptive_sync" in source
