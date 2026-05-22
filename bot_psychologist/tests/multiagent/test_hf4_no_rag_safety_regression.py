from __future__ import annotations

from pathlib import Path
import sys

CURRENT_FILE = Path(__file__).resolve()
BOT_PSYCHOLOGIST_ROOT = CURRENT_FILE.parents[2]
if str(BOT_PSYCHOLOGIST_ROOT) not in sys.path:
    sys.path.insert(0, str(BOT_PSYCHOLOGIST_ROOT))

from bot_agent.multiagent.knowledge_policy import build_safe_knowledge_debug_detail_v1  # noqa: E402


def test_hf4_knowledge_debug_preview_remains_sanitized() -> None:
    hits = [
        {
            "chunk_id": "chunk-1",
            "source": "book",
            "score": 0.8,
            "content": "Это безопасный фрагмент контекста для пользователя.",
            "governance": {
                "chunk_type": "book",
                "allowed_use": ["writer_context"],
                "safety_flags": [],
            },
        }
    ]
    policy_trace = {
        "decisions": [
            {
                "chunk_id": "chunk-1",
                "action": "include_writer_context",
                "reasons": [],
                "risk_flags": [],
            }
        ]
    }
    details = build_safe_knowledge_debug_detail_v1(
        semantic_hits=hits,
        knowledge_policy_trace=policy_trace,
    )
    assert len(details) == 1
    assert details[0]["content_preview"] != ""
    assert details[0]["content_redacted"] is True
    assert "content_full" not in details[0]

