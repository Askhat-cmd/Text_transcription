from __future__ import annotations

from api.retrieval_policy import (
    POLICY_VERSION,
    apply_retrieval_governance_policy,
    is_safety_context_query,
)


def _hit(allowed_use: str) -> dict:
    return {
        "metadata": {
            "governance_allowed_use": allowed_use,
        }
    }


def test_is_safety_context_query_detects_marker() -> None:
    assert is_safety_context_query("мне очень плохо и страшно оставаться одному") is True
    assert is_safety_context_query("хочу обсудить прокрастинацию") is False


def test_apply_policy_filters_internal_only_for_non_safety() -> None:
    hits = [_hit("internal_only,safety_protocol"), _hit("writer_context,diagnostic_lens")]
    filtered, trace = apply_retrieval_governance_policy(
        "если я не лучший, я будто никто",
        hits,
        top_k=5,
    )
    assert len(filtered) == 1
    assert filtered[0]["metadata"]["governance_allowed_use"] == "writer_context,diagnostic_lens"
    assert trace["policy_version"] == POLICY_VERSION
    assert trace["safety_context"] is False
    assert trace["internal_only_filtered_count"] == 1
    assert "internal_only_non_safety_query" in trace["filter_reasons"]


def test_apply_policy_allows_internal_only_for_safety_query() -> None:
    hits = [_hit("internal_only,safety_protocol"), _hit("writer_context")]
    filtered, trace = apply_retrieval_governance_policy(
        "мне очень плохо и я на грани",
        hits,
        top_k=5,
    )
    assert len(filtered) == 2
    assert trace["safety_context"] is True
    assert trace["internal_only_filtered_count"] == 0

