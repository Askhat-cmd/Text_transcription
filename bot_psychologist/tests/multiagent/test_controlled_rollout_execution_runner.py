from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_diagnostic_center_controlled_rollout_execution as runner  # noqa: E402


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_controlled_rollout_execution_runner(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path
    reports_dir = repo_root / "TO_DO_LIST" / "reports"
    logs_dir = repo_root / "TO_DO_LIST" / "logs"
    source_dir = logs_dir / "PRD-046.1.30"
    output_dir = logs_dir / "PRD-046.1.31"
    docs_dir = repo_root / "docs"

    _write(reports_dir / "PRD-046.1.30_IMPLEMENTATION_REPORT.md", "- final_status: `passed`\n- decision: `ready_for_controlled_rollout_execution_prd`\n- blockers: `none`\n- warnings: `none`\n- `no_mutation_proof_passed=true`\n- `docs_synced=true`\n")
    _write(reports_dir / "PRD-046.1.30_NEXT_PRD_RECOMMENDATION.md", "PRD-046.1.31")
    _write_json(
        source_dir / "scorecard.json",
        {
            "final_status": "passed",
            "decision": "ready_for_controlled_rollout_execution_prd",
            "blockers": [],
            "warnings": [],
            "no_mutation_proof_passed": True,
            "docs_synced": True,
            "broad_rollout_allowed": False,
            "production_ready": False,
            "normal_user_activation_allowed": False,
        },
    )
    _write_json(source_dir / "cohort_policy.json", {"max_target_users": 3})
    _write_json(source_dir / "controlled_rollout_plan.json", {"provider_call_budget_max": 12})
    _write(docs_dir / "PROJECT_STATE.md", "PRD-046.1.30")
    _write(
        docs_dir / "DIAGNOSTIC_CENTER_RUNTIME_MAP.md",
        "Broad rollout is disabled\nNormal-user activation is disabled\nProduction-ready declaration is not granted\nRollback-first\n",
    )
    _write(
        docs_dir / "DIAGNOSTIC_CENTER_EVAL_HARNESS.md",
        "Rollback and hard-stop gates\nSafety/KB boundary and trace/provider sanitization gates\nBotDB stability gates\nArtifact encoding hygiene validation\n",
    )
    _write(docs_dir / "ROADMAP.md", "PRD-046.1.30")
    _write(docs_dir / "PRD_INDEX.md", "PRD-046.1.30")
    _write(docs_dir / "DECISIONS.md", "ADR-049")

    monkeypatch.setattr(
        runner.execution,
        "build_botdb_stability_gate",
        lambda _url: {
            "gate_passed": True,
            "botdb_live_reachable": True,
            "registry_source_count": 1,
            "dashboard_chroma_status": "ok",
            "dashboard_chroma_count": 247,
            "query_endpoint_status": 200,
            "semantic_fallback_used": False,
            "botdb_circuit_open": False,
            "blocker_reason": "",
            "live_probe": {},
        },
    )

    args = argparse.Namespace(
        repo_root=str(repo_root),
        reports_dir=str(reports_dir),
        docs_dir=str(docs_dir),
        logs_dir=str(logs_dir),
        source_dir=str(source_dir),
        output_dir=str(output_dir),
        admin_base_url="http://127.0.0.1:8003",
        strict=True,
    )
    result = runner.run(args)
    assert result["status"] == "passed"
    assert (output_dir / "controlled_rollout_decision.json").exists()
