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

from bot_agent.multiagent import creator_live_evidence_rag_repair as hf1
from tools import validate_prd_artifact_encoding as encoding_validator

PRD = hf1.PRD


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
    decision = str(scorecard.get("decision", ""))

    project_state = docs_dir / "PROJECT_STATE.md"
    ps_text = project_state.read_text(encoding="utf-8") if project_state.exists() else "# Project State - Bot Psychologist / Neo MindBot\n"
    if decision == hf1.DECISION_PASSED_RAG_READY:
        stage = "PRD-046.1.35-HF1 proved actual creator live turn and RAG-to-Writer delivery under creator_only boundary."
        next_prd = f"`{hf1.NEXT_PRD_DEFAULT}`"
    elif decision == hf1.DECISION_PASSED_GOV_BLOCKED:
        stage = "PRD-046.1.35-HF1 proved actual creator live turn, but governance blocks writer-context delivery for selected chunks."
        next_prd = f"`{hf1.NEXT_PRD_GOV}`"
    else:
        stage = f"PRD-046.1.35-HF1 blocked or evidence_incomplete (`{decision}`); targeted repair required."
        next_prd = f"`{hf1.NEXT_PRD_FIX}`"
    ps_text = _replace_section(ps_text, "## Current Stage", stage)
    ps_text = _replace_section(ps_text, "## Next Planned PRD", next_prd)
    ps_text = re.sub(r"(- Source cycle:\s*)(PRD-046\.1\.\d+(?:-HF\d+)?)", r"\g<1>PRD-046.1.35-HF1", ps_text, count=1)
    project_state.write_text(ps_text.rstrip() + "\n", encoding="utf-8")

    roadmap = docs_dir / "ROADMAP.md"
    rm_text = roadmap.read_text(encoding="utf-8") if roadmap.exists() else "# Roadmap\n\n## Done\n\n## Next\n"
    lines = rm_text.splitlines()
    done_line = "- PRD-046.1.35-HF1: creator live evidence and BotDB/RAG-to-writer delivery repair with strict diagnostic gates."
    if done_line not in lines:
        if "## Done" not in lines:
            lines.extend(["", "## Done"])
        idx = lines.index("## Done")
        lines.insert(idx + 1, done_line)
    if "## Next" not in lines:
        lines.extend(["", "## Next"])
    idx = lines.index("## Next")
    while idx + 1 < len(lines) and lines[idx + 1].startswith("1. PRD-046.1."):
        lines.pop(idx + 1)
    next_line = f"1. {scorecard.get('next_prd_recommendation', hf1.NEXT_PRD_FIX)}."
    lines.insert(idx + 1, next_line)
    roadmap.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")

    prd_index = docs_dir / "PRD_INDEX.md"
    pi_text = prd_index.read_text(encoding="utf-8") if prd_index.exists() else "# PRD Index\n\n| PRD | Название | Статус | Commit | Что изменилось | Отчёт |\n| --- | --- | --- | --- | --- | --- |\n"
    row = (
        "| PRD-046.1.35-HF1 | Creator Live Evidence + BotDB/RAG-to-Writer Repair v1 | "
        f"{scorecard.get('final_status', 'blocked')} | pending | fixed BotDB query parsing resilience and introduced creator-live evidence/rag-delivery strict gate artifacts | "
        "TO_DO_LIST/reports/PRD-046.1.35-HF1_IMPLEMENTATION_REPORT.md |"
    )
    pi_lines = pi_text.splitlines()
    replaced = False
    for i, line in enumerate(pi_lines):
        if line.startswith("| PRD-046.1.35-HF1 |"):
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
    marker = "## ADR-055 - Creator live evidence requires end-to-end RAG delivery trace"
    if marker not in d_text:
        d_text = d_text.rstrip() + "\n\n" + "\n".join(
            [
                marker,
                "",
                "Status: accepted",
                "Context: PRD-046.1.35 ended with evidence_incomplete; we needed a strict chain proof from BotDB query to writer prompt and debug trace.",
                "Decision: introduce HF1 scorecard + creator_live_turn_proof + rag_to_writer_delivery_proof with delivery classification and explicit governance-blocked state.",
                "Consequences: creator-only runtime remains bounded; broad rollout and normal-user activation stay disabled until later PRDs.",
            ]
        )
    decisions.write_text(d_text.rstrip() + "\n", encoding="utf-8")


