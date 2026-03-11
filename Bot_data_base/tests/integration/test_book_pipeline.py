import json
from pathlib import Path

import pytest
import numpy as np

from pipeline_runner import PipelineRunner
from processors.sd_labeler import SDLabeler
from storage.chroma_manager import ChromaManager


class DummyModel:
    def encode(self, texts, convert_to_numpy=True):
        return np.zeros((len(texts), 3), dtype=float)


def _write_config(tmp_path: Path) -> Path:
    cfg = {
        "pipeline": {
            "youtube": {"output_dir": "processed/youtube", "subtitles_dir": "uploads/subtitles"},
            "books": {"output_dir": "processed/books", "uploads_dir": "uploads/books"},
        },
        "chunking": {
            "youtube": {"min_tokens": 5, "max_tokens": 50},
            "book": {"target_tokens": 40, "min_tokens": 10, "max_tokens": 60, "overlap_tokens": 10},
        },
        "sd_labeling": {"batch_size": 5, "min_confidence": 0.5},
        "storage": {
            "chroma_db_path": "chroma",
            "collection_name": "test_col",
            "json_export_dir": "processed",
            "registry_path": "registry.json",
        },
    }
    path = tmp_path / "config.yaml"
    import yaml

    path.write_text(yaml.safe_dump(cfg), encoding="utf-8")
    return path


@pytest.mark.asyncio
async def test_full_book_pipeline(tmp_path, monkeypatch):
    monkeypatch.setattr(ChromaManager, "_init_embedding_model", lambda self: DummyModel())

    def fake_call_openai(self, texts):
        return json.dumps([
            {
                "sd_level": "GREEN",
                "sd_secondary": "",
                "sd_confidence": 0.9,
                "complexity": 0.4,
                "reasoning": "ok",
            }
            for _ in texts
        ])

    monkeypatch.setattr(SDLabeler, "_call_openai", fake_call_openai)

    config_path = _write_config(tmp_path)
    runner = PipelineRunner(config_path=str(config_path))

    fixture_path = Path(__file__).resolve().parents[1] / "fixtures" / "sample_book.md"
    result = await runner.run_book(
        file_path=str(fixture_path),
        author="Экхарт Толле",
        author_id="tolle_eckhart",
        book_title="Сила настоящего",
        language="ru",
        job_id="job_002",
    )

    assert result["status"] == "done"
    assert result["blocks_count"] >= 2

    json_path = result["json_path"]
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    first_block = data["blocks"][0]
    assert first_block["metadata"]["author"] == "Экхарт Толле"
    assert first_block["sd_level"] in {"BEIGE","PURPLE","RED","BLUE","ORANGE","GREEN","YELLOW","TURQUOISE","UNCERTAIN"}


@pytest.mark.asyncio
async def test_duplicate_book_skipped(tmp_path, monkeypatch):
    monkeypatch.setattr(ChromaManager, "_init_embedding_model", lambda self: DummyModel())

    def fake_call_openai(self, texts):
        return json.dumps([
            {
                "sd_level": "GREEN",
                "sd_secondary": "",
                "sd_confidence": 0.9,
                "complexity": 0.4,
                "reasoning": "ok",
            }
            for _ in texts
        ])

    monkeypatch.setattr(SDLabeler, "_call_openai", fake_call_openai)

    config_path = _write_config(tmp_path)
    runner = PipelineRunner(config_path=str(config_path))

    fixture_path = Path(__file__).resolve().parents[1] / "fixtures" / "sample_book.md"
    await runner.run_book(
        file_path=str(fixture_path),
        author="Экхарт Толле",
        author_id="tolle_eckhart",
        book_title="Сила настоящего",
        language="ru",
        job_id="job_010",
    )

    result2 = await runner.run_book(
        file_path=str(fixture_path),
        author="Экхарт Толле",
        author_id="tolle_eckhart",
        book_title="Сила настоящего",
        language="ru",
        job_id="job_011",
    )

    assert result2["status"] == "skipped"

