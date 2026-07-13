from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent.agents import writer_agent_call_llm_slice3 as slice3_module
from bot_agent.multiagent.writer_kb_payload import format_writer_kb_payload_for_prompt


def test_extract_call_llm_slice3_returns_writer_payload_text_and_debug_patch() -> None:
    ctx = {
        "writer_kb_payload_enabled": True,
        "writer_kb_payload_failed": False,
        "writer_kb_payload_failure_reason": "",
        "writer_kb_payload": {
            "selected_cards": [
                {
                    "card_id": "c1",
                    "title": "Нейросталкинг",
                    "source_doc_id": "doc-1",
                    "summary": "Наблюдение автоматических реакций.",
                }
            ]
        },
        "semantic_hits": [{"content": "legacy hit"}],
        "writer_kb_payload_trace": {"payload_chunk_count": 1},
        "runtime_truth_trace_v1": {"profile": "safe_guided"},
        "writer_kb_payload_future_graduation_notes": {"todo": "none"},
        "semantic_cards_pilot": {"selected_count": 1},
        "writer_grounding_visibility_v1": {"sent_to_writer": True},
    }

    result = slice3_module._extract_call_llm_slice3_kb_payload_and_trace(ctx)

    assert result.writer_kb_payload_text == format_writer_kb_payload_for_prompt(
        payload=ctx["writer_kb_payload"],
        legacy_hits=ctx["semantic_hits"],
        fallback_reason="writer_kb_payload_empty_or_failed",
    )
    assert result.last_debug_patch == {
        "writer_kb_payload_trace": {"payload_chunk_count": 1},
        "runtime_truth_trace_v1": {"profile": "safe_guided"},
        "writer_kb_payload_future_graduation_notes": {"todo": "none"},
        "semantic_cards_pilot": {"selected_count": 1},
        "writer_grounding_visibility_v1": {"sent_to_writer": True},
        "writer_kb_payload_enabled": True,
        "writer_kb_payload_failed": False,
    }


def test_extract_call_llm_slice3_normalizes_builder_failure_and_invalid_trace_shapes() -> None:
    ctx = {
        "writer_kb_payload_enabled": True,
        "writer_kb_payload_failed": True,
        "writer_kb_payload_failure_reason": "builder_failure",
        "writer_kb_payload": [],
        "semantic_hits": [],
        "writer_kb_payload_trace": "bad",
        "runtime_truth_trace_v1": None,
        "writer_kb_payload_future_graduation_notes": [],
        "semantic_cards_pilot": "bad",
        "writer_grounding_visibility_v1": 7,
    }

    result = slice3_module._extract_call_llm_slice3_kb_payload_and_trace(ctx)

    assert result.writer_kb_payload_text == format_writer_kb_payload_for_prompt(
        payload={},
        legacy_hits=[],
        fallback_reason="writer_kb_payload_empty_or_failed",
    )
    assert result.last_debug_patch == {
        "writer_kb_payload_trace": {},
        "runtime_truth_trace_v1": {},
        "writer_kb_payload_future_graduation_notes": {},
        "semantic_cards_pilot": {},
        "writer_grounding_visibility_v1": {},
        "writer_kb_payload_enabled": True,
        "writer_kb_payload_failed": True,
    }


def test_extract_call_llm_slice3_uses_disabled_fallback_reason() -> None:
    result = slice3_module._extract_call_llm_slice3_kb_payload_and_trace(
        {
            "writer_kb_payload_enabled": False,
            "writer_kb_payload_failed": False,
            "semantic_hits": [{"content": "legacy"}],
        }
    )

    assert result.writer_kb_payload_text == format_writer_kb_payload_for_prompt(
        payload={},
        legacy_hits=[{"content": "legacy"}],
        fallback_reason="writer_kb_payload_disabled",
    )
    assert list(result.last_debug_patch.keys()) == [
        "writer_kb_payload_trace",
        "runtime_truth_trace_v1",
        "writer_kb_payload_future_graduation_notes",
        "semantic_cards_pilot",
        "writer_grounding_visibility_v1",
        "writer_kb_payload_enabled",
        "writer_kb_payload_failed",
    ]
