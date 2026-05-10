from __future__ import annotations

import json
from pathlib import Path

from tools.run_retrieval_eval import REQUIRED_CATEGORIES, validate_dataset_payload


def test_retrieval_eval_dataset_exists_and_valid() -> None:
    dataset_path = Path("Bot_data_base/eval/retrieval_eval_v1.json")
    assert dataset_path.exists(), "retrieval eval dataset is missing"
    payload = json.loads(dataset_path.read_text(encoding="utf-8"))
    errors = validate_dataset_payload(payload)
    assert errors == []


def test_retrieval_eval_dataset_has_required_categories() -> None:
    payload = json.loads(Path("Bot_data_base/eval/retrieval_eval_v1.json").read_text(encoding="utf-8"))
    cases = payload.get("cases") or []
    counts = {category: 0 for category in REQUIRED_CATEGORIES}
    for case in cases:
        category = str(case.get("category") or "")
        if category in counts:
            counts[category] += 1
    assert all(counts[category] >= 2 for category in REQUIRED_CATEGORIES)

