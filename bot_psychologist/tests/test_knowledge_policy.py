from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from bot_agent.multiagent.contracts.memory_bundle import SemanticHit
from bot_agent.multiagent.knowledge_policy import apply_knowledge_policy_v1


def _hit(*, chunk_id: str, content: str, governance: dict | None = None, chunking_quality: dict | None = None):
    return SemanticHit(
        chunk_id=chunk_id,
        source="book",
        score=0.9,
        content=content,
        governance=governance or {},
        chunking_quality=chunking_quality or {},
    )


def test_policy_drops_do_not_use_chunk() -> None:
    hit = _hit(
        chunk_id="c1",
        content="text",
        governance={"chunk_type": "excluded", "allowed_use": ["do_not_use"], "safety_flags": []},
    )
    decisions, _ = apply_knowledge_policy_v1([hit])
    assert decisions[0].action == "drop"
    assert "do_not_use_or_excluded" in decisions[0].reasons


def test_policy_internal_only_not_allowed_for_writer() -> None:
    hit = _hit(
        chunk_id="c2",
        content="internal text",
        governance={"chunk_type": "style", "allowed_use": ["internal_only", "diagnostic_lens"], "safety_flags": ["source_style_not_user_facing"]},
    )
    decisions, _ = apply_knowledge_policy_v1([hit])
    d = decisions[0]
    assert d.action == "internal_only"
    assert d.allowed_for_writer is False
    assert d.sanitized_content == ""


def test_not_for_direct_quote_is_sanitized_and_truncated() -> None:
    hit = _hit(
        chunk_id="c3",
        content="Очень длинный контент " * 40,
        governance={"chunk_type": "theory", "allowed_use": ["writer_context"], "safety_flags": ["not_for_direct_quote"]},
    )
    decisions, _ = apply_knowledge_policy_v1([hit])
    d = decisions[0]
    assert d.action == "include_writer_context"
    assert len(d.sanitized_content) <= 240
    assert "content_sanitized_not_for_direct_quote" in d.reasons


def test_practice_suggestion_only_for_practice_chunk() -> None:
    practice_hit = _hit(
        chunk_id="c4",
        content="Шаг 1: вдох",
        governance={"chunk_type": "practice", "allowed_use": ["writer_context", "practice_suggestion"], "safety_flags": []},
    )
    non_practice_hit = _hit(
        chunk_id="c5",
        content="Паттерн избегания",
        governance={"chunk_type": "lens", "allowed_use": ["writer_context", "practice_suggestion"], "safety_flags": []},
    )
    decisions, _ = apply_knowledge_policy_v1([practice_hit, non_practice_hit])
    assert decisions[0].allowed_for_practice is True
    assert decisions[1].allowed_for_practice is False


def test_practice_low_resource_check_flag_preserved() -> None:
    hit = _hit(
        chunk_id="c6",
        content="Шаг 1: вдох",
        governance={
            "chunk_type": "practice",
            "allowed_use": ["writer_context", "practice_suggestion"],
            "safety_flags": [],
            "practice_metadata": {"low_resource_safe": False},
        },
    )
    decisions, _ = apply_knowledge_policy_v1([hit])
    d = decisions[0]
    assert "practice_requires_low_resource_check" in d.reasons
    assert "practice_requires_low_resource_check" in d.risk_flags


def test_mixed_intent_high_drops_writer_context() -> None:
    hit = _hit(
        chunk_id="c7",
        content="text",
        governance={"chunk_type": "theory", "allowed_use": ["writer_context"], "safety_flags": []},
        chunking_quality={"mixed_intent_risk": True, "mixed_intent_severity": "high"},
    )
    decisions, _ = apply_knowledge_policy_v1([hit])
    assert decisions[0].action == "drop"
    assert decisions[0].allowed_for_writer is False


def test_legacy_no_governance_kept_with_risk_flag() -> None:
    hit = SemanticHit(chunk_id="c8", content="legacy", source="legacy", score=0.6)
    decisions, _ = apply_knowledge_policy_v1([hit])
    d = decisions[0]
    assert d.action == "include_writer_context"
    assert "legacy_no_governance" in d.risk_flags
