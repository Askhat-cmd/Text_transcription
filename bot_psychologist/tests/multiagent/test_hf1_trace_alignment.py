from __future__ import annotations

from pathlib import Path
import sys

CURRENT_FILE = Path(__file__).resolve()
BOT_PSYCHOLOGIST_ROOT = CURRENT_FILE.parents[2]
if str(BOT_PSYCHOLOGIST_ROOT) not in sys.path:
    sys.path.insert(0, str(BOT_PSYCHOLOGIST_ROOT))
from bot_agent.multiagent import creator_live_evidence_rag_repair as hf1


def test_hf1_trace_alignment_detects_mismatch() -> None:
    rag = {
        "context_assembly_knowledge_hits_count": 2,
        "writer_prompt_knowledge_hits_count": 0,
    }
    payload = hf1.build_ui_trace_alignment_gate(rag_proof=rag)

    assert payload["mismatch_detected"] is True
    assert payload["ui_trace_alignment_gate"] == "blocked"

