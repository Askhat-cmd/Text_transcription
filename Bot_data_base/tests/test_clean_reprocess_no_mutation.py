from __future__ import annotations

import json
from pathlib import Path

from tools.clean_source_reprocess import run_clean_source_reprocess_cli


def _write_json(path: Path, payload: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def test_clean_reprocess_cli_does_not_mutate_production_files(tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path
    botdb = repo / "Bot_data_base"
    raw = botdb / "data" / "uploads" / "books" / "book.md"
    raw.parent.mkdir(parents=True, exist_ok=True)
    raw.write_text("# Глава 1\nТекст для проверки", encoding="utf-8")

    config_path = botdb / "config.yaml"
    config_path.write_text(
        "chunking:\n"
        "  book:\n"
        "    target_tokens: 100\n"
        "    min_tokens: 20\n"
        "    max_tokens: 300\n"
        "    overlap_tokens: 0\n",
        encoding="utf-8",
    )

    registry_path = botdb / "data" / "registry.json"
    _write_json(
        registry_path,
        [
            {
                "source_id": "123__кузница_духа",
                "source_type": "book",
                "title": "Кузница Духа",
                "author": "Автор",
                "author_id": "123",
                "language": "ru",
                "status": "done",
                "added_at": "2026-05-01T00:00:00",
                "processed_at": "2026-05-01T00:10:00",
                "blocks_count": 1,
                "sd_distribution": {},
                "file_paths": {"upload": "data/uploads/books/book.md"},
                "error_message": None,
                "pipeline_version": "v1",
            }
        ],
    )

    all_blocks_path = botdb / "data" / "processed" / "all_blocks_merged.json"
    _write_json(
        all_blocks_path,
        {
            "blocks": [
                {
                    "id": "b1",
                    "text": "Текст",
                    "source": "book:123__кузница_духа",
                    "metadata": {
                        "source_id": "123__кузница_духа",
                        "governance": {"chunk_type": "theory", "allowed_use": ["writer_context"], "safety_flags": ["not_for_direct_quote"]},
                        "chunking_quality": {"mixed_intent_risk": False},
                    },
                }
            ]
        },
    )

    readiness_path = repo / "TO_DO_LIST" / "logs" / "PRD-046.0.7-HF2" / "reprocess_readiness_gate.json"
    _write_json(
        readiness_path,
        {
            "ready_for_clean_reprocess": True,
            "active_source_count": 1,
            "active_source_id": "123__кузница_духа",
            "legacy_sd_active": False,
            "chroma_count": 1,
        },
    )
    review_queue_path = repo / "TO_DO_LIST" / "logs" / "PRD-046.0.7" / "review_queue.json"
    _write_json(review_queue_path, {"review_items_count": 0})

    monkeypatch.chdir(repo)
    before_registry = registry_path.read_text(encoding="utf-8")
    before_blocks = all_blocks_path.read_text(encoding="utf-8")

    result = run_clean_source_reprocess_cli(
        source_prd="PRD-046.0.8",
        mode="candidate",
        readiness_json=readiness_path,
        output_dir=repo / "TO_DO_LIST" / "logs" / "PRD-046.0.8",
        reports_dir=repo / "TO_DO_LIST" / "reports",
        config_path=config_path,
        registry_path=registry_path,
        all_blocks_path=all_blocks_path,
        review_queue_path=review_queue_path,
    )

    assert result["preflight_passed"] is True
    assert registry_path.read_text(encoding="utf-8") == before_registry
    assert all_blocks_path.read_text(encoding="utf-8") == before_blocks
