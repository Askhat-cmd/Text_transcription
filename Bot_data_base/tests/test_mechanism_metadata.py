from __future__ import annotations

from knowledge_governance.mechanism_metadata import (
    MechanismAwareChunkMetadata,
    adapt_block_to_mechanism_metadata,
    sanitize_metadata_preview,
    validate_mechanism_metadata,
)


def _block(
    *,
    block_id: str = "b1",
    title: str = "Механизм контроля",
    summary: str = "Контроль помогает пережить уязвимость, но зажимает жизнь.",
    text: str = "Когда тревога растет, человек усиливает контроль и избегает неопределенности.",
    chunk_type: str = "lens",
    allowed_use: list[str] | None = None,
    safety_flags: list[str] | None = None,
    practice_metadata: dict | None = None,
    extra_governance: dict | None = None,
) -> dict:
    governance = {
        "schema_version": "governance_v1",
        "chunk_type": chunk_type,
        "allowed_use": allowed_use or ["writer_context", "diagnostic_lens"],
        "safety_flags": safety_flags or ["not_for_direct_quote"],
        "source_trace": {"source_id": "src1", "source_title": "Source One", "source_type": "book"},
    }
    if practice_metadata is not None:
        governance["practice_metadata"] = practice_metadata
    if extra_governance:
        governance.update(extra_governance)
    return {
        "id": block_id,
        "title": title,
        "summary": summary,
        "text": text,
        "source": "book:src1",
        "metadata": {
            "source_title": "Source One",
            "source_type": "book",
            "heading_path": ["H1", "H2"],
            "governance": governance,
            "chunking_quality": {"schema_version": "chunking_quality_v1"},
        },
    }


def test_valid_minimal_concept_chunk_passes() -> None:
    metadata = MechanismAwareChunkMetadata(
        chunk_id="c1",
        source_id="src1",
        source_doc="Doc",
        source_type="book",
        chunk_type="concept",
        title="Факт и интерпретация",
        core_thesis="Событие и смысл не одно и то же.",
        allowed_use=["direct_to_writer", "retrieval_seed"],
        visibility="writer_allowed",
        quote_policy="paraphrase_only",
        depth_level=1,
    )
    result = validate_mechanism_metadata(metadata)
    assert result["errors"] == []


def test_lens_block_normalizes_to_mechanism_with_hints() -> None:
    metadata, validation = adapt_block_to_mechanism_metadata(_block())
    payload = metadata.to_dict()
    assert payload["chunk_type"] == "mechanism"
    assert "control_as_safety" in payload["mechanism_hints"]
    assert "internal_lens" in payload["allowed_use"]
    assert validation["errors"] == []


def test_extended_depth_is_mapped_with_warning_flag() -> None:
    metadata, _ = adapt_block_to_mechanism_metadata(
        _block(extra_governance={"depth_level": 5})
    )
    payload = metadata.to_dict()
    assert payload["depth_level"] == 3
    assert "extended_depth_needs_manual_review" in payload["quality_flags"]


def test_unknown_legacy_fields_are_preserved() -> None:
    metadata, _ = adapt_block_to_mechanism_metadata(
        _block(extra_governance={"old_lens_family": "control", "mystery_key": 7})
    )
    payload = metadata.to_dict()
    assert payload["legacy_metadata"]["old_lens_family"] == "control"
    assert payload["legacy_metadata"]["mystery_key"] == 7


def test_practice_suggestion_requires_practice_chunk() -> None:
    metadata = MechanismAwareChunkMetadata(
        chunk_id="c2",
        source_id="src1",
        source_doc="Doc",
        source_type="book",
        chunk_type="concept",
        title="Bad",
        core_thesis="Bad",
        allowed_use=["practice_suggestion"],
        visibility="writer_allowed",
        quote_policy="paraphrase_only",
        depth_level=1,
    )
    result = validate_mechanism_metadata(metadata)
    assert "practice_suggestion_requires_practice_chunk" in result["errors"]


def test_internal_only_conflicts_with_direct_to_writer() -> None:
    metadata = MechanismAwareChunkMetadata(
        chunk_id="c3",
        source_id="src1",
        source_doc="Doc",
        source_type="book",
        chunk_type="concept",
        title="Bad",
        core_thesis="Bad",
        allowed_use=["internal_only", "direct_to_writer"],
        visibility="internal_only",
        quote_policy="paraphrase_only",
        depth_level=1,
    )
    result = validate_mechanism_metadata(metadata)
    assert "internal_only_conflicts_with_direct_to_writer" in result["errors"]


def test_source_fragment_direct_to_writer_is_blocked() -> None:
    metadata = MechanismAwareChunkMetadata(
        chunk_id="c4",
        source_id="src1",
        source_doc="Doc",
        source_type="book",
        chunk_type="source_fragment",
        title="Raw fragment",
        core_thesis="Raw fragment",
        allowed_use=["direct_to_writer"],
        visibility="source_only",
        quote_policy="paraphrase_only",
        depth_level=0,
    )
    result = validate_mechanism_metadata(metadata)
    assert "source_fragment_direct_to_writer_blocked" in result["errors"]


def test_high_intensity_practice_requires_contraindications() -> None:
    metadata = MechanismAwareChunkMetadata(
        chunk_id="p1",
        source_id="src1",
        source_doc="Doc",
        source_type="manual",
        chunk_type="practice",
        title="Deep practice",
        core_thesis="Deep practice",
        allowed_use=["practice_suggestion"],
        visibility="writer_allowed",
        quote_policy="paraphrase_only",
        depth_level=1,
        intensity="high",
        practice={"steps_short": ["Step 1"], "contraindications": []},
    )
    result = validate_mechanism_metadata(metadata)
    assert "high_intensity_practice_requires_contraindications" in result["errors"]


def test_sanitized_preview_hides_full_text() -> None:
    metadata, _ = adapt_block_to_mechanism_metadata(_block(text="очень длинный текст " * 50))
    preview = sanitize_metadata_preview(metadata)
    assert "text" not in preview
    assert len(preview["core_thesis"]) <= 180
