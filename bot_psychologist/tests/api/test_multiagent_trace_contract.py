from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from api.routes.common import (
    _build_multiagent_trace_storage_payload,
    _normalize_semantic_hits_detail_for_debug_trace_compat,
)


def test_multiagent_trace_storage_payload_sets_multiagent_contract_version() -> None:
    payload = _build_multiagent_trace_storage_payload({"tokens_total": 42})
    assert payload["trace_contract_version"] == "multiagent_v1"


def test_multiagent_trace_storage_payload_drops_forbidden_legacy_trace_keys() -> None:
    payload = _build_multiagent_trace_storage_payload(
        {
            "sd_classification": "safe",
            "sd_detail": "x",
            "sd_level": "GREEN",
            "user_level": "advanced",
            "decision_rule_id": "10",
            "mode_reason": "legacy_rule",
            "confidence_level": "medium",
            "informational_mode": True,
            "applied_mode_prompt": "legacy",
            "tokens_total": 7,
        }
    )

    for key in (
        "sd_classification",
        "sd_detail",
        "sd_level",
        "user_level",
        "decision_rule_id",
        "mode_reason",
        "confidence_level",
        "informational_mode",
        "applied_mode_prompt",
    ):
        assert key not in payload

    assert payload["tokens_total"] == 7


def test_multiagent_trace_storage_payload_keeps_tokens_and_turn_diff() -> None:
    turn_diff = {
        "route_changed": True,
        "state_changed": False,
        "config_changed_keys": ["pipeline_mode"],
        "memory_delta": {
            "turns_added": 1,
            "summary_changed": False,
            "semantic_hits_delta": 0,
        },
    }
    payload = _build_multiagent_trace_storage_payload(
        {
            "tokens_prompt": 10,
            "tokens_completion": 5,
            "tokens_total": 15,
            "turn_diff": turn_diff,
        }
    )

    assert payload["tokens_prompt"] == 10
    assert payload["tokens_completion"] == 5
    assert payload["tokens_total"] == 15
    assert payload["turn_diff"] == turn_diff


def test_semantic_hits_compat_normalization_supports_multiagent_input() -> None:
    raw = [
        {
            "chunk_id": "c1",
            "source": "doc",
            "score": 0.77,
            "content_preview": "preview",
            "content_full": "full",
        }
    ]
    normalized = _normalize_semantic_hits_detail_for_debug_trace_compat(raw)

    assert normalized == [
        {
            "block_id": "c1",
            "score": 0.77,
            "text_preview": "preview",
            "source": "doc",
        }
    ]
