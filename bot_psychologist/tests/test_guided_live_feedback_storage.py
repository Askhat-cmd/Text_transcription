from __future__ import annotations

import json
from pathlib import Path

from bot_agent.live_testing import feedback_capture as fc


def test_storage_saves_sanitized_session_without_raw_dialogue(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(fc, "LIVE_FEEDBACK_BASE_DIR", tmp_path / "live_feedback", raising=False)

    trace_summary = fc.build_trace_summary(
        debug_payload={
            "active_line": {"user_intent": "understand", "continuity_mode": "continue_existing_line"},
            "response_planner": {
                "next_move": "deepen_mechanism",
                "answer_shape": "mechanism_explanation",
                "response_depth": "short",
                "question_policy": "none",
                "practice_policy": "forbidden",
            },
            "planner_drift_guard": {"status": "ok", "severity": "none", "flags": []},
            "model_used": "gpt-5-mini",
            "writer_fallback_used": False,
        },
        user_message_preview="a" * 250,
        answer_preview="b" * 300,
        user_id="user-42",
    )
    record = fc.create_feedback_record(
        session_id="session-test",
        turn_id="turn-1",
        user_rating=4,
        comment="feedback",
        trace_summary=trace_summary,
    )
    payload = fc.append_feedback_record(record=record)

    assert payload["feedback_count"] == 1
    path = fc.get_session_storage_path("session-test")
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["feedback_count"] == 1

    raw = json.dumps(saved, ensure_ascii=False).lower()
    assert "raw_dialogue" not in raw
    assert "provider_payload" not in raw
    assert "api_key" not in raw

    entry = saved["records"][0]
    assert len(entry["trace_summary"]["user_message_preview"]) <= 180
    assert len(entry["trace_summary"]["answer_preview"]) <= 240


def test_trace_summary_extraction_shape() -> None:
    summary = fc.build_trace_summary(
        debug_payload={
            "active_line": {"user_intent": "x", "continuity_mode": "y"},
            "response_planner": {"next_move": "n", "answer_shape": "s"},
            "planner_drift_guard": {"status": "warning", "severity": "medium", "flags": ["q"]},
            "model_used": "m",
            "writer_fallback_used": True,
        },
    )

    assert summary["active_line"]["user_intent"] == "x"
    assert summary["response_planner"]["next_move"] == "n"
    assert summary["planner_drift_guard"]["status"] == "warning"
    assert summary["writer"]["fallback_used"] is True
