from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


DATASET_PATH = Path(__file__).resolve().parents[2] / "tests" / "calibration" / "state_analyzer_calibration_cases.json"

VALID_NERVOUS = {"window", "hyper", "hypo"}
VALID_INTENT = {"clarify", "vent", "explore", "contact", "solution"}
VALID_OPENNESS = {"open", "mixed", "defensive", "collapsed"}
VALID_OK_POSITION = {"I+W+", "I-W+", "I+W-", "I-W-"}
VALID_MODES = {"validate", "reflect", "explore", "regulate", "practice", "safe_override"}

CATEGORY_MINIMUMS = {
    "contact": 6,
    "low_resource_support": 8,
    "clarify": 8,
    "solution": 8,
    "vent": 6,
    "explore": 6,
    "defensive": 6,
    "collapsed": 5,
    "hyper": 5,
    "hypo": 5,
    "safety": 4,
    "ambiguous_short": 4,
    "continuity_followup": 4,
    "project_fear_evaluation": 4,
    "practice_request": 4,
}

INTENT_MINIMUMS = {"contact": 10, "clarify": 10, "solution": 10}
NERVOUS_MINIMUMS = {"hypo": 8, "hyper": 8}
MODE_MINIMUMS = {"validate": 8, "regulate": 8, "practice": 8, "reflect": 8}


def _case_categories(case: dict) -> set[str]:
    categories: set[str] = set()
    category = case.get("category")
    if isinstance(category, str) and category:
        categories.add(category)
    tags = case.get("tags")
    if isinstance(tags, list):
        for tag in tags:
            if isinstance(tag, str) and tag:
                categories.add(tag)
    return categories


def test_dataset_exists_and_valid_json() -> None:
    assert DATASET_PATH.exists(), f"missing dataset: {DATASET_PATH}"
    payload = json.loads(DATASET_PATH.read_text(encoding="utf-8-sig"))
    assert isinstance(payload, list)
    assert payload
    assert 60 <= len(payload) <= 80


def test_dataset_schema_and_coverage() -> None:
    cases = json.loads(DATASET_PATH.read_text(encoding="utf-8-sig"))

    ids: set[str] = set()
    category_counts: Counter[str] = Counter()
    intent_counts: Counter[str] = Counter()
    nervous_counts: Counter[str] = Counter()
    mode_counts: Counter[str] = Counter()
    low_confidence_count = 0

    for index, case in enumerate(cases):
        label = f"case[{index}]"
        assert isinstance(case, dict), label
        for key in ("id", "title", "category", "user_message", "previous_thread", "expected", "notes"):
            assert key in case, f"{label}: missing {key}"

        case_id = case["id"]
        assert isinstance(case_id, str) and case_id
        assert case_id not in ids, f"duplicate id: {case_id}"
        ids.add(case_id)

        assert isinstance(case["title"], str) and case["title"].strip()
        assert isinstance(case["category"], str) and case["category"].strip()
        assert isinstance(case["user_message"], str) and case["user_message"].strip()
        assert case["previous_thread"] is None or isinstance(case["previous_thread"], dict)
        assert isinstance(case["notes"], str)

        expected = case["expected"]
        assert isinstance(expected, dict)
        assert expected["nervous_state"] in VALID_NERVOUS
        assert expected["intent"] in VALID_INTENT
        assert expected["openness"] in VALID_OPENNESS
        assert expected["ok_position"] in VALID_OK_POSITION
        assert expected["response_mode_new_thread"] in VALID_MODES
        confidence_min = float(expected["confidence_min"])
        assert 0.0 <= confidence_min <= 1.0
        if confidence_min <= 0.55:
            low_confidence_count += 1

        for category in _case_categories(case):
            category_counts[category] += 1
        intent_counts[str(expected["intent"])] += 1
        nervous_counts[str(expected["nervous_state"])] += 1
        mode_counts[str(expected["response_mode_new_thread"])] += 1

    for category, minimum in CATEGORY_MINIMUMS.items():
        assert category_counts[category] >= minimum, f"{category}: {category_counts[category]} < {minimum}"
    for intent, minimum in INTENT_MINIMUMS.items():
        assert intent_counts[intent] >= minimum, f"{intent}: {intent_counts[intent]} < {minimum}"
    for nervous, minimum in NERVOUS_MINIMUMS.items():
        assert nervous_counts[nervous] >= minimum, f"{nervous}: {nervous_counts[nervous]} < {minimum}"
    for mode, minimum in MODE_MINIMUMS.items():
        assert mode_counts[mode] >= minimum, f"{mode}: {mode_counts[mode]} < {minimum}"
    assert low_confidence_count >= 4, f"low_confidence_count={low_confidence_count}"
