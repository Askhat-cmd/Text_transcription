from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _run(mode: str, log_dir: Path) -> tuple[int, dict]:
    script = Path(__file__).resolve().parents[1] / "scripts" / "run_prd_047_10_hf2_followup_reliability.py"
    cmd = [
        sys.executable,
        str(script),
        "--mode",
        mode,
        "--log-dir",
        str(log_dir),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    payload = json.loads(proc.stdout.strip()) if proc.stdout.strip() else {}
    return proc.returncode, payload


def test_runner_dry_mode_passes(tmp_path: Path) -> None:
    code, payload = _run("dry", tmp_path)
    assert code == 0
    assert payload.get("status") == "passed"


def test_runner_direct_mode_passes(tmp_path: Path) -> None:
    code, payload = _run("direct", tmp_path)
    assert code == 0
    assert payload.get("status") == "passed"
