from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx


REPO_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = REPO_ROOT / "TO_DO_LIST" / "logs" / "PRD-047.36-HF2"
SOURCE_MATERIAL_PATH = REPO_ROOT / "TO_DO_LIST" / "source_materials" / "PRD-047.1" / "КУЗНИЦА ДУХА v.2.md"

API_HEADERS = {
    "X-API-Key": "dev-key-001",
    "X-Device-Fingerprint": "prd-047-36-hf2-audit",
    "Content-Type": "application/json; charset=utf-8",
}

PROBES = [
    ("A1", "Что такое анестетическая депрессия?"),
    ("A2", "анестетическая депрессия это ведь еще и психологический термин, что ты знаешь об этом?"),
    ("A3", "Так стоп! Что такое анестетическая депрессия в Нейросталкинге?"),
    ("A4", "Что такое программа несовершенное Я?"),
    ("A5", "Назови пять драйверов выживания."),
    ("A6", "Что значит страдание как безопасность?"),
    ("A7", "Что такое контролёр в панике?"),
    ("A8", "Что такое духовная кома?"),
]


def _ascii_json_body(query: str, session_id: str) -> bytes:
    payload = {
        "query": query,
        "debug": True,
        "session_id": session_id,
    }
    return json.dumps(payload, ensure_ascii=True, separators=(",", ":")).encode("ascii")


def _safe_preview(text: str, *, max_len: int = 180) -> str:
    normalized = " ".join(str(text or "").split())
    if len(normalized) <= max_len:
        return normalized
    return normalized[: max_len - 3].rstrip() + "..."


def _sanitize_botdb_chunk(item: dict[str, Any], *, rank: int) -> dict[str, Any]:
    governance = item.get("governance") if isinstance(item.get("governance"), dict) else {}
    return {
        "rank": rank,
        "chunk_id": str(item.get("chunk_id", "") or ""),
        "source_doc": str(item.get("block_title", "") or ""),
        "source_type": str(item.get("source_type", "") or ""),
        "chunk_type": str(governance.get("chunk_type", "") or "general_text"),
        "allowed_use": list(governance.get("allowed_use", []) or []),
        "quote_policy": str(governance.get("quote_policy", "") or "paraphrase_only"),
        "score": float(item.get("score", 0.0) or 0.0),
        "preview": _safe_preview(str(item.get("content", "") or "")),
    }


def _query_botdb(*, botdb_base_url: str, query: str, search_mode: str) -> dict[str, Any]:
    payload = {
        "query": query,
        "top_k": 10,
        "pre_filter_k": 40,
        "use_rerank": False,
        "search_mode": search_mode,
    }
    response = httpx.post(f"{botdb_base_url.rstrip('/')}/api/query/", json=payload, timeout=30.0)
    response.raise_for_status()
    body = response.json()
    chunks = [
        _sanitize_botdb_chunk(item, rank=index)
        for index, item in enumerate(list(body.get("chunks", []) or [])[:10], start=1)
        if isinstance(item, dict)
    ]
    return {
        "status_code": response.status_code,
        "search_mode": search_mode,
        "chunks": chunks,
        "debug": body.get("debug") if isinstance(body.get("debug"), dict) else {},
    }


def _run_adaptive_probe(*, backend_base_url: str, query: str, session_id: str) -> dict[str, Any]:
    response = httpx.post(
        f"{backend_base_url.rstrip('/')}/api/v1/questions/adaptive",
        content=_ascii_json_body(query, session_id),
        headers={**API_HEADERS, "X-Session-Id": session_id},
        timeout=60.0,
    )
    response.raise_for_status()
    payload = response.json()
    debug_response = httpx.get(
        f"{backend_base_url.rstrip('/')}/api/debug/session/{session_id}/multiagent-trace",
        headers={"X-API-Key": "dev-key-001"},
        timeout=60.0,
    )
    debug_response.raise_for_status()
    debug_payload = debug_response.json()
    return {
        "answer": str(payload.get("answer", "") or ""),
        "debug_trace": debug_payload,
    }


