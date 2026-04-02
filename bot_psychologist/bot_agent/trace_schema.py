"""Trace payload schema checks for runtime observability (Phase 9)."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Tuple


REQUIRED_KEYS = {
    "session_id": str,
    "turn_number": int,
    "pipeline_stages": list,
    "llm_calls": list,
    "tokens_total": (int, type(None)),
    "recommended_mode": (str, type(None)),
    "resolved_route": (str, type(None)),
    "output_validation": (dict, type(None)),
}


def validate_trace_payload(payload: Mapping[str, Any]) -> Tuple[bool, List[str]]:
    errors: List[str] = []
    for key, expected_type in REQUIRED_KEYS.items():
        if key not in payload:
            errors.append(f"missing:{key}")
            continue
        if not isinstance(payload.get(key), expected_type):
            errors.append(f"type:{key}")

    stages = payload.get("pipeline_stages")
    if isinstance(stages, list):
        for idx, stage in enumerate(stages):
            if not isinstance(stage, Mapping):
                errors.append(f"pipeline_stages[{idx}]:not_object")
                continue
            if "name" not in stage:
                errors.append(f"pipeline_stages[{idx}].name:missing")
            if "duration_ms" in stage and not isinstance(stage.get("duration_ms"), int):
                errors.append(f"pipeline_stages[{idx}].duration_ms:type")

    llm_calls = payload.get("llm_calls")
    if isinstance(llm_calls, list):
        for idx, call in enumerate(llm_calls):
            if not isinstance(call, Mapping):
                errors.append(f"llm_calls[{idx}]:not_object")

    return len(errors) == 0, errors


def attach_trace_schema_status(payload: Dict[str, Any]) -> Dict[str, Any]:
    valid, errors = validate_trace_payload(payload)
    payload["trace_schema_valid"] = valid
    payload["trace_schema_errors"] = errors
    return payload
