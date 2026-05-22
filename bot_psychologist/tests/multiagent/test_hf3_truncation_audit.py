from __future__ import annotations

from pathlib import Path
import sys

CURRENT_FILE = Path(__file__).resolve()
BOT_PSYCHOLOGIST_ROOT = CURRENT_FILE.parents[2]
if str(BOT_PSYCHOLOGIST_ROOT) not in sys.path:
    sys.path.insert(0, str(BOT_PSYCHOLOGIST_ROOT))

from bot_agent.multiagent import creator_live_rag_delivery_hf3 as hf3


def test_hf3_truncation_audit_detects_caps(tmp_path: Path) -> None:
    kp = tmp_path / "bot_psychologist/bot_agent/multiagent/knowledge_policy.py"
    wa = tmp_path / "bot_psychologist/bot_agent/multiagent/agents/writer_agent.py"
    kp.parent.mkdir(parents=True, exist_ok=True)
    wa.parent.mkdir(parents=True, exist_ok=True)
    kp.write_text("_POLICY_SANITIZED_MAX_CHARS = 240\n\ndef _trim_to_word_boundary():\n    pass\n", encoding="utf-8")
    wa.write_text("x = h[:300]\nconversation_context=(ctx['conversation_context'])[:2000]\n", encoding="utf-8")

    audit = hf3.build_writer_kb_truncation_audit(
        repo_root=tmp_path,
        selected_evidence={"query_id": "q1", "writer_prompt_knowledge_hits_count": 1, "context_assembly_knowledge_hits_count": 1},
    )
    assert audit["writer_kb_truncation_gate"] == "warning"
    assert audit["truncation_detected"] is True
    assert audit["truncation_blocker"] is False
