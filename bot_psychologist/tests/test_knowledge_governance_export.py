from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from bot_agent.knowledge_governance.chunker import chunk_markdown_document_v1
from bot_agent.knowledge_governance.contracts import KnowledgeSourceManifest
from bot_agent.knowledge_governance.export import export_governed_chunks_to_db_json_v1


def _manifest() -> KnowledgeSourceManifest:
    return KnowledgeSourceManifest(
        source_id="neo_mindbot_notes",
        title="Neo MindBot КОНСПЕКТ",
        source_kind="architecture_notes",
        author=None,
        language="ru",
        version="notes",
        allowed_global_use=["internal_only", "style_guidance"],
        default_safety_flags=["source_style_not_user_facing", "not_for_direct_quote"],
    )


def test_export_has_db_json_compatible_shape() -> None:
    text = "# Принципы\n\nНе использовать как прямую цитату.\n\n## Style\n\nОтвет должен быть конкретным."
    chunks = chunk_markdown_document_v1(text=text, manifest=_manifest())
    payload = export_governed_chunks_to_db_json_v1(chunks=chunks, manifest=_manifest())
    assert payload["schema_version"] == "governed_kb_v1"
    assert payload["source_id"] == "neo_mindbot_notes"
    assert isinstance(payload["blocks"], list)
    assert payload["blocks"]
    first = payload["blocks"][0]
    for key in ("id", "title", "summary", "text", "complexity", "metadata"):
        assert key in first
    governance = first["metadata"]["governance"]
    for key in ("chunk_type", "allowed_use", "safety_flags", "lens_family", "tags", "practice_metadata"):
        assert key in governance
