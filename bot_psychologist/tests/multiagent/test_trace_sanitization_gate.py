from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_final_acceptance as module


def test_trace_sanitization_gate_detects_forbidden_markers() -> None:
    payload = module.build_trace_sanitization_gate(
        {
            "safe_artifact": {"value": "ok"},
            "unsafe_artifact": {"debug": "content_full=raw text"},
        }
    )
    assert payload["contains_raw_content_full"] is True
    assert payload["final_status"] == "failed"
