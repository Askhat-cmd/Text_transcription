from __future__ import annotations

from bot_agent.experiments.live_turn_note import build_live_turn_note


def test_live_turn_note_is_natural_language_not_json_contract() -> None:
    note = build_live_turn_note(
        {
            "current_user_message": "Ты слишком сложно объяснил, скажи проще и не давай практику.",
            "explicit_constraints": ["Не читать лекцию.", "Не предлагать практику."],
        }
    )

    assert note
    assert not note.startswith("{")
    assert not note.startswith("[")
    assert "lecture" in note.lower() or "simpl" in note.lower()
    assert "practice" in note.lower()


def test_live_turn_note_mentions_no_internal_db_when_requested() -> None:
    note = build_live_turn_note(
        {
            "current_user_message": "Ответь не опираясь на внутреннюю БД.",
            "explicit_constraints": ["Не использовать внутреннюю БД."],
        }
    )

    assert "internal db" in note.lower()
