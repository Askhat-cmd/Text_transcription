from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from bot_agent.multiagent.contracts.memory_bundle import MemoryBundle, SemanticHit
from bot_agent.multiagent.writer_context_package import build_writer_context_package_v1


def test_no_blind_truncation_neurostalking_payload(monkeypatch) -> None:
    monkeypatch.setenv("WRITER_KB_PAYLOAD_ENABLED", "true")
    monkeypatch.setenv("WRITER_KB_PAYLOAD_EXCERPT_TARGET_CHARS", "110")
    monkeypatch.setenv("WRITER_KB_PAYLOAD_EXCERPT_MAX_CHARS", "140")
    content = (
        "**Нейросталкинг** — это работа с наблюдением за триггерами и автоматическими реакциями.\n\n"
        "**НеоСталкинг** — это второй этаж, где человек уже видит конфигурацию механизма и "
        "может выбирать ответ точнее."
    )
    bundle = MemoryBundle(
        semantic_hits=[
            SemanticHit(
                chunk_id="c1",
                source="123__kuznica_duha",
                score=0.92,
                content=content,
                chunking_quality={"chunk_type": "concept"},
            )
        ],
        knowledge_rag_hits=[
            {
                "chunk_id": "c1",
                "source": "123__kuznica_duha",
                "score": 0.92,
                "content": content,
                "chunking_quality": {"chunk_type": "concept"},
            }
        ],
    )

    payload = build_writer_context_package_v1(
        memory_bundle=bundle,
        context_package=None,
        retrieval_decision={
            "rag_included_count": 1,
            "rag_included_for_writer": [
                {
                    "chunk_id": "c1",
                    "source": "123__kuznica_duha",
                    "score": 0.92,
                    "content": content,
                    "chunking_quality": {"chunk_type": "concept"},
                }
            ],
            "planned_composed_query": "что такое нейросталкинг",
        },
        fresh_chat_context_policy={},
    )

    kb_payload = payload["writer_kb_payload"]
    trace = payload["writer_kb_payload_trace"]
    assert kb_payload["enabled"] is True
    assert kb_payload["chunk_count"] == 1
    assert kb_payload["chunks"][0]["content_excerpt"]
    assert kb_payload["chunks"][0]["content_excerpt"] != content[:220]
    assert "**НеоСталкинг** — это в" not in kb_payload["chunks"][0]["content_excerpt"]
    assert trace["mid_sentence_cut_count"] == 0


def test_retrieval_decision_fields_remain_unchanged_when_payload_enabled(monkeypatch) -> None:
    monkeypatch.setenv("WRITER_KB_PAYLOAD_ENABLED", "true")
    decision = {
        "rag_included_count": 1,
        "rag_included_reason": "selected_for_writer",
        "planned_composed_query": "нейросталкинг паттерны",
        "retrieval_action": "query_kb",
        "rag_included_for_writer": [
            {
                "chunk_id": "c1",
                "source": "doc",
                "content": "Нейросталкинг помогает замечать паттерны и триггеры.",
            }
        ],
    }
    payload = build_writer_context_package_v1(
        memory_bundle=MemoryBundle(),
        context_package=None,
        retrieval_decision=decision,
        fresh_chat_context_policy={},
    )

    assert payload["rag_gate_decision"]["planned_composed_query"] == "нейросталкинг паттерны"
    assert payload["rag_gate_decision"]["retrieval_action"] == "query_kb"
    assert payload["writer_kb_payload_trace"]["input_rag_for_writer_count"] == 1