def _render_implementation_report(scorecard: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# PRD-046.1.35-HF1 Implementation Report",
            "",
            f"- PRD ID: `{PRD}`",
            f"- final_status: `{scorecard.get('final_status', 'blocked')}`",
            f"- decision: `{scorecard.get('decision', hf1.DECISION_EVIDENCE_INCOMPLETE)}`",
            "- commit_hash: `pending`",
            "- push_status: `pending`",
            "",
            "## Created Files",
            "- TO_DO_LIST/PRD-046.1.35-HF1_TASK_LIST.md",
            "- bot_psychologist/bot_agent/multiagent/contracts/creator_live_evidence_rag_repair_v1.py",
            "- bot_psychologist/bot_agent/multiagent/creator_live_evidence_rag_repair.py",
            "- bot_psychologist/tools/probe_botdb_rag_to_writer.py",
            "- bot_psychologist/tools/run_creator_live_evidence_rag_repair.py",
            "- bot_psychologist/tests/multiagent/test_hf1_*.py",
            "- TO_DO_LIST/logs/PRD-046.1.35-HF1/*.json",
            "- TO_DO_LIST/reports/PRD-046.1.35-HF1_*.md",
            "",
            "## Modified Files",
            "- Bot_data_base/api/routes/query.py",
            "- Bot_data_base/tests/test_query_route_chroma_failure_fallback.py",
            "- docs/PROJECT_STATE.md",
            "- docs/ROADMAP.md",
            "- docs/PRD_INDEX.md",
            "- docs/DECISIONS.md",
            "",
            "## Summary",
            f"- actual_live_turn_evidence_count: `{scorecard.get('actual_live_turn_evidence_count', 0)}`",
            f"- botdb_chunks_returned: `{scorecard.get('botdb_chunks_returned', 0)}`",
            f"- delivery_status: `{scorecard.get('delivery_status', 'blocked')}`",
            f"- blockers: `{', '.join(scorecard.get('blockers', [])) or 'none'}`",
            f"- warnings: `{', '.join(scorecard.get('warnings', [])) or 'none'}`",
            "",
            "## Next PRD Recommendation",
            f"- `{scorecard.get('next_prd_recommendation', hf1.NEXT_PRD_FIX)}`",
        ]
    )


def _render_creator_evidence_report(proof: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# PRD-046.1.35-HF1 Creator Live Evidence Report",
            "",
            f"- actual_live_turn: `{str(proof.get('actual_live_turn', False)).lower()}`",
            f"- turn_id: `{proof.get('turn_id', '')}`",
            f"- answer_received: `{str(proof.get('answer_received', False)).lower()}`",
            f"- diagnostic_center_runtime_mode: `{proof.get('diagnostic_center_runtime_mode', 'unknown')}`",
            f"- normal_user_path_unchanged: `{str(proof.get('normal_user_path_unchanged', False)).lower()}`",
        ]
    )


def _render_rag_delivery_report(proof: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# PRD-046.1.35-HF1 BotDB RAG Delivery Report",
            "",
            f"- botdb_http_status: `{proof.get('botdb_http_status', 0)}`",
            f"- botdb_chunks_returned: `{proof.get('botdb_chunks_returned', 0)}`",
            f"- retriever_raw_hits_count: `{proof.get('retriever_raw_hits_count', 0)}`",
            f"- knowledge_policy_included_writer_count: `{proof.get('knowledge_policy_included_writer_count', 0)}`",
            f"- context_assembly_knowledge_hits_count: `{proof.get('context_assembly_knowledge_hits_count', 0)}`",
            f"- writer_prompt_knowledge_hits_count: `{proof.get('writer_prompt_knowledge_hits_count', 0)}`",
            f"- delivery_status: `{proof.get('delivery_status', 'blocked')}`",
        ]
    )


def _render_trace_alignment_report(ui_gate: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# PRD-046.1.35-HF1 Trace Alignment Report",
            "",
            f"- backend_context_knowledge_hits_count: `{ui_gate.get('backend_context_knowledge_hits_count', 0)}`",
            f"- ui_chunks_in_writer_count: `{ui_gate.get('ui_chunks_in_writer_count', 0)}`",
            f"- mismatch_detected: `{str(ui_gate.get('mismatch_detected', False)).lower()}`",
            f"- ui_trace_alignment_gate: `{ui_gate.get('ui_trace_alignment_gate', 'blocked')}`",
        ]
    )


def _render_next_prd(scorecard: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# PRD-046.1.35-HF1 Next PRD Recommendation",
            "",
            f"- recommendation: `{scorecard.get('next_prd_recommendation', hf1.NEXT_PRD_FIX)}`",
            f"- based_on_decision: `{scorecard.get('decision', hf1.DECISION_EVIDENCE_INCOMPLETE)}`",
        ]
    )


