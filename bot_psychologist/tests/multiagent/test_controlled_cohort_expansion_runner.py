from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_controlled_cohort_expansion as gate
from tools import run_diagnostic_center_controlled_cohort_expansion_provider_smoke as runner


def test_controlled_cohort_expansion_runner_outputs_required_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _fake_botdb(_: str) -> dict[str, object]:
        return {
            "botdb_preflight_passed": True,
            "dashboard_chroma_count": 247,
            "dashboard_chroma_status": "ok",
            "registry_sources_count": 1,
            "focus_source": gate.FOCUS_SOURCE_ID,
            "query_status_code": 200,
            "semantic_fallback_used": False,
            "botdb_circuit_open": False,
            "checks": {},
        }

    monkeypatch.setattr(gate, "build_botdb_preflight", _fake_botdb)
    out_dir = tmp_path / "out"
    result = runner.run(
        argparse.Namespace(
            repo_root=".",
            source_dirs=[
                "TO_DO_LIST/logs/PRD-046.1.23",
                "TO_DO_LIST/logs/PRD-046.1.24",
                "TO_DO_LIST/logs/PRD-046.1.25",
                "TO_DO_LIST/logs/PRD-046.1.26",
            ],
            reports_dir="TO_DO_LIST/reports",
            output_dir=str(out_dir),
            fixture_path="bot_psychologist/tests/fixtures/diagnostic_center_controlled_cohort_expansion_cases.json",
            admin_base_url="http://127.0.0.1:8003",
            provider_mode="mock",
            strict=True,
        )
    )
    assert result["status"] in {"passed", "blocked"}
    for name in (
        "source_gate.json",
        "botdb_preflight.json",
        "cohort_policy.json",
        "provider_execution_evidence.json",
        "provider_budget_gate.json",
        "normal_user_no_effect_gate.json",
        "quality_micro_shift_gate.json",
        "safety_kb_boundary_gate.json",
        "trace_provider_sanitization_gate.json",
        "rollback_gate.json",
        "botdb_stability_gate.json",
        "hard_stop_gate.json",
        "no_mutation_proof.json",
        "artifact_encoding_hygiene.json",
        "decision_gate.json",
        "test_command_output.txt",
    ):
        assert (out_dir / name).exists(), name

