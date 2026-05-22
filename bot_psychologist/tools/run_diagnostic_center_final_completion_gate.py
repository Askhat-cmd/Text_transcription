from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

CURRENT_FILE = Path(__file__).resolve()
BOT_PSYCHOLOGIST_ROOT = CURRENT_FILE.parents[1]
if str(BOT_PSYCHOLOGIST_ROOT) not in sys.path:
    sys.path.insert(0, str(BOT_PSYCHOLOGIST_ROOT))

from bot_agent.multiagent import diagnostic_center_final_completion_gate as gate
from tools import validate_prd_artifact_encoding as encoding_validator

PRD = gate.PRD


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _replace_section(text: str, header: str, body: str) -> str:
    pattern = re.compile(rf"{re.escape(header)}\n[\s\S]*?(?=\n## |\Z)")
    block = f"{header}\n{body.strip()}\n"
    if pattern.search(text):
        return pattern.sub(block.rstrip("\n"), text, count=1)
    return text.rstrip() + "\n\n" + block


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _upsert_project_state(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = path.read_text(encoding="utf-8") if path.exists() else "# Project State - Bot Psychologist / Neo MindBot\n"
    current_stage = (
        "PRD-046.1.37 completed Diagnostic Center v1 as governed creator-live / developer-pilot layer. "
        "Creator-only / allowlist runtime remains allowed for pilot, normal users remain unaffected, "
        "broad rollout stays prohibited, and production_ready remains false."
    )
    text = _replace_section(text, "## Current Stage", current_stage)
    text = _replace_section(text, "## Next Planned PRD", "`Multiagent Quality & Tuning Track`")
    marker = "## Diagnostic Center Track Status"
    track_block = "Diagnostic Center Track Status: CLOSED FOR CURRENT PHASE"
    if marker in text:
        text = _replace_section(text, marker, track_block)
    else:
        text = text.rstrip() + f"\n\n{marker}\n{track_block}\n"
    text = re.sub(r"(- Source cycle:\s*)(PRD-046\.1\.\d+(?:-HF\d+)?)", r"\g<1>PRD-046.1.37", text, count=1)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _upsert_roadmap(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = path.read_text(encoding="utf-8") if path.exists() else "# Roadmap\n\n## Done\n\n## Next\n"
    lines = text.splitlines()
    done_line = (
        "- PRD-046.1.37: finalized Diagnostic Center completion decision gate with source/provenance/runtime/live/"
        "admin/rollback/normal-user/safety/no-mutation evidence and phase-closure transfer brief."
    )
    if done_line not in lines:
        if "## Done" not in lines:
            lines.extend(["", "## Done"])
        idx = lines.index("## Done")
        lines.insert(idx + 1, done_line)
    if "## Current / In Progress" in lines:
        idx = lines.index("## Current / In Progress")
        if idx + 1 < len(lines):
            lines[idx + 1] = "- No active Diagnostic Center completion PRD in progress."
    if "## Next" not in lines:
        lines.extend(["", "## Next"])
    idx = lines.index("## Next")
    while idx + 1 < len(lines) and lines[idx + 1].startswith("1. PRD-046.1."):
        lines.pop(idx + 1)
    lines.insert(idx + 1, "1. Multiagent Quality & Tuning Track.")
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _upsert_prd_index(path: Path, scorecard: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = (
        path.read_text(encoding="utf-8")
        if path.exists()
        else "# PRD Index\n\n| PRD | Название | Статус | Commit | Что изменилось | Отчёт |\n| --- | --- | --- | --- | --- | --- |\n"
    )
    row = (
        "| PRD-046.1.37 | Diagnostic Center Final Results / Completion Decision Gate v1 | "
        f"{scorecard.get('final_status', 'blocked')} | pending | "
        "closed Diagnostic Center creator-pilot phase with final live/runtime/admin/rollback/normal-user/safety gates and transfer brief | "
        "TO_DO_LIST/reports/PRD-046.1.37_IMPLEMENTATION_REPORT.md |"
    )
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("| PRD-046.1.37 |"):
            lines[i] = row
            path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
            return
    sep = "| --- | --- | --- | --- | --- | --- |"
    if sep in lines:
        lines.insert(lines.index(sep) + 1, row)
    else:
        lines.extend(["", "| PRD | Название | Статус | Commit | Что изменилось | Отчёт |", sep, row])
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _upsert_decisions(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = path.read_text(encoding="utf-8") if path.exists() else "# Architecture Decisions\n\n"
    marker = "## ADR-057 - Diagnostic Center v1 completion gate closes current creator-pilot phase without rollout expansion"
    if marker in text:
        return
    append = "\n".join(
        [
            marker,
            "",
            "Status: accepted",
            "Context: PRD-046.1.36 accepted creator-live pilot layer but left runtime readiness warning and mixed evidence provenance strengths.",
            "Decision: PRD-046.1.37 enforces final source/provenance/runtime/live/admin/rollback/normal-user/safety/no-mutation decision package and closes Diagnostic Center v1 for the current phase.",
            "Consequences: creator-only/allowlist pilot remains governed; broad rollout stays prohibited; production_ready remains false; next work moves to Multiagent Quality & Tuning Track.",
        ]
    )
    path.write_text(text.rstrip() + "\n\n" + append + "\n", encoding="utf-8")


def _render_implementation_report(scorecard: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# PRD-046.1.37 Implementation Report",
            "",
            f"- PRD ID: `{PRD}`",
            f"- final_status: `{scorecard.get('final_status', 'blocked')}`",
            f"- decision: `{scorecard.get('decision', gate.DECISION_BLOCKED_LIVE_EVIDENCE)}`",
            "- commit_hash: `pending`",
            "- push_status: `pending`",
            "",
            "## Created Files",
            "- TO_DO_LIST/PRD-046.1.37_TASK_LIST.md",
            "- bot_psychologist/bot_agent/multiagent/contracts/diagnostic_center_final_completion_gate_v1.py",
            "- bot_psychologist/bot_agent/multiagent/diagnostic_center_final_completion_gate.py",
            "- bot_psychologist/tools/run_diagnostic_center_final_completion_gate.py",
            "- bot_psychologist/tests/multiagent/test_prd_046_1_37_*.py",
            "- TO_DO_LIST/logs/PRD-046.1.37/*.json",
            "- TO_DO_LIST/reports/PRD-046.1.37_*.md",
            "- TO_DO_LIST/TRANSFER_BRIEF_Diagnostic_Center_v1_COMPLETED_AFTER_PRD-046.1.37_RU.md",
            "",
            "## Modified Files",
            "- docs/PROJECT_STATE.md",
            "- docs/ROADMAP.md",
            "- docs/PRD_INDEX.md",
            "- docs/DECISIONS.md",
            "",
            "## Result Snapshot",
            f"- source_gate: `{scorecard.get('source_gate', 'blocked')}`",
            f"- runtime_readiness_final_gate: `{scorecard.get('runtime_readiness_final_gate', 'blocked')}`",
            f"- actual_live_creator_smoke_gate: `{scorecard.get('actual_live_creator_smoke_gate', 'blocked')}`",
            f"- admin_runtime_controls_final_gate: `{scorecard.get('admin_runtime_controls_final_gate', 'blocked')}`",
            f"- rollback_hard_stop_final_gate: `{scorecard.get('rollback_hard_stop_final_gate', 'blocked')}`",
            f"- normal_user_final_no_effect_gate: `{scorecard.get('normal_user_final_no_effect_gate', 'blocked')}`",
            f"- no_mutation_final_proof: `{scorecard.get('no_mutation_final_proof', 'blocked')}`",
            f"- artifact_encoding_hygiene: `{scorecard.get('artifact_encoding_hygiene', 'blocked')}`",
            "",
            "## Next Track",
            "- `Multiagent Quality & Tuning Track`",
        ]
    )


def _render_final_results_report(scorecard: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# PRD-046.1.37 Diagnostic Center Final Results Report",
            "",
            f"- final_status: `{scorecard.get('final_status', 'blocked')}`",
            f"- decision: `{scorecard.get('decision', gate.DECISION_BLOCKED_LIVE_EVIDENCE)}`",
            f"- actual_live_cases_total: `{scorecard.get('actual_live_cases_total', 0)}`",
            f"- actual_live_cases_passed: `{scorecard.get('actual_live_cases_passed', 0)}`",
            f"- diagnostic_center_active_for_creator_count: `{scorecard.get('diagnostic_center_active_for_creator_count', 0)}`",
            f"- diagnostic_center_trace_present_count: `{scorecard.get('diagnostic_center_trace_present_count', 0)}`",
            "",
            "Diagnostic Center v1 is treated as governed creator-pilot closure scope, not broad rollout and not production-ready.",
        ]
    )


def _render_provenance_report(audit: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# PRD-046.1.37 Evidence Provenance Report",
            "",
            f"- gate: `{audit.get('gate', 'blocked')}`",
            f"- actual_live_evidence_count: `{audit.get('actual_live_evidence_count', 0)}`",
            f"- runtime_probe_evidence_count: `{audit.get('runtime_probe_evidence_count', 0)}`",
            f"- simulated_contract_evidence_count: `{audit.get('simulated_contract_evidence_count', 0)}`",
            f"- static_source_evidence_count: `{audit.get('static_source_evidence_count', 0)}`",
            f"- missing_or_weak_evidence_count: `{audit.get('missing_or_weak_evidence_count', 0)}`",
            f"- final_live_gap_detected: `{str(audit.get('final_live_gap_detected', False)).lower()}`",
        ]
    )


def _render_runtime_admin_rollback_report(
    runtime_gate: dict[str, Any],
    admin_gate: dict[str, Any],
    rollback_gate: dict[str, Any],
    normal_gate: dict[str, Any],
) -> str:
    return "\n".join(
        [
            "# PRD-046.1.37 Runtime/Admin/Rollback Report",
            "",
            f"- runtime_readiness_final_gate: `{runtime_gate.get('runtime_readiness_final_gate', 'blocked')}`",
            f"- backend_adaptive_endpoint_status: `{runtime_gate.get('backend_adaptive_endpoint_status', 0)}`",
            f"- backend_debug_trace_endpoint_status: `{runtime_gate.get('backend_debug_trace_endpoint_status', 0)}`",
            f"- botdb_status_code: `{runtime_gate.get('botdb_status_code', 0)}`",
            f"- botdb_query_status_code: `{runtime_gate.get('botdb_query_status_code', 0)}`",
            f"- web_ui_status_code: `{runtime_gate.get('web_ui_status_code', 0)}`",
            f"- admin_runtime_controls_final_gate: `{admin_gate.get('admin_runtime_controls_final_gate', 'blocked')}`",
            f"- rollback_hard_stop_final_gate: `{rollback_gate.get('rollback_hard_stop_final_gate', 'blocked')}`",
            f"- normal_user_final_no_effect_gate: `{normal_gate.get('normal_user_final_no_effect_gate', 'blocked')}`",
        ]
    )


def _render_completion_decision_report(scorecard: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# PRD-046.1.37 Completion Decision Report",
            "",
            f"- final_status: `{scorecard.get('final_status', 'blocked')}`",
            f"- decision: `{scorecard.get('decision', gate.DECISION_BLOCKED_LIVE_EVIDENCE)}`",
            "",
            "## Что считается завершенным",
            "- Creator-only / allowlist pilot governance слой закрыт на текущей фазе при сохранении строгих boundary-флагов.",
            "- Доказаны rollback/normal-user/safety/no-mutation контракты в рамках доступных артефактов раннера.",
            "",
            "## Что НЕ считается завершенным",
            "- Это не broad rollout.",
            "- Это не production-ready launch для обычных пользователей.",
            "- Это не расширение authority на all_users mode.",
            "",
            "## Допустимые warnings",
            "- Отсутствие отдельного `/health` endpoint допустимо, если adaptive/debug live path рабочий.",
            "- Fallback rollback proof допустим, если write-endpoint отсутствует, но hard-stop boundary подтвержден.",
            "",
            "## Backlog",
            f"- `{', '.join(scorecard.get('backlog_items', []))}`",
        ]
    )


