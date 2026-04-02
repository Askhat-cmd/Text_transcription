from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.practice_selector import PracticeSelector


def test_practice_channel_rotation_prefers_alternative_channel(tmp_path: Path) -> None:
    db_path = tmp_path / "practices.json"
    payload = [
        {
            "id": "body_first",
            "title": "Тело 1",
            "channel": "body",
            "scientific_basis": "polyvagal",
            "triggers": ["practice"],
            "nervous_system_states": ["window"],
            "request_functions": ["directive"],
            "core_themes": ["прокрастинация"],
            "instruction": "i1",
            "micro_tuning": "m1",
            "closure": "c1",
            "time_limit_minutes": 5,
            "contraindications": [],
        },
        {
            "id": "action_alt",
            "title": "Действие",
            "channel": "action",
            "scientific_basis": "act",
            "triggers": ["practice"],
            "nervous_system_states": ["window"],
            "request_functions": ["directive"],
            "core_themes": ["прокрастинация"],
            "instruction": "i2",
            "micro_tuning": "m2",
            "closure": "c2",
            "time_limit_minutes": 5,
            "contraindications": [],
        },
    ]
    db_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    selector = PracticeSelector(db_path=db_path)
    selection = selector.select(
        route="practice",
        nervous_system_state="window",
        request_function="directive",
        core_theme="прокрастинация",
        last_practice_channel="body",
    )
    assert selection.primary is not None
    assert selection.primary.entry.channel == "action"

