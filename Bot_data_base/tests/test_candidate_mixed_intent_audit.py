from __future__ import annotations

from tools.clean_source_reprocess import build_mixed_intent_audit_report


def _mk_block(block_id: str, text: str, chunk_type: str = "theory") -> dict:
    return {
        "id": block_id,
        "text": text,
        "source": "book:123__кузница_духа",
        "metadata": {
            "source_id": "123__кузница_духа",
            "governance": {
                "chunk_type": chunk_type,
                "allowed_use": ["writer_context"],
                "safety_flags": ["not_for_direct_quote"],
            },
            "chunking_quality": {
                "mixed_intent_risk": True,
                "mixed_intent_severity": "medium",
                "mixed_intent_reason": "ambiguous_primary_with_secondary_markers",
                "primary_role": "theory",
                "secondary_role_markers": ["practice"],
            },
        },
    }


def test_mixed_intent_audit_collects_cases_and_safe_preview() -> None:
    block = _mk_block(
        "m1",
        "> Из сессии: клиент попробовал практику и описывает эффект без запроса на инструкцию.",
    )

    report = build_mixed_intent_audit_report(source_prd="PRD-046.0.8-HF2", candidate_blocks=[block])

    assert report["schema_version"] == "candidate_mixed_intent_audit_v1"
    assert report["mixed_intent_alerts_before"] == 1
    assert len(report["mixed_intent_cases"]) == 1
    case = report["mixed_intent_cases"][0]
    assert case["block_id"] == "m1"
    assert len(case["safe_preview"]) <= 220
