from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CallLLMSlice5KbPayloadAndPhilosophyInputs:
    writer_kb_payload_enabled: str
    writer_kb_payload_trace_version: str
    writer_kb_payload_failed: str
    knowledge_answer_needed: str
    knowledge_answer_concept: str
    knowledge_answer_kb_grounding: str
    knowledge_answer_first: str
    do_not_ask_user_to_define_term_before_answering: str
    practice_allowed: str
    knowledge_answer_writer_instruction: str
    philosophy_kernel_version: str
    philosophy_kernel_quote_policy: str
    philosophy_kernel_selected_lenses: str
    philosophy_kernel_prompt_block: str
    philosophy_kernel_prompt_compactness: str
    writer_freedom_prompt_block: str
    writer_freedom_contract_version: str
    writer_freedom_level: str
    writer_mode_hint: str
    mode_is_hint_not_cage: str
    writer_question_limit: int
    practice_requires_gate: str
    writer_freedom_hard_boundaries: str


def _extract_call_llm_slice5_kb_payload_and_philosophy(
    ctx: dict[str, Any],
    knowledge_answer: dict[str, Any],
    knowledge_answer_first: bool,
    do_not_ask_definition: bool,
    practice_allowed: bool,
    philosophy_kernel: dict[str, Any],
    writer_freedom_contract: dict[str, Any],
    selected_lenses: list[str],
    freedom_hard_boundaries: list[str],
) -> CallLLMSlice5KbPayloadAndPhilosophyInputs:
    return CallLLMSlice5KbPayloadAndPhilosophyInputs(
        writer_kb_payload_enabled=str(
            bool(ctx.get("writer_kb_payload_enabled", False))
        ).lower(),
        writer_kb_payload_trace_version=str(
            ctx.get("writer_kb_payload_trace_version", "writer_kb_payload_trace_v1")
            or "writer_kb_payload_trace_v1"
        ),
        writer_kb_payload_failed=str(
            bool(ctx.get("writer_kb_payload_failed", False))
        ).lower(),
        knowledge_answer_needed=str(
            bool(knowledge_answer.get("needed", False))
        ).lower(),
        knowledge_answer_concept=str(knowledge_answer.get("concept", "") or "none"),
        knowledge_answer_kb_grounding=str(
            bool(knowledge_answer.get("kb_grounding_available", False))
        ).lower(),
        knowledge_answer_first=str(knowledge_answer_first).lower(),
        do_not_ask_user_to_define_term_before_answering=str(
            do_not_ask_definition
        ).lower(),
        practice_allowed=str(practice_allowed).lower(),
        knowledge_answer_writer_instruction=str(
            knowledge_answer.get("writer_instruction", "none") or "none"
        ),
        philosophy_kernel_version=str(
            ctx.get(
                "philosophy_kernel_version",
                philosophy_kernel.get("kernel_version", ""),
            )
        ),
        philosophy_kernel_quote_policy=str(
            ctx.get(
                "philosophy_kernel_quote_policy",
                philosophy_kernel.get("quote_policy", "internal_lens_not_citation"),
            )
        ),
        philosophy_kernel_selected_lenses=", ".join(selected_lenses) or "none",
        philosophy_kernel_prompt_block=str(
            ctx.get("philosophy_kernel_prompt_block", "") or "none"
        ),
        philosophy_kernel_prompt_compactness=str(
            ctx.get("philosophy_kernel_prompt_compactness", {}) or {}
        ),
        writer_freedom_prompt_block=str(
            ctx.get("writer_freedom_prompt_block", "") or "none"
        ),
        writer_freedom_contract_version=str(
            ctx.get(
                "writer_freedom_contract_version",
                writer_freedom_contract.get("version", ""),
            )
        ),
        writer_freedom_level=str(
            ctx.get(
                "writer_freedom_level",
                writer_freedom_contract.get("freedom_level", "guided"),
            )
        ),
        writer_mode_hint=str(
            ctx.get("writer_mode_hint", writer_freedom_contract.get("mode_hint", ""))
        ),
        mode_is_hint_not_cage=str(
            bool(ctx.get("mode_is_hint_not_cage", True))
        ).lower(),
        writer_question_limit=int(ctx.get("writer_question_limit", 1) or 1),
        practice_requires_gate=str(
            bool(ctx.get("practice_requires_gate", True))
        ).lower(),
        writer_freedom_hard_boundaries=", ".join(freedom_hard_boundaries)
        or "no_diagnosis,no_unsolicited_practice",
    )
