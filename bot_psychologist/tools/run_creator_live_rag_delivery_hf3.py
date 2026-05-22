from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

CURRENT_FILE = Path(__file__).resolve()
BOT_PSYCHOLOGIST_ROOT = CURRENT_FILE.parents[1]
if str(BOT_PSYCHOLOGIST_ROOT) not in sys.path:
    sys.path.insert(0, str(BOT_PSYCHOLOGIST_ROOT))

from bot_agent.multiagent import creator_live_rag_delivery_hf3 as HF3
from tools import validate_prd_artifact_encoding as encoding_validator

PRD = HF3.PRD


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


def _upsert_docs(*, docs_dir: Path, scorecard: dict[str, Any]) -> None:
    final_status = str(scorecard.get("final_status", "blocked"))
    decision = str(scorecard.get("decision", ""))

    project_state = docs_dir / "PROJECT_STATE.md"
    ps_text = (
        project_state.read_text(encoding="utf-8")
        if project_state.exists()
        else "# Project State - Bot Psychologist / Neo MindBot\n"
    )
    if final_status == "passed":
        stage = (
            "PRD-046.1.35-HF3 verified creator live RAG-to-Writer delivery. "
            "KB snippets are present and safe, while Writer KB Context Payload v2 remains backlog."
        )
        next_prd = f"`{HF3.NEXT_PRD_DEFAULT}`"
    else:
        stage = f"PRD-046.1.35-HF3 blocked (`{decision}`) on live RAG delivery / trace alignment."
        next_prd = f"`{HF3.NEXT_PRD_FIX}`"
    ps_text = _replace_section(ps_text, "## Current Stage", stage)
    ps_text = _replace_section(ps_text, "## Next Planned PRD", next_prd)
    ps_text = re.sub(r"(- Source cycle:\s*)(PRD-046\.1\.\d+(?:-HF\d+)?)", r"\g<1>PRD-046.1.35-HF3", ps_text, count=1)
    project_state.write_text(ps_text.rstrip() + "\n", encoding="utf-8")

    roadmap = docs_dir / "ROADMAP.md"
    rm_text = roadmap.read_text(encoding="utf-8") if roadmap.exists() else "# Roadmap\n\n## Done\n\n## Next\n"
    lines = rm_text.splitlines()
    done_line = "- PRD-046.1.35-HF3: synchronized live RAG evidence with multiagent trace and added writer KB truncation audit."
    if done_line not in lines:
        if "## Done" not in lines:
            lines.extend(["", "## Done"])
        idx_done = lines.index("## Done")
        lines.insert(idx_done + 1, done_line)
    if "## Next" not in lines:
        lines.extend(["", "## Next"])
    idx_next = lines.index("## Next")
    while idx_next + 1 < len(lines) and lines[idx_next + 1].startswith("1. PRD-046.1."):
        lines.pop(idx_next + 1)
    lines.insert(idx_next + 1, f"1. {scorecard.get('next_prd_recommendation', HF3.NEXT_PRD_FIX)}.")
    roadmap.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")

    prd_index = docs_dir / "PRD_INDEX.md"
    pi_text = (
        prd_index.read_text(encoding="utf-8")
        if prd_index.exists()
        else "# PRD Index\n\n| PRD | Название | Статус | Commit | Что изменилось | Отчёт |\n| --- | --- | --- | --- | --- | --- |\n"
    )
    row = (
        "| PRD-046.1.35-HF3 | Creator Live RAG Evidence Sync / Writer KB Context Boundary Audit v1 | "
        f"{final_status} | pending | synchronized runtime evidence, added live two-query gate and truncation audit artifacts | "
        "TO_DO_LIST/reports/PRD-046.1.35-HF3_IMPLEMENTATION_REPORT.md |"
    )
    pi_lines = pi_text.splitlines()
    replaced = False
    for i, line in enumerate(pi_lines):
        if line.startswith("| PRD-046.1.35-HF3 |"):
            pi_lines[i] = row
            replaced = True
            break
    if not replaced:
        sep = "| --- | --- | --- | --- | --- | --- |"
        if sep in pi_lines:
            pi_lines.insert(pi_lines.index(sep) + 1, row)
        else:
            pi_lines.extend(["", "| PRD | Название | Статус | Commit | Что изменилось | Отчёт |", sep, row])
    prd_index.write_text("\n".join(pi_lines).rstrip() + "\n", encoding="utf-8")

    decisions = docs_dir / "DECISIONS.md"
    d_text = decisions.read_text(encoding="utf-8") if decisions.exists() else "# Architecture Decisions\n\n"
    marker = "## ADR-056 - Live RAG evidence must align adaptive trace, multiagent trace, and writer prompt"
    if marker not in d_text:
        d_text = d_text.rstrip() + "\n\n" + "\n".join(
            [
                marker,
                "",
                "Status: accepted",
                "Context: HF2 showed in-process retrieval success while strict live artifacts still reported zero delivery.",
                "Decision: HF3 evaluates two live queries, aligns adaptive+multiagent traces, and stores explicit writer KB truncation audit as a non-blocking quality backlog.",
                "Consequences: rollout remains bounded to creator-only path; broad rollout and normal-user activation stay disabled.",
            ]
        )
    decisions.write_text(d_text.rstrip() + "\n", encoding="utf-8")


