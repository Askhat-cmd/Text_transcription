from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.trace_schema import attach_trace_schema_status, validate_trace_payload


def test_trace_payload_schema_valid_payload() -> None:
    payload = {
        "session_id": "u1",
        "turn_number": 2,
        "pipeline_stages": [{"name": "retrieval", "duration_ms": 10}],
        "llm_calls": [{"step": "answer"}],
        "tokens_total": 42,
        "recommended_mode": "PRESENCE",
        "resolved_route": "reflect",
        "output_validation": {"enabled": True},
    }
    valid, errors = validate_trace_payload(payload)
    assert valid is True
    assert errors == []


def test_trace_payload_schema_detects_missing_and_type_errors() -> None:
    payload = {
        "session_id": "u1",
        "turn_number": "2",
        "pipeline_stages": ["bad_stage"],
        "llm_calls": "bad_calls",
        "tokens_total": "42",
        "recommended_mode": None,
        "resolved_route": None,
        "output_validation": None,
    }
    valid, errors = validate_trace_payload(payload)
    assert valid is False
    assert "type:turn_number" in errors
    assert "type:llm_calls" in errors


def test_attach_trace_schema_status_writes_flags() -> None:
    payload = {
        "session_id": "u1",
        "turn_number": 1,
        "pipeline_stages": [],
        "llm_calls": [],
        "tokens_total": None,
        "recommended_mode": None,
        "resolved_route": None,
        "output_validation": None,
    }
    enriched = attach_trace_schema_status(payload)
    assert "trace_schema_valid" in enriched
    assert "trace_schema_errors" in enriched
