from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_diagnostic_center_final_completion_hf1 as runner  # noqa: E402


def test_prd_046_1_37_hf1_docs_correction_marks_pending(tmp_path: Path) -> None:
    docs = tmp_path / "docs" / "PROJECT_STATE.md"
    docs.parent.mkdir(parents=True, exist_ok=True)
    docs.write_text(
        "\n".join(
            [
                "# Project State",
                "## Current Stage",
                "completed text",
                "## Next Planned PRD",
                "`Multiagent Quality & Tuning Track`",
                "## Diagnostic Center Track Status",
                "Diagnostic Center Track Status: CLOSED FOR CURRENT PHASE",
            ]
        ),
        encoding="utf-8",
    )
    payload = runner._apply_docs_state_pre_rerun_correction(tmp_path)  # noqa: SLF001
    assert payload["docs_state_pre_rerun_correction"] == "passed"
    updated = docs.read_text(encoding="utf-8")
    assert "PENDING FINAL ACTUAL-LIVE EVIDENCE REPAIR" in updated
    assert "not formally completed yet" in updated
