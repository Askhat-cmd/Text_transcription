from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
RUNNER_PATH = REPO_ROOT / "TO_DO_LIST" / "tools" / "run_prd_047_39_architecture_inventory.py"


def _load_runner():
    spec = importlib.util.spec_from_file_location("prd_047_39_runner", RUNNER_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_log_manifest_keeps_markdown_evidence() -> None:
    runner = _load_runner()

    tier = runner.classify_log_file(
        "TO_DO_LIST/logs/PRD-047.38/automated_owner_pilot_report.md",
        5000,
        referenced_by_name=False,
    )

    assert tier == "evidence_of_record"


def test_log_manifest_marks_png_as_raw_artifact() -> None:
    runner = _load_runner()

    tier = runner.classify_log_file(
        "TO_DO_LIST/logs/PRD-047.36-HF4/fresh_chat_after_reload.png",
        250000,
        referenced_by_name=False,
    )

    assert tier == "raw_artifact"


def test_legacy_sd_flag_is_retirement_candidate() -> None:
    runner = _load_runner()

    status = runner._propose_flag_status(
        "SD_LEGACY_ENABLED",
        [{"path": "bot_psychologist/bot_agent/runtime_config.py"}],
    )

    assert status == "retirement_candidate"
