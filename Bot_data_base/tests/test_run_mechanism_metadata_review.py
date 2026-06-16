from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from tools.run_mechanism_metadata_review import run


def test_queue_mode_creates_queue_template_and_csv(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports"
    result = run(
        argparse.Namespace(
            mode="queue",
            source="kuznica",
            decisions_file="",
            out_dir=str(tmp_path),
            reports_dir=str(reports_dir),
            botdb_base_url="http://127.0.0.1:8003",
        )
    )
    assert result["status"] == "passed"
    required = [
        "review_queue.json",
        "review_queue.md",
        "review_queue.csv",
        "review_decisions_template.json",
        "review_decisions_template.md",
        "curation_status_report.json",
        "curation_status_report.md",
        "review_decision_validation_report.json",
        "review_decision_validation_report.md",
    ]
    for relative in required:
        assert (tmp_path / relative).exists(), relative
    queue_document = json.loads((tmp_path / "review_queue.json").read_text(encoding="utf-8"))
    assert queue_document["queue_count"] == 80
    with (tmp_path / "review_queue.csv").open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == [
            "candidate_id",
            "queue_priority",
            "chunk_type",
            "risk_level",
            "heading_path",
            "content_preview",
            "candidate_fields_preview",
            "manual_review_reasons",
            "validation_warnings",
            "recommended_reviewer_action",
        ]


def test_fixture_and_preview_modes_produce_non_live_overlay(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports"
    fixture_result = run(
        argparse.Namespace(
            mode="fixture",
            source="kuznica",
            decisions_file="",
            out_dir=str(tmp_path),
            reports_dir=str(reports_dir),
            botdb_base_url="http://127.0.0.1:8003",
        )
    )
    assert fixture_result["status"] == "passed"
    preview_result = run(
        argparse.Namespace(
            mode="preview",
            source="kuznica",
            decisions_file=str(tmp_path / "review_decisions_fixture.json"),
            out_dir=str(tmp_path),
            reports_dir=str(reports_dir),
            botdb_base_url="http://127.0.0.1:8003",
        )
    )
    assert preview_result["status"] == "passed"
    preview = json.loads((tmp_path / "curated_overlay_preview.json").read_text(encoding="utf-8"))
    summary = json.loads((tmp_path / "curated_overlay_summary.json").read_text(encoding="utf-8"))
    assert preview["live_apply_allowed"] is False
    assert preview["chroma_reindex_required_before_runtime_use"] is True
    assert summary["accepted_item_count"] == preview["summary"]["accepted_item_count"]
    assert summary["accepted_item_count"] > 0


def test_validate_mode_template_and_negative_fixture(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports"
    run(
        argparse.Namespace(
            mode="queue",
            source="kuznica",
            decisions_file="",
            out_dir=str(tmp_path),
            reports_dir=str(reports_dir),
            botdb_base_url="http://127.0.0.1:8003",
        )
    )
    template_result = run(
        argparse.Namespace(
            mode="validate",
            source="kuznica",
            decisions_file=str(tmp_path / "review_decisions_template.json"),
            out_dir=str(tmp_path),
            reports_dir=str(reports_dir),
            botdb_base_url="http://127.0.0.1:8003",
        )
    )
    assert template_result["status"] == "passed_with_no_accepted_fields"
    run(
        argparse.Namespace(
            mode="fixture",
            source="kuznica",
            decisions_file="",
            out_dir=str(tmp_path),
            reports_dir=str(reports_dir),
            botdb_base_url="http://127.0.0.1:8003",
        )
    )
    negative_result = run(
        argparse.Namespace(
            mode="validate",
            source="kuznica",
            decisions_file=str(tmp_path / "review_decisions_negative_fixture.json"),
            out_dir=str(tmp_path),
            reports_dir=str(reports_dir),
            botdb_base_url="http://127.0.0.1:8003",
        )
    )
    assert negative_result["status"] == "failed"


def test_full_mode_creates_required_artifacts(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports"
    result = run(
        argparse.Namespace(
            mode="full",
            source="kuznica",
            decisions_file="",
            out_dir=str(tmp_path),
            reports_dir=str(reports_dir),
            botdb_base_url="http://127.0.0.1:8003",
        )
    )
    assert result["status"] in {"passed", "warning"}
    required = [
        "source_gate_report.json",
        "source_gate_report.md",
        "review_queue.json",
        "review_queue.md",
        "review_queue.csv",
        "review_decisions_template.json",
        "review_decisions_template.md",
        "review_decisions_fixture.json",
        "review_decision_validation_report.json",
        "review_decision_validation_report.md",
        "curation_status_report.json",
        "curation_status_report.md",
        "curated_overlay_preview.json",
        "curated_overlay_preview.md",
        "curated_overlay_summary.json",
        "curated_overlay_summary.md",
        "anti_runtime_activation_report.json",
        "no_mutation_proof.json",
        "encoding_hygiene_report.json",
        "implementation_summary.json",
        "botdb_readonly_smoke.json",
    ]
    for relative in required:
        assert (tmp_path / relative).exists(), relative
