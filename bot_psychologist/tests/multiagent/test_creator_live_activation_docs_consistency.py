from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_creator_live_activation as gate  # noqa: E402


def test_creator_live_activation_docs_consistency() -> None:
    payload = gate.build_docs_consistency_gate(
        project_state_text=Path("docs/PROJECT_STATE.md").read_text(encoding="utf-8"),
        roadmap_text=Path("docs/ROADMAP.md").read_text(encoding="utf-8"),
        prd_index_text=Path("docs/PRD_INDEX.md").read_text(encoding="utf-8"),
        decisions_text=Path("docs/DECISIONS.md").read_text(encoding="utf-8"),
    )
    assert isinstance(payload["docs_consistency_gate_passed"], bool)