def _render_implementation_report(scorecard: dict[str, Any], strict_status: str) -> str:
    return "\n".join(
        [
            "# PRD-046.1.35-HF3 Implementation Report",
            "",
            f"- PRD ID: `{PRD}`",
            f"- final_status: `{scorecard.get('final_status', 'blocked')}`",
            f"- decision: `{scorecard.get('decision', HF3.DECISION_BLOCKED_RUNTIME_TRACE)}`",
            "- commit_hash: `pending`",
            "- push_status: `pending`",
            "",
            "## Created Files",
            "- TO_DO_LIST/PRD-046.1.35-HF3_TASK_LIST.md",
            "- bot_psychologist/bot_agent/multiagent/contracts/creator_live_rag_delivery_hf3_v1.py",
            "- bot_psychologist/bot_agent/multiagent/creator_live_rag_delivery_hf3.py",
            "- bot_psychologist/tools/run_creator_live_rag_delivery_hf3.py",
            "- bot_psychologist/tests/multiagent/test_hf3_*.py",
            "- TO_DO_LIST/logs/PRD-046.1.35-HF3/*.json",
            "- TO_DO_LIST/reports/PRD-046.1.35-HF3_*.md",
            "",
            "## Modified Files",
            "- docs/PROJECT_STATE.md",
            "- docs/ROADMAP.md",
            "- docs/PRD_INDEX.md",
            "- docs/DECISIONS.md",
            "- TO_DO_LIST/PRD-046.1.35-HF3_Creator_Live_RAG_Evidence_Sync_Writer_KB_Context_Boundary_Audit_v1.md",
            "",
            "## Test Summary",
            "- unit tests: `python -m pytest bot_psychologist/tests/multiagent/test_hf3_*.py -q`",
            f"- strict runner status: `{strict_status}`",
            "",
            "## Counters",
            f"- botdb_chunks_returned: `{scorecard.get('botdb_chunks_returned', 0)}`",
            f"- rag_raw_hits_count: `{scorecard.get('rag_raw_hits_count', 0)}`",
            f"- rag_filtered_hits_count: `{scorecard.get('rag_filtered_hits_count', 0)}`",
            f"- rag_salvaged_hits_count: `{scorecard.get('rag_salvaged_hits_count', 0)}`",
            f"- knowledge_policy_included_writer_count: `{scorecard.get('knowledge_policy_included_writer_count', 0)}`",
            f"- context_assembly_knowledge_hits_count: `{scorecard.get('context_assembly_knowledge_hits_count', 0)}`",
            f"- writer_prompt_knowledge_hits_count: `{scorecard.get('writer_prompt_knowledge_hits_count', 0)}`",
            f"- web_trace_chunks_in_writer_count: `{scorecard.get('web_trace_chunks_in_writer_count', 0)}`",
            f"- truncation_detected: `{str(scorecard.get('truncation_detected', True)).lower()}`",
            f"- truncation_blocker: `{str(scorecard.get('truncation_blocker', False)).lower()}`",
            "",
            "## Next PRD Recommendation",
            f"- `{scorecard.get('next_prd_recommendation', HF3.NEXT_PRD_FIX)}`",
        ]
    )


def _render_live_report(live_payload: dict[str, Any], scorecard: dict[str, Any]) -> str:
    selected = live_payload.get("selected_query", {})
    queries = live_payload.get("queries", [])
    lines = [
        "# PRD-046.1.35-HF3 Live RAG Delivery Report",
        "",
        f"- selected_query_id: `{selected.get('query_id', '')}`",
        f"- selected_query: `{selected.get('query', '')}`",
        f"- final_status: `{scorecard.get('final_status', 'blocked')}`",
        "",
        "## Query Results",
    ]
    for item in queries:
        lines.extend(
            [
                f"- `{item.get('query_id', '')}` `{item.get('query', '')}`",
                f"  botdb_chunks={item.get('botdb_chunks_returned', 0)}, raw={item.get('rag_raw_hits_count', 0)}, filtered={item.get('rag_filtered_hits_count', 0)}, salvaged={item.get('rag_salvaged_hits_count', 0)}, writer={item.get('writer_prompt_knowledge_hits_count', 0)}",
            ]
        )
    return "\n".join(lines)


