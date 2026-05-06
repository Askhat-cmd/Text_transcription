from __future__ import annotations

import json
from pathlib import Path


DATASET_PATH = Path(__file__).resolve().parent / "quality_baseline_cases.json"

REQUIRED_CATEGORIES = {
    "contact",
    "clarify",
    "vent",
    "solution",
    "open_explore",
    "defensive",
    "collapsed_or_low_resource",
    "I-W+",
    "I+W-",
    "I-W-",
    "continuity",
    "thread_switch",
    "memory_relevance",
    "too_generic_risk",
    "practice_step",
}


def _load_cases() -> list[dict]:
    assert DATASET_PATH.exists(), f"Dataset not found: {DATASET_PATH}"
    data = json.loads(DATASET_PATH.read_text(encoding="utf-8-sig"))
    assert isinstance(data, list), "Dataset root must be a JSON list"
    return data


def test_dataset_schema_and_coverage() -> None:
    cases = _load_cases()
    assert 20 <= len(cases) <= 30, "Dataset must contain 20-30 cases"

    ids: list[str] = []
    categories: set[str] = set()
    single_turn = 0
    multi_turn = 0
    defensive = 0
    concrete_step_cases = 0
    no_new_framework_cases = 0
    continuity_priority_cases = 0
    safety_adjacent_non_crisis = 0
    explicit_crisis = 0

    for case in cases:
        assert isinstance(case, dict), "Each case must be an object"
        for key in ("id", "title", "category", "user_turns", "expected"):
            assert key in case, f"Missing key `{key}` in case: {case}"

        case_id = case["id"]
        title = case["title"]
        category = case["category"]
        turns = case["user_turns"]
        expected = case["expected"]

        assert isinstance(case_id, str) and case_id.strip(), "Case id must be non-empty string"
        assert isinstance(title, str) and title.strip(), f"Case `{case_id}` title must be non-empty"
        assert isinstance(category, str) and category.strip(), f"Case `{case_id}` category must be non-empty"
        assert isinstance(turns, list) and turns, f"Case `{case_id}` user_turns must be non-empty list"
        assert all(isinstance(turn, str) and turn.strip() for turn in turns), (
            f"Case `{case_id}` turns must contain non-empty strings"
        )
        assert isinstance(expected, dict), f"Case `{case_id}` expected must be object"
        assert "should" in expected and isinstance(expected["should"], list), (
            f"Case `{case_id}` expected.should must be list"
        )
        assert "should_not" in expected and isinstance(expected["should_not"], list), (
            f"Case `{case_id}` expected.should_not must be list"
        )

        ids.append(case_id)
        categories.add(category)

        if len(turns) == 1:
            single_turn += 1
        else:
            multi_turn += 1

        if category == "defensive":
            defensive += 1

        joined_should = " ".join(item.lower() for item in expected["should"] if isinstance(item, str))
        joined_should_not = " ".join(
            item.lower() for item in expected["should_not"] if isinstance(item, str)
        )
        title_lower = str(title).lower()
        turns_text = " ".join(turns).lower()

        if "micro-step" in joined_should or "concrete" in joined_should or "шаг" in turns_text:
            concrete_step_cases += 1

        if "introduce new framework" in joined_should_not:
            no_new_framework_cases += 1

        if category == "continuity" or "continuity" in [
            str(item).lower() for item in expected.get("quality_focus", [])
        ]:
            continuity_priority_cases += 1

        quality_focus = [str(item).lower() for item in expected.get("quality_focus", [])]
        has_safety_signal = (
            "safety" in joined_should
            or any("safety" in item for item in quality_focus)
        )
        if has_safety_signal and "crisis" not in title_lower:
            safety_adjacent_non_crisis += 1

        if "crisis" in title_lower:
            explicit_crisis += 1

    assert len(ids) == len(set(ids)), "Case IDs must be unique"
    assert REQUIRED_CATEGORIES.issubset(categories), (
        f"Missing required categories: {sorted(REQUIRED_CATEGORIES - categories)}"
    )

    assert single_turn >= 5, "Need at least 5 single-turn cases"
    assert multi_turn >= 8, "Need at least 8 multi-turn cases"
    assert defensive >= 3, "Need at least 3 defensive cases"
    assert concrete_step_cases >= 3, "Need at least 3 concrete-step cases"
    assert no_new_framework_cases >= 3, "Need at least 3 no-new-framework cases"
    assert continuity_priority_cases >= 3, "Need at least 3 continuity-priority cases"
    assert safety_adjacent_non_crisis >= 2, "Need at least 2 safety-adjacent non-crisis cases"
    assert explicit_crisis >= 1, "Need at least 1 explicit crisis case"
