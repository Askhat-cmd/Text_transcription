"""Answer obligation resolver for unified dialogue policy."""

from __future__ import annotations

from typing import Any

from .dialogue_policy import resolve_profile_preset


ANSWER_OBLIGATION_RESOLVER_VERSION = "answer_obligation_resolver_v1"


def build_answer_obligation_resolver_v1(
    *,
    dialogue_act_resolution: dict[str, Any] | None,
    last_assistant_offer: dict[str, Any] | None,
    unanswered_question_state: dict[str, Any] | None,
    dialogue_style_state: dict[str, Any] | None,
    dialogue_policy: dict[str, Any] | None,
) -> dict[str, Any]:
    act = str((dialogue_act_resolution or {}).get("dialogue_act", "unknown") or "unknown")
    last_offer = dict(last_assistant_offer or {})
    unanswered = dict(unanswered_question_state or {})
    style = dict(dialogue_style_state or {})
    policy = dict(dialogue_policy or {})
    profile_preset = str(policy.get("profile_preset") or resolve_profile_preset(policy.get("profile")))

    tone = str(style.get("tone", "neutral") or "neutral")
    length_preference = str(style.get("length_preference", "adaptive") or "adaptive")
    avoid = [str(item) for item in list(style.get("avoid", []) or []) if str(item).strip()]

    style_overrides = {
        "tone": tone,
        "length_preference": length_preference,
        "complexity_preference": str(style.get("complexity_preference", "normal") or "normal"),
        "avoid": avoid,
        "avoid_overexplaining": "overexplaining" in avoid,
        "avoid_unrequested_practice": "unrequested_practice" in avoid,
    }
    depth = "medium"
    if length_preference == "short":
        depth = "short"
    elif length_preference == "detailed":
        depth = "long"
    elif profile_preset == "safe_guided":
        depth = "short"

    if act == "repair_complaint":
        if unanswered.get("answer_required") and str(unanswered.get("last_direct_user_question", "") or "").strip():
            return {
                "version": ANSWER_OBLIGATION_RESOLVER_VERSION,
                "answer_obligation": "repair_and_answer_last_question",
                "answer_shape": "direct_repair_then_answer",
                "question_policy": "optional_none",
                "depth": "medium" if depth == "short" else depth,
                "style_overrides": style_overrides,
                "source": [
                    "dialogue_act=repair_complaint",
                    "unanswered_question_state=pending",
                    f"profile_preset={profile_preset}",
                ],
            }
        return {
            "version": ANSWER_OBLIGATION_RESOLVER_VERSION,
            "answer_obligation": "repair_ask_to_repeat_briefly",
            "answer_shape": "brief_repair_then_repeat_request",
            "question_policy": "single_if_needed",
            "depth": "short",
            "style_overrides": style_overrides,
            "source": [
                "dialogue_act=repair_complaint",
                "unanswered_question_state=missing",
                f"profile_preset={profile_preset}",
            ],
        }

    if act == "summary_request":
        return {
            "version": ANSWER_OBLIGATION_RESOLVER_VERSION,
            "dialogue_act": "summary_request",
            "answer_required": True,
            "answer_obligation": "summarize_current_conversation",
            "answer_shape": "structured_summary",
            "question_policy": "none",
            "practice_policy": "forbidden",
            "depth": depth if depth != "short" else "medium",
            "must_answer": "summary of current conversation",
            "must_not": [
                "ask whether the user wants a summary",
                "answer the previous assistant offer instead of summarizing",
                "add a practice unless the user explicitly asked for one",
            ],
            "writer_should": [
                "summarize the current conversation in the Writer's own words",
                "use available current conversation context as source",
                "keep planner and diagnostic content advisory only",
            ],
            "summary_request": True,
            "summary_scope": "current_conversation",
            "should_not_confirm_last_offer": True,
            "no_confirmation_needed": True,
            "no_practice_unless_requested": True,
            "style_overrides": style_overrides,
            "source": [
                "dialogue_act=summary_request",
                "explicit_user_request=summary",
                f"profile_preset={profile_preset}",
            ],
        }

    if act == "confirmation_to_last_offer" and bool(last_offer.get("is_open")):
        offer_type = str(last_offer.get("offer_type", "none") or "none")
        shape = "structured_explanation"
        if offer_type == "practice":
            shape = "one_step"
        elif offer_type == "summarize":
            shape = "structured_summary"
        elif offer_type in {"shorten", "expand"}:
            shape = "format_followup"
        return {
            "version": ANSWER_OBLIGATION_RESOLVER_VERSION,
            "answer_obligation": "answer_last_offer",
            "answer_shape": shape,
            "question_policy": "optional_none",
            "depth": "medium" if offer_type != "shorten" else "short",
            "style_overrides": style_overrides,
            "source": [
                "dialogue_act=confirmation_to_last_offer",
                "last_assistant_offer.is_open=true",
                f"profile_preset={profile_preset}",
            ],
        }

    if act == "close_ack":
        return {
            "version": ANSWER_OBLIGATION_RESOLVER_VERSION,
            "answer_obligation": "close_gently",
            "answer_shape": "gentle_close",
            "question_policy": "none",
            "depth": "short",
            "style_overrides": style_overrides,
            "source": ["dialogue_act=close_ack", f"profile_preset={profile_preset}"],
        }

    if act == "self_intro":
        return {
            "version": ANSWER_OBLIGATION_RESOLVER_VERSION,
            "answer_obligation": "acknowledge_self_intro",
            "answer_shape": "short_contact",
            "question_policy": "optional_none",
            "depth": "short",
            "style_overrides": style_overrides,
            "source": ["dialogue_act=self_intro", f"profile_preset={profile_preset}"],
        }

    if act == "knowledge_question":
        return {
            "version": ANSWER_OBLIGATION_RESOLVER_VERSION,
            "answer_obligation": "answer_knowledge_question",
            "answer_shape": "structured_explanation",
            "question_policy": "optional_none",
            "depth": depth if depth != "short" else "medium",
            "reason": "knowledge_question_requires_direct_answer",
            "confidence": "high",
            "style_overrides": style_overrides,
            "source": ["dialogue_act=knowledge_question", f"profile_preset={profile_preset}"],
        }

    if act == "practice_request":
        return {
            "version": ANSWER_OBLIGATION_RESOLVER_VERSION,
            "answer_obligation": "provide_one_bounded_practice",
            "answer_shape": "one_short_practice",
            "question_policy": "none",
            "practice_policy": "allowed_explicit_request",
            "depth": "short",
            "reason": "explicit_practice_request_requires_single_bounded_practice",
            "confidence": "high",
            "style_overrides": style_overrides,
            "source": ["dialogue_act=practice_request", "explicit_user_request=practice", f"profile_preset={profile_preset}"],
        }

    if act == "concrete_situation_question":
        return {
            "version": ANSWER_OBLIGATION_RESOLVER_VERSION,
            "answer_obligation": "answer_concrete_situation",
            "answer_shape": "contextual_explanation",
            "question_policy": "optional_none",
            "depth": depth if depth != "short" else "medium",
            "reason": "concrete_situation_requires_contextual_answer",
            "confidence": "high",
            "style_overrides": style_overrides,
            "source": ["dialogue_act=concrete_situation_question", f"profile_preset={profile_preset}"],
        }

    if act == "direct_question":
        return {
            "version": ANSWER_OBLIGATION_RESOLVER_VERSION,
            "answer_obligation": "answer_direct_question",
            "answer_shape": "direct_answer",
            "question_policy": "optional_none",
            "depth": depth,
            "reason": "direct_question_requires_direct_answer",
            "confidence": "high",
            "style_overrides": style_overrides,
            "source": ["dialogue_act=direct_question", f"profile_preset={profile_preset}"],
        }

    if act in {"greeting", "contact_open"}:
        return {
            "version": ANSWER_OBLIGATION_RESOLVER_VERSION,
            "answer_obligation": "continue_thread",
            "answer_shape": "simple_contact",
            "question_policy": "optional_none",
            "depth": "short",
            "style_overrides": style_overrides,
            "source": [f"dialogue_act={act}", f"profile_preset={profile_preset}"],
        }

    if act == "continuation_request":
        return {
            "version": ANSWER_OBLIGATION_RESOLVER_VERSION,
            "answer_obligation": "continue_thread",
            "answer_shape": "structured_explanation",
            "question_policy": "optional_none",
            "depth": depth,
            "style_overrides": style_overrides,
            "source": ["dialogue_act=continuation_request", f"profile_preset={profile_preset}"],
        }

    return {
        "version": ANSWER_OBLIGATION_RESOLVER_VERSION,
        "answer_obligation": "continue_thread",
        "answer_shape": "structured_explanation",
        "question_policy": "optional_none",
        "depth": depth,
        "style_overrides": style_overrides,
        "source": ["dialogue_act=fallback_unknown", f"profile_preset={profile_preset}"],
    }


__all__ = ["ANSWER_OBLIGATION_RESOLVER_VERSION", "build_answer_obligation_resolver_v1"]
