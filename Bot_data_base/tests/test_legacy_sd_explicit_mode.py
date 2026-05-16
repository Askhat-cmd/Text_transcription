from __future__ import annotations

import asyncio
from pathlib import Path

from models.universal_block import UniversalBlock
from pipeline_runner import PipelineRunner


class _DummyBookIngestor:
    def validate_file(self, _file_path: str):
        return True, None

    def load_text(self, _file_path: str) -> str:
        return "dummy text"


class _DummyBookChunker:
    def chunk_file_from_text(self, text: str, **_kwargs):
        return [UniversalBlock(text=text, source_type="book")]


class _DummyLabeler:
    def __init__(self) -> None:
        self.calls = 0

    def label_blocks(self, blocks):
        self.calls += 1
        for block in blocks:
            block.sd_level = "BLUE"
        return blocks


class _DummyRegistry:
    def __init__(self) -> None:
        self.last_update_kwargs = None

    def is_processed(self, _source_id: str) -> bool:
        return False

    def add_source(self, _record) -> None:
        return None

    def update_status(self, _source_id: str, _status: str, **kwargs) -> None:
        self.last_update_kwargs = kwargs


class _DummyExporter:
    def __init__(self, out: Path) -> None:
        self.out = out

    def export(self, _blocks, _source_id: str, _source_type: str) -> str:
        self.out.write_text("{}", encoding="utf-8")
        return str(self.out)


class _DummyChroma:
    def add_blocks(self, blocks) -> int:
        return len(blocks)


def _build_runner(tmp_path: Path) -> tuple[PipelineRunner, _DummyLabeler, _DummyRegistry]:
    runner = PipelineRunner.__new__(PipelineRunner)
    runner.job_manager = None
    runner.legacy_sd_enabled = True
    runner.book_ingestor = _DummyBookIngestor()
    runner.book_chunker = _DummyBookChunker()
    labeler = _DummyLabeler()
    runner.sd_labeler = labeler
    runner.block_normalizer = type("_Norm", (), {"normalize": staticmethod(lambda blocks: blocks)})()
    runner.chroma_manager = _DummyChroma()
    registry = _DummyRegistry()
    runner.registry = registry
    runner.json_exporter = _DummyExporter(tmp_path / "book.json")
    return runner, labeler, registry


def test_legacy_sd_explicit_mode_calls_labeler(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("pipeline_runner.normalize_governance_profile", lambda profile, fallback="general_book": profile or fallback)
    monkeypatch.setattr(
        "pipeline_runner.apply_governance_to_blocks_v1",
        lambda **kwargs: kwargs["blocks"],
    )
    monkeypatch.setattr("pipeline_runner.build_chunking_quality_v1", lambda _block: {})

    runner, labeler, registry = _build_runner(tmp_path)
    result = asyncio.run(
        runner.run_book(
            file_path=str(tmp_path / "dummy.txt"),
            author="Author",
            author_id="author_id",
            book_title="Book",
            language="ru",
            job_id="",
        )
    )

    assert result["status"] == "done"
    assert labeler.calls == 1
    assert registry.last_update_kwargs is not None
    assert registry.last_update_kwargs["sd_distribution"] == {"BLUE": 1}
