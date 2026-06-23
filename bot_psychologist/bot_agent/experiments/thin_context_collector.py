"""Thin context builder for PRD-047.28 experiment variants B and C."""

from __future__ import annotations

from typing import Any

from .thin_spine_cases import ExperimentCase


_MUST_NOT_TO_CONSTRAINT = {
    "use_internal_db": "Do not rely on internal DB or hidden knowledge.",
    "offer_breathing_as_only_solution": "Do not present breathing as the only solution.",
    "lecture": "Do not turn the answer into a lecture.",
    "forced_practice": "Do not force a practice.",
}


def collect_thin_context(
    *,
    case: ExperimentCase,
    recent_turn_count: int,
    include_kb: bool,
) -> dict[str, Any]:
    recent_messages = [dict(item) for item in case.recent_messages[-max(recent_turn_count, 0) :]]
    explicit_constraints = list(case.explicit_constraints)
    for item in case.expected_behavior.must_not:
        mapped = _MUST_NOT_TO_CONSTRAINT.get(item)
        if mapped and mapped not in explicit_constraints:
            explicit_constraints.append(mapped)
    if not case.expected_behavior.kb_allowed:
        no_kb_constraint = "Do not use internal DB or internal knowledge package for this answer."
        if no_kb_constraint not in explicit_constraints:
            explicit_constraints.append(no_kb_constraint)

    knowledge_package_present = bool(include_kb and case.expected_behavior.kb_allowed and case.knowledge_package)
    knowledge_package = [
        {
            "title": item.title,
            "content": item.content,
            "source": item.source,
        }
        for item in case.knowledge_package
    ] if knowledge_package_present else []

    return {
        "case_id": case.case_id,
        "group": case.group,
        "title": case.title,
        "current_user_message": case.current_user_message,
        "recent_messages": recent_messages,
        "recent_turn_count": len(recent_messages),
        "case_summary": case.case_summary,
        "quality_focus": list(case.quality_focus),
        "expected_behavior": {
            "must_answer_directly": case.expected_behavior.must_answer_directly,
            "kb_allowed": case.expected_behavior.kb_allowed,
            "practice_allowed": case.expected_behavior.practice_allowed,
            "must_not": list(case.expected_behavior.must_not),
            "preferred_mode": case.expected_behavior.preferred_mode,
        },
        "explicit_constraints": explicit_constraints,
        "knowledge_package": knowledge_package,
        "knowledge_package_present": knowledge_package_present,
        "knowledge_package_reason": (
            "included"
            if knowledge_package_present
            else ("user_or_case_forbids_kb" if not case.expected_behavior.kb_allowed else "no_fixture_knowledge")
        ),
    }
