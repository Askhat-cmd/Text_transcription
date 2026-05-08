from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from bot_agent.knowledge_governance.chunker import chunk_markdown_document_v1
from bot_agent.knowledge_governance.contracts import KnowledgeSourceManifest


def _manifest() -> KnowledgeSourceManifest:
    return KnowledgeSourceManifest(
        source_id="forge_spirit_v2",
        title="КУЗНИЦА ДУХА v.2",
        source_kind="practice_manual",
        author="Author",
        language="ru",
        version="v2",
        allowed_global_use=["diagnostic_lens", "practice_suggestion", "writer_context"],
        default_safety_flags=["requires_grounding"],
    )


def test_chunker_preserves_heading_path_and_detects_practice() -> None:
    text = (
        "# Глава 1\n\n"
        "Теория о саморегуляции.\n\n"
        "## Практика 1: Дыхание\n\n"
        "Цель: заметить состояние.\n\n"
        "Время: 3 минуты.\n\n"
        "Шаг 1. Вдох.\n"
        "Шаг 2. Выдох.\n"
    )
    chunks = chunk_markdown_document_v1(text=text, manifest=_manifest(), max_chars=1000, soft_min_chars=200)
    assert chunks
    practice_chunks = [chunk for chunk in chunks if chunk.chunk_type == "practice"]
    assert practice_chunks, "practice section must be classified as practice"
    practice = practice_chunks[0]
    assert "Практика 1: Дыхание" in practice.heading_path
    assert practice.practice_metadata.get("goal")
    assert "practice_suggestion" in practice.allowed_use


def test_chunker_sets_practice_guard_when_low_resource_not_safe() -> None:
    text = (
        "# Практика 2: Дневник\n\n"
        "Цель: проанализировать глубинные схемы.\n\n"
        "Время: 30 минут.\n\n"
        "Шаг 1. Запиши все мысли подробно.\n"
        "Шаг 2. Сформируй 5 выводов.\n"
        "Шаг 3. Определи корневую программу.\n"
        "Шаг 4. Запиши план изменений.\n"
    )
    chunks = chunk_markdown_document_v1(text=text, manifest=_manifest(), max_chars=1200, soft_min_chars=200)
    assert chunks
    practice = chunks[0]
    assert practice.chunk_type == "practice"
    assert practice.practice_metadata.get("low_resource_safe") is False
    assert "practice_requires_low_resource_check" in practice.safety_flags
