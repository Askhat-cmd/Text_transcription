from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.memory_v11 import build_snapshot_v11, compose_memory_context_v11


@dataclass
class _Turn:
    user_input: str
    bot_response: str


def test_context_continuity_between_sessions_uses_summary_plus_recent_window() -> None:
    previous_summary = "РџРѕР»СЊР·РѕРІР°С‚РµР»СЊ РёСЃСЃР»РµРґСѓРµС‚ РїР°С‚С‚РµСЂРЅ РёР·Р±РµРіР°РЅРёСЏ РѕС‚РІРµС‚СЃС‚РІРµРЅРЅРѕСЃС‚Рё."
    snapshot = build_snapshot_v11(
        diagnostics={
            "interaction_mode": "coaching",
            "nervous_system_state": "window",
            "request_function": "explore",
            "core_theme": "РёР·Р±РµРіР°РЅРёРµ РѕС‚РІРµС‚СЃС‚РІРµРЅРЅРѕСЃС‚Рё",
        },
        route="reflect",
        summary_staleness="fresh",
    )
    turns = [
        _Turn(user_input="СЏ СЃРЅРѕРІР° РѕС‚РєР»Р°РґС‹РІР°СЋ РІР°Р¶РЅС‹Рµ РґРµР»Р°", bot_response="РґР°РІР°Р№ СЂР°Р·Р±РµСЂРµРј С€Р°Рі Р·Р° С€Р°РіРѕРј"),
        _Turn(user_input="С…РѕС‡Сѓ РёР·РјРµРЅРёС‚СЊ СЌС‚Рѕ", bot_response="РІС‹РґРµР»РёРј РѕРґРёРЅ РЅРµР±РѕР»СЊС€РѕР№ С€Р°Рі"),
    ]
    bundle = compose_memory_context_v11(
        summary=previous_summary,
        summary_updated_at=4,
        total_turns=5,
        snapshot=snapshot,
        recent_turns=turns,
    )
    assert bundle.summary_used is True
    assert bundle.snapshot_used is False
    assert previous_summary in bundle.context_text
