from __future__ import annotations

from tools.controlled_candidate_apply import verify_no_unplanned_mutation


def test_no_unplanned_mutation_passes_for_allowed_paths() -> None:
    before = {"a": "1", "b": "2", "c": "3"}
    after = {"a": "9", "b": "2", "c": "8"}
    check = verify_no_unplanned_mutation(
        before_hashes=before,
        after_hashes=after,
        allowed_mutated_paths={"a", "c"},
    )
    assert check["passed"] is True
    assert check["unexpected_mutations"] == []


def test_no_unplanned_mutation_fails_for_unexpected_paths() -> None:
    before = {"a": "1", "b": "2"}
    after = {"a": "9", "b": "7"}
    check = verify_no_unplanned_mutation(
        before_hashes=before,
        after_hashes=after,
        allowed_mutated_paths={"a"},
    )
    assert check["passed"] is False
    assert check["unexpected_mutations"] == ["b"]
