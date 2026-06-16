from __future__ import annotations

import argparse
import json
from pathlib import Path

from tools.run_mechanism_metadata_enrichment import run


def test_deterministic_runner_creates_required_artifacts(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports"
    result = run(
        argparse.Namespace(
            mode="deterministic",
            source="kuznica",
            limit=6,
            out_dir=str(tmp_path),
            reports_dir=str(reports_dir),
            confirm_provider=False,
        )
    )
    assert result["status"] in {"passed", "warning"}
    required = [
        "source_audit.json",
        "source_audit.md",
        "kuznica_source_profile.json",
        "kuznica_source_profile.md",
        "kuznica_chapter_coverage_report.json",
        "kuznica_chapter_coverage_report.md",
        "enrichment_schema_snapshot.json",
        "enrichment_candidates_deterministic.json",
        "enrichment_candidates_sample.md",
        "enrichment_quality_report.json",
        "enrichment_quality_report.md",
        "manual_review_pack.json",
        "manual_review_pack.md",
        "anti_heuristic_compliance_report.json",
        "no_mutation_proof.json",
        "encoding_hygiene_report.json",
        "llm_enrichment_skipped.json",
    ]
    for relative in required:
        assert (tmp_path / relative).exists(), relative


def test_runner_outputs_are_sanitized(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports"
    run(
        argparse.Namespace(
            mode="deterministic",
            source="kuznica",
            limit=4,
            out_dir=str(tmp_path),
            reports_dir=str(reports_dir),
            confirm_provider=False,
        )
    )
    payload = json.loads((tmp_path / "enrichment_candidates_deterministic.json").read_text(encoding="utf-8"))
    serialized = json.dumps(payload, ensure_ascii=False)
    assert "content_full" not in serialized
    assert "raw_provider_payload" not in serialized
    assert payload["candidate_count"] == len(payload["candidates"])
    assert payload["candidate_count"] > 0


def test_llm_mode_without_confirm_skips_safely(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports"
    result = run(
        argparse.Namespace(
            mode="llm-candidate",
            source="kuznica",
            limit=2,
            out_dir=str(tmp_path),
            reports_dir=str(reports_dir),
            confirm_provider=False,
        )
    )
    assert result["status"] == "skipped"
    payload = json.loads((tmp_path / "llm_enrichment_skipped.json").read_text(encoding="utf-8"))
    assert payload["reason"] == "confirm_provider_flag_missing"
    assert payload["provider_llm_calls_used"] is False


def test_llm_mode_without_api_key_creates_skipped_artifact(tmp_path: Path, monkeypatch) -> None:
    reports_dir = tmp_path / "reports"
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    result = run(
        argparse.Namespace(
            mode="llm-candidate",
            source="kuznica",
            limit=2,
            out_dir=str(tmp_path),
            reports_dir=str(reports_dir),
            confirm_provider=True,
        )
    )
    assert result["status"] == "skipped"
    payload = json.loads((tmp_path / "llm_enrichment_skipped.json").read_text(encoding="utf-8"))
    assert payload["reason"] == "openai_api_key_missing"
