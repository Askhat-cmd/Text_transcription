from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_second_provider_backed_smoke as gate


def test_second_provider_backed_smoke_safety_kb_boundary_gate() -> None:
    payload = gate.build_safety_kb_boundary_gate()
    assert payload["raw_kb_text_exposure_count"] == 0
    assert payload["kb_authority_citation_count"] == 0
    assert payload["safety_kb_boundary_gate_passed"] is True
