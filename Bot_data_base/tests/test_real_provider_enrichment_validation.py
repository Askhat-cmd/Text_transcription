from __future__ import annotations

from tools.real_provider_enrichment_run import _estimate_usage_from_overlay


def test_estimate_usage_tracks_missing_and_failures() -> None:
    overlay = {
        "items": [
            {"advisory": {"summary": "ok"}, "quality": {"review_reasons": []}},
            {"advisory": {"summary": ""}, "quality": {"review_reasons": ["missing_real_provider_output"]}},
            {"advisory": {"summary": ""}, "quality": {"review_reasons": ["provider_error:TimeoutError"]}},
        ]
    }
    usage = _estimate_usage_from_overlay(overlay, input_price_per_1k=0.001, output_price_per_1k=0.002)
    assert usage["requests"] == 3
    assert usage["items_completed"] == 1
    assert usage["items_failed"] == 1
    assert usage["missing_real_provider_output_count"] == 1

