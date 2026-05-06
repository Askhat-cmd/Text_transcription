from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
RUNNER_PATH = REPO_ROOT / "bot_psychologist" / "scripts" / "run_state_analyzer_calibration.py"
DATASET_PATH = REPO_ROOT / "bot_psychologist" / "tests" / "calibration" / "state_analyzer_calibration_cases.json"


def _load_runner_module():
    spec = importlib.util.spec_from_file_location("run_state_analyzer_calibration", RUNNER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_runner_module_imports() -> None:
    module = _load_runner_module()
    assert hasattr(module, "main")
    assert callable(module.main)
    assert hasattr(module, "_severity_from_case")
    assert callable(module._severity_from_case)


def test_runner_dry_run_creates_reports(tmp_path: Path) -> None:
    json_report = tmp_path / "calibration_report.json"
    md_report = tmp_path / "calibration_report.md"

    result = subprocess.run(
        [
            sys.executable,
            str(RUNNER_PATH),
            "--mode",
            "dry-run",
            "--dataset",
            str(DATASET_PATH),
            "--output",
            str(json_report),
            "--markdown-output",
            str(md_report),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + "\n" + result.stderr
    assert json_report.exists()
    assert md_report.exists()

    report = json.loads(json_report.read_text(encoding="utf-8"))
    assert report["run_metadata"]["mode"] == "dry-run"
    assert report["run_metadata"]["cases_total"] >= 60
    assert "summary" in report


def test_severity_rules_detect_high_mismatch() -> None:
    module = _load_runner_module()
    case = {"category": "low_resource_support", "tags": ["contact", "hypo"]}
    expected = {
        "nervous_state": "hypo",
        "intent": "contact",
        "openness": "mixed",
        "ok_position": "I+W+",
        "response_mode_new_thread": "validate",
        "confidence_min": 0.65,
    }
    actual = {
        "nervous_state": "window",
        "intent": "clarify",
        "openness": "open",
        "ok_position": "I+W+",
        "response_mode_new_thread": "reflect",
        "confidence": 0.82,
    }
    matches = {
        "nervous_state": False,
        "intent": False,
        "openness": False,
        "ok_position": True,
        "response_mode_new_thread": False,
    }
    severity, note = module._severity_from_case(
        case=case,
        expected=expected,
        actual=actual,
        matches=matches,
        confidence_ok=True,
    )
    assert severity == "high"
    assert "Low-resource/contact" in note


def test_confusion_matrix_accumulates() -> None:
    module = _load_runner_module()
    confusion = {"intent": {}}
    module._update_confusion(confusion, field="intent", expected="contact", actual="contact")
    module._update_confusion(confusion, field="intent", expected="contact", actual="clarify")
    module._update_confusion(confusion, field="intent", expected="contact", actual="clarify")
    sorted_confusion = module._sorted_confusion(confusion)
    assert sorted_confusion["intent"]["contact"]["contact"] == 1
    assert sorted_confusion["intent"]["contact"]["clarify"] == 2
