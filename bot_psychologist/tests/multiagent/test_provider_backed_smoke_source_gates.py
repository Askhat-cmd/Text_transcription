from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_diagnostic_center_provider_backed_smoke_readiness as runner


def test_provider_backed_smoke_source_gates_pass(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    runner.run(
        argparse.Namespace(
            repo_root=".",
            reports_dir="TO_DO_LIST/reports",
            logs_root="TO_DO_LIST/logs",
            output_dir=str(out_dir),
            admin_base_url="http://127.0.0.1:8003",
            strict=True,
        )
    )
    dc_gate = json.loads((out_dir / "diagnostic_center_source_gate.json").read_text(encoding="utf-8"))
    botdb_gate = json.loads((out_dir / "botdb_recovery_source_gate.json").read_text(encoding="utf-8"))
    assert dc_gate["diagnostic_center_source_gate_passed"] is True
    assert botdb_gate["botdb_recovery_source_gate_passed"] is True
