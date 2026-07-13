from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CallLLMSlice6FinalAnswerDirectiveAndLegacyInputs:
    final_answer_directive_json: str
    writer_visible_final_answer_directive_json: str
    final_answer_directive_version: str
    final_answer_current_user_request: str
    final_answer_must_answer_source: str
    final_answer_previous_must_answer_demoted: str
    final_answer_previous_must_answer: str
    final_answer_explicit_continue_previous_detected: str
    final_answer_answer_target: str
    final_answer_writer_contact_mode: str
    final_answer_diagnostic_center_role: str
    final_answer_planner_role: str
    final_answer_active_line_role: str
    final_answer_diagnostic_card_role: str
    writer_first_prompt_assembly_enabled: str
    legacy_blocks_visible_to_writer: str
    legacy_blocks_source_signals_only: str
    legacy_constraints_suppressed_csv: str
    writer_visible_advisory_summary: str
    writer_visible_practice_note: str
    writer_grounding_authority_note: str
    writer_grounding_visibility_json: str


def _extract_call_llm_slice6_final_answer_directive_and_legacy(
    ctx: dict[str, Any],
) -> CallLLMSlice6FinalAnswerDirectiveAndLegacyInputs:
    return CallLLMSlice6FinalAnswerDirectiveAndLegacyInputs(
        final_answer_directive_json=str(
            ctx.get("final_answer_directive_json", "{}") or "{}"
        ),
        writer_visible_final_answer_directive_json=str(
            ctx.get("writer_visible_final_answer_directive_json", "{}") or "{}"
        ),
        final_answer_directive_version=str(
            ctx.get("final_answer_directive_version", "final_answer_directive_v1")
            or "final_answer_directive_v1"
        ),
        final_answer_current_user_request=str(
            ctx.get("final_answer_current_user_request", "") or ""
        ),
        final_answer_must_answer_source=str(
            ctx.get("final_answer_must_answer_source", "latest_turn") or "latest_turn"
        ),
        final_answer_previous_must_answer_demoted=str(
            bool(ctx.get("final_answer_previous_must_answer_demoted", False))
        ).lower(),
        final_answer_previous_must_answer=str(
            ctx.get("final_answer_previous_must_answer", "") or "none"
        ),
        final_answer_explicit_continue_previous_detected=str(
            bool(ctx.get("final_answer_explicit_continue_previous_detected", False))
        ).lower(),
        final_answer_answer_target=str(
            ctx.get("final_answer_answer_target", "latest_turn") or "latest_turn"
        ),
        final_answer_writer_contact_mode=str(
            ctx.get("final_answer_writer_contact_mode", "structured_answer")
            or "structured_answer"
        ),
        final_answer_diagnostic_center_role=str(
            ctx.get("final_answer_diagnostic_center_role", "guided_legacy")
            or "guided_legacy"
        ),
        final_answer_planner_role=str(
            ctx.get("final_answer_planner_role", "guided_legacy") or "guided_legacy"
        ),
        final_answer_active_line_role=str(
            ctx.get("final_answer_active_line_role", "guided_legacy")
            or "guided_legacy"
        ),
        final_answer_diagnostic_card_role=str(
            ctx.get("final_answer_diagnostic_card_role", "guided_legacy")
            or "guided_legacy"
        ),
        writer_first_prompt_assembly_enabled=str(
            bool(ctx.get("writer_first_prompt_assembly_enabled", False))
        ).lower(),
        legacy_blocks_visible_to_writer=str(
            bool(ctx.get("legacy_blocks_visible_to_writer", True))
        ).lower(),
        legacy_blocks_source_signals_only=str(
            bool(ctx.get("legacy_blocks_source_signals_only", False))
        ).lower(),
        legacy_constraints_suppressed_csv=str(
            ctx.get("legacy_constraints_suppressed_csv", "none") or "none"
        ),
        writer_visible_advisory_summary=str(
            ctx.get("writer_visible_advisory_summary", "") or "нет"
        ),
        writer_visible_practice_note=str(
            ctx.get("writer_visible_practice_note", "") or "нет"
        ),
        writer_grounding_authority_note=str(
            ctx.get("writer_grounding_authority_note", "") or "none"
        ),
        writer_grounding_visibility_json=str(
            ctx.get("writer_grounding_visibility_json", "{}") or "{}"
        ),
    )
