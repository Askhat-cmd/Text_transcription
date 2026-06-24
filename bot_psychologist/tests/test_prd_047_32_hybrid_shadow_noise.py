from __future__ import annotations

from types import SimpleNamespace

import pytest

from bot_agent.multiagent.hybrid_retrieval_planner import build_hybrid_retrieval_plan_v1
from bot_agent.multiagent.runtime_trace_summary import build_runtime_trace_summary_v1


@pytest.mark.asyncio
async def test_invalid_shadow_planner_json_is_shadow_only(monkeypatch) -> None:
    import bot_agent.multiagent.hybrid_retrieval_planner as planner_module

    async def _invalid_completion(**_: object) -> SimpleNamespace:
        return SimpleNamespace(
            text="this is not json",
            tokens_prompt=10,
            tokens_completion=3,
            tokens_total=13,
        )

    monkeypatch.setattr(planner_module, "create_agent_completion", _invalid_completion)

    result = await build_hybrid_retrieval_plan_v1(
        user_message="На моем примере как это связано с контролем, но без длинной теории?",
        recent_turns_compact=[],
        last_assistant_offer={},
        thread_state_compact={},
        state_snapshot_compact={},
        dialogue_pragmatics={},
        fresh_chat_policy={},
        constraints=[],
        planner_mode="shadow",
        client=object(),
    )

    assert result["valid"] is False
    assert result["fallback_used"] is True
    assert result["error"] == "JSONDecodeError:invalid_json"
    assert result["planner_status"] == "shadow_invalid_json"
    assert result["fallback_scope"] == "shadow_only"
    assert result["owner_severity"] == "info"
    assert result["production_query_source"] == "current_turn_focus_v1"
    assert result["production_answer_affected"] is False
    assert "this is not json" not in result["error"]


def test_runtime_summary_reports_shadow_json_error_as_not_production_impacting() -> None:
    summary = build_runtime_trace_summary_v1(
        entrypoint="multiagent_adapter",
        final_answer_directive={
            "answer_obligation": "answer_concrete_situation",
            "must_answer": "current question",
        },
        writer_debug={
            "runtime_truth_trace_v1": {
                "trace_version": "runtime_truth_trace_v1",
                "writer_visible_payload_count": 0,
                "filtered_out_for_writer_count": 0,
                "writer_visible_payload_ids": [],
                "writer_visible_payload_types": [],
            },
            "writer_kb_payload_trace": {},
            "writer_grounding_visibility_v1": {},
        },
        overlay_shadow={},
        user_message="current question",
        dialogue_act_resolution={"dialogue_act": "support_request"},
        retrieval_decision={"retrieval_query_source": "current_turn_focus_v1"},
        hybrid_retrieval_plan={
            "mode": "shadow",
            "valid": False,
            "error": "JSONDecodeError:invalid_json",
            "fallback_used": True,
            "planner_status": "shadow_invalid_json",
            "fallback_scope": "shadow_only",
            "production_query_source": "current_turn_focus_v1",
            "production_answer_affected": False,
        },
    )

    truth = summary["runtime_truth_trace_v1"]

    assert summary["planner_shadow_status"] == "shadow_invalid_json"
    assert summary["planner_fallback_scope"] == "shadow_only"
    assert summary["planner_json_decode_error_affected_production_answer"] is False
    assert truth["planner_shadow_status"] == "shadow_invalid_json"
    assert truth["json_decode_error_affected_production_answer"] is False
    assert truth["production_query_source"] == "current_turn_focus_v1"
