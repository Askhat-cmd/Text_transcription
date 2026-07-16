from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CallLLMSlice9RetrievalHumanLikeAndFinalShapeInputs:
    retrieval_decision_version: str
    retrieval_action: str
    retrieval_rag_candidates_count: int
    retrieval_rag_included_count: int
    retrieval_rag_included_reason: str
    retrieval_rag_suppressed_reason: str
    retrieval_writer_can_ignore_rag: str
    retrieval_rag_relevance: str
    retrieval_inherited_topic: str
    retrieval_inherited_offer_type: str
    human_like_enabled: str
    human_like_answer_style: str
    human_like_default_depth: str
    human_like_question_is_optional: str
    human_like_do_not_force_question: str
    human_like_do_not_force_practice: str
    human_like_flexible_length_allowed: str
    human_like_respect_user_requested_format: str
    human_like_repair_user_dissatisfaction: str
    human_like_direct_answer_repair: str
    human_like_support_answer_compactness: str
    human_like_preferred_shape: str
    human_like_target_length_chars: str
    human_like_avoid_mechanism_heavy_default: str
    human_like_prefer_direct_answer_first: str
    human_like_prefer_single_main_mechanism: str
    human_like_max_list_items: str
    final_answer_shape_profile: str
    final_answer_shape_profile_notes_block: str
    constraint_resolution_profile: str
    constraint_resolution_planner_authority: str
    constraint_resolution_overruled: str
    constraint_resolution_reason: str


def _extract_call_llm_slice9_retrieval_human_like_and_final_shape(
    ctx: dict[str, Any],
    *,
    human_like_answer_policy: dict[str, Any],
    repair_user_dissatisfaction: bool,
    constraint_resolution: dict[str, Any],
    dialogue_profile: str,
    overruled_constraints: list[str],
) -> CallLLMSlice9RetrievalHumanLikeAndFinalShapeInputs:
    return CallLLMSlice9RetrievalHumanLikeAndFinalShapeInputs(
        retrieval_decision_version=str(
            ctx.get("retrieval_decision_version", "contextual_retrieval_gating_v1")
            or "contextual_retrieval_gating_v1"
        ),
        retrieval_action=str(ctx.get("retrieval_action", "none") or "none"),
        retrieval_rag_candidates_count=int(
            ctx.get("retrieval_rag_candidates_count", 0) or 0
        ),
        retrieval_rag_included_count=int(
            ctx.get("retrieval_rag_included_count", 0) or 0
        ),
        retrieval_rag_included_reason=str(
            ctx.get("retrieval_rag_included_reason", "") or ""
        ),
        retrieval_rag_suppressed_reason=str(
            ctx.get("retrieval_rag_suppressed_reason", "") or ""
        ),
        retrieval_writer_can_ignore_rag=str(
            bool(ctx.get("retrieval_writer_can_ignore_rag", True))
        ).lower(),
        retrieval_rag_relevance=str(
            ctx.get("retrieval_rag_relevance", "unknown") or "unknown"
        ),
        retrieval_inherited_topic=str(ctx.get("retrieval_inherited_topic", "") or ""),
        retrieval_inherited_offer_type=str(
            ctx.get("retrieval_inherited_offer_type", "unknown") or "unknown"
        ),
        human_like_enabled=str(
            bool(human_like_answer_policy.get("enabled", False))
        ).lower(),
        human_like_answer_style=str(
            human_like_answer_policy.get("answer_style", "guided_compact")
            or "guided_compact"
        ),
        human_like_default_depth=str(
            human_like_answer_policy.get("default_depth", "short_to_medium")
            or "short_to_medium"
        ),
        human_like_question_is_optional=str(
            bool(human_like_answer_policy.get("question_is_optional", False))
        ).lower(),
        human_like_do_not_force_question=str(
            bool(human_like_answer_policy.get("do_not_force_question_at_end", False))
        ).lower(),
        human_like_do_not_force_practice=str(
            bool(human_like_answer_policy.get("do_not_force_practice_frame", False))
        ).lower(),
        human_like_flexible_length_allowed=str(
            bool(human_like_answer_policy.get("do_not_force_max_sentences", False))
        ).lower(),
        human_like_respect_user_requested_format=str(
            bool(human_like_answer_policy.get("respect_user_requested_format", False))
        ).lower(),
        human_like_repair_user_dissatisfaction=str(
            bool(repair_user_dissatisfaction)
        ).lower(),
        human_like_direct_answer_repair=str(
            bool(
                human_like_answer_policy.get(
                    "direct_answer_repair_when_user_complains", False
                )
            )
        ).lower(),
        human_like_support_answer_compactness=str(
            human_like_answer_policy.get("support_answer_compactness", "adaptive")
            or "adaptive"
        ),
        human_like_preferred_shape=str(
            human_like_answer_policy.get("preferred_shape", "adaptive")
            or "adaptive"
        ),
        human_like_target_length_chars=str(
            human_like_answer_policy.get("target_length_chars", "") or ""
        ),
        human_like_avoid_mechanism_heavy_default=str(
            bool(human_like_answer_policy.get("avoid_mechanism_heavy_default", False))
        ).lower(),
        human_like_prefer_direct_answer_first=str(
            bool(human_like_answer_policy.get("prefer_direct_answer_first", False))
        ).lower(),
        human_like_prefer_single_main_mechanism=str(
            bool(
                human_like_answer_policy.get(
                    "prefer_single_main_mechanism", False
                )
            )
        ).lower(),
        human_like_max_list_items=str(
            int(human_like_answer_policy.get("max_list_items", 0) or 0)
        ),
        final_answer_shape_profile=str(
            ctx.get("final_answer_shape_profile", "adaptive_current_pipeline")
            or "adaptive_current_pipeline"
        ),
        final_answer_shape_profile_notes_block=(
            "\n".join(
                f"- {str(item).strip()}"
                for item in list(ctx.get("final_answer_shape_profile_notes", []) or [])
                if str(item).strip()
            )
            or "- Follow the current answer obligation and stay direct."
        ),
        constraint_resolution_profile=str(
            constraint_resolution.get("profile", dialogue_profile) or dialogue_profile
        ),
        constraint_resolution_planner_authority=str(
            constraint_resolution.get("planner_authority", "guided") or "guided"
        ),
        constraint_resolution_overruled=", ".join(overruled_constraints) or "none",
        constraint_resolution_reason=str(
            constraint_resolution.get("overrule_reason", "none") or "none"
        ),
    )
