from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from bot_agent.multiagent.overlay_shadow_trace import (
    OVERLAY_SHADOW_TRACE_VERSION,
    build_overlay_shadow_trace,
)


def _write_overlay(path: Path) -> None:
    payload = {
        "prd_id": "PRD-047.20",
        "batch_id": "batch_1",
        "evaluation_only": True,
        "human_final_approval": False,
        "summary": {"accepted_item_count": 2},
        "items": [
            {
                "candidate_id": "cand-1",
                "chunk_type": "mechanism",
                "risk_level": "medium",
                "source_ref": {
                    "heading_path": ["Контроль как защита"],
                    "content_preview": "FULL SOURCE SHOULD NOT LEAK",
                },
                "accepted_fields": {
                    "summary_candidate": "Контроль здесь может работать как попытка удержать безопасность.",
                    "core_thesis_candidate": "Когда страшно, контроль иногда становится способом защиты.",
                    "safe_user_translation_candidate": "Похоже, контроль сейчас нужен как защита от страха.",
                    "allowed_writer_use_candidate": "Только как мягкая гипотеза, а не как диагноз.",
                    "mechanism_hints_candidates": ["control_as_safety"],
                    "recommended_moves_candidates": ["translate_pattern_softly"],
                },
            },
            {
                "candidate_id": "cand-2",
                "chunk_type": "practice",
                "risk_level": "medium",
                "source_ref": {
                    "heading_path": ["Факт против интерпретации"],
                    "content_preview": "ANOTHER FULL SOURCE SHOULD NOT LEAK",
                },
                "accepted_fields": {
                    "summary_candidate": "Полезно отделять факт от истории о факте.",
                    "core_thesis_candidate": "Сначала назвать факт, потом проверить интерпретацию.",
                    "allowed_writer_use_candidate": "Только как один короткий следующий шаг по запросу.",
                    "recommended_moves_candidates": ["keep_one_practice_max"],
                },
            },
        ],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def test_overlay_shadow_trace_disabled_returns_default_off_payload(tmp_path: Path) -> None:
    overlay_path = tmp_path / "overlay.json"
    _write_overlay(overlay_path)

    trace = build_overlay_shadow_trace(
        user_message="мне страшно потерять контроль",
        retrieval_query="контроль страх",
        state_snapshot={"intent": "explore"},
        thread_state={"phase": "clarify"},
        overlay_file=str(overlay_path),
        enabled=False,
    )

    assert trace["schema_version"] == OVERLAY_SHADOW_TRACE_VERSION
    assert trace["enabled"] is False
    assert trace["reason"] == "disabled_by_config"
    assert trace["used_for_writer"] is False
    assert trace["used_for_retrieval_execution"] is False


def test_overlay_shadow_trace_missing_file_is_non_blocking_skip(tmp_path: Path) -> None:
    trace = build_overlay_shadow_trace(
        user_message="мне страшно потерять контроль",
        retrieval_query="контроль страх",
        state_snapshot={"intent": "explore"},
        thread_state={"phase": "clarify"},
        overlay_file=str(tmp_path / "missing.json"),
        enabled=True,
    )

    assert trace["enabled"] is True
    assert trace["status"] == "skipped"
    assert trace["reason"] == "overlay_file_missing"
    assert trace["would_help"] is False
    assert trace["used_for_writer"] is False


def test_overlay_shadow_trace_limits_matches_and_sanitizes_cards(tmp_path: Path) -> None:
    overlay_path = tmp_path / "overlay.json"
    _write_overlay(overlay_path)

    trace = build_overlay_shadow_trace(
        user_message="я боюсь и пытаюсь все контролировать",
        retrieval_query="контроль страх защита",
        state_snapshot={"intent": "explore", "nervous_state": "hyper"},
        thread_state={"phase": "clarify", "active_frame": {"active_concept": "страх"}},
        overlay_file=str(overlay_path),
        enabled=True,
        max_matches=1,
        min_score=0.0,
    )

    assert trace["status"] == "ok"
    assert trace["enabled"] is True
    assert trace["would_help"] is True
    assert trace["match_count"] == 1
    assert len(trace["matched_candidates"]) == 1
    top = trace["matched_candidates"][0]
    assert top["candidate_id"] == "cand-1"
    assert len(top["safe_user_translation_preview"]) <= 180
    assert len(top["allowed_writer_use_preview"]) <= 180
    assert len(top["summary_preview"]) <= 220
    rendered = json.dumps(trace, ensure_ascii=False)
    assert "FULL SOURCE SHOULD NOT LEAK" not in rendered
    assert top["trace_only"] is True
    assert trace["used_for_writer"] is False
    assert trace["used_for_retrieval_execution"] is False
