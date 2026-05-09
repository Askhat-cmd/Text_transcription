import json
from pathlib import Path

import pytest

from tools.source_reprocess import run_source_reprocess


def _mk_block(block_id: str, source: str = "book:123__кузница_духа") -> dict:
    return {
        "id": block_id,
        "text": "Практика: Шаг 1 сделай паузу, Шаг 2 опиши состояние.",
        "title": "Практика",
        "summary": "",
        "sd_level": "GREEN",
        "sd_confidence": 0.7,
        "complexity": 0.4,
        "source": source,
        "metadata": {
            "author": "Author",
            "author_id": "123",
            "source_title": "Кузница Духа",
            "language": "ru",
            "source_type": "book",
            "chapter_title": "Глава 1",
            "chunk_index": 0,
        },
    }


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def test_dry_run_does_not_mutate_processed_files(tmp_path: Path) -> None:
    all_blocks = tmp_path / "processed" / "all_blocks_merged.json"
    source_file = tmp_path / "processed" / "books" / "123__кузница_духа_blocks.json"
    payload = {"schema_version": "v1", "blocks_count": 1, "blocks": [_mk_block("b1")]}
    _write_json(all_blocks, payload)
    _write_json(source_file, payload)

    before = all_blocks.read_text(encoding="utf-8")
    result = run_source_reprocess(
        source_hint="КУЗНИЦА ДУХА",
        all_blocks_path=all_blocks,
        processed_dir=tmp_path / "processed",
        output_dir=tmp_path / "logs",
        reports_dir=tmp_path / "reports",
        config_path=tmp_path / "config.yaml",
        registry_path=tmp_path / "registry.json",
        mode="backfill_only",
        confirm=True,
        dry_run=True,
    )

    after = all_blocks.read_text(encoding="utf-8")
    assert result["mutation_performed"] is False
    assert before == after


def test_reprocess_without_confirm_is_blocked(tmp_path: Path) -> None:
    all_blocks = tmp_path / "processed" / "all_blocks_merged.json"
    source_file = tmp_path / "processed" / "books" / "123__кузница_духа_blocks.json"
    payload = {"blocks": [_mk_block("b1")]}
    _write_json(all_blocks, payload)
    _write_json(source_file, payload)

    with pytest.raises(RuntimeError, match="requires --confirm"):
        run_source_reprocess(
            source_hint="КУЗНИЦА ДУХА",
            all_blocks_path=all_blocks,
            processed_dir=tmp_path / "processed",
            output_dir=tmp_path / "logs",
            reports_dir=tmp_path / "reports",
            config_path=tmp_path / "config.yaml",
            registry_path=tmp_path / "registry.json",
            mode="reprocess",
            confirm=False,
            dry_run=False,
        )


def test_calibrate_without_confirm_is_blocked(tmp_path: Path) -> None:
    all_blocks = tmp_path / "processed" / "all_blocks_merged.json"
    source_file = tmp_path / "processed" / "books" / "123__кузница_духа_blocks.json"
    payload = {"blocks": [_mk_block("b1")]}
    _write_json(all_blocks, payload)
    _write_json(source_file, payload)

    with pytest.raises(RuntimeError, match="requires --confirm"):
        run_source_reprocess(
            source_hint="КУЗНИЦА ДУХА",
            all_blocks_path=all_blocks,
            processed_dir=tmp_path / "processed",
            output_dir=tmp_path / "logs",
            reports_dir=tmp_path / "reports",
            config_path=tmp_path / "config.yaml",
            registry_path=tmp_path / "registry.json",
            mode="calibrate_classification",
            confirm=False,
            dry_run=False,
        )


def test_backup_created_before_mutation(tmp_path: Path) -> None:
    all_blocks = tmp_path / "processed" / "all_blocks_merged.json"
    source_file = tmp_path / "processed" / "books" / "123__кузница_духа_blocks.json"
    payload = {"schema_version": "v1", "blocks_count": 1, "blocks": [_mk_block("b1")]}
    _write_json(all_blocks, payload)
    _write_json(source_file, payload)

    result = run_source_reprocess(
        source_hint="КУЗНИЦА ДУХА",
        all_blocks_path=all_blocks,
        processed_dir=tmp_path / "processed",
        output_dir=tmp_path / "logs",
        reports_dir=tmp_path / "reports",
        config_path=tmp_path / "config.yaml",
        registry_path=tmp_path / "registry.json",
        mode="backfill_only",
        confirm=True,
        dry_run=False,
    )

    assert result["mutation_performed"] is True
    assert result["backup_created"] is True
    assert result["backup_path"]
    assert Path(result["backup_path"]).exists()