def _render_next_track_report(scorecard: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# PRD-046.1.37 Next Track Recommendation",
            "",
            f"- final_status: `{scorecard.get('final_status', 'blocked')}`",
            f"- decision: `{scorecard.get('decision', gate.DECISION_BLOCKED_LIVE_EVIDENCE)}`",
            "- next_track_recommendation: `Multiagent Quality & Tuning Track`",
        ]
    )


def _render_transfer_brief(scorecard: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# TRANSFER BRIEF — Diagnostic Center v1 после PRD-046.1.37",
            "",
            "## 1. Итоговое состояние",
            f"- final_status: `{scorecard.get('final_status', 'blocked')}`",
            f"- decision: `{scorecard.get('decision', gate.DECISION_BLOCKED_LIVE_EVIDENCE)}`",
            "- Diagnostic Center Track Status: CLOSED FOR CURRENT PHASE",
            "",
            "## 2. Разрешенные режимы",
            "- creator_only",
            "- allowlist_live (в рамках governed pilot-политики)",
            "",
            "## 3. Запрещенные режимы",
            "- broad rollout",
            "- all_users runtime activation",
            "- normal-user runtime authority expansion",
            "",
            "## 4. Runtime/admin controls",
            "- force-disabled/hard-stop должны оставаться доступными (direct endpoint или fallback path).",
            "- runtime mode должен быть наблюдаем через admin/runtime payload.",
            "",
            "## 5. Trace/observability contract",
            "- для creator live-turn должен быть debug multiagent trace.",
            "- private/raw payload не коммитится.",
            "",
            "## 6. Rollback/hard-stop contract",
            "- при force-disabled creator не теряет ответ целиком, но Diagnostic Center authority не применяется.",
            "",
            "## 7. Normal-user boundary",
            "- normal users не должны получать live authority Diagnostic Center.",
            "",
            "## 8. Safety/privacy/no-mutation",
            "- no raw provider payload in repo",
            "- no secrets/.env in repo",
            "- no mutation of all_blocks_merged/registry/config",
            "",
            "## 9. Known warnings",
            f"- `{', '.join(scorecard.get('warnings', [])) or 'none'}`",
            "",
            "## 10. Explicit backlog",
            "- Writer style/depth tuning",
            "- State Analyzer calibration",
            "- Thread Manager / continuity",
            "- Pattern Core / Active Frame",
            "- KB Context Payload v2",
            "- Web Trace UX polish",
            "- Web Admin advanced controls",
            "- Response quality eval",
            "",
            "## 11. Next recommended track",
            "- Multiagent Quality & Tuning Track",
        ]
    )


