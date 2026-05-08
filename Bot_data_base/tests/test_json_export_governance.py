import json

from models.universal_block import UniversalBlock
from storage.json_export import JSONExporter


def test_json_export_preserves_governance_and_chunking_quality(tmp_path) -> None:
    exporter = JSONExporter(base_dir=str(tmp_path))
    block = UniversalBlock(
        text="Тестовый блок",
        title="Тест",
        source_type="book",
        source_id="source_x",
        sd_level="GREEN",
        governance={
            "schema_version": "governance_v1",
            "chunk_type": "practice",
            "allowed_use": ["writer_context", "practice_suggestion"],
            "safety_flags": ["not_for_direct_quote"],
            "lens_family": ["somatic"],
            "tags": ["practice"],
            "practice_metadata": {"low_resource_safe": True},
            "governance_notes": [],
            "source_trace": {"adapter": "bot_data_base_governance_adapter_v1"},
        },
        chunking_quality={
            "schema_version": "chunking_quality_v1",
            "possible_practice_split": False,
        },
    )

    path = exporter.export([block], "source_x", "book")
    payload = json.loads(open(path, "r", encoding="utf-8").read())
    metadata = payload["blocks"][0]["metadata"]

    assert "governance" in metadata
    assert metadata["governance"]["schema_version"] == "governance_v1"
    assert metadata["chunking_quality"]["schema_version"] == "chunking_quality_v1"
