from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import validate_prd_artifact_encoding as validator


def _make_base_dirs(tmp_path: Path) -> tuple[Path, Path]:
    logs_dir = tmp_path / "TO_DO_LIST" / "logs" / "PRD-046.1.2"
    reports_dir = tmp_path / "TO_DO_LIST" / "reports"
    logs_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir, reports_dir


def test_validator_passes_clean_utf8_text_json_md(tmp_path: Path) -> None:
    logs_dir, reports_dir = _make_base_dirs(tmp_path)
    (logs_dir / "test_command_output.txt").write_text("ok\n", encoding="utf-8")
    (logs_dir / "sample.json").write_text(json.dumps({"k": "v"}, ensure_ascii=False), encoding="utf-8")
    (reports_dir / "PRD-046.1.2_IMPLEMENTATION_REPORT.md").write_text("# report\nok\n", encoding="utf-8")

    out_dir = tmp_path / "out"
    report = validator.run(
        argparse.Namespace(
            prd="PRD-046.1.2",
            logs_dir=str(logs_dir),
            reports_dir=str(reports_dir),
            out_dir=str(out_dir),
            report_prd="PRD-046.1.2-HF1",
            repo_root=str(tmp_path),
            fixed_file=[],
        )
    )
    assert report["final_status"] == "passed"
    assert report["utf8_decode_error_count"] == 0
    assert report["nul_byte_file_count"] == 0
    assert report["nul_char_file_count"] == 0
    assert report["json_parse_error_count"] == 0


def test_validator_detects_nul_bytes_and_nul_chars(tmp_path: Path) -> None:
    logs_dir, reports_dir = _make_base_dirs(tmp_path)
    _ = reports_dir
    (logs_dir / "bad.txt").write_bytes(b"a\x00b\x00")
    report = validator.run(
        argparse.Namespace(
            prd="PRD-046.1.2",
            logs_dir=str(logs_dir),
            reports_dir=str(reports_dir),
            out_dir=str(tmp_path / "out"),
            report_prd="PRD-046.1.2-HF1",
            repo_root=str(tmp_path),
            fixed_file=[],
        )
    )
    assert report["final_status"] == "failed"
    assert report["nul_byte_file_count"] == 1
    assert report["nul_char_file_count"] == 1


def test_validator_detects_invalid_utf8_and_invalid_json(tmp_path: Path) -> None:
    logs_dir, reports_dir = _make_base_dirs(tmp_path)
    _ = reports_dir
    (logs_dir / "invalid_utf8.txt").write_bytes(b"\xff\xfe\xfd")
    (logs_dir / "invalid_json.json").write_text("{broken-json", encoding="utf-8")
    report = validator.run(
        argparse.Namespace(
            prd="PRD-046.1.2",
            logs_dir=str(logs_dir),
            reports_dir=str(reports_dir),
            out_dir=str(tmp_path / "out"),
            report_prd="PRD-046.1.2-HF1",
            repo_root=str(tmp_path),
            fixed_file=[],
        )
    )
    assert report["final_status"] == "failed"
    assert report["utf8_decode_error_count"] == 1
    assert report["json_parse_error_count"] == 1


def test_validator_detects_unexpected_debug_dir(tmp_path: Path) -> None:
    logs_dir, reports_dir = _make_base_dirs(tmp_path)
    (logs_dir / "ok.txt").write_text("ok", encoding="utf-8")
    (logs_dir.parent / "PRD-046.1.2-debug").mkdir(parents=True, exist_ok=True)
    report = validator.run(
        argparse.Namespace(
            prd="PRD-046.1.2",
            logs_dir=str(logs_dir),
            reports_dir=str(reports_dir),
            out_dir=str(tmp_path / "out"),
            report_prd="PRD-046.1.2-HF1",
            repo_root=str(tmp_path),
            fixed_file=[],
        )
    )
    assert report["final_status"] == "failed"
    assert report["unexpected_debug_dir_count"] == 1


def test_validator_main_returns_non_zero_for_blockers(tmp_path: Path) -> None:
    logs_dir, reports_dir = _make_base_dirs(tmp_path)
    (logs_dir / "bad.txt").write_bytes(b"\xff\xfe\xfd")
    out_dir = tmp_path / "out"
    cmd = [
        sys.executable,
        "-m",
        "bot_psychologist.tools.validate_prd_artifact_encoding",
        "--prd",
        "PRD-046.1.2",
        "--logs-dir",
        str(logs_dir),
        "--reports-dir",
        str(reports_dir),
        "--out-dir",
        str(out_dir),
        "--repo-root",
        str(tmp_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    assert result.returncode == 2