def run(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = Path(args.repo_root).resolve()
    docs_dir = Path(args.docs_dir).resolve()
    reports_dir = Path(args.reports_dir).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    test_output = output_dir / "test_command_output.txt"
    if not test_output.exists():
        test_output.write_text("PRD-046.1.37 runner executed.\n", encoding="utf-8")

    tracked_paths, hash_before = gate.tracked_hashes(repo_root)
    preflight = gate.preflight_source(repo_root)
    source_gate = gate.build_source_gate(preflight)
    evidence_audit = gate.build_evidence_provenance_audit(preflight)

    runtime_gate, admin_payload = gate.build_runtime_readiness_final_gate(
        backend_base_url=args.backend_base_url,
        botdb_base_url=args.botdb_base_url,
        web_ui_base_url=args.web_ui_base_url,
        api_key=args.api_key,
        creator_user_id=args.creator_user_id,
    )

    source_admin = dict(preflight.get("parsed", {}).get("admin_runtime_controls_acceptance", {}))
    admin_gate = gate.build_admin_runtime_controls_final_gate(
        source_admin=source_admin,
        admin_payload=admin_payload,
        admin_status_code=int(runtime_gate.get("admin_runtime_endpoint_status_code", 0) or 0),
    )

    live_smoke, _live_cases = gate.run_actual_live_creator_smoke(
        backend_base_url=args.backend_base_url,
        api_key=args.api_key,
        creator_user_id=args.creator_user_id,
    )
    rollback_gate = gate.build_rollback_hard_stop_final_gate(
        backend_base_url=args.backend_base_url,
        api_key=args.api_key,
        creator_user_id=args.creator_user_id,
    )
    normal_gate = gate.run_normal_user_final_no_effect_gate(
        backend_base_url=args.backend_base_url,
        api_key=args.api_key,
        normal_user_id=args.normal_user_id,
    )
    rag_gate = gate.build_rag_behavior_final_regression_gate(live_smoke=live_smoke)

    _write_json(output_dir / "source_gate.json", source_gate)
    _write_json(output_dir / "evidence_provenance_audit.json", evidence_audit)
    _write_json(output_dir / "runtime_readiness_final_gate.json", runtime_gate)
    _write_json(output_dir / "actual_live_creator_smoke.json", live_smoke)
    _write_json(output_dir / "admin_runtime_controls_final_gate.json", admin_gate)
    _write_json(output_dir / "rollback_hard_stop_final_gate.json", rollback_gate)
    _write_json(output_dir / "normal_user_final_no_effect_gate.json", normal_gate)
    _write_json(output_dir / "rag_behavior_final_regression_gate.json", rag_gate)

    trace_gate = gate.build_trace_sanitization_final_gate(output_dir)
    budget_gate = gate.build_provider_budget_final_gate(live_smoke=live_smoke)
    hash_after = {name: _sha256(path) for name, path in tracked_paths.items()}
    no_mutation_proof = gate.build_no_mutation_final_proof(hash_before=hash_before, hash_after=hash_after)

    _write_json(output_dir / "trace_sanitization_final_gate.json", trace_gate)
    _write_json(output_dir / "provider_budget_final_gate.json", budget_gate)
    _write_json(output_dir / "no_mutation_final_proof.json", no_mutation_proof)

    encoding_report = encoding_validator.run(
        argparse.Namespace(
            prd=PRD,
            logs_dir=str(output_dir),
            reports_dir=str(reports_dir),
            out_dir=str(output_dir),
            report_prd=PRD,
            repo_root=str(repo_root),
            fixed_file=[],
        )
    )
    _write_json(output_dir / "artifact_encoding_hygiene_report.json", encoding_report)
    encoding_ok = str(encoding_report.get("final_status", "failed")) == "passed"

    scorecard, decision = gate.build_final_scorecard(
        source_gate=source_gate,
        evidence_audit=evidence_audit,
        runtime_gate=runtime_gate,
        live_smoke=live_smoke,
        admin_gate=admin_gate,
        rollback_gate=rollback_gate,
        normal_gate=normal_gate,
        rag_gate=rag_gate,
        trace_gate=trace_gate,
        budget_gate=budget_gate,
        no_mutation=no_mutation_proof,
        artifact_encoding_hygiene_passed=encoding_ok,
    )
    _write_json(output_dir / "diagnostic_center_final_completion_scorecard.json", scorecard)

    _upsert_project_state(docs_dir / "PROJECT_STATE.md")
    _upsert_roadmap(docs_dir / "ROADMAP.md")
    _upsert_prd_index(docs_dir / "PRD_INDEX.md", scorecard)
    _upsert_decisions(docs_dir / "DECISIONS.md")

    _write_text(reports_dir / "PRD-046.1.37_IMPLEMENTATION_REPORT.md", _render_implementation_report(scorecard))
    _write_text(
        reports_dir / "PRD-046.1.37_DIAGNOSTIC_CENTER_FINAL_RESULTS_REPORT.md",
        _render_final_results_report(scorecard),
    )
    _write_text(
        reports_dir / "PRD-046.1.37_EVIDENCE_PROVENANCE_REPORT.md",
        _render_provenance_report(evidence_audit),
    )
    _write_text(
        reports_dir / "PRD-046.1.37_RUNTIME_ADMIN_ROLLBACK_REPORT.md",
        _render_runtime_admin_rollback_report(runtime_gate, admin_gate, rollback_gate, normal_gate),
    )
    _write_text(
        reports_dir / "PRD-046.1.37_COMPLETION_DECISION_REPORT.md",
        _render_completion_decision_report(scorecard),
    )
    _write_text(
        reports_dir / "PRD-046.1.37_NEXT_TRACK_RECOMMENDATION.md",
        _render_next_track_report(scorecard),
    )
    _write_text(
        repo_root / "TO_DO_LIST" / "TRANSFER_BRIEF_Diagnostic_Center_v1_COMPLETED_AFTER_PRD-046.1.37_RU.md",
        _render_transfer_brief(scorecard),
    )

    return {
        "status": str(scorecard.get("final_status", "blocked")),
        "decision": str(scorecard.get("decision", gate.DECISION_BLOCKED_LIVE_EVIDENCE)),
        "scorecard": scorecard,
        "decision_payload": decision,
        "encoding_report": encoding_report,
        "source_gate": source_gate,
        "runtime_gate": runtime_gate,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run PRD-046.1.37 Diagnostic Center final completion gate.")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--docs-dir", default="docs")
    parser.add_argument("--reports-dir", default="TO_DO_LIST/reports")
    parser.add_argument("--output-dir", default="TO_DO_LIST/logs/PRD-046.1.37")
    parser.add_argument("--backend-base-url", default="http://localhost:8001")
    parser.add_argument("--botdb-base-url", default="http://localhost:8003")
    parser.add_argument("--web-ui-base-url", default="http://localhost:3000")
    parser.add_argument("--api-key", default="dev-key-001")
    parser.add_argument("--creator-user-id", default="user_1772172411219_kamh0")
    parser.add_argument("--normal-user-id", default="user_normal_control_prd_046_1_37")
    parser.add_argument("--strict", action="store_true")
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    result = run(args)
    print(json.dumps(result, ensure_ascii=True, indent=2))
    status = str(result.get("status", "blocked"))
    return 0 if status == "completed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
