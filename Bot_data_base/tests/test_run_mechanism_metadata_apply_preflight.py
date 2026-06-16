from __future__ import annotations

import argparse
import json
from pathlib import Path
from uuid import uuid4

from tools.run_mechanism_metadata_apply_preflight import run


OVERLAY_FILE = "TO_DO_LIST/logs/PRD-047.18/curated_overlay_preview.json"


def _workspace_tmp() -> Path:
    repo_root = Path(__file__).resolve().parents[2]
    base = repo_root / ".tmp_pytest_prd_047_19"
    base.mkdir(parents=True, exist_ok=True)
    path = base / f"runner_{uuid4().hex}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_intake_mode_creates_reports() -> None:
    tmp_path = _workspace_tmp()
    reports_dir = tmp_path / "reports"
    result = run(
        argparse.Namespace(
            mode="intake",
            overlay_file=OVERLAY_FILE,
            out_dir=str(tmp_path),
            reports_dir=str(reports_dir),
            botdb_base_url="http://127.0.0.1:8003",
        )
    )
    assert result["status"] == "passed_fixture_only"
    assert (tmp_path / "overlay_intake_report.json").exists()
    assert (tmp_path / "overlay_intake_report.md").exists()


def test_plan_mode_creates_snapshot_and_plan() -> None:
    tmp_path = _workspace_tmp()
    reports_dir = tmp_path / "reports"
    result = run(
        argparse.Namespace(
            mode="plan",
            overlay_file=OVERLAY_FILE,
            out_dir=str(tmp_path),
            reports_dir=str(reports_dir),
            botdb_base_url="http://127.0.0.1:8003",
        )
    )
    assert result["status"] == "passed"
    assert (tmp_path / "field_mapping_snapshot.json").exists()
    assert (tmp_path / "dry_run_apply_plan.json").exists()
    assert (tmp_path / "dry_run_apply_plan.md").exists()


def test_preflight_mode_returns_expected_blockers() -> None:
    tmp_path = _workspace_tmp()
    reports_dir = tmp_path / "reports"
    result = run(
        argparse.Namespace(
            mode="preflight",
            overlay_file=OVERLAY_FILE,
            out_dir=str(tmp_path),
            reports_dir=str(reports_dir),
            botdb_base_url="http://127.0.0.1:8003",
        )
    )
    assert result["status"] == "passed_with_expected_blockers"
    payload = json.loads((tmp_path / "apply_preflight_report.json").read_text(encoding="utf-8"))
    assert payload["ready_for_live_apply"] is False
    assert "overlay_fixture_only" in payload["expected_blockers"]


def test_full_mode_creates_required_artifacts() -> None:
    tmp_path = _workspace_tmp()
    reports_dir = tmp_path / "reports"
    result = run(
        argparse.Namespace(
            mode="full",
            overlay_file=OVERLAY_FILE,
            out_dir=str(tmp_path),
            reports_dir=str(reports_dir),
            botdb_base_url="http://127.0.0.1:8003",
        )
    )
    assert result["status"] in {"passed_with_expected_blockers", "warning"}
    required = [
        "source_gate_report.json",
        "source_gate_report.md",
        "overlay_intake_report.json",
        "overlay_intake_report.md",
        "field_mapping_snapshot.json",
        "dry_run_apply_plan.json",
        "dry_run_apply_plan.md",
        "apply_preflight_report.json",
        "apply_preflight_report.md",
        "negative_overlay_missing_mapping.json",
        "negative_overlay_real_but_empty_source_preview.json",
        "negative_overlay_practice_without_contraindications.json",
        "anti_runtime_activation_report.json",
        "no_mutation_proof.json",
        "encoding_hygiene_report.json",
        "botdb_readonly_smoke.json",
    ]
    for relative in required:
        assert (tmp_path / relative).exists(), relative