def _classify_probe(source_trace: dict[str, Any]) -> str:
    loss_stage = str(source_trace.get("loss_stage", "") or "unknown")
    loss_reason = str(source_trace.get("loss_reason", "") or "")
    payload_match = source_trace.get("payload_match") if isinstance(source_trace.get("payload_match"), dict) else {}
    runtime_match = source_trace.get("best_runtime_match") if isinstance(source_trace.get("best_runtime_match"), dict) else {}

    if loss_stage == "none" and bool(payload_match.get("near_exact_match", False)):
        return "PASS_source_found_and_payload_visible"
    if loss_stage == "raw_source":
        return "FAIL_raw_source_missing"
    if loss_stage == "runtime_retrieval":
        return "FAIL_runtime_candidate_missing"
    if loss_stage == "gate":
        if loss_reason in {"latest_turn_no_internal_db", "filtered_by_narrow_practice_grounding"}:
            return "PASS_source_found_filtered_with_valid_reason"
        if bool(runtime_match.get("near_exact_match", False)):
            return "FAIL_gate_filtered_without_clear_reason"
        return "FAIL_payload_missing_after_selection"
    if loss_stage == "writer_payload":
        return "FAIL_payload_missing_after_selection"
    if loss_stage == "writer_usage":
        return "FAIL_writer_ignored_payload"
    return "INCONCLUSIVE_missing_trace_or_insufficient_fields"


def _source_material_present() -> bool:
    if not SOURCE_MATERIAL_PATH.exists():
        return False
    content = SOURCE_MATERIAL_PATH.read_text(encoding="utf-8")
    return "анестетическая депрессия" in content.lower()