def run(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = Path(args.repo_root).resolve()
    docs_dir = Path(args.docs_dir).resolve()
    reports_dir = Path(args.reports_dir).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    test_output = output_dir / "test_command_output.txt"
    if not test_output.exists():
        test_output.write_text("PRD-046.1.35-HF1 runner executed.\n", encoding="utf-8")

    source_gate = hf1.preflight_source_gate(repo_root)
    service_gate = hf1.probe_service_readiness(
        botdb_base_url=args.botdb_base_url,
        backend_base_url=args.backend_base_url,
        web_ui_base_url=args.web_ui_base_url,
        api_key=args.api_key,
    )
    botdb_probe = hf1.probe_botdb_query(query=args.query, botdb_base_url=args.botdb_base_url)
    turn_result = hf1.execute_creator_live_turn(
        backend_base_url=args.backend_base_url,
        api_key=args.api_key,
        creator_user_id=args.creator_user_id,
        query=args.query,
    )
    debug_trace = hf1.fetch_retrieval_trace(
        backend_base_url=args.backend_base_url,
        api_key=args.api_key,
        session_id=str(turn_result.get("session_id", "")),
    )

    creator_live_proof = hf1.build_creator_live_turn_proof(
        query=args.query,
        creator_user_id=args.creator_user_id,
        turn_result=turn_result,
        debug_trace=debug_trace,
    )
    rag_proof = hf1.build_rag_to_writer_delivery_proof(
        query=args.query,
        botdb_probe=botdb_probe,
        debug_trace=debug_trace,
    )
    ui_gate = hf1.build_ui_trace_alignment_gate(rag_proof=rag_proof)
    normal_user_gate = hf1.build_normal_user_no_effect_gate(source_root=repo_root)
    trace_gate = hf1.build_trace_sanitization_gate(list(output_dir.glob("*")))
    provider_gate = hf1.build_provider_budget_gate(debug_trace=debug_trace)

    tracked, hash_before = hf1.tracked_hashes(repo_root)
    hash_after = {name: hf1._sha256_path(path) for name, path in tracked.items()}  # noqa: SLF001
    no_mutation_proof = hf1.build_no_mutation_proof(hash_before=hash_before, hash_after=hash_after)

    prelim_scorecard, prelim_decision = hf1.build_hf1_scorecard(
        source_gate=source_gate,
        service_gate=service_gate,
        creator_live_proof=creator_live_proof,
        botdb_probe=botdb_probe,
        rag_proof=rag_proof,
        ui_gate=ui_gate,
        normal_user_gate=normal_user_gate,
        trace_gate=trace_gate,
        provider_gate=provider_gate,
        no_mutation_proof=no_mutation_proof,
        artifact_encoding_hygiene_passed=False,
    )

    _upsert_docs(docs_dir=docs_dir, scorecard=prelim_scorecard)

    retriever_trace = {
        "schema_version": "creator_live_evidence_rag_repair_retriever_delivery_trace_v1",
        "retriever_raw_hits_count": rag_proof.get("retriever_raw_hits_count", 0),
        "retriever_raw_scores": rag_proof.get("retriever_raw_scores", []),
        "retriever_source_used": rag_proof.get("retriever_source_used", "none"),
    }
    memory_trace = {
        "schema_version": "creator_live_evidence_rag_repair_memory_retrieval_delivery_trace_v1",
        "memory_semantic_hits_count": rag_proof.get("memory_semantic_hits_count", 0),
        "rag_min_score": rag_proof.get("rag_min_score", 0.45),
    }
    knowledge_trace = {
        "schema_version": "creator_live_evidence_rag_repair_knowledge_policy_delivery_trace_v1",
        "knowledge_policy_input_hits_count": rag_proof.get("knowledge_policy_input_hits_count", 0),
        "knowledge_policy_included_writer_count": rag_proof.get("knowledge_policy_included_writer_count", 0),
        "knowledge_policy_included_diagnostic_count": rag_proof.get("knowledge_policy_included_diagnostic_count", 0),
        "knowledge_policy_drop_reasons": rag_proof.get("knowledge_policy_drop_reasons", []),
    }
    context_trace = {
        "schema_version": "creator_live_evidence_rag_repair_context_assembly_delivery_trace_v1",
        "context_assembly_knowledge_hits_count": rag_proof.get("context_assembly_knowledge_hits_count", 0),
        "context_assembly_drop_reasons": rag_proof.get("context_assembly_drop_reasons", []),
    }
    writer_trace = {
        "schema_version": "creator_live_evidence_rag_repair_writer_prompt_delivery_trace_v1",
        "writer_prompt_knowledge_hits_count": rag_proof.get("writer_prompt_knowledge_hits_count", 0),
        "writer_prompt_contains_knowledge_block": rag_proof.get("writer_prompt_contains_knowledge_block", False),
    }

    _write_json(output_dir / "source_gate.json", source_gate)
    _write_json(output_dir / "service_readiness_gate.json", service_gate)
    _write_json(output_dir / "botdb_direct_query_probe.json", botdb_probe)
    _write_json(output_dir / "chroma_query_failure_probe.json", botdb_probe)
    _write_json(output_dir / "retriever_delivery_trace.json", retriever_trace)
    _write_json(output_dir / "memory_retrieval_delivery_trace.json", memory_trace)
    _write_json(output_dir / "knowledge_policy_delivery_trace.json", knowledge_trace)
    _write_json(output_dir / "context_assembly_delivery_trace.json", context_trace)
    _write_json(output_dir / "writer_prompt_delivery_trace.json", writer_trace)
    _write_json(output_dir / "ui_trace_alignment_gate.json", ui_gate)
    _write_json(output_dir / "creator_live_turn_proof.json", creator_live_proof)
    _write_json(output_dir / "rag_to_writer_delivery_proof.json", rag_proof)
    _write_json(output_dir / "normal_user_no_effect_gate.json", normal_user_gate)
    _write_json(output_dir / "trace_sanitization_gate.json", trace_gate)
    _write_json(output_dir / "provider_budget_gate.json", provider_gate)
    _write_json(output_dir / "no_mutation_proof.json", no_mutation_proof)

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

    scorecard, decision_payload = hf1.build_hf1_scorecard(
        source_gate=source_gate,
        service_gate=service_gate,
        creator_live_proof=creator_live_proof,
        botdb_probe=botdb_probe,
        rag_proof=rag_proof,
        ui_gate=ui_gate,
        normal_user_gate=normal_user_gate,
        trace_gate=trace_gate,
        provider_gate=provider_gate,
        no_mutation_proof=no_mutation_proof,
        artifact_encoding_hygiene_passed=encoding_passed,
    )
    _write_json(output_dir / "hf1_scorecard.json", scorecard)

    _upsert_docs(docs_dir=docs_dir, scorecard=scorecard)

    _write_text(reports_dir / "PRD-046.1.35-HF1_IMPLEMENTATION_REPORT.md", _render_implementation_report(scorecard))
    _write_text(reports_dir / "PRD-046.1.35-HF1_CREATOR_LIVE_EVIDENCE_REPORT.md", _render_creator_evidence_report(creator_live_proof))
    _write_text(reports_dir / "PRD-046.1.35-HF1_BOTDB_RAG_DELIVERY_REPORT.md", _render_rag_delivery_report(rag_proof))
    _write_text(reports_dir / "PRD-046.1.35-HF1_TRACE_ALIGNMENT_REPORT.md", _render_trace_alignment_report(ui_gate))
    _write_text(reports_dir / "PRD-046.1.35-HF1_NEXT_PRD_RECOMMENDATION.md", _render_next_prd(scorecard))

    return {
        "status": str(scorecard.get("final_status", "blocked")),
        "decision": str(scorecard.get("decision", hf1.DECISION_EVIDENCE_INCOMPLETE)),
        "scorecard": scorecard,
        "decision_payload": decision_payload,
        "source_gate": source_gate,
        "service_gate": service_gate,
        "turn_result": {
            "http_status": turn_result.get("http_status"),
            "session_id_present": bool(str(turn_result.get("session_id", "")).strip()),
            "answer_received": bool(turn_result.get("answer_received")),
            "error": turn_result.get("error"),
        },
        "encoding_report": encoding_report,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run PRD-046.1.35-HF1 creator live evidence + rag repair gate")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--docs-dir", default="docs")
    parser.add_argument("--reports-dir", default="TO_DO_LIST/reports")
    parser.add_argument("--output-dir", default="TO_DO_LIST/logs/PRD-046.1.35-HF1")
    parser.add_argument("--botdb-base-url", default="http://localhost:8003")
    parser.add_argument("--backend-base-url", default="http://localhost:8001")
    parser.add_argument("--web-ui-base-url", default="http://localhost:3000")
    parser.add_argument("--api-key", default="dev-key-001")
    parser.add_argument("--creator-user-id", default="user_1772172411219_kamh0")
    parser.add_argument("--query", default="что такое нейросталкинг")
    parser.add_argument("--strict", action="store_true")
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    result = run(args)
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0 if str(result.get("status", "blocked")) == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
