import json
import os

from models.universal_block import UniversalBlock
from storage.json_export import JSONExporter


def test_export_creates_file(tmp_path):
    exporter = JSONExporter(base_dir=str(tmp_path))
    blocks = [
        UniversalBlock(
            text="Тест",
            author="А",
            sd_level="GREEN",
            source_type="book",
            source_id="test_book",
        )
    ]
    path = exporter.export(blocks, "test_book", "book")
    assert os.path.exists(path)


def test_exported_json_valid(tmp_path):
    exporter = JSONExporter(base_dir=str(tmp_path))
    blocks = [
        UniversalBlock(
            text="Тест",
            sd_level="GREEN",
            source_type="youtube",
            source_id="vid123",
        )
    ]
    path = exporter.export(blocks, "vid123", "youtube")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert "blocks" in data
    assert data["blocks"][0]["text"] == "Тест"
    assert "sd_level" in data["blocks"][0]


def test_bot_format_fields(tmp_path):
    exporter = JSONExporter(base_dir=str(tmp_path))
    blocks = [
        UniversalBlock(
            text="Осознанность",
            sd_level="GREEN",
            complexity=0.4,
            author="Автор",
            source_type="book",
            source_id="book1",
        )
    ]
    path = exporter.export(blocks, "book1", "book")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    block = data["blocks"][0]
    for field in ["text", "sd_level", "complexity", "source", "metadata"]:
        assert field in block, f"Missing field: {field}"
