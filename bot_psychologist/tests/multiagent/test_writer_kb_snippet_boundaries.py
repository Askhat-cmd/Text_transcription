from __future__ import annotations

import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from bot_agent.multiagent.contracts.memory_bundle import SemanticHit
from bot_agent.multiagent.knowledge_policy import apply_knowledge_policy_v1


def _hit(text: str) -> SemanticHit:
    return SemanticHit(
        chunk_id="writer_1",
        source="book",
        score=0.95,
        content=text,
        governance={
            "chunk_type": "theory",
            "allowed_use": ["writer_context"],
            "safety_flags": ["not_for_direct_quote"],
        },
        chunking_quality={},
    )


def _tail(text: str) -> str:
    return text[:-1] if text.endswith("…") else text


def test_writer_kb_snippet_boundary_not_midword_for_welcome_case() -> None:
    text = "Знакомо? Добро пожаловать в практику наблюдения за мыслями без спешки. " * 20
    decisions, _ = apply_knowledge_policy_v1([_hit(text)])
    snippet = decisions[0].to_writer_hit_dict()["content"]
    assert snippet.endswith("…")
    assert not _tail(snippet).endswith("пожаловат")


def test_writer_kb_snippet_boundary_not_midword_for_eat_on_run_case() -> None:
    text = "Ешь на бегу, думаешь на бегу, слушаешь на бегу, и тело не успевает выдохнуть. " * 20
    decisions, _ = apply_knowledge_policy_v1([_hit(text)])
    snippet = decisions[0].to_writer_hit_dict()["content"]
    assert snippet.endswith("…")
    assert not re.search(r"\b[А-Яа-яЁё]{1,2}$", _tail(snippet))
