from __future__ import annotations

import sys
from pathlib import Path


CURRENT_FILE = Path(__file__).resolve()
BOT_PSYCHOLOGIST_ROOT = CURRENT_FILE.parents[1]
if str(BOT_PSYCHOLOGIST_ROOT) not in sys.path:
    sys.path.insert(0, str(BOT_PSYCHOLOGIST_ROOT))

from tools import prd_047_36_owner_pilot_readiness_gate_lib as gate


def test_payload_excerpt_integrity_detects_match_inside_excerpt() -> None:
    records = gate.build_payload_excerpt_integrity_records(
        scenario_id="S5",
        user_message="Что такое анестетическая депрессия?",
        payload_chunks=[
            {
                "chunk_id": "c1",
                "content_excerpt": "Анестетическая депрессия — это внутренняя эмоциональная анестезия.",
                "content_truncated": True,
                "original_char_count": 900,
                "sent_char_count": 120,
                "truncation_reason": "excerpt_budget",
            }
        ],
        source_trace={"focus_terms": ["анестетическая", "депрессия"]},
    )
    payload = records[0]["payload_excerpt_integrity_v1"]
    assert payload["matched_span_in_excerpt"] is True
    assert payload["blocker"] is False


def test_payload_excerpt_integrity_flags_cut_off_match() -> None:
    records = gate.build_payload_excerpt_integrity_records(
        scenario_id="S5",
        user_message="Что такое анестетическая депрессия?",
        payload_chunks=[
            {
                "chunk_id": "c2",
                "content_excerpt": "Это состояние внутренней пустоты без ключевого термина.",
                "content_truncated": True,
                "original_char_count": 900,
                "sent_char_count": 90,
                "truncation_reason": "excerpt_budget",
            }
        ],
        source_trace={"focus_terms": ["анестетическая", "депрессия"]},
    )
    payload = records[0]["payload_excerpt_integrity_v1"]
    assert payload["matched_span_in_excerpt"] is False
    assert payload["blocker"] is True
    assert payload["blocker_reason"] == "matched_span_cut_off"

