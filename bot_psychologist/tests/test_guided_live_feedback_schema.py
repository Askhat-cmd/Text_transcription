from __future__ import annotations

from bot_agent.live_testing.feedback_capture import (
    LIVE_FEEDBACK_SCHEMA_VERSION,
    create_feedback_record,
)


def test_live_feedback_schema_fields_exist() -> None:
    record = create_feedback_record(
        session_id="Session 01",
        turn_id="Turn#1",
        scenario_id="gl_001",
        user_rating=4,
        comment="ok",
        trace_summary={"response_planner": {"next_move": "deepen_mechanism"}},
    )
    payload = record.to_dict()

    assert payload["schema_version"] == LIVE_FEEDBACK_SCHEMA_VERSION
    for key in (
        "session_id",
        "turn_id",
        "created_at_utc",
        "scenario_id",
        "user_rating",
        "felt_alive",
        "felt_understood",
        "felt_too_rigid",
        "felt_too_generic",
        "felt_too_long",
        "felt_too_short",
        "too_much_practice",
        "too_many_questions",
        "missed_context",
        "safety_concern",
        "comment",
        "trace_summary",
    ):
        assert key in payload


def test_invalid_rating_is_normalized() -> None:
    low = create_feedback_record(session_id="s", turn_id="t", user_rating=-4)
    high = create_feedback_record(session_id="s", turn_id="t", user_rating=99)
    bad = create_feedback_record(session_id="s", turn_id="t", user_rating="bad")

    assert low.user_rating == 1
    assert high.user_rating == 5
    assert bad.user_rating is None


def test_session_id_and_turn_id_are_sanitized() -> None:
    record = create_feedback_record(session_id=" Live Session !! ", turn_id="Turn 1 ???")
    assert record.session_id == "live_session"
    assert record.turn_id == "turn_1"
