from __future__ import annotations

import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BOT_PSYCHOLOGIST_ROOT = PROJECT_ROOT / "bot_psychologist"
if str(BOT_PSYCHOLOGIST_ROOT) not in sys.path:
    sys.path.insert(0, str(BOT_PSYCHOLOGIST_ROOT))

from bot_agent.multiagent.knowledge_policy import apply_knowledge_policy_v1
from bot_agent.multiagent.contracts.memory_bundle import SemanticHit


def _hit(content: str) -> SemanticHit:
    return SemanticHit(
        chunk_id="k1",
        source="book",
        score=0.9,
        content=content,
        governance={"chunk_type": "theory", "allowed_use": ["writer_context"], "safety_flags": ["not_for_direct_quote"]},
        chunking_quality={},
    )


def _tail_without_ellipsis(text: str) -> str:
    return text[:-1] if text.endswith("…") else text


def test_retrieval_snippet_truncation_respects_word_boundary() -> None:
    long_text = "Добро пожаловать в практику осознанности и внимательного дыхания. " * 20
    decisions, _ = apply_knowledge_policy_v1([_hit(long_text)])
    snippet = decisions[0].sanitized_content
    assert snippet.endswith("…")
    assert not snippet.endswith(" ")
    assert len(snippet) <= 240
    tail = _tail_without_ellipsis(snippet)
    assert tail[-1] in {".", "!", "?", "й", "я", "а", "о", "ь", "т", "г", "у", "ы", "м", "р", "н", "с", "л"}


def test_retrieval_snippet_no_midword_cut_for_cyrillic_tail() -> None:
    text = "Ешь на бегу, думаешь на бегу, живешь на бегу, и тревога становится фоном. " * 20
    decisions, _ = apply_knowledge_policy_v1([_hit(text)])
    snippet = decisions[0].sanitized_content
    assert snippet.endswith("…")
    tail = _tail_without_ellipsis(snippet)
    assert not re.search(r"\b[А-Яа-яЁё]{1,2}$", tail)
