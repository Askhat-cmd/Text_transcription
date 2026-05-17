from __future__ import annotations

import json
from pathlib import Path

import yaml

from tools import run_final_runtime_readiness_summary as runner


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _bootstrap_repo(tmp_path: Path) -> tuple[dict[str, Path], Path]:
    repo_root = tmp_path / "repo"
    logs_dir = repo_root / "TO_DO_LIST" / "logs" / "PRD-046.0.11"
    logs_dir.mkdir(parents=True, exist_ok=True)

    config = {
        "sd_labeling": {"enabled": False, "explicit_legacy_mode": False},
        "legacy_sd_labeling": {"enabled": False, "explicit_legacy_mode": False},
    }
    (repo_root / "Bot_data_base" / "data" / "processed").mkdir(parents=True, exist_ok=True)
    (repo_root / "Bot_data_base" / "data").mkdir(parents=True, exist_ok=True)
    (repo_root / "Bot_data_base").mkdir(parents=True, exist_ok=True)
    (repo_root / "docs").mkdir(parents=True, exist_ok=True)
    (repo_root / "TO_DO_LIST" / "reports").mkdir(parents=True, exist_ok=True)

    (repo_root / "Bot_data_base" / "config.yaml").write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    _write_json(repo_root / "Bot_data_base" / "data" / "processed" / "all_blocks_merged.json", {"blocks": [{"id": "1", "metadata": {}}]})
    _write_json(
        repo_root / "Bot_data_base" / "data" / "registry.json",
        [{"source_id": "123__кузница_духа", "status": "done", "blocks_count": 247, "title": "Кузница Духа"}],
    )

    project_state = """# Project State
Current Stage:
post-PRD-046.0.11-final-runtime-readiness-summary

User message -> State Analyzer -> Thread Manager -> Memory Retrieval -> Context Assembly -> Diagnostic Card -> Writer Move Compliance -> Writer -> Validator/Trace -> Memory Update.
Runtime работает без cascade legacy режима.
KB is an internal lens library, not a quote source.
"""
    (repo_root / "docs" / "PROJECT_STATE.md").write_text(project_state, encoding="utf-8")

    roadmap = """# Roadmap
## Done
- PRD-046.0.11: Final Runtime Readiness Summary v1 completed.

## Next
1. PRD-046.1 - Diagnostic Center v1 Readiness / Architecture PRD.
"""
    (repo_root / "docs" / "ROADMAP.md").write_text(roadmap, encoding="utf-8")
    (repo_root / "docs" / "PRD_INDEX.md").write_text("| PRD-046.0.11 | Final Runtime Readiness Summary v1 | passed | test | x | y |", encoding="utf-8")
    (repo_root / "docs" / "DECISIONS.md").write_text("# Decisions\n", encoding="utf-8")

    _write_json(
        repo_root / "TO_DO_LIST" / "logs" / "PRD-046.0.10-HF1" / "runtime_smoke_utf8.json",
        {"ok": True},
    )
    _write_json(
        repo_root / "TO_DO_LIST" / "logs" / "PRD-046.0.10-HF1" / "utf8_artifact_check.json",
        {"mojibake_markers_found": []},
    )
    _write_json(
        repo_root / "TO_DO_LIST" / "logs" / "PRD-046.0.10-HF1" / "sd_config_effective_state.json",
        {"legacy_sd_enabled_effective": False},
    )
    _write_json(
        repo_root / "TO_DO_LIST" / "logs" / "PRD-046.0.7.2-HF4" / "strict_quality_gate_hf4.json",
        {"quality_gate_passed": True},
    )
    _write_json(
        repo_root / "TO_DO_LIST" / "logs" / "PRD-046.0.7.2" / "retrieval_quality_smoke.json",
        {"retrieval_quality_passed": True, "raw_full_text_leak_detected": False, "internal_only_unsafe_exposure_count": 0},
    )
    _write_json(
        repo_root / "TO_DO_LIST" / "logs" / "PRD-046.0.6-HF1" / "retrieval_eval_scorecard.json",
        {
            "top5_semantic_match_rate": 1.0,
            "top5_governance_present_rate": 1.0,
            "raw_full_text_leak_detected": False,
            "internal_only_unsafe_exposure_count": 0,
            "weak_cases_count": 0,
        },
    )
    _write_json(
        repo_root / "TO_DO_LIST" / "logs" / "PRD-046.0.7.1" / "apply_result.json",
        {
            "apply_summary": {
                "text_changed_count": 0,
                "chunk_type_changed_count": 0,
                "allowed_use_changed_count": 0,
                "safety_flags_changed_count": 0,
                "source_id_changed_count": 0,
                "block_id_changed_count": 0,
                "governance_invariant_violations": 0,
            }
        },
    )

    paths = runner._required_paths(repo_root, logs_dir)
    return paths, logs_dir


