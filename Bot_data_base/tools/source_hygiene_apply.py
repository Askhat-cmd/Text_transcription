from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_SOURCE_PRD = "PRD-046.0.7-HF1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize(value: Any) -> str:
    return str(value or "").strip()


def _to_int(value: Any) -> int:
    try:
        return int(value)
    except Exception:
        return 0


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _save_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _save_markdown(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def build_hygiene_plan(
    *,
    audit_payload: dict[str, Any],
    source_prd: str,
) -> dict[str, Any]:
    sources = audit_payload.get("sources") or []
    planned_actions: list[dict[str, Any]] = []
    errors: list[str] = []
    warnings: list[str] = []
    blocked_actions_count = 0
    archive_count = 0
    delete_count = 0
    focus_source_protected = True

    for row in sources:
        source_id = _normalize(row.get("source_id"))
        action = _normalize(row.get("recommended_hygiene_action"))
        status = _normalize(row.get("status"))
        blocks_count = _to_int(row.get("blocks_count"))
        is_focus = bool(row.get("is_focus_source"))
        reason = list(row.get("reason") or [])

        if action not in {"archive", "safe_delete_zero_block", "keep", "manual_review"}:
            warnings.append(f"unknown_action:{source_id}:{action}")
            action = "manual_review"

        if is_focus and action in {"archive", "safe_delete_zero_block"}:
            focus_source_protected = False
            blocked_actions_count += 1
            errors.append(f"focus_source_protection_violation:{source_id}")
            action = "keep"

        if blocks_count > 0 and action == "safe_delete_zero_block":
            blocked_actions_count += 1
            errors.append(f"unsafe_delete_non_zero_block_source:{source_id}")
            action = "manual_review"

        if action == "archive":
            archive_count += 1
        elif action == "safe_delete_zero_block":
            delete_count += 1

        planned_actions.append(
            {
                "source_id": source_id,
                "status": status,
                "blocks_count": blocks_count,
                "is_focus_source": is_focus,
                "action": action,
                "reason": reason,
            }
        )

    return {
        "schema_version": "source_hygiene_plan_v1",
        "source_prd": source_prd,
        "generated_at": _utc_now(),
        "mode": "dry_run",
        "valid": len(errors) == 0,
        "focus_source_protected": focus_source_protected,
        "planned_actions": planned_actions,
        "planned_archive_count": archive_count,
        "planned_safe_delete_zero_block_count": delete_count,
        "blocked_actions_count": blocked_actions_count,
        "errors": errors,
        "warnings": warnings,
    }


def _snapshot_inputs(
    *,
    backup_dir: Path,
    registry_path: Path,
    audit_payload: dict[str, Any],
) -> None:
    backup_dir.mkdir(parents=True, exist_ok=True)
    registry_snapshot = backup_dir / "registry_snapshot_before.json"
    inventory_snapshot = backup_dir / "source_inventory_before.json"
    registry_snapshot.write_text(registry_path.read_text(encoding="utf-8"), encoding="utf-8")
    inventory_snapshot.write_text(
        json.dumps(audit_payload.get("sources") or [], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _apply_archive(
    *,
    registry_records: list[dict[str, Any]],
    plan: dict[str, Any],
) -> tuple[list[dict[str, Any]], int]:
    by_source_plan: dict[str, dict[str, Any]] = {}
    for item in plan.get("planned_actions") or []:
        source_id = _normalize(item.get("source_id"))
        if not source_id:
            continue
        action = _normalize(item.get("action"))
        slot = by_source_plan.setdefault(
            source_id,
            {"action": "keep", "is_focus_source": False, "reason": []},
        )
        slot["is_focus_source"] = bool(slot.get("is_focus_source")) or bool(item.get("is_focus_source"))
        current_action = _normalize(slot.get("action"))
        if action == "archive":
            slot["action"] = "archive"
        elif action == "safe_delete_zero_block" and current_action not in {"archive"}:
            slot["action"] = "safe_delete_zero_block"
        elif action == "manual_review" and current_action not in {"archive", "safe_delete_zero_block"}:
            slot["action"] = "manual_review"
        for reason in item.get("reason") or []:
            value = str(reason)
            if value not in slot["reason"]:
                slot["reason"].append(value)

    mutated = 0
    updated: list[dict[str, Any]] = []
    for row in registry_records:
        source_id = _normalize(row.get("source_id"))
        source_plan = by_source_plan.get(source_id) or {}
        action = _normalize(source_plan.get("action"))
        blocks_count = _to_int(row.get("blocks_count"))
        is_focus = bool(source_plan.get("is_focus_source"))
        reasons = [str(value) for value in (source_plan.get("reason") or [])]
        allow_archive_registry_only = "registry_only_blocks_test_like" in reasons

        can_archive = blocks_count <= 0 or allow_archive_registry_only
        if action == "archive" and not is_focus and can_archive and _normalize(row.get("status")) != "archived":
            row = dict(row)
            row["status"] = "archived"
            mutated += 1
        updated.append(row)
    return updated, mutated


def _render_plan_report(plan: dict[str, Any], result: dict[str, Any], source_prd: str) -> str:
    heading = "SOURCE HYGIENE APPLY REPORT" if _normalize(result.get("mode")) == "apply" else "SOURCE HYGIENE PLAN REPORT"
    lines = [
        f"# {source_prd} {heading}",
        "",
        "## Plan Summary",
        f"- mode: `{result.get('mode')}`",
        f"- valid: `{result.get('valid')}`",
        f"- mutated: `{result.get('mutated')}`",
        f"- focus_source_protected: `{result.get('focus_source_protected')}`",
        f"- planned_archive_count: `{plan.get('planned_archive_count', 0)}`",
        f"- planned_safe_delete_zero_block_count: `{plan.get('planned_safe_delete_zero_block_count', 0)}`",
        f"- blocked_actions_count: `{plan.get('blocked_actions_count', 0)}`",
        "",
        "## Errors",
    ]
    errors = result.get("errors") or []
    lines.extend([f"- `{err}`" for err in errors] or ["- none"])
    lines.extend(["", "## Warnings"])
    warnings = result.get("warnings") or []
    lines.extend([f"- `{warn}`" for warn in warnings] or ["- none"])
    lines.extend(["", "## Planned Actions", "| source_id | status | blocks | action |", "| --- | --- | ---: | --- |"])
    for action in plan.get("planned_actions") or []:
        lines.append(
            f"| `{action.get('source_id','')}` | `{action.get('status','')}` | {int(action.get('blocks_count') or 0)} | `{action.get('action','')}` |"
        )
    lines.append("")
    return "\n".join(lines)


def run_apply_cli(
    *,
    audit_json: Path,
    plan_json: Path,
    apply_result_json: Path,
    report_md: Path,
    source_prd: str,
    mode: str,
    confirm: bool,
    allow_safe_delete_zero_block: bool,
) -> dict[str, Any]:
    root = Path.cwd()
    botdb_dir = root / "Bot_data_base"
    registry_path = botdb_dir / "data" / "registry.json"
    backup_dir = apply_result_json.parent / "backups"

    audit_payload = _load_json(audit_json)
    plan = build_hygiene_plan(audit_payload=audit_payload, source_prd=source_prd)
    plan["mode"] = mode

    if mode == "apply" and not confirm:
        result = {
            "schema_version": "source_hygiene_apply_result_v1",
            "source_prd": source_prd,
            "generated_at": _utc_now(),
            "mode": mode,
            "valid": False,
            "mutated": False,
            "focus_source_protected": bool(plan.get("focus_source_protected")),
            "errors": list(plan.get("errors") or []) + ["confirm_required_for_apply_mode"],
            "warnings": plan.get("warnings") or [],
        }
        _save_json(plan_json, plan)
        _save_json(apply_result_json, result)
        _save_markdown(report_md, _render_plan_report(plan, result, source_prd))
        return result

    registry_records = _load_json(registry_path) if registry_path.exists() else []
    if not isinstance(registry_records, list):
        registry_records = []

    mutated = False
    mutation_count = 0
    apply_after_payload: dict[str, Any] | None = None

    if mode == "apply" and bool(plan.get("valid")):
        _snapshot_inputs(backup_dir=backup_dir, registry_path=registry_path, audit_payload=audit_payload)
        updated_records, archive_updates = _apply_archive(registry_records=registry_records, plan=plan)
        mutation_count += int(archive_updates)

        if allow_safe_delete_zero_block:
            keep_ids = {
                _normalize(item.get("source_id"))
                for item in plan.get("planned_actions") or []
                if _normalize(item.get("action")) != "safe_delete_zero_block"
            }
            before = len(updated_records)
            updated_records = [
                row for row in updated_records if _normalize(row.get("source_id")) in keep_ids
            ]
            mutation_count += max(0, before - len(updated_records))
        elif int(plan.get("planned_safe_delete_zero_block_count") or 0) > 0:
            plan_warnings = list(plan.get("warnings") or [])
            plan_warnings.append("safe_delete_zero_block_skipped_without_allow_flag")
            plan["warnings"] = plan_warnings

        if mutation_count > 0:
            registry_path.write_text(
                json.dumps(updated_records, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            mutated = True

        apply_after_payload = {
            "schema_version": "source_hygiene_apply_after_v1",
            "source_prd": source_prd,
            "generated_at": _utc_now(),
            "records_count": len(updated_records),
            "archived_count": sum(1 for row in updated_records if _normalize(row.get("status")) == "archived"),
        }
        _save_json(apply_result_json.parent / "source_hygiene_apply_after.json", apply_after_payload)

    result = {
        "schema_version": "source_hygiene_apply_result_v1",
        "source_prd": source_prd,
        "generated_at": _utc_now(),
        "mode": mode,
        "valid": bool(plan.get("valid")),
        "mutated": mutated,
        "registry_mutated": mutated,
        "focus_source_protected": bool(plan.get("focus_source_protected")),
        "planned_archive_count": int(plan.get("planned_archive_count") or 0),
        "planned_safe_delete_zero_block_count": int(plan.get("planned_safe_delete_zero_block_count") or 0),
        "blocked_actions_count": int(plan.get("blocked_actions_count") or 0),
        "applied_mutation_count": mutation_count,
        "errors": plan.get("errors") or [],
        "warnings": plan.get("warnings") or [],
    }
    if apply_after_payload is not None:
        result["apply_after"] = apply_after_payload

    _save_json(plan_json, plan)
    _save_json(apply_result_json, result)
    _save_markdown(report_md, _render_plan_report(plan, result, source_prd))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Safe archive/delete planning for source hygiene.")
    parser.add_argument(
        "--audit-json",
        default="TO_DO_LIST/logs/PRD-046.0.7-HF1/source_hygiene_audit.json",
    )
    parser.add_argument(
        "--plan-json",
        default="TO_DO_LIST/logs/PRD-046.0.7-HF1/source_hygiene_plan.json",
    )
    parser.add_argument(
        "--apply-result-json",
        default="TO_DO_LIST/logs/PRD-046.0.7-HF1/source_hygiene_apply_result.json",
    )
    parser.add_argument(
        "--output-md",
        default="TO_DO_LIST/reports/PRD-046.0.7-HF1_SOURCE_HYGIENE_PLAN_REPORT.md",
    )
    parser.add_argument("--source-prd", default=DEFAULT_SOURCE_PRD)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm", action="store_true")
    parser.add_argument("--allow-safe-delete-zero-block", action="store_true")
    args = parser.parse_args()

    mode = "apply" if args.apply else "dry_run"
    if args.dry_run:
        mode = "dry_run"

    payload = run_apply_cli(
        audit_json=Path(args.audit_json),
        plan_json=Path(args.plan_json),
        apply_result_json=Path(args.apply_result_json),
        report_md=Path(args.output_md),
        source_prd=args.source_prd,
        mode=mode,
        confirm=bool(args.confirm),
        allow_safe_delete_zero_block=bool(args.allow_safe_delete_zero_block),
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
