from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_limited_activation_readiness as gate  # noqa: E402


def test_limited_activation_readiness_docs_consistency_gate() -> None:
    project_state = Path("docs/PROJECT_STATE.md").read_text(encoding="utf-8")
    roadmap = Path("docs/ROADMAP.md").read_text(encoding="utf-8")
    prd_index = Path("docs/PRD_INDEX.md").read_text(encoding="utf-8")
    decisions = Path("docs/DECISIONS.md").read_text(encoding="utf-8")
    payload = gate.build_docs_consistency_gate(
        project_state_text=project_state,
        roadmap_text=roadmap,
        prd_index_text=prd_index,
        decisions_text=decisions,
    )
    assert isinstance(payload["docs_consistency_gate_passed"], bool)

