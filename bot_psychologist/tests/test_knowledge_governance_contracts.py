from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from bot_agent.knowledge_governance.chunker import chunk_markdown_document_v1
from bot_agent.knowledge_governance.contracts import (
    GovernedKnowledgeChunk,
    KnowledgeSourceManifest,
)
from bot_agent.knowledge_governance.validators import validate_governed_chunks_v1


def _manifest() -> KnowledgeSourceManifest:
    return KnowledgeSourceManifest(
        source_id="test_source",
        title="Test Source",
        source_kind="practice_manual",
        author="Author",
        language="ru",
        version="v1",
        allowed_global_use=["writer_context"],
        default_safety_flags=["requires_grounding"],
    )


def test_manifest_roundtrip() -> None:
    manifest = _manifest()
    restored = KnowledgeSourceManifest.from_dict(manifest.to_dict())
    assert restored.to_dict() == manifest.to_dict()


def test_governed_chunk_roundtrip() -> None:
    chunk = GovernedKnowledgeChunk(
        chunk_id="s::chunk::0001::abc12345",
        source_id="s",
        source_title="title",
        chunk_index=1,
        heading_path=["A", "B"],
        title="Chunk title",
        text="Chunk text",
        summary="Chunk summary",
        chunk_type="practice",
        allowed_use=["practice_suggestion"],
        safety_flags=["practice_requires_low_resource_check"],
        practice_metadata={"low_resource_safe": False, "steps_count": 4},
    )
    restored = GovernedKnowledgeChunk.from_dict(chunk.to_dict())
    assert restored.to_dict() == chunk.to_dict()


def test_validator_reports_unknown_enum_error() -> None:
    chunk = GovernedKnowledgeChunk(
        chunk_id="invalid::chunk::0001::deadbeef",
        source_id="invalid",
        source_title="invalid",
        chunk_index=1,
        heading_path=["Invalid"],
        title="Invalid",
        text="text",
        summary="summary",
        chunk_type="unknown_type",
        allowed_use=["writer_context"],
        safety_flags=[],
    )
    report = validate_governed_chunks_v1([chunk])
    assert any("invalid_chunk_type" in error for error in report["errors"])


def test_chunk_id_is_stable_for_same_input() -> None:
    text = "# Глава 1\n\nТеория.\n\n## Практика\n\nЦель: снизить напряжение.\nВремя: 3 минуты.\nШаг 1. Вдох."
    chunks_first = chunk_markdown_document_v1(text=text, manifest=_manifest())
    chunks_second = chunk_markdown_document_v1(text=text, manifest=_manifest())
    assert [chunk.chunk_id for chunk in chunks_first] == [chunk.chunk_id for chunk in chunks_second]
