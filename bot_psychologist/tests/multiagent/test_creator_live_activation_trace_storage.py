from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_creator_live_activation as gate  # noqa: E402


def test_trace_storage_gate(tmp_path: Path) -> None:
    payload = gate.build_trace_storage_gate(repo_root=Path("."), output_dir=tmp_path)
    assert payload["trace_storage_gate_passed"] is True
    assert (tmp_path / "sanitized_trace_sample.json").exists()
