from __future__ import annotations

from tools.real_provider_enrichment_run import run_provider_preflight


def test_provider_preflight_blocks_when_budget_missing(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    payload = run_provider_preflight(
        inventory={"items": [{"safe_preview": "abc"}]},
        model="gpt-4o-mini",
        configured_budget_usd=0.0,
        hard_stop_budget_usd=0.0,
        timeout_seconds=3.0,
        input_price_per_1k=0.001,
        output_price_per_1k=0.001,
    )
    assert payload["passed"] is False
    assert "configured_budget_missing" in payload["blockers"]
    assert "api_key_missing" in payload["blockers"]

