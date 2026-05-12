from __future__ import annotations

import json
from pathlib import Path

from tools.source_hygiene_apply import build_hygiene_plan, run_apply_cli


def test_build_hygiene_plan_blocks_focus_mutation() -> None:
    audit_payload = {
        "sources": [
            {
                "source_id": "123__кузница_духа",
                "is_focus_source": True,
                "recommended_hygiene_action": "archive",
                "status": "done",
                "blocks_count": 229,
                "reason": ["focus_source_protected"],
            }
        ]
    }
    plan = build_hygiene_plan(audit_payload=audit_payload, source_prd="PRD-046.0.7-HF1")
    assert plan["valid"] is False
    assert plan["focus_source_protected"] is False
    assert any("focus_source_protection_violation" in err for err in plan["errors"])


def test_run_apply_cli_dry_run_no_mutation(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path
    botdb = repo_root / "Bot_data_base"
    (botdb / "data").mkdir(parents=True, exist_ok=True)
    registry_path = botdb / "data" / "registry.json"
    registry_path.write_text(
        json.dumps(
            [
                {
                    "source_id": "test123",
                    "source_type": "youtube",
                    "title": "",
                    "author": "Автор",
                    "author_id": "a",
                    "language": "ru",
                    "status": "processing",
                    "added_at": "2026-05-10T00:00:00",
                    "processed_at": None,
                    "blocks_count": 0,
                    "sd_distribution": {},
                    "file_paths": {},
                    "error_message": None,
                    "pipeline_version": "v1",
                }
            ],
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    audit_json = repo_root / "out" / "audit.json"
    audit_json.parent.mkdir(parents=True, exist_ok=True)
    audit_json.write_text(
        json.dumps(
            {
                "sources": [
                    {
                        "source_id": "test123",
                        "is_focus_source": False,
                        "recommended_hygiene_action": "archive",
                        "status": "processing",
                        "blocks_count": 0,
                        "reason": ["processing_stale"],
                    }
                ]
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    monkeypatch.chdir(repo_root)
    plan_json = repo_root / "out" / "plan.json"
    result_json = repo_root / "out" / "apply_result.json"
    report_md = repo_root / "out" / "plan.md"
    result = run_apply_cli(
        audit_json=audit_json,
        plan_json=plan_json,
        apply_result_json=result_json,
        report_md=report_md,
        source_prd="PRD-046.0.7-HF1",
        mode="dry_run",
        confirm=False,
        allow_safe_delete_zero_block=False,
    )
    assert result["mode"] == "dry_run"
    assert result["mutated"] is False
    assert json.loads(registry_path.read_text(encoding="utf-8"))[0]["status"] == "processing"


def test_run_apply_cli_requires_confirm_for_apply(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path
    botdb = repo_root / "Bot_data_base"
    (botdb / "data").mkdir(parents=True, exist_ok=True)
    (botdb / "data" / "registry.json").write_text("[]", encoding="utf-8")
    audit_json = repo_root / "out" / "audit.json"
    audit_json.parent.mkdir(parents=True, exist_ok=True)
    audit_json.write_text(json.dumps({"sources": []}, ensure_ascii=False), encoding="utf-8")
    monkeypatch.chdir(repo_root)
    result = run_apply_cli(
        audit_json=audit_json,
        plan_json=repo_root / "out" / "plan.json",
        apply_result_json=repo_root / "out" / "apply_result.json",
        report_md=repo_root / "out" / "plan.md",
        source_prd="PRD-046.0.7-HF1",
        mode="apply",
        confirm=False,
        allow_safe_delete_zero_block=False,
    )
    assert result["valid"] is False
    assert "confirm_required_for_apply_mode" in result["errors"]