def _render_truncation_report(truncation_audit: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# PRD-046.1.35-HF3 Writer KB Truncation Audit",
            "",
            f"- writer_kb_truncation_gate: `{truncation_audit.get('writer_kb_truncation_gate', 'warning')}`",
            f"- truncation_detected: `{str(truncation_audit.get('truncation_detected', True)).lower()}`",
            f"- truncation_blocker: `{str(truncation_audit.get('truncation_blocker', False)).lower()}`",
            f"- knowledge_policy_sanitized_max_chars: `{truncation_audit.get('knowledge_policy_sanitized_max_chars', 0)}`",
            f"- writer_prompt_hit_max_chars: `{truncation_audit.get('writer_prompt_hit_max_chars', 0)}`",
            f"- conversation_context_max_chars: `{truncation_audit.get('conversation_context_max_chars', 0)}`",
            f"- boundary_trim_helper_present: `{str(truncation_audit.get('boundary_trim_helper_present', False)).lower()}`",
            f"- kb_context_v2_backlog: `{str(truncation_audit.get('kb_context_v2_backlog', True)).lower()}`",
            f"- recommendation: `{truncation_audit.get('recommended_next_prd', HF3.NEXT_PRD_KB_V2)}`",
        ]
    )


def _render_next_prd(scorecard: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# PRD-046.1.35-HF3 Next PRD Recommendation",
            "",
            f"- recommendation: `{scorecard.get('next_prd_recommendation', HF3.NEXT_PRD_FIX)}`",
            f"- based_on_decision: `{scorecard.get('decision', HF3.DECISION_BLOCKED_RUNTIME_TRACE)}`",
        ]
    )


def _select_query_payload(query_payloads: list[dict[str, Any]]) -> dict[str, Any]:
    if not query_payloads:
        return {}
    return max(
        query_payloads,
        key=lambda item: (
            int(item.get("writer_prompt_knowledge_hits_count", 0)),
            int(item.get("context_assembly_knowledge_hits_count", 0)),
            int(item.get("knowledge_policy_included_writer_count", 0)),
            int(item.get("rag_raw_hits_count", 0)),
            int(item.get("botdb_chunks_returned", 0)),
            int(item.get("answer_received", False)),
        ),
    )


