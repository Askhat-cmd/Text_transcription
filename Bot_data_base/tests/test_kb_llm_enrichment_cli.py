from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools import kb_llm_enrichment
from tools.kb_llm_enrichment import _parse_llm_json, _select_stratified_blocks, run_enrichment


def _mk_block(block_id: str, chunk_type: str, mixed_intent: str = "none") -> dict:
    return {
        "id": block_id,
        "text": (
            f"Тестовый фрагмент {block_id}. Описывает паттерн и контекст. "
            "Шаг 1: пауза. Шаг 2: внимание к телу."
        ),
        "title": f"Блок {block_id}",
        "summary": "",
        "source": "book:123__кузница_духа",
        "metadata": {
            "source_title": "Кузница Духа",
            "chapter_title": "Глава 1",
            "governance": {
                "chunk_type": chunk_type,
                "allowed_use": ["writer_context", "practice_suggestion"],
                "safety_flags": ["not_for_direct_quote", "practice_requires_low_resource_check"],
            },
            "chunking_quality": {"mixed_intent_severity": mixed_intent},
        },
    }


def test_parse_llm_json_rejects_invalid_payload() -> None:
    with pytest.raises(Exception):
        _parse_llm_json("not-json")


def test_parse_llm_json_accepts_fenced_json() -> None:
    parsed = _parse_llm_json("```json\n{\"summary_candidate\": \"ok\"}\n```")
    assert parsed["summary_candidate"] == "ok"


def test_select_stratified_blocks_covers_types_and_mixed_intent() -> None:
    blocks: list[dict] = []
    for chunk_type in ("case", "lens", "practice", "safety", "style", "theory"):
        blocks.append(_mk_block(f"{chunk_type}-1", chunk_type, mixed_intent="medium"))
        blocks.append(_mk_block(f"{chunk_type}-2", chunk_type, mixed_intent="none"))
    selected = _select_stratified_blocks(blocks, limit=12)
    selected_types = {row["metadata"]["governance"]["chunk_type"] for row in selected}
    assert selected_types == {"case", "lens", "practice", "safety", "style", "theory"}
    assert len([row for row in selected if row["metadata"]["chunking_quality"]["mixed_intent_severity"] == "medium"]) >= 3


def test_run_enrichment_dry_run_no_mutation_and_no_raw_leaks(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    blocks_path = tmp_path / "all_blocks_merged.json"
    all_blocks = {
        "blocks": [
            _mk_block("case-1", "case", "medium"),
            _mk_block("lens-1", "lens", "high"),
            _mk_block("practice-1", "practice", "medium"),
            _mk_block("safety-1", "safety"),
            _mk_block("style-1", "style"),
            _mk_block("theory-1", "theory"),
        ]
    }
    blocks_path.write_text(json.dumps(all_blocks, ensure_ascii=False), encoding="utf-8")
    before = blocks_path.read_text(encoding="utf-8")

    monkeypatch.setattr(
        kb_llm_enrichment,
        "_evaluate_preflight",
        lambda: {"preflight_passed": True, "reasons": [], "observed": {}},
    )

    output_dir = tmp_path / "logs"
    reports_dir = tmp_path / "reports"
    prompt_path = tmp_path / "kb_enrichment_v1.md"
    prompt_path.write_text("json only", encoding="utf-8")

    result = run_enrichment(
        source_hint="КУЗНИЦА ДУХА",
        blocks_path=blocks_path,
        output_dir=output_dir,
        reports_dir=reports_dir,
        prompt_path=prompt_path,
        limit=6,
        offset=0,
        chunk_type_filter="",
        dry_run=True,
        write_overlay=False,
        apply_changes=False,
        confirm=False,
        mock_llm=True,
        max_concurrency=1,
        max_retries=2,
        timeout_seconds=10.0,
    )

    after = blocks_path.read_text(encoding="utf-8")
    assert before == after
    assert result["status"] == "done"

    candidates_path = output_dir / "enrichment_candidates.jsonl"
    assert candidates_path.exists()
    assert (output_dir / "enrichment_calibration_candidates.jsonl").exists()
    assert (output_dir / "enrichment_calibration_validation_report.json").exists()
    assert (output_dir / "enrichment_calibration_diff_summary.json").exists()
    assert (output_dir / "failed_candidate_examples_sanitized.jsonl").exists()
    overlay_readiness = json.loads((output_dir / "overlay_readiness_report.json").read_text(encoding="utf-8"))
    assert overlay_readiness["run_kind"] == "mock"
    assert overlay_readiness["production_ready"] is False
    assert overlay_readiness["promotion_allowed"] is False
    lines = [json.loads(line) for line in candidates_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert lines
    blob = json.dumps(lines, ensure_ascii=False).lower()
    assert "content_full" not in blob
    assert "raw_full_text" not in blob
    assert "raw_llm_prompt_with_text" not in blob


def test_write_overlay_requires_confirm(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    blocks_path = tmp_path / "all_blocks_merged.json"
    blocks_path.write_text(json.dumps({"blocks": [_mk_block("b1", "theory")]}), encoding="utf-8")
    monkeypatch.setattr(
        kb_llm_enrichment,
        "_evaluate_preflight",
        lambda: {"preflight_passed": True, "reasons": [], "observed": {}},
    )

    with pytest.raises(RuntimeError, match="requires --confirm"):
        run_enrichment(
            source_hint="КУЗНИЦА ДУХА",
            blocks_path=blocks_path,
            output_dir=tmp_path / "logs",
            reports_dir=tmp_path / "reports",
            prompt_path=tmp_path / "prompt.md",
            limit=1,
            offset=0,
            chunk_type_filter="",
            dry_run=False,
            write_overlay=True,
            apply_changes=False,
            confirm=False,
            mock_llm=True,
            max_concurrency=1,
            max_retries=1,
            timeout_seconds=5.0,
        )
