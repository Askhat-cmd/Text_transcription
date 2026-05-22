from __future__ import annotations

import json
from pathlib import Path
import sys

CURRENT_FILE = Path(__file__).resolve()
BOT_PSYCHOLOGIST_ROOT = CURRENT_FILE.parents[2]
if str(BOT_PSYCHOLOGIST_ROOT) not in sys.path:
    sys.path.insert(0, str(BOT_PSYCHOLOGIST_ROOT))

from bot_agent.multiagent import creator_live_rag_delivery_hf3 as hf3


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_hf3_source_gate_reads_hf2_memory_evidence(tmp_path: Path) -> None:
    _write(
        tmp_path / "TO_DO_LIST/logs/PRD-046.1.35-HF2/hf2_scorecard.json",
        json.dumps(
            {
                "final_status": "evidence_incomplete",
                "decision": "hf2_blocked_context_delivery_failed",
                "botdb_chunks_returned": 4,
                "normal_user_activation_allowed": False,
                "broad_rollout_allowed": False,
                "production_ready": False,
            },
            ensure_ascii=False,
        ),
    )
    _write(
        tmp_path / "TO_DO_LIST/logs/PRD-046.1.35-HF2/test_command_output.txt",
        "rag_raw_hits_count=4\nrag_salvaged_hits_count=3\nknowledge_policy_included_writer_count=3\n",
    )
    _write(tmp_path / "TO_DO_LIST/logs/PRD-046.1.35-HF2/botdb_direct_query_probe.json", "{}")
    _write(tmp_path / "TO_DO_LIST/reports/PRD-046.1.35-HF2_IMPLEMENTATION_REPORT.md", "ok")
    _write(tmp_path / "TO_DO_LIST/reports/PRD-046.1.35-HF2_NEXT_PRD_RECOMMENDATION.md", "ok")
    _write(tmp_path / "docs/PROJECT_STATE.md", "ok")
    _write(tmp_path / "docs/ROADMAP.md", "ok")
    _write(tmp_path / "docs/PRD_INDEX.md", "ok")
    _write(tmp_path / "docs/DECISIONS.md", "ok")

    result = hf3.preflight_source_gate(tmp_path)
    assert result["source_gate_passed"] is True
    assert result["memory_agent_evidence_from_hf2_command_log"]["rag_raw_hits_count=4"] is True