def _ok_fetch(url: str) -> dict:
    registry_payload = {
        "sources": [
            {
                "source_id": "123__кузница_духа",
                "title": "Кузница Духа",
                "status": "done",
                "blocks_count": 247,
                "delete_policy": {"state": "protected"},
            }
        ]
    }
    dashboard_payload = {
        "blocks": {"production_total": 247},
        "chroma": {"count": 247},
        "governance": {"legacy_sd_active": False},
        "sources": {"active": 1},
    }
    if url.endswith("/api/registry/") or url.endswith("/api/registry"):
        return {"ok": True, "status_code": 200, "body": registry_payload, "error": None}
    if url.endswith("/api/dashboard/") or url.endswith("/api/dashboard"):
        return {"ok": True, "status_code": 200, "body": dashboard_payload, "error": None}
    return {"ok": True, "status_code": 200, "body": {"ok": True}, "error": None}


def _run(monkeypatch, tmp_path: Path, fetch=_ok_fetch, mutate=None):
    paths, logs_dir = _bootstrap_repo(tmp_path)
    if mutate is not None:
        mutate(paths)
    monkeypatch.setattr(runner, "REPO_ROOT", tmp_path / "repo")
    monkeypatch.setattr(runner, "BOTDB_DIR", tmp_path / "repo" / "Bot_data_base")
    monkeypatch.setattr(
        runner,
        "_required_paths",
        lambda _repo_root, _logs_dir: paths,
    )
    monkeypatch.setattr(
        runner,
        "run_diagnostic",
        lambda **_: {
            "status": "ok",
            "total_count": 247,
            "source_ids": ["123__кузница_духа"],
            "count_by_source_id": {"123__кузница_духа": 247},
            "errors": [],
            "warnings": [],
        },
    )
    args = runner.argparse.Namespace(
        base_url="http://127.0.0.1:8003",
        logs_dir=str(logs_dir),
        offline_docs_only=False,
        strict=True,
    )
    summary = runner.run(args, fetch_json=fetch)
    return summary, paths


def test_happy_path_passes_and_contains_required_domains(monkeypatch, tmp_path: Path) -> None:
    summary, _ = _run(monkeypatch, tmp_path)
    assert summary["final_status"] == "passed"
    assert summary["diagnostic_center_prerequisites_ready"] is True
    assert set(summary["domains"].keys()) == {
        "runtime",
        "admin_api",
        "knowledge_base",
        "chroma",
        "retrieval",
        "governance",
        "legacy_sd",
        "utf8",
        "docs",
        "no_mutation",
    }
    assert summary["domains"]["no_mutation"]["provider_called"] is False
    assert summary["domains"]["no_mutation"]["chroma_reindex_performed"] is False
    assert summary["domains"]["no_mutation"]["production_apply_performed"] is False


def test_endpoint_unreachable_produces_blocker(monkeypatch, tmp_path: Path) -> None:
    def _fetch(url: str) -> dict:
        if url.endswith("/api/status"):
            return {"ok": False, "status_code": None, "body": None, "error": "conn refused"}
        return _ok_fetch(url)

    summary, _ = _run(monkeypatch, tmp_path, fetch=_fetch)
    assert summary["final_status"] == "done_with_readiness_blocker"
    codes = {b["code"] for b in summary["blockers"]}
    assert "endpoint_unreachable" in codes


def test_chroma_mismatch_produces_blocker(monkeypatch, tmp_path: Path) -> None:
    def _fetch(url: str) -> dict:
        payload = _ok_fetch(url)
        if url.endswith("/api/dashboard") or url.endswith("/api/dashboard/"):
            payload["body"]["chroma"]["count"] = 229
        return payload

    summary, _ = _run(monkeypatch, tmp_path, fetch=_fetch)
    assert summary["final_status"] == "done_with_readiness_blocker"
    codes = {b["code"] for b in summary["blockers"]}
    assert "dashboard_chroma_count_mismatch" in codes


def test_missing_utf8_artifact_is_blocker(monkeypatch, tmp_path: Path) -> None:
    def _mutate(paths: dict[str, Path]) -> None:
        paths["utf8_artifact_check"].unlink()

    summary, _ = _run(monkeypatch, tmp_path, mutate=_mutate)
    assert summary["final_status"] == "done_with_readiness_blocker"
    assert any(b["code"] == "utf8_artifact_check_missing" for b in summary["blockers"])


def test_legacy_sd_enabled_is_blocker(monkeypatch, tmp_path: Path) -> None:
    def _mutate(paths: dict[str, Path]) -> None:
        cfg_path = paths["config"]
        cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
        cfg["sd_labeling"]["enabled"] = True
        cfg_path.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")

    summary, _ = _run(monkeypatch, tmp_path, mutate=_mutate)
    assert summary["final_status"] == "done_with_readiness_blocker"
    assert any(b["code"] == "sd_labeling_not_default_disabled" for b in summary["blockers"])


def test_docs_next_order_violation_is_blocker(monkeypatch, tmp_path: Path) -> None:
    def _mutate(paths: dict[str, Path]) -> None:
        paths["roadmap"].write_text(
            "# Roadmap\n## Done\n- PRD-046.0.11 completed\n\n## Next\n1. PRD-046.0.99 - wrong\n2. PRD-046.1\n",
            encoding="utf-8",
        )

    summary, _ = _run(monkeypatch, tmp_path, mutate=_mutate)
    assert summary["final_status"] == "done_with_readiness_blocker"
    assert any(b["code"] == "roadmap_next_order_invalid" for b in summary["blockers"])
