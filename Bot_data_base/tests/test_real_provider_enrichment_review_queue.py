from __future__ import annotations

from tools.real_provider_enrichment_run import _reason_counts


def test_reason_counts_are_aggregated() -> None:
    queue = {
        "items": [
            {"review_reasons": ["low_confidence", "missing_summary"]},
            {"review_reasons": ["low_confidence"]},
        ]
    }
    counts = _reason_counts(queue)
    assert counts["low_confidence"] == 2
    assert counts["missing_summary"] == 1

