import json
from pathlib import Path

import pytest
import numpy as np

from pipeline_runner import PipelineRunner
from processors.sd_labeler import SDLabeler
from storage.chroma_manager import ChromaManager
from ingestors.youtube_ingestor import YouTubeIngestor


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
            "book": {"target_tokens": 100, "min_tokens": 20, "max_tokens": 150, "overlap_tokens": 10},
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
async def test_full_youtube_pipeline(tmp_path, monkeypatch):
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

    def fake_fetch(self, video_id):
        return ("Текст видео. " * 20, {"title": "Видео", "channel": "Канал", "language": "ru", "published_date": "2020-01-01"})

    monkeypatch.setattr(YouTubeIngestor, "fetch_raw_text", fake_fetch)

    config_path = _write_config(tmp_path)
    runner = PipelineRunner(config_path=str(config_path))

    result = await runner.run_youtube(
        url="https://youtube.com/watch?v=test123",
        author="Тест Автор",
        author_id="test_avtor",
        job_id="job_001",
    )

    assert result["status"] == "done"
    assert result["blocks_count"] > 0

    json_path = result["json_path"]
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert len(data["blocks"]) > 0
    assert all(b["sd_level"] != "" for b in data["blocks"])


@pytest.mark.asyncio
async def test_duplicate_skipped(tmp_path, monkeypatch):
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

    def fake_fetch(self, video_id):
        return ("Текст видео. " * 10, {"title": "Видео", "channel": "Канал", "language": "ru", "published_date": "2020-01-01"})

    monkeypatch.setattr(YouTubeIngestor, "fetch_raw_text", fake_fetch)

    config_path = _write_config(tmp_path)
    runner = PipelineRunner(config_path=str(config_path))

    await runner.run_youtube("https://youtube.com/watch?v=test123", "A", "a", "job_001")
    result2 = await runner.run_youtube("https://youtube.com/watch?v=test123", "A", "a", "job_002")
    assert result2["status"] == "skipped"
