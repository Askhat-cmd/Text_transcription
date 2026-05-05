from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from api.routes.common import _build_multiagent_metadata


def test_build_multiagent_metadata_keeps_runtime_thread_and_model_fields() -> None:
    raw = {
        "runtime": "multiagent",
        "runtime_entrypoint": "multiagent_adapter",
        "pipeline_version": "multiagent_v1",
        "thread_id": "th-1",
        "phase": "clarify",
        "response_mode": "reflect",
        "relation_to_thread": "new_thread",
        "continuity_score": 0.88,
        "model_used": "gpt-5-mini",
        "writer_api_mode": "responses",
        "state_analyzer_api_mode": "responses",
        "tokens_prompt": 10,
        "tokens_completion": 4,
        "tokens_total": 14,
        "estimated_cost_usd": 0.0001,
        "legacy_fallback_used": False,
    }

    metadata = _build_multiagent_metadata(raw, None)

    assert metadata["runtime"] == "multiagent"
    assert metadata["runtime_entrypoint"] == "multiagent_adapter"
    assert metadata["pipeline_version"] == "multiagent_v1"
    assert metadata["thread_id"] == "th-1"
    assert metadata["phase"] == "clarify"
    assert metadata["response_mode"] == "reflect"
    assert metadata["relation_to_thread"] == "new_thread"
    assert metadata["continuity_score"] == 0.88
    assert metadata["model_used"] == "gpt-5-mini"
    assert metadata["writer_api_mode"] == "responses"
    assert metadata["state_analyzer_api_mode"] == "responses"


def test_build_multiagent_metadata_drops_forbidden_legacy_keys() -> None:
    raw = {
        "runtime": "multiagent",
        "user_level": "advanced",
        "user_level_adapter_applied": True,
        "sd_level": "GREEN",
        "sd_secondary": ["x"],
        "sd_confidence": 0.9,
        "sd_method": "classifier",
        "sd_allowed_blocks": 3,
        "decision_rule_id": 10,
        "mode_reason": "legacy_rule",
        "confidence_level": "medium",
        "response_mode": "presence",
    }

    metadata = _build_multiagent_metadata(raw, None)

    for key in (
        "user_level",
        "user_level_adapter_applied",
        "sd_level",
        "sd_secondary",
        "sd_confidence",
        "sd_method",
        "sd_allowed_blocks",
        "decision_rule_id",
        "mode_reason",
        "confidence_level",
    ):
        assert key not in metadata


def test_build_multiagent_metadata_applies_defaults_and_debug_fallbacks() -> None:
    raw = {
        "response_mode": "presence",
    }
    debug = {
        "runtime_entrypoint": "multiagent_adapter",
        "pipeline_version": "multiagent_v1",
        "legacy_fallback_used": False,
        "direct_multiagent_cutover": True,
        "thread_id": "th-debug",
        "phase": "exploring",
        "model_used": "gpt-5-mini",
    }

    metadata = _build_multiagent_metadata(raw, debug)

    assert metadata["runtime"] == "multiagent"
    assert metadata["runtime_entrypoint"] == "multiagent_adapter"
    assert metadata["pipeline_version"] == "multiagent_v1"
    assert metadata["legacy_fallback_used"] is False
    assert metadata["direct_multiagent_cutover"] is True
    assert metadata["thread_id"] == "th-debug"
    assert metadata["phase"] == "exploring"
    assert metadata["model_used"] == "gpt-5-mini"


def test_build_multiagent_metadata_preserves_response_mode_and_syncs_recommended_mode() -> None:
    metadata = _build_multiagent_metadata(
        {
            "response_mode": "reflect",
        },
        None,
    )

    assert metadata["response_mode"] == "reflect"
    assert metadata["recommended_mode"] == "reflect"
