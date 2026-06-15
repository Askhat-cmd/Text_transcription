from __future__ import annotations

import argparse
import json
from pathlib import Path

from tools.run_mechanism_metadata_audit import run


def test_fixture_mode_creates_required_artifacts(tmp_path: Path) -> None:
    result = run(
        argparse.Namespace(
            mode="fixture",
            limit=10,
            out_dir=str(tmp_path),
        )
    )
    assert result["audit"]["fixture_chunks_checked"] >= 1
    assert (tmp_path / "mechanism_metadata_schema_snapshot.json").exists()
    assert (tmp_path / "mechanism_metadata_audit.json").exists()
    assert (tmp_path / "mechanism_metadata_audit.md").exists()
    assert (tmp_path / "sample_normalized_chunks.json").exists()
    assert (tmp_path / "chunk_type_distribution.json").exists()
    assert (tmp_path / "metadata_completeness_report.json").exists()
    assert (tmp_path / "anti_heuristic_compliance_report.json").exists()
    assert (tmp_path / "no_mutation_proof.json").exists()
    assert (tmp_path / "encoding_hygiene_report.json").exists()


def test_runner_outputs_are_sanitized(tmp_path: Path) -> None:
    run(argparse.Namespace(mode="fixture", limit=10, out_dir=str(tmp_path)))
    sample_payload = json.loads((tmp_path / "sample_normalized_chunks.json").read_text(encoding="utf-8"))
    audit_md = (tmp_path / "mechanism_metadata_audit.md").read_text(encoding="utf-8")
    assert sample_payload
    assert "text" not in sample_payload[0]
    assert "очень длинный" not in audit_md