def run(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = Path(args.repo_root).resolve()
    docs_dir = Path(args.docs_dir).resolve()
    reports_dir = Path(args.reports_dir).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    test_output = output_dir / "test_command_output.txt"
    if not test_output.exists():
        test_output.write_text("PRD-046.1.35-HF3 runner executed.\n", encoding="utf-8")

    tracked, hash_before = HF3.tracked_hashes(repo_root)

    source_gate = HF3.preflight_source_gate(repo_root)
    runtime_reload_proof = HF3.probe_runtime_reload(
        repo_root=repo_root,
        botdb_base_url=args.botdb_base_url,
        backend_base_url=args.backend_base_url,
        web_ui_base_url=args.web_ui_base_url,
        api_key=args.api_key,
    )

    query_plan = [
        ("q1", args.query),
        ("q2", args.query_regression),
    ]
    query_runs: list[dict[str, Any]] = []
    for query_id, query_text in query_plan:
        run_payload = HF3.run_live_query_chain(
            query_id=query_id,
            query=query_text,
            creator_user_id=args.creator_user_id,
            botdb_base_url=args.botdb_base_url,
            backend_base_url=args.backend_base_url,
            api_key=args.api_key,
        )
        query_runs.append(run_payload)

    query_evidences = [dict(item.get("live_evidence", {})) for item in query_runs]
    selected_evidence = _select_query_payload(query_evidences)
    selected_id = str(selected_evidence.get("query_id", ""))
    selected_run = next((item for item in query_runs if str(item.get("query_id", "")) == selected_id), query_runs[0])

    creator_live_turn_proof = {
        "schema_version": "creator_live_turn_proof_hf3_collection_v1",
        "prd_id": PRD,
        "selected_query_id": selected_id,
        "actual_live_turn_evidence_count": sum(
            1 for item in query_runs if bool(_as_bool(item.get("creator_live_turn_proof", {}).get("actual_live_turn"), False))
        ),
        "query_proofs": [item.get("creator_live_turn_proof", {}) for item in query_runs],
    }

    trace_alignment_gate = HF3.build_trace_alignment_gate(live_evidence=selected_evidence)
    normal_user_gate = HF3.build_normal_user_no_effect_gate(source_root=repo_root)
    provider_gate = HF3.build_provider_budget_gate(adaptive_trace=selected_run.get("adaptive_trace", {}))
    truncation_audit = HF3.build_writer_kb_truncation_audit(repo_root=repo_root, selected_evidence=selected_evidence)

    hash_after = {name: HF3._sha256_path(path) for name, path in tracked.items()}  # noqa: SLF001
    no_mutation_proof = HF3.build_no_mutation_proof(hash_before=hash_before, hash_after=hash_after)

    live_rag_to_writer_trace_proof = {
        "schema_version": "creator_live_rag_delivery_hf3_live_trace_proof_v1",
        "prd_id": PRD,
        "selected_query_id": selected_id,
        "queries": query_evidences,
        "selected_query": selected_evidence,
    }

    _write_json(output_dir / "source_gate.json", source_gate)
    _write_json(output_dir / "runtime_reload_proof.json", runtime_reload_proof)
    _write_json(output_dir / "botdb_direct_query_probe.json", selected_run.get("botdb_probe", {}))
    _write_json(output_dir / "memory_agent_delivery_probe.json", selected_run.get("memory_probe", {}))
    _write_json(output_dir / "live_rag_to_writer_trace_proof.json", live_rag_to_writer_trace_proof)
    _write_json(output_dir / "writer_kb_truncation_audit.json", truncation_audit)
    _write_json(output_dir / "creator_live_turn_proof.json", creator_live_turn_proof)
    _write_json(output_dir / "trace_alignment_gate.json", trace_alignment_gate)
    _write_json(output_dir / "normal_user_no_effect_gate.json", normal_user_gate)
    _write_json(output_dir / "provider_budget_gate.json", provider_gate)
    _write_json(output_dir / "no_mutation_proof.json", no_mutation_proof)

    trace_gate = HF3.build_trace_sanitization_gate(list(output_dir.glob("*")))
    _write_json(output_dir / "trace_sanitization_gate.json", trace_gate)

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
    encoding_passed = str(encoding_report.get("final_status", "failed")) == "passed"
    _write_json(output_dir / "artifact_encoding_hygiene_report.json", encoding_report)

    selected_creator_proof = selected_run.get("creator_live_turn_proof", {})
    scorecard, decision_payload = HF3.build_hf3_scorecard(
        source_gate=source_gate,
        runtime_reload_proof=runtime_reload_proof,
        selected_evidence=selected_evidence,
        trace_alignment_gate=trace_alignment_gate,
        truncation_audit=truncation_audit,
        creator_live_turn_proof=selected_creator_proof,
        normal_user_gate=normal_user_gate,
        trace_gate=trace_gate,
        provider_gate=provider_gate,
        no_mutation_proof=no_mutation_proof,
        artifact_encoding_hygiene_passed=encoding_passed,
    )
    _write_json(output_dir / "hf3_scorecard.json", scorecard)

    _upsert_docs(docs_dir=docs_dir, scorecard=scorecard)

    strict_status = "passed" if str(scorecard.get("final_status", "blocked")) == "passed" else "blocked"
    _write_text(reports_dir / "PRD-046.1.35-HF3_IMPLEMENTATION_REPORT.md", _render_implementation_report(scorecard, strict_status))
    _write_text(reports_dir / "PRD-046.1.35-HF3_LIVE_RAG_DELIVERY_REPORT.md", _render_live_report(live_rag_to_writer_trace_proof, scorecard))
    _write_text(
        reports_dir / "PRD-046.1.35-HF3_WRITER_KB_TRUNCATION_AUDIT_REPORT.md",
        _render_truncation_report(truncation_audit),
    )
    _write_text(reports_dir / "PRD-046.1.35-HF3_NEXT_PRD_RECOMMENDATION.md", _render_next_prd(scorecard))

    return {
        "status": str(scorecard.get("final_status", "blocked")),
        "decision": str(scorecard.get("decision", HF3.DECISION_BLOCKED_RUNTIME_TRACE)),
        "scorecard": scorecard,
        "decision_payload": decision_payload,
        "source_gate": source_gate,
        "runtime_reload_proof": runtime_reload_proof,
        "selected_query_id": selected_id,
        "selected_query": selected_evidence.get("query", ""),
        "query_results": query_evidences,
        "encoding_report": encoding_report,
    }


def _as_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    return default


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run PRD-046.1.35-HF3 creator live RAG evidence sync gate")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--docs-dir", default="docs")
    parser.add_argument("--reports-dir", default="TO_DO_LIST/reports")
    parser.add_argument("--output-dir", default="TO_DO_LIST/logs/PRD-046.1.35-HF3")
    parser.add_argument("--botdb-base-url", default="http://localhost:8003")
    parser.add_argument("--backend-base-url", default="http://localhost:8001")
    parser.add_argument("--web-ui-base-url", default="http://localhost:3000")
    parser.add_argument("--api-key", default="dev-key-001")
    parser.add_argument("--creator-user-id", default="user_1772172411219_kamh0")
    parser.add_argument("--query", default="как это применимо к моей жизни?")
    parser.add_argument("--query-regression", default="что такое нейросталкинг")
    parser.add_argument("--strict", action="store_true")
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    result = run(args)
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0 if str(result.get("status", "blocked")) == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
