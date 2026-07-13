from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..writer_kb_payload import format_writer_kb_payload_for_prompt


@dataclass(frozen=True)
class CallLLMSlice3Inputs:
    writer_kb_payload_text: str
    last_debug_patch: dict[str, Any]


def _extract_call_llm_slice3_kb_payload_and_trace(
    ctx: dict[str, Any],
) -> CallLLMSlice3Inputs:
    writer_kb_payload_fallback_reason = str(
        ctx.get("writer_kb_payload_failure_reason", "")
        or (
            "writer_kb_payload_disabled"
            if not bool(ctx.get("writer_kb_payload_enabled", False))
            else "writer_kb_payload_empty_or_failed"
        )
    )
    if writer_kb_payload_fallback_reason == "builder_failure":
        writer_kb_payload_fallback_reason = "writer_kb_payload_empty_or_failed"
    writer_kb_payload_text = format_writer_kb_payload_for_prompt(
        payload=(
            dict(ctx.get("writer_kb_payload", {}))
            if isinstance(ctx.get("writer_kb_payload"), dict)
            else {}
        ),
        legacy_hits=list(ctx.get("semantic_hits", []) or []),
        fallback_reason=writer_kb_payload_fallback_reason,
    )
    last_debug_patch = {
        "writer_kb_payload_trace": (
            dict(ctx.get("writer_kb_payload_trace", {}))
            if isinstance(ctx.get("writer_kb_payload_trace"), dict)
            else {}
        ),
        "runtime_truth_trace_v1": (
            dict(ctx.get("runtime_truth_trace_v1", {}))
            if isinstance(ctx.get("runtime_truth_trace_v1"), dict)
            else {}
        ),
        "writer_kb_payload_future_graduation_notes": (
            dict(ctx.get("writer_kb_payload_future_graduation_notes", {}))
            if isinstance(ctx.get("writer_kb_payload_future_graduation_notes"), dict)
            else {}
        ),
        "semantic_cards_pilot": (
            dict(ctx.get("semantic_cards_pilot", {}))
            if isinstance(ctx.get("semantic_cards_pilot"), dict)
            else {}
        ),
        "writer_grounding_visibility_v1": (
            dict(ctx.get("writer_grounding_visibility_v1", {}))
            if isinstance(ctx.get("writer_grounding_visibility_v1"), dict)
            else {}
        ),
        "writer_kb_payload_enabled": bool(ctx.get("writer_kb_payload_enabled", False)),
        "writer_kb_payload_failed": bool(ctx.get("writer_kb_payload_failed", False)),
    }
    return CallLLMSlice3Inputs(
        writer_kb_payload_text=writer_kb_payload_text,
        last_debug_patch=last_debug_patch,
    )
