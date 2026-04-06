from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.practice_selector import PracticeSelector


def _write_db(path: Path, payload: list[dict]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def test_practice_selector_filters_by_state_and_request(tmp_path: Path) -> None:
    db_path = tmp_path / "practices.json"
    _write_db(
        db_path,
        [
            {
                "id": "body_hyper",
                "title": "Дыхание",
                "channel": "body",
                "scientific_basis": "polyvagal",
                "triggers": ["regulate"],
                "nervous_system_states": ["hyper"],
                "request_functions": ["discharge"],
                "core_themes": ["тревога"],
                "instruction": "Инструкция",
                "micro_tuning": "Тюнинг",
                "closure": "Закрытие",
                "time_limit_minutes": 2,
                "contraindications": [],
            },
            {
                "id": "thinking_window",
                "title": "Карта мысли",
                "channel": "thinking",
                "scientific_basis": "act",
                "triggers": ["reflect"],
                "nervous_system_states": ["window"],
                "request_functions": ["understand"],
                "core_themes": ["избегание"],
                "instruction": "Инструкция",
                "micro_tuning": "Тюнинг",
                "closure": "Закрытие",
                "time_limit_minutes": 5,
                "contraindications": [],
            },
        ],
    )
    selector = PracticeSelector(db_path=db_path)
    selection = selector.select(
        route="regulate",
        nervous_system_state="hyper",
        request_function="discharge",
        core_theme="сильная тревога",
    )
    assert selection.primary is not None
    assert selection.primary.entry.id == "body_hyper"


def test_practice_selector_respects_contraindications(tmp_path: Path) -> None:
    db_path = tmp_path / "practices.json"
    _write_db(
        db_path,
        [
            {
                "id": "unsafe",
                "title": "Опасная",
                "channel": "action",
                "scientific_basis": "none",
                "triggers": ["practice"],
                "nervous_system_states": ["window"],
                "request_functions": ["solution"],
                "core_themes": ["кризис"],
                "instruction": "Инструкция",
                "micro_tuning": "Тюнинг",
                "closure": "Закрытие",
                "time_limit_minutes": 5,
                "contraindications": ["acute_self_harm_plan"],
            }
        ],
    )
    selector = PracticeSelector(db_path=db_path)
    selection = selector.select(
        route="practice",
        nervous_system_state="window",
        request_function="solution",
        core_theme="кризис",
        safety_flags=["acute_self_harm_plan"],
    )
    assert selection.primary is None
