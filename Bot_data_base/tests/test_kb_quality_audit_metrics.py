from tools.kb_quality_audit import (
    audit_chunk_distribution,
    audit_mixed_intent,
    audit_no_citation_readiness,
    audit_practice_completeness,
    audit_structure_boundaries,
    build_manual_review_candidates,
)


def _mk_block(
    *,
    chunk_id: str,
    text: str,
    title: str = "",
    summary: str = "",
    source: str = "book:123__кузница_духа",
    source_title: str = "Кузница Духа",
    chunk_type: str = "",
    allowed_use: list[str] | None = None,
    safety_flags: list[str] | None = None,
    lens_family: list[str] | None = None,
    heading_path: list[str] | None = None,
    boundary_confidence: float | None = None,
    split_reason: str = "",
    section_role_hint: str = "",
    mixed_intent_risk: bool = False,
    mixed_intent_severity: str = "none",
    mixed_intent_primary_role: str = "",
    mixed_intent_secondary_roles: list[str] | None = None,
    mixed_intent_reason: str = "",
    low_resource_safe: bool | None = None,
) -> dict:
    governance = {
        "chunk_type": chunk_type,
        "allowed_use": allowed_use or [],
        "safety_flags": safety_flags or [],
        "lens_family": lens_family or [],
        "practice_metadata": {},
    }
    if low_resource_safe is not None:
        governance["practice_metadata"]["low_resource_safe"] = low_resource_safe

    return {
        "id": chunk_id,
        "title": title,
        "summary": summary,
        "text": text,
        "source": source,
        "metadata": {
            "source_title": source_title,
            "source_type": "book",
            "governance": governance,
            "heading_path": heading_path or [],
            "section_role_hint": section_role_hint,
            "boundary_confidence": boundary_confidence,
            "split_reason": split_reason,
            "chunking_quality": {
                "mixed_intent_risk": mixed_intent_risk,
                "mixed_intent_severity": mixed_intent_severity,
                "primary_role": mixed_intent_primary_role,
                "secondary_role_markers": mixed_intent_secondary_roles or [],
                "mixed_intent_reason": mixed_intent_reason,
            },
        },
    }


def test_chunk_distribution_counts_chunk_types_correctly() -> None:
    blocks = [
        _mk_block(
            chunk_id="1",
            text="Практика с шагами",
            chunk_type="practice",
            allowed_use=["practice_suggestion"],
            safety_flags=["not_for_direct_quote"],
            lens_family=["procrastination"],
        ),
        _mk_block(chunk_id="2", text="Теория", chunk_type="theory", allowed_use=["writer_context"]),
        _mk_block(chunk_id="3", text="Без разметки"),
    ]

    metrics = audit_chunk_distribution(blocks)
    assert metrics["chunk_type_distribution"]["practice"] == 1
    assert metrics["chunk_type_distribution"]["theory"] == 1
    assert metrics["chunk_type_distribution"]["unknown/empty"] == 1


def test_empty_lens_family_detected() -> None:
    metrics = audit_chunk_distribution([_mk_block(chunk_id="1", text="x", chunk_type="theory")])
    assert metrics["lens_family_distribution"]["unknown/empty"] == 1


def test_low_boundary_confidence_detected() -> None:
    result = audit_structure_boundaries(
        [
            _mk_block(
                chunk_id="low",
                text="text " * 400,
                chunk_type="practice",
                boundary_confidence=0.2,
                split_reason="semantic",
                heading_path=[],
            )
        ]
    )
    assert result["boundary_confidence_buckets"]["low"] == 1
    assert any(item["category"] == "missing_heading_path" for item in result["findings"])


def test_mixed_intent_medium_high_detected() -> None:
    result = audit_mixed_intent(
        [
            _mk_block(
                chunk_id="m1",
                text="mix",
                chunk_type="practice",
                mixed_intent_risk=True,
                mixed_intent_severity="high",
                mixed_intent_primary_role="practice",
                mixed_intent_secondary_roles=["safety"],
                mixed_intent_reason="multiple_strong_secondary_roles",
            )
        ]
    )
    assert result["mixed_intent_severity_distribution"]["high"] == 1
    assert result["top_mixed_chunks"][0]["chunk_id"] == "m1"


def test_practice_completeness_flags_missing_steps_and_low_resource() -> None:
    result = audit_practice_completeness(
        [
            _mk_block(
                chunk_id="p1",
                text="Практика: дыши спокойно.",
                chunk_type="practice",
                low_resource_safe=False,
            )
        ]
    )
    assert result["practice_chunks_total"] == 1
    assert result["practice_with_steps_count"] == 0
    reasons = result["practice_chunks_needing_review"][0]["issue_reason"]
    assert "missing_steps" in reasons
    assert "missing_low_resource_marker" in reasons


def test_no_citation_audit_flags_writer_context_without_not_for_direct_quote() -> None:
    result = audit_no_citation_readiness(
        [
            _mk_block(
                chunk_id="q1",
                text="теория",
                chunk_type="theory",
                allowed_use=["writer_context"],
                safety_flags=[],
            )
        ]
    )
    assert result["writer_context_without_not_for_direct_quote_count"] == 1


def test_manual_review_candidates_sorted_by_severity() -> None:
    blocks = [
        _mk_block(
            chunk_id="a",
            text="te" * 200,
            chunk_type="theory",
            allowed_use=["writer_context"],
            safety_flags=[],
            boundary_confidence=0.3,
        ),
        _mk_block(
            chunk_id="b",
            text="Практика без шагов",
            chunk_type="practice",
            allowed_use=["practice_suggestion"],
            safety_flags=["not_for_direct_quote"],
            boundary_confidence=0.9,
        ),
    ]
    mixed = {"top_mixed_chunks": []}
    no_citation = audit_no_citation_readiness([blocks[0]])
    practice = audit_practice_completeness([blocks[1]])

    queue = build_manual_review_candidates(
        blocks=blocks,
        mixed=mixed,
        no_citation=no_citation,
        practice=practice,
        limit=10,
    )
    assert queue
    assert queue[0]["priority"] == "P0"


def test_reports_do_not_include_long_raw_content_in_queue() -> None:
    huge_text = "очень длинный текст " * 100
    blocks = [
        _mk_block(
            chunk_id="x1",
            text=huge_text,
            chunk_type="theory",
            allowed_use=["writer_context"],
            safety_flags=[],
            boundary_confidence=0.2,
        )
    ]
    queue = build_manual_review_candidates(
        blocks=blocks,
        mixed={"top_mixed_chunks": []},
        no_citation=audit_no_citation_readiness(blocks),
        practice={"practice_chunks_needing_review": []},
        limit=10,
    )
    assert queue
    assert len(queue[0]["safe_preview"]) <= 160