def run_audit(*, backend_base_url: str, botdb_base_url: str) -> dict[str, Any]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    matrix: list[dict[str, Any]] = []
    markdown_lines = [
        "# PRD-047.36-HF2 Retrieval Recall Audit",
        "",
        f"- backend_base_url: `{backend_base_url}`",
        f"- botdb_base_url: `{botdb_base_url}`",
        f"- source_material_phrase_present_in_workspace: `{_source_material_present()}`",
        "",
    ]

    for probe_id, query in PROBES:
        session_id = f"prd-047-36-hf2-{probe_id.lower()}-{uuid4().hex[:8]}"
        raw_hybrid = _query_botdb(botdb_base_url=botdb_base_url, query=query, search_mode="hybrid")
        raw_semantic = _query_botdb(botdb_base_url=botdb_base_url, query=query, search_mode="semantic")
        adaptive = _run_adaptive_probe(backend_base_url=backend_base_url, query=query, session_id=session_id)
        debug_trace = adaptive["debug_trace"] if isinstance(adaptive.get("debug_trace"), dict) else {}
        runtime_truth = debug_trace.get("runtime_truth_trace_v1") if isinstance(debug_trace.get("runtime_truth_trace_v1"), dict) else {}
        writer_payload_trace = debug_trace.get("writer_kb_payload_trace") if isinstance(debug_trace.get("writer_kb_payload_trace"), dict) else {}
        semantic_cards_trace = debug_trace.get("semantic_cards_pilot") if isinstance(debug_trace.get("semantic_cards_pilot"), dict) else {}
        source_trace = runtime_truth.get("source_chunk_match_trace_v1") if isinstance(runtime_truth.get("source_chunk_match_trace_v1"), dict) else {}
        classification = _classify_probe(source_trace)

        row = {
            "probe_id": probe_id,
            "query": query,
            "classification": classification,
            "source_material_phrase_present_in_workspace": _source_material_present() if probe_id in {"A1", "A2", "A3"} else None,
            "raw_source_search_top_10": raw_hybrid["chunks"],
            "botdb_vector_top_10": raw_semantic["chunks"],
            "botdb_lexical_or_keyword_top_10": [],
            "runtime_memory_candidates_top_10": list(debug_trace.get("memory_context", {}).get("semantic_hits", []) or []) if isinstance(debug_trace.get("memory_context"), dict) else [],
            "hybrid_candidates_top_10": list(debug_trace.get("retrieval_decision", {}).get("rag_included_for_writer", []) or []) if isinstance(debug_trace.get("retrieval_decision"), dict) else [],
            "semantic_card_candidates": list(semantic_cards_trace.get("candidate_scores", []) or []),
            "filtered_candidates": list(runtime_truth.get("filtered_out_for_writer", []) or []),
            "writer_payload_chunks": list(writer_payload_trace.get("chunk_summaries", []) or []),
            "runtime_truth_summary": {
                "retrieved_candidates_count": int(runtime_truth.get("retrieved_candidates_count", 0) or 0),
                "filtered_out_for_writer_count": int(runtime_truth.get("filtered_out_for_writer_count", 0) or 0),
                "writer_visible_payload_count": int(runtime_truth.get("writer_visible_payload_count", 0) or 0),
                "payload_decision_reason": str(runtime_truth.get("payload_decision_reason", "") or ""),
                "grounding_visibility_reason": str(runtime_truth.get("grounding_visibility_reason", "") or ""),
                "writer_kb_payload_status": str(runtime_truth.get("writer_kb_payload_status", "") or ""),
                "writer_kb_payload_primary_path": str(runtime_truth.get("writer_kb_payload_primary_path", "") or ""),
                "retrieval_gate_recovery_applied": bool(
                    runtime_truth.get("retrieval_gate_recovery_applied", False)
                ),
            },
            "writer_grounding_visibility_v1": debug_trace.get("writer_grounding_visibility_v1", {}),
            "retrieval_decision_summary": {
                "retrieval_action": str(debug_trace.get("retrieval_decision", {}).get("retrieval_action", "") or ""),
                "retrieval_need": str(debug_trace.get("retrieval_decision", {}).get("retrieval_need", "") or ""),
                "rag_included_count": int(debug_trace.get("retrieval_decision", {}).get("rag_included_count", 0) or 0),
                "rag_suppressed_reason": str(debug_trace.get("retrieval_decision", {}).get("rag_suppressed_reason", "") or ""),
            },
            "source_chunk_match_trace_v1": source_trace,
            "final_answer_summary": _safe_preview(str(adaptive.get("answer", "") or ""), max_len=260),
        }
        matrix.append(row)

        markdown_lines.extend(
            [
                f"## {probe_id}",
                f"- query: `{query}`",
                f"- classification: `{classification}`",
                f"- loss_stage: `{source_trace.get('loss_stage', 'unknown')}`",
                f"- loss_reason: `{source_trace.get('loss_reason', '')}`",
                f"- best_raw_match: `{dict(source_trace.get('best_raw_match', {})).get('chunk_id', 'none')}`",
                f"- best_runtime_match: `{dict(source_trace.get('best_runtime_match', {})).get('chunk_id', 'none')}`",
                f"- payload_match: `{dict(source_trace.get('payload_match', {})).get('chunk_id', 'none')}`",
                f"- answer_preview: `{row['final_answer_summary']}`",
                "",
            ]
        )

    matrix_path = OUTPUT_DIR / "candidate_path_matrix.json"
    audit_path = OUTPUT_DIR / "retrieval_recall_audit.md"
    matrix_path.write_text(json.dumps({"probes": matrix}, ensure_ascii=False, indent=2), encoding="utf-8")
    audit_path.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")
    return {
        "candidate_path_matrix": str(matrix_path),
        "retrieval_recall_audit": str(audit_path),
        "probe_count": len(matrix),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend-base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--botdb-base-url", default="http://127.0.0.1:8003")
    args = parser.parse_args()
    result = run_audit(
        backend_base_url=str(args.backend_base_url),
        botdb_base_url=str(args.botdb_base_url),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
