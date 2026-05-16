from __future__ import annotations

from review.dashboard_chroma_reconciliation import build_chroma_count_reconciliation


def _smoke_payload(chroma_count: int | None) -> dict:
    chroma = {"status": "ok", "indexed_source_ids": ["123__кузница_духа"]}
    if chroma_count is not None:
        chroma["count"] = chroma_count
    return {
        "api_checks": {
            "/api/dashboard": {
                "ok": True,
                "status_code": 200,
                "body": {"blocks": {"production_total": 247}, "chroma": chroma},
            }
        },
        "focus_blocks_count": 247,
        "dashboard_blocks_count": 247,
        "chroma_count": chroma_count,
    }


def test_reconciliation_passes_with_live_247() -> None:
    result = build_chroma_count_reconciliation(
        source_prd="PRD-046.0.7.2-HF3",
        admin_base_url="http://127.0.0.1:8003",
        smoke=_smoke_payload(247),
        expected_source_id="123__кузница_духа",
        expected_blocks=247,
        direct_chroma_count=247,
        historical_chroma_count=247,
        historical_proof_path="x.json",
    )
    assert result["strict_gate_passed"] is True
    assert result["issues"] == []
    assert result["reconciliation_status"] == "passed_strict_chroma_reconciliation"


def test_reconciliation_blocks_on_live_229_even_if_historical_247() -> None:
    result = build_chroma_count_reconciliation(
        source_prd="PRD-046.0.7.2-HF3",
        admin_base_url="http://127.0.0.1:8003",
        smoke=_smoke_payload(229),
        expected_source_id="123__кузница_духа",
        expected_blocks=247,
        direct_chroma_count=None,
        historical_chroma_count=247,
        historical_proof_path="x.json",
    )
    assert result["strict_gate_passed"] is False
    assert "dashboard_chroma_count_mismatch" in result["issues"]
    assert result["reconciliation_status"] == "blocked_live_dashboard_chroma_mismatch"
    assert "historical_proof_cannot_override_live_dashboard_mismatch" in result["warnings"]


def test_reconciliation_detects_dashboard_source_bug_when_direct_247_live_229() -> None:
    result = build_chroma_count_reconciliation(
        source_prd="PRD-046.0.7.2-HF3",
        admin_base_url="http://127.0.0.1:8003",
        smoke=_smoke_payload(229),
        expected_source_id="123__кузница_духа",
        expected_blocks=247,
        direct_chroma_count=247,
        historical_chroma_count=247,
        historical_proof_path="x.json",
    )
    assert result["strict_gate_passed"] is False
    assert result["reconciliation_status"] == "blocked_dashboard_count_source_mismatch"


def test_reconciliation_detects_actual_chroma_stale_when_direct_229_live_229() -> None:
    result = build_chroma_count_reconciliation(
        source_prd="PRD-046.0.7.2-HF3",
        admin_base_url="http://127.0.0.1:8003",
        smoke=_smoke_payload(229),
        expected_source_id="123__кузница_духа",
        expected_blocks=247,
        direct_chroma_count=229,
        historical_chroma_count=247,
        historical_proof_path="x.json",
    )
    assert result["strict_gate_passed"] is False
    assert result["reconciliation_status"] == "blocked_actual_chroma_count_mismatch"


def test_reconciliation_blocks_when_chroma_schema_missing() -> None:
    result = build_chroma_count_reconciliation(
        source_prd="PRD-046.0.7.2-HF3",
        admin_base_url="http://127.0.0.1:8003",
        smoke=_smoke_payload(None),
        expected_source_id="123__кузница_духа",
        expected_blocks=247,
        direct_chroma_count=None,
        historical_chroma_count=247,
        historical_proof_path="x.json",
    )
    assert result["strict_gate_passed"] is False
    assert "dashboard_chroma_schema_missing" in result["issues"]
    assert result["reconciliation_status"] == "blocked_dashboard_chroma_schema_missing"
