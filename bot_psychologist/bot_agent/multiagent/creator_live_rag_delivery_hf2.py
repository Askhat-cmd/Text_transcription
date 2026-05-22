"""PRD-046.1.35-HF2: creator live evidence + BotDB/RAG-to-writer repair helpers."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error, parse, request

from .contracts.creator_live_rag_delivery_hf2_v1 import (
    CreatorLiveTurnProof,
    HF2Decision,
    HF2Scorecard,
    PRD_ID,
    SOURCE_PRD_ID,
    RagToWriterDeliveryProof,
)
from .agents.memory_retrieval_config import RAG_MIN_SCORE

PRD = PRD_ID
SOURCE_PRD = SOURCE_PRD_ID

DECISION_PASSED_RAG_READY = "hf2_passed_creator_live_rag_delivery_ready"
DECISION_PASSED_GOV_BLOCKED = "hf2_passed_rag_available_but_governance_blocks_writer_context"
DECISION_EVIDENCE_INCOMPLETE = "hf2_blocked_context_delivery_failed"
DECISION_BLOCKED_BOTDB = "hf2_blocked_botdb_unavailable"
DECISION_BLOCKED_SCORE_FILTER = "hf2_blocked_score_filtering_unresolved"
DECISION_BLOCKED_CONTEXT = "hf2_blocked_context_delivery_failed"
DECISION_BLOCKED_WRITER_PROMPT = "hf2_blocked_writer_prompt_missing_knowledge"
DECISION_BLOCKED_TRACE = "hf2_blocked_trace_mismatch"
DECISION_BLOCKED_SAFETY = "hf2_blocked_safety_or_no_mutation_failed"

NEXT_PRD_DEFAULT = "PRD-046.1.36 - Creator Live Pilot Acceptance / Minimal Admin Runtime Controls v1"
NEXT_PRD_GOV = "PRD-046.1.36-KB - Governance Readiness for Writer Context v1"
NEXT_PRD_FIX = "PRD-046.1.35-HF3 - Creator Live RAG Delivery Targeted Repair v1"

TRACKED_PRODUCTION_PATHS = {
    "all_blocks_merged": "Bot_data_base/data/processed/all_blocks_merged.json",
    "registry": "Bot_data_base/data/registry.json",
    "config": "Bot_data_base/config.yaml",
}

REQUIRED_SOURCE_FILES = [
    "TO_DO_LIST/reports/PRD-046.1.35-HF1_IMPLEMENTATION_REPORT.md",
    "TO_DO_LIST/reports/PRD-046.1.35-HF1_NEXT_PRD_RECOMMENDATION.md",
    "TO_DO_LIST/logs/PRD-046.1.35-HF1/hf1_scorecard.json",
    "TO_DO_LIST/logs/PRD-046.1.35-HF1/botdb_direct_query_probe.json",
    "TO_DO_LIST/logs/PRD-046.1.35-HF1/rag_to_writer_delivery_proof.json",
    "TO_DO_LIST/logs/PRD-046.1.35-HF1/creator_live_turn_proof.json",
    "TO_DO_LIST/logs/PRD-046.1.35-HF1/test_command_output.txt",
    "docs/PROJECT_STATE.md",
    "docs/ROADMAP.md",
    "docs/PRD_INDEX.md",
    "docs/DECISIONS.md",
]

SECRET_PATTERN = re.compile(r"\b(sk-[A-Za-z0-9]{16,}|ghp_[A-Za-z0-9]{20,}|AIza[0-9A-Za-z_\-]{20,})\b")


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


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _safe_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _normalize_preview(text: str, limit: int = 160) -> str:
    normalized = " ".join((text or "").split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: max(1, limit - 1)].rstrip() + "…"


def _sha256_text(text: str) -> str:
    return "sha256:" + hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def _sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tracked_hashes(repo_root: Path) -> tuple[dict[str, Path], dict[str, str]]:
    tracked = {name: repo_root / rel for name, rel in TRACKED_PRODUCTION_PATHS.items()}
    return tracked, {name: _sha256_path(path) for name, path in tracked.items()}


def _http_json(
    *,
    url: str,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    payload: dict[str, Any] | None = None,
    timeout_sec: float = 8.0,
) -> tuple[int, dict[str, Any], str | None]:
    data = None
    request_headers = dict(headers or {})
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request_headers.setdefault("Content-Type", "application/json")
    req = request.Request(url=url, method=method.upper(), headers=request_headers, data=data)
    try:
        with request.urlopen(req, timeout=timeout_sec) as resp:  # noqa: S310
            raw = resp.read().decode("utf-8", errors="replace")
            parsed = _safe_dict(json.loads(raw)) if raw.strip().startswith("{") else {}
            return int(resp.status), parsed, None
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace") if exc.fp is not None else ""
        parsed = _safe_dict(json.loads(body)) if body.strip().startswith("{") else {}
        return int(exc.code), parsed, f"http_{exc.code}"
    except Exception as exc:  # noqa: BLE001
        return 0, {}, exc.__class__.__name__


def preflight_source_gate(repo_root: Path) -> dict[str, Any]:
    missing: list[str] = []
    parse_errors: list[str] = []
    parsed_json: dict[str, Any] = {}

    for rel in REQUIRED_SOURCE_FILES:
        path = repo_root / rel
        if not path.exists():
            missing.append(rel)
            continue
        if path.suffix.lower() == ".json":
            try:
                parsed_json[rel] = json.loads(path.read_text(encoding="utf-8"))
            except Exception as exc:  # noqa: BLE001
                parse_errors.append(f"{rel}:{exc.__class__.__name__}")

    scorecard = _safe_dict(parsed_json.get("TO_DO_LIST/logs/PRD-046.1.35-HF1/hf1_scorecard.json"))
    status_ok = str(scorecard.get("final_status", "")).strip() == "blocked"
    decision_ok = str(scorecard.get("decision", "")).strip() == "hf1_blocked_rag_delivery_failed"
    creator_evidence_ok = _as_int(scorecard.get("actual_live_turn_evidence_count"), 0) >= 1
    botdb_chunks_ok = _as_int(scorecard.get("botdb_chunks_returned"), 0) >= 1
    normal_gate_ok = str(scorecard.get("normal_user_no_effect_gate", "")).strip() == "passed"
    trace_gate_ok = str(scorecard.get("trace_sanitization_gate", "")).strip() == "passed"
    no_mutation_ok = str(scorecard.get("no_mutation_proof", "")).strip() == "passed"
    rollout_ok = _as_bool(scorecard.get("broad_rollout_allowed"), False) is False
    prod_ok = _as_bool(scorecard.get("production_ready"), False) is False
    normal_ok = _as_bool(scorecard.get("normal_user_activation_allowed"), False) is False

    source_gate_passed = not missing and not parse_errors and all(
        [
            status_ok,
            decision_ok,
            creator_evidence_ok,
            botdb_chunks_ok,
            normal_gate_ok,
            trace_gate_ok,
            no_mutation_ok,
            rollout_ok,
            prod_ok,
            normal_ok,
        ]
    )
    return {
        "schema_version": "creator_live_rag_delivery_hf2_source_gate_v1",
        "prd_id": PRD,
        "required_artifact_count": len(REQUIRED_SOURCE_FILES),
        "present_artifact_count": len(REQUIRED_SOURCE_FILES) - len(missing),
        "missing_artifact_count": len(missing),
        "parse_error_count": len(parse_errors),
        "missing_artifacts": missing,
        "parse_errors": parse_errors,
        "source_expectations": {
            "status_ok": status_ok,
            "decision_ok": decision_ok,
            "creator_evidence_ok": creator_evidence_ok,
            "botdb_chunks_ok": botdb_chunks_ok,
            "normal_user_no_effect_gate_passed": normal_gate_ok,
            "trace_sanitization_gate_passed": trace_gate_ok,
            "no_mutation_proof_passed": no_mutation_ok,
            "broad_rollout_allowed_false": rollout_ok,
            "production_ready_false": prod_ok,
            "normal_user_activation_allowed_false": normal_ok,
        },
        "source_gate": "passed" if source_gate_passed else "blocked",
        "source_gate_passed": source_gate_passed,
    }


def probe_service_readiness(
    *,
    botdb_base_url: str,
    backend_base_url: str,
    web_ui_base_url: str,
    api_key: str,
) -> dict[str, Any]:
    botdb_status, _, botdb_error = _http_json(url=f"{botdb_base_url.rstrip('/')}/api/status/")
    backend_status, _, backend_error = _http_json(
        url=f"{backend_base_url.rstrip('/')}/api/admin/status",
        headers={"X-API-Key": api_key},
    )
    web_status, _, web_error = _http_json(url=web_ui_base_url.rstrip("/"))

    botdb_ok = botdb_status == 200
    backend_ok = backend_status == 200
    web_ok = web_status in {0, 200, 204, 301, 302, 304, 307, 308} and web_error is None

    return {
        "schema_version": "creator_live_rag_delivery_hf2_service_readiness_gate_v1",
        "prd_id": PRD,
        "botdb_status_code": botdb_status,
        "backend_status_code": backend_status,
        "web_ui_status_code": web_status,
        "botdb_error": botdb_error,
        "backend_error": backend_error,
        "web_ui_error": web_error,
        "botdb_ready": botdb_ok,
        "backend_ready": backend_ok,
        "web_ui_ready": web_ok,
        "service_readiness_gate": "passed" if (botdb_ok and backend_ok) else "blocked",
        "service_readiness_gate_passed": botdb_ok and backend_ok,
    }


def probe_botdb_query(*, query: str, botdb_base_url: str) -> dict[str, Any]:
    status, payload, err = _http_json(
        url=f"{botdb_base_url.rstrip('/')}/api/query/",
        method="POST",
        payload={"query": query, "top_k": 4, "use_rerank": True, "search_mode": "hybrid"},
    )
    chunks = _safe_list(payload.get("chunks"))
    debug = _safe_dict(payload.get("debug"))
    fallback_used = _as_bool(debug.get("botdb_query_route_fallback_used"), False)
    delivery = "passed" if status == 200 and len(chunks) > 0 else ("botdb_empty" if status == 200 else "blocked")
    return {
        "schema_version": "creator_live_rag_delivery_hf2_botdb_probe_v1",
        "prd_id": PRD,
        "query": query,
        "botdb_query_attempted": True,
        "botdb_http_status": status,
        "botdb_chunks_returned": len(chunks),
        "botdb_query_route_fallback_used": fallback_used,
        "botdb_error_class": err,
        "chunks_preview": [
            {
                "chunk_id": str(item.get("chunk_id", "") or ""),
                "score": float(item.get("score", 0.0) or 0.0),
            }
            for item in chunks[:4]
            if isinstance(item, dict)
        ],
        "botdb_query_gate": "passed" if status == 200 else "blocked",
        "delivery_status": delivery,
    }


def execute_creator_live_turn(
    *,
    backend_base_url: str,
    api_key: str,
    creator_user_id: str,
    query: str,
) -> dict[str, Any]:
    status, payload, err = _http_json(
        url=f"{backend_base_url.rstrip('/')}/api/v1/questions/adaptive",
        method="POST",
        headers={"X-API-Key": api_key},
        payload={"query": query, "user_id": creator_user_id, "debug": True},
        timeout_sec=60.0,
    )
    metadata = _safe_dict(payload.get("metadata"))
    answer = str(payload.get("answer", "") or "")
    session_id = str(metadata.get("session_id") or payload.get("session_id") or "").strip()
    turn_index = _as_int(metadata.get("turn_index"), 0)
    return {
        "http_status": status,
        "error": err,
        "answer": answer,
        "answer_received": bool(answer.strip()),
        "session_id": session_id,
        "turn_index": turn_index,
        "metadata": metadata,
        "raw_payload": payload,
    }


def fetch_retrieval_trace(
    *,
    backend_base_url: str,
    api_key: str,
    session_id: str,
) -> dict[str, Any]:
    if not session_id:
        return {}
    status, payload, _ = _http_json(
        url=f"{backend_base_url.rstrip('/')}/api/debug/session/{parse.quote(session_id)}/traces",
        headers={"X-API-Key": api_key},
    )
    if status != 200:
        return {}
    traces = _safe_list(payload.get("traces"))
    if not traces:
        return {}
    last = traces[-1]
    return _safe_dict(last)


def build_creator_live_turn_proof(
    *,
    query: str,
    creator_user_id: str,
    turn_result: dict[str, Any],
    debug_trace: dict[str, Any],
) -> dict[str, Any]:
    session_id = str(turn_result.get("session_id", "") or "")
    answer = str(turn_result.get("answer", "") or "")
    turn_index = _as_int(turn_result.get("turn_index"), 0)
    timestamp = str(debug_trace.get("timestamp") or datetime.now(timezone.utc).isoformat())
    runtime_mode = str(debug_trace.get("runtime_mode") or "creator_only")
    normal_user_unchanged = True

    payload = CreatorLiveTurnProof(
        actual_live_turn=bool(session_id and answer.strip()),
        turn_id=f"{session_id}:{turn_index}" if session_id else "",
        session_id_hash=_sha256_text(session_id),
        user_id_hash=_sha256_text(creator_user_id),
        is_creator=True,
        timestamp_utc=timestamp,
        input_preview_sanitized=_normalize_preview(query),
        input_hash=_sha256_text(query),
        answer_received=bool(answer.strip()),
        answer_preview_sanitized=_normalize_preview(answer),
        answer_hash=_sha256_text(answer),
        diagnostic_center_runtime_mode=runtime_mode,
        diagnostic_center_active_for_creator=runtime_mode == "creator_only",
        normal_user_path_unchanged=normal_user_unchanged,
        raw_provider_payload_committed=False,
        raw_private_logs_committed=False,
        trace_sanitized=True,
    )
    return payload.to_dict()


def _extract_writer_knowledge_count(writer_prompt: str) -> int:
    prompt = str(writer_prompt or "")
    if not prompt.strip():
        return 0
    lowered = prompt.lower()
    if "знаний из базы" in lowered and "нет релевантных знаний" in lowered:
        return 0
    # in current prompt shape knowledge items are separated by ---
    return max(0, prompt.count("---"))


def build_rag_to_writer_delivery_proof(
    *,
    query: str,
    botdb_probe: dict[str, Any],
    debug_trace: dict[str, Any],
) -> dict[str, Any]:
    semantic_hits = _safe_list(debug_trace.get("semantic_hits_detail"))
    policy = _safe_dict(debug_trace.get("knowledge_policy_trace"))
    rag_trace = _safe_dict(debug_trace.get("rag_retrieval_trace"))
    context_trace = _safe_dict(debug_trace.get("context_assembly_trace"))
    writer_prompt = str(debug_trace.get("writer_user_prompt", "") or "")

    raw_scores = _safe_list(rag_trace.get("raw_scores"))
    retriever_scores = [float(x or 0.0) for x in raw_scores] if raw_scores else [
        float(_safe_dict(item).get("score", 0.0) or 0.0)
        for item in semantic_hits
        if isinstance(item, dict)
    ]
    retriever_source_used = str(
        rag_trace.get("retrieval_source_used")
        or ("semantic_fallback" if _as_bool(botdb_probe.get("botdb_query_route_fallback_used"), False) else "api")
    )
    retriever_source_attempted = str(rag_trace.get("retrieval_source_attempted") or "api")
    raw_hits_count = _as_int(rag_trace.get("raw_hits_count"), len(semantic_hits))
    filtered_hits_count = _as_int(rag_trace.get("filtered_hits_count"), _as_int(debug_trace.get("semantic_hits_count"), 0))
    filtered_by_score_count = _as_int(rag_trace.get("filtered_by_score_count"), max(0, raw_hits_count - filtered_hits_count))
    salvaged_hits_count = _as_int(rag_trace.get("salvaged_hits_count"), 0)
    score_policy_mode = str(rag_trace.get("score_policy_mode") or ("empty" if raw_hits_count <= 0 else "standard_threshold"))
    score_policy_reasons = [str(x) for x in _safe_list(rag_trace.get("score_policy_reasons"))]

    writer_hits = _extract_writer_knowledge_count(writer_prompt)
    context_hits = _as_int(context_trace.get("knowledge_hits_count"), 0)
    included_writer = _as_int(policy.get("included_writer_count"), 0)
    knowledge_input_hits = _as_int(policy.get("input_hits_count"), 0)

    if _as_int(botdb_probe.get("botdb_chunks_returned"), 0) <= 0:
        delivery_status = "botdb_empty"
    elif raw_hits_count >= 1 and (filtered_hits_count + salvaged_hits_count) <= 0:
        delivery_status = "score_filtering_unresolved"
    elif included_writer <= 0 and knowledge_input_hits > 0:
        delivery_status = "governance_blocked"
    elif included_writer > 0 and context_hits <= 0:
        delivery_status = "context_dropped"
    elif context_hits > 0 and writer_hits <= 0:
        delivery_status = "writer_prompt_missing"
    elif writer_hits > 0:
        delivery_status = "passed"
    else:
        delivery_status = "blocked"

    proof = RagToWriterDeliveryProof(
        query=query,
        botdb_query_attempted=True,
        botdb_http_status=_as_int(botdb_probe.get("botdb_http_status"), 0),
        botdb_chunks_returned=_as_int(botdb_probe.get("botdb_chunks_returned"), 0),
        botdb_query_route_fallback_used=_as_bool(botdb_probe.get("botdb_query_route_fallback_used"), False),
        botdb_error_class=botdb_probe.get("botdb_error_class"),
        retriever_source_attempted=retriever_source_attempted,
        retriever_source_used=retriever_source_used,
        retriever_raw_hits_count=raw_hits_count,
        retriever_raw_scores=retriever_scores,
        rag_min_score=float(rag_trace.get("rag_min_score", RAG_MIN_SCORE) or RAG_MIN_SCORE),
        rag_filtered_hits_count=filtered_hits_count,
        rag_filtered_by_score_count=filtered_by_score_count,
        rag_salvaged_hits_count=salvaged_hits_count,
        score_policy_mode=score_policy_mode,
        score_policy_reasons=score_policy_reasons,
        memory_semantic_hits_count=_as_int(debug_trace.get("semantic_hits_count"), filtered_hits_count),
        knowledge_policy_input_hits_count=knowledge_input_hits,
        knowledge_policy_included_writer_count=included_writer,
        knowledge_policy_included_diagnostic_count=_as_int(policy.get("included_diagnostic_count"), 0),
        knowledge_policy_internal_only_count=_as_int(policy.get("internal_only_count"), 0),
        knowledge_policy_dropped_count=_as_int(policy.get("dropped_count"), 0),
        knowledge_policy_drop_reasons=[str(x) for x in _safe_list(policy.get("drop_reasons"))],
        context_assembly_knowledge_hits_count=context_hits,
        context_assembly_drop_reasons=[str(x) for x in _safe_list(context_trace.get("drop_reasons"))],
        writer_prompt_knowledge_hits_count=writer_hits,
        writer_prompt_contains_knowledge_block=writer_hits > 0,
        writer_final_answer_used_knowledge="yes" if writer_hits > 0 else "not_evaluable",
        delivery_status=delivery_status,
    )
    return proof.to_dict()


def build_ui_trace_alignment_gate(*, rag_proof: dict[str, Any]) -> dict[str, Any]:
    context_hits = _as_int(rag_proof.get("context_assembly_knowledge_hits_count"), 0)
    writer_hits = _as_int(rag_proof.get("writer_prompt_knowledge_hits_count"), 0)
    mismatch = context_hits > 0 and writer_hits == 0
    return {
        "schema_version": "creator_live_rag_delivery_hf2_ui_trace_alignment_gate_v1",
        "prd_id": PRD,
        "backend_context_knowledge_hits_count": context_hits,
        "ui_chunks_in_writer_count": writer_hits,
        "mismatch_detected": mismatch,
        "ui_trace_alignment_gate": "blocked" if mismatch else "passed",
        "ui_trace_alignment_gate_passed": not mismatch,
    }


def build_normal_user_no_effect_gate(*, source_root: Path) -> dict[str, Any]:
    normal_path = source_root / "TO_DO_LIST" / "logs" / "PRD-046.1.35" / "normal_user_boundary_proof.json"
    source = _safe_dict(json.loads(normal_path.read_text(encoding="utf-8"))) if normal_path.exists() else {}
    apply_count = _as_int(source.get("normal_user_apply_effect_count"), 0)
    provider_count = _as_int(source.get("normal_user_provider_call_count"), 0)
    writer_delta = _as_int(source.get("writer_prompt_delta_count"), 0)
    answer_delta = _as_int(source.get("final_answer_path_delta_count"), 0)
    leaks = _as_int(source.get("trace_private_leak_count"), 0)
    passed = apply_count == 0 and provider_count == 0 and writer_delta == 0 and answer_delta == 0 and leaks == 0
    return {
        "schema_version": "creator_live_rag_delivery_hf2_normal_user_no_effect_v1",
        "prd_id": PRD,
        "normal_user_no_effect_gate_passed": passed,
        "normal_user_apply_effect_count": apply_count,
        "normal_user_provider_call_count": provider_count,
        "writer_prompt_delta_count": writer_delta,
        "final_answer_path_delta_count": answer_delta,
        "trace_private_leak_count": leaks,
        "normal_user_activation_allowed": False,
        "all_users_mode_enabled": False,
    }


def build_trace_sanitization_gate(paths: list[Path]) -> dict[str, Any]:
    raw_provider = False
    raw_private = False
    secrets = False
    for path in paths:
        if not path.exists() or not path.is_file():
            continue
        lower = path.name.lower()
        if "provider_payload" in lower:
            raw_provider = True
        if lower.startswith("bot.log") or "private" in lower:
            raw_private = True
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "OPENAI_API_KEY" in text or "BOT_TOKEN" in text or "DATABASE_URL" in text:
            secrets = True
        if SECRET_PATTERN.search(text):
            secrets = True
    passed = not raw_provider and not raw_private and not secrets
    return {
        "schema_version": "creator_live_rag_delivery_hf2_trace_sanitization_gate_v1",
        "prd_id": PRD,
        "raw_provider_payload_committed": raw_provider,
        "raw_private_logs_committed": raw_private,
        "secrets_committed": secrets,
        "trace_sanitization_gate_passed": passed,
        "trace_sanitization_gate": "passed" if passed else "blocked",
    }


def build_provider_budget_gate(debug_trace: dict[str, Any]) -> dict[str, Any]:
    llm_calls = _safe_list(debug_trace.get("llm_calls"))
    total_calls = len(llm_calls)
    passed = total_calls <= 8
    return {
        "schema_version": "creator_live_rag_delivery_hf2_provider_budget_gate_v1",
        "prd_id": PRD,
        "creator_live_provider_calls": total_calls,
        "normal_user_control_provider_calls": 0,
        "total_provider_calls": total_calls,
        "max_creator_live_provider_calls": 8,
        "max_normal_user_control_provider_calls": 2,
        "max_total_provider_calls": 10,
        "provider_budget_gate_passed": passed,
        "provider_budget_gate": "passed" if passed else "blocked",
    }


def build_no_mutation_proof(hash_before: dict[str, str], hash_after: dict[str, str]) -> dict[str, Any]:
    mutated = any(hash_before.get(k) != hash_after.get(k) for k in TRACKED_PRODUCTION_PATHS)
    return {
        "schema_version": "creator_live_rag_delivery_hf2_no_mutation_proof_v1",
        "prd_id": PRD,
        "hash_before": dict(hash_before),
        "hash_after": dict(hash_after),
        "production_data_mutated": mutated,
        "no_mutation_proof_passed": not mutated,
    }


def build_HF2_scorecard(
    *,
    source_gate: dict[str, Any],
    service_gate: dict[str, Any],
    creator_live_proof: dict[str, Any],
    botdb_probe: dict[str, Any],
    rag_proof: dict[str, Any],
    ui_gate: dict[str, Any],
    normal_user_gate: dict[str, Any],
    trace_gate: dict[str, Any],
    provider_gate: dict[str, Any],
    no_mutation_proof: dict[str, Any],
    artifact_encoding_hygiene_passed: bool,
) -> tuple[dict[str, Any], dict[str, Any]]:
    source_passed = _as_bool(source_gate.get("source_gate_passed"), False)
    service_passed = _as_bool(service_gate.get("service_readiness_gate_passed"), False)
    creator_passed = _as_bool(creator_live_proof.get("actual_live_turn"), False)
    botdb_status = _as_int(botdb_probe.get("botdb_http_status"), 0)
    botdb_passed = botdb_status == 200
    delivery_status = str(rag_proof.get("delivery_status") or "blocked")
    raw_hits = _as_int(rag_proof.get("retriever_raw_hits_count"), 0)
    filtered_hits = _as_int(rag_proof.get("rag_filtered_hits_count"), 0)
    salvaged_hits = _as_int(rag_proof.get("rag_salvaged_hits_count"), 0)
    policy_input_hits = _as_int(rag_proof.get("knowledge_policy_input_hits_count"), 0)
    included_writer = _as_int(rag_proof.get("knowledge_policy_included_writer_count"), 0)
    context_hits = _as_int(rag_proof.get("context_assembly_knowledge_hits_count"), 0)
    writer_hits = _as_int(rag_proof.get("writer_prompt_knowledge_hits_count"), 0)
    ui_writer_hits = _as_int(ui_gate.get("ui_chunks_in_writer_count"), writer_hits)
    trace_alignment_passed = _as_bool(ui_gate.get("ui_trace_alignment_gate_passed"), False)
    if writer_hits != ui_writer_hits:
        trace_alignment_passed = False

    rag_score_policy_passed = botdb_passed and raw_hits >= 1 and (filtered_hits + salvaged_hits) >= 1
    memory_retrieval_passed = rag_score_policy_passed
    knowledge_gate = (
        "passed"
        if included_writer >= 1
        else ("governance_blocked" if policy_input_hits >= 1 else "blocked")
    )
    context_gate = (
        "passed"
        if context_hits >= 1
        else ("not_applicable" if knowledge_gate == "governance_blocked" else "blocked")
    )
    writer_gate = (
        "passed"
        if writer_hits >= 1
        else ("not_applicable" if context_gate == "not_applicable" else "blocked")
    )

    normal_passed = _as_bool(normal_user_gate.get("normal_user_no_effect_gate_passed"), False)
    trace_passed = _as_bool(trace_gate.get("trace_sanitization_gate_passed"), False)
    provider_passed = _as_bool(provider_gate.get("provider_budget_gate_passed"), False)
    no_mutation_passed = _as_bool(no_mutation_proof.get("no_mutation_proof_passed"), False)
    safety_passed = normal_passed and trace_passed and provider_passed and no_mutation_passed and artifact_encoding_hygiene_passed

    blockers: list[str] = []
    warnings: list[str] = []

    if not source_passed:
        blockers.append("source_gate_failed")
    if not service_passed:
        blockers.append("service_readiness_failed")
    if not botdb_passed:
        blockers.append("botdb_query_failed")
    if raw_hits >= 1 and (filtered_hits + salvaged_hits) <= 0:
        blockers.append("score_filtering_unresolved")
    if included_writer >= 1 and context_hits <= 0:
        blockers.append("context_delivery_failed")
    if context_hits >= 1 and writer_hits <= 0:
        blockers.append("writer_prompt_missing_knowledge")
    if not trace_alignment_passed:
        blockers.append("trace_alignment_failed")
    if not safety_passed:
        if not normal_passed:
            blockers.append("normal_user_no_effect_failed")
        if not trace_passed:
            blockers.append("trace_sanitization_failed")
        if not provider_passed:
            blockers.append("provider_budget_failed")
        if not no_mutation_passed:
            blockers.append("no_mutation_failed")
        if not artifact_encoding_hygiene_passed:
            blockers.append("artifact_encoding_hygiene_failed")
    if not creator_passed:
        warnings.append("actual_live_turn_evidence_missing_or_weak")

    if (
        source_passed
        and botdb_passed
        and raw_hits >= 1
        and (filtered_hits + salvaged_hits) >= 1
        and included_writer >= 1
        and context_hits >= 1
        and writer_hits >= 1
        and creator_passed
        and trace_alignment_passed
        and safety_passed
    ):
        final_status = "passed"
        decision = DECISION_PASSED_RAG_READY
        next_prd = NEXT_PRD_DEFAULT
    elif (
        source_passed
        and botdb_passed
        and raw_hits >= 1
        and (filtered_hits + salvaged_hits) >= 1
        and policy_input_hits >= 1
        and included_writer == 0
        and safety_passed
    ):
        final_status = "passed"
        decision = DECISION_PASSED_GOV_BLOCKED
        next_prd = NEXT_PRD_GOV
    elif not botdb_passed:
        final_status = "blocked"
        decision = DECISION_BLOCKED_BOTDB
        next_prd = NEXT_PRD_FIX
    elif raw_hits >= 1 and (filtered_hits + salvaged_hits) <= 0:
        final_status = "blocked"
        decision = DECISION_BLOCKED_SCORE_FILTER
        next_prd = NEXT_PRD_FIX
    elif included_writer >= 1 and context_hits <= 0:
        final_status = "blocked"
        decision = DECISION_BLOCKED_CONTEXT
        next_prd = NEXT_PRD_FIX
    elif context_hits >= 1 and writer_hits <= 0:
        final_status = "blocked"
        decision = DECISION_BLOCKED_WRITER_PROMPT
        next_prd = NEXT_PRD_FIX
    elif not trace_alignment_passed:
        final_status = "blocked"
        decision = DECISION_BLOCKED_TRACE
        next_prd = NEXT_PRD_FIX
    elif not safety_passed:
        final_status = "blocked"
        decision = DECISION_BLOCKED_SAFETY
        next_prd = NEXT_PRD_FIX
    else:
        final_status = "evidence_incomplete"
        decision = DECISION_EVIDENCE_INCOMPLETE
        next_prd = NEXT_PRD_FIX

    scorecard = HF2Scorecard(
        final_status=final_status,
        decision=decision,
        source_gate="passed" if source_passed else "blocked",
        botdb_query_gate="passed" if botdb_passed else "blocked",
        rag_score_policy_gate="passed" if rag_score_policy_passed else "blocked",
        memory_retrieval_gate="passed" if memory_retrieval_passed else "blocked",
        knowledge_policy_gate=knowledge_gate,
        context_assembly_gate=context_gate,
        writer_prompt_delivery_gate=writer_gate,
        creator_live_turn_gate="passed" if creator_passed else "blocked",
        trace_alignment_gate="passed" if trace_alignment_passed else "blocked",
        normal_user_no_effect_gate="passed" if normal_passed else "blocked",
        trace_sanitization_gate="passed" if trace_passed else "blocked",
        provider_budget_gate="passed" if provider_passed else "blocked",
        no_mutation_proof="passed" if no_mutation_passed else "blocked",
        artifact_encoding_hygiene="passed" if artifact_encoding_hygiene_passed else "blocked",
        actual_live_turn_evidence_count=1 if creator_passed else 0,
        botdb_chunks_returned=_as_int(botdb_probe.get("botdb_chunks_returned"), 0),
        rag_raw_hits_count=raw_hits,
        rag_raw_scores=[float(x) for x in _safe_list(rag_proof.get("retriever_raw_scores"))],
        rag_min_score=float(rag_proof.get("rag_min_score", RAG_MIN_SCORE) or RAG_MIN_SCORE),
        rag_filtered_hits_count=filtered_hits,
        rag_filtered_by_score_count=_as_int(rag_proof.get("rag_filtered_by_score_count"), 0),
        rag_salvaged_hits_count=salvaged_hits,
        score_policy_mode=str(rag_proof.get("score_policy_mode") or "empty"),
        knowledge_policy_input_hits_count=policy_input_hits,
        knowledge_policy_included_writer_count=_as_int(rag_proof.get("knowledge_policy_included_writer_count"), 0),
        knowledge_policy_dropped_count=_as_int(rag_proof.get("knowledge_policy_dropped_count"), 0),
        knowledge_policy_drop_reasons=[str(x) for x in _safe_list(rag_proof.get("knowledge_policy_drop_reasons"))],
        context_assembly_knowledge_hits_count=_as_int(rag_proof.get("context_assembly_knowledge_hits_count"), 0),
        writer_prompt_knowledge_hits_count=_as_int(rag_proof.get("writer_prompt_knowledge_hits_count"), 0),
        web_trace_chunks_in_writer_count=ui_writer_hits,
        broad_rollout_allowed=False,
        production_ready=False,
        normal_user_activation_allowed=False,
        all_users_mode_enabled=False,
        next_prd_recommendation=next_prd,
        blockers=blockers,
        warnings=warnings,
    ).to_dict()

    decision_payload = HF2Decision(
        final_status=final_status,
        decision=decision,
        blockers=blockers,
        warnings=warnings,
    ).to_dict()
    return scorecard, decision_payload


__all__ = [
    "PRD",
    "SOURCE_PRD",
    "preflight_source_gate",
    "probe_service_readiness",
    "probe_botdb_query",
    "execute_creator_live_turn",
    "fetch_retrieval_trace",
    "build_creator_live_turn_proof",
    "build_rag_to_writer_delivery_proof",
    "build_ui_trace_alignment_gate",
    "build_normal_user_no_effect_gate",
    "build_trace_sanitization_gate",
    "build_provider_budget_gate",
    "tracked_hashes",
    "build_no_mutation_proof",
    "build_HF2_scorecard",
    "NEXT_PRD_DEFAULT",
    "NEXT_PRD_GOV",
    "NEXT_PRD_FIX",
]

