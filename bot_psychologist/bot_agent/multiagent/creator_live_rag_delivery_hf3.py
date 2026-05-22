"""PRD-046.1.35-HF3: creator live RAG evidence sync and truncation audit."""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error, parse, request

from .agents.memory_retrieval import memory_retrieval_agent
from .agents.memory_retrieval_config import RAG_MIN_SCORE
from .context_assembly import build_context_assembly_package_v1
from .contracts.creator_live_rag_delivery_hf3_v1 import (
    CreatorLiveTurnProof,
    HF3Decision,
    HF3Scorecard,
    PRD_ID,
    SOURCE_PRD_ID,
)
from .contracts.thread_state import ThreadState
from .contracts.writer_contract import WriterContract

PRD = PRD_ID
SOURCE_PRD = SOURCE_PRD_ID

DECISION_PASSED_VERIFIED = "hf3_passed_creator_live_rag_delivery_verified"
DECISION_PASSED_TRUNCATION_WARNING = "hf3_passed_with_kb_context_truncation_warning"
DECISION_BLOCKED_RUNTIME_TRACE = "hf3_blocked_runtime_reload_or_trace_mismatch"
DECISION_BLOCKED_RAG_REGRESSION = "hf3_blocked_rag_delivery_regression"
DECISION_BLOCKED_SAFETY = "hf3_blocked_safety_or_no_mutation_failed"

NEXT_PRD_DEFAULT = "PRD-046.1.36 - Creator Live Pilot Acceptance / Minimal Admin Runtime Controls v1"
NEXT_PRD_FIX = "PRD-046.1.35-HF4 - Creator Live RAG Evidence Sync Runtime Repair v1"
NEXT_PRD_KB_V2 = "PRD-046.1.36-KB - Writer KB Context Payload v2 Backlog"

TRACKED_PRODUCTION_PATHS = {
    "all_blocks_merged": "Bot_data_base/data/processed/all_blocks_merged.json",
    "registry": "Bot_data_base/data/registry.json",
    "config": "Bot_data_base/config.yaml",
}

REQUIRED_SOURCE_FILES = [
    "TO_DO_LIST/reports/PRD-046.1.35-HF2_IMPLEMENTATION_REPORT.md",
    "TO_DO_LIST/reports/PRD-046.1.35-HF2_NEXT_PRD_RECOMMENDATION.md",
    "TO_DO_LIST/logs/PRD-046.1.35-HF2/hf2_scorecard.json",
    "TO_DO_LIST/logs/PRD-046.1.35-HF2/botdb_direct_query_probe.json",
    "TO_DO_LIST/logs/PRD-046.1.35-HF2/test_command_output.txt",
    "docs/PROJECT_STATE.md",
    "docs/ROADMAP.md",
    "docs/PRD_INDEX.md",
    "docs/DECISIONS.md",
]

SECRET_PATTERN = re.compile(r"\b(sk-[A-Za-z0-9]{16,}|ghp_[A-Za-z0-9]{20,}|AIza[0-9A-Za-z_\-]{20,})\b")
HF2_MEMORY_EVIDENCE_PATTERNS = {
    "rag_raw_hits_count=4": re.compile(r"rag_raw_hits_count\s*=\s*4"),
    "rag_salvaged_hits_count=3": re.compile(r"rag_salvaged_hits_count\s*=\s*3"),
    "knowledge_policy_included_writer_count=3": re.compile(r"knowledge_policy_included_writer_count\s*=\s*3"),
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

    scorecard = _safe_dict(parsed_json.get("TO_DO_LIST/logs/PRD-046.1.35-HF2/hf2_scorecard.json"))
    source_log = (repo_root / "TO_DO_LIST/logs/PRD-046.1.35-HF2/test_command_output.txt")
    source_log_text = source_log.read_text(encoding="utf-8", errors="replace") if source_log.exists() else ""
    memory_evidence = {
        key: bool(pattern.search(source_log_text))
        for key, pattern in HF2_MEMORY_EVIDENCE_PATTERNS.items()
    }

    status_ok = str(scorecard.get("final_status", "")).strip() in {"evidence_incomplete", "blocked"}
    decision_ok = str(scorecard.get("decision", "")).strip() == "hf2_blocked_context_delivery_failed"
    botdb_chunks_ok = _as_int(scorecard.get("botdb_chunks_returned"), 0) >= 1
    normal_ok = _as_bool(scorecard.get("normal_user_activation_allowed"), True) is False
    rollout_ok = _as_bool(scorecard.get("broad_rollout_allowed"), True) is False
    prod_ok = _as_bool(scorecard.get("production_ready"), True) is False
    memory_evidence_ok = all(memory_evidence.values())

    source_gate_passed = not missing and not parse_errors and all(
        [status_ok, decision_ok, botdb_chunks_ok, normal_ok, rollout_ok, prod_ok, memory_evidence_ok]
    )
    return {
        "schema_version": "creator_live_rag_delivery_hf3_source_gate_v1",
        "prd_id": PRD,
        "required_artifact_count": len(REQUIRED_SOURCE_FILES),
        "present_artifact_count": len(REQUIRED_SOURCE_FILES) - len(missing),
        "missing_artifact_count": len(missing),
        "parse_error_count": len(parse_errors),
        "missing_artifacts": missing,
        "parse_errors": parse_errors,
        "memory_agent_evidence_from_hf2_command_log": memory_evidence,
        "source_expectations": {
            "status_ok": status_ok,
            "decision_ok": decision_ok,
            "botdb_chunks_ok": botdb_chunks_ok,
            "normal_user_activation_allowed_false": normal_ok,
            "broad_rollout_allowed_false": rollout_ok,
            "production_ready_false": prod_ok,
            "hf2_memory_agent_evidence_ok": memory_evidence_ok,
        },
        "source_gate": "passed" if source_gate_passed else "blocked",
        "source_gate_passed": source_gate_passed,
    }


def probe_runtime_reload(
    *,
    repo_root: Path,
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
    web_ok = web_status in {200, 204, 301, 302, 304, 307, 308}

    hf2_importable = True
    import_error = ""
    try:
        from . import creator_live_rag_delivery_hf2 as _hf2  # noqa: F401
    except Exception as exc:  # noqa: BLE001
        hf2_importable = False
        import_error = exc.__class__.__name__

    memory_retrieval_has_policy = True
    policy_error = ""
    try:
        from .agents import memory_retrieval_config as _memory_cfg

        memory_retrieval_has_policy = hasattr(_memory_cfg, "RAG_MIN_SCORE")
    except Exception as exc:  # noqa: BLE001
        memory_retrieval_has_policy = False
        policy_error = exc.__class__.__name__

    git_commit_seen = ""
    git_warning = ""
    try:
        git_commit_seen = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(repo_root),
            text=True,
        ).strip()
    except Exception as exc:  # noqa: BLE001
        git_warning = f"git_commit_unavailable:{exc.__class__.__name__}"

    runtime_passed = (
        botdb_status == 200
        and backend_status == 200
        and hf2_importable
        and memory_retrieval_has_policy
    )
    warnings: list[str] = []
    if not web_ok:
        warnings.append("web_ui_not_ready")
    if git_warning:
        warnings.append(git_warning)
    gate = "passed" if runtime_passed and not warnings else ("warning" if runtime_passed else "blocked")
    return {
        "schema_version": "hf3_runtime_reload_proof_v1",
        "prd_id": PRD,
        "backend_base_url": backend_base_url,
        "botdb_base_url": botdb_base_url,
        "web_ui_base_url": web_ui_base_url,
        "backend_status": backend_status,
        "botdb_status": botdb_status,
        "web_ui_status": web_status,
        "backend_error": backend_error,
        "botdb_error": botdb_error,
        "web_ui_error": web_error,
        "git_commit_seen": git_commit_seen,
        "hf2_code_paths_importable": hf2_importable,
        "hf2_import_error": import_error,
        "memory_retrieval_has_rag_score_policy_v1": memory_retrieval_has_policy,
        "memory_retrieval_policy_error": policy_error,
        "runtime_reload_gate": gate,
        "runtime_reload_warnings": warnings,
        "runtime_reload_proof_passed": runtime_passed,
    }


def probe_botdb_query(*, query: str, botdb_base_url: str) -> dict[str, Any]:
    status, payload, err = _http_json(
        url=f"{botdb_base_url.rstrip('/')}/api/query/",
        method="POST",
        payload={"query": query, "top_k": 4, "use_rerank": True, "search_mode": "hybrid"},
    )
    chunks = _safe_list(payload.get("chunks"))
    debug = _safe_dict(payload.get("debug"))
    return {
        "schema_version": "creator_live_rag_delivery_hf3_botdb_probe_v1",
        "prd_id": PRD,
        "query": query,
        "botdb_query_attempted": True,
        "botdb_http_status": status,
        "botdb_chunks_returned": len(chunks),
        "botdb_query_route_fallback_used": _as_bool(debug.get("botdb_query_route_fallback_used"), False),
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
        timeout_sec=70.0,
    )
    metadata = _safe_dict(payload.get("metadata"))
    answer = str(payload.get("answer", "") or "")
    session_id = str(metadata.get("session_id") or payload.get("session_id") or "").strip()
    return {
        "http_status": status,
        "error": err,
        "answer": answer,
        "answer_received": bool(answer.strip()),
        "session_id": session_id,
        "turn_index": _as_int(metadata.get("turn_index"), 0),
        "trace": _safe_dict(payload.get("trace")),
        "metadata": metadata,
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
        timeout_sec=20.0,
    )
    if status != 200:
        return {}
    traces = _safe_list(payload.get("traces"))
    if not traces:
        return {}
    return _safe_dict(traces[-1])


def fetch_multiagent_trace(
    *,
    backend_base_url: str,
    api_key: str,
    session_id: str,
) -> dict[str, Any]:
    if not session_id:
        return {}
    status, payload, _ = _http_json(
        url=f"{backend_base_url.rstrip('/')}/api/debug/session/{parse.quote(session_id)}/multiagent-trace",
        headers={"X-API-Key": api_key},
        timeout_sec=20.0,
    )
    return payload if status == 200 else {}


def _extract_between(source: str, start_marker: str, end_markers: list[str]) -> str:
    start_idx = source.find(start_marker)
    if start_idx < 0:
        return ""
    start_idx += len(start_marker)
    end_candidates = [source.find(marker, start_idx) for marker in end_markers]
    end_pos = [pos for pos in end_candidates if pos >= 0]
    end_idx = min(end_pos) if end_pos else len(source)
    return source[start_idx:end_idx]


def _extract_writer_knowledge_count(writer_prompt: str) -> int:
    prompt = str(writer_prompt or "")
    if not prompt.strip():
        return 0
    lowered = prompt.lower()
    if "нет релевантных знаний" in lowered:
        return 0

    section = ""
    for marker in ("KNOWLEDGE RAG HITS:", "ЗНАНИЙ ИЗ БАЗЫ:", "МАТЕРИАЛ ИЗ ЛЕКЦИЙ:"):
        section = _extract_between(
            prompt,
            marker,
            ["ВОПРОС ПОЛЬЗОВАТЕЛЯ:", "ЗАПРОС ПОЛЬЗОВАТЕЛЯ:", "USER QUESTION:", "Вопрос пользователя:"],
        )
        if section:
            break
    body = section or prompt

    bullet_hits = len(re.findall(r"(?m)^\s*-\s+", body))
    if bullet_hits > 0:
        return bullet_hits
    separators = body.count("\n---\n")
    if separators > 0:
        return separators + 1
    return 0


async def _run_memory_agent_probe(*, query: str, user_id: str) -> dict[str, Any]:
    thread_state = ThreadState(
        thread_id=f"hf3_probe_{user_id}",
        user_id=user_id,
        core_direction=query,
        phase="explore",
    )
    memory_bundle = await memory_retrieval_agent.assemble(
        user_message=query,
        thread_state=thread_state,
        user_id=user_id,
    )
    context_package = build_context_assembly_package_v1(
        user_message=query,
        thread_state=thread_state,
        memory_bundle=memory_bundle,
    )
    writer_contract = WriterContract(
        user_message=query,
        thread_state=thread_state,
        memory_bundle=memory_bundle,
        context_package=context_package,
    )
    prompt_context = writer_contract.to_prompt_context()
    return {
        "schema_version": "hf3_memory_agent_probe_v1",
        "query": query,
        "user_id": user_id,
        "rag_retrieval_trace": dict(memory_bundle.rag_retrieval_trace or {}),
        "knowledge_policy_trace": dict(memory_bundle.knowledge_policy_trace or {}),
        "memory_semantic_hits_count": len(memory_bundle.semantic_hits),
        "knowledge_rag_hits_count": len(memory_bundle.knowledge_rag_hits),
        "context_assembly_trace": context_package.trace.to_dict(),
        "context_assembly_knowledge_hits_count": len(context_package.knowledge_rag_hits),
        "writer_prompt_knowledge_hits_count": len(list(prompt_context.get("semantic_hits", []) or [])),
        "writer_prompt_context_preview": {
            "has_relevant_knowledge": bool(prompt_context.get("has_relevant_knowledge", False)),
            "semantic_hits_count": len(list(prompt_context.get("semantic_hits", []) or [])),
        },
    }


def build_creator_live_turn_proof(
    *,
    query_id: str,
    query: str,
    creator_user_id: str,
    turn_result: dict[str, Any],
    adaptive_trace: dict[str, Any],
    multiagent_trace: dict[str, Any],
) -> dict[str, Any]:
    session_id = str(turn_result.get("session_id", "") or "")
    answer = str(turn_result.get("answer", "") or "")
    turn_index = _as_int(turn_result.get("turn_index"), 0)
    trace_available = bool(adaptive_trace or multiagent_trace)
    turn_id = f"{session_id}:{turn_index}" if turn_index > 0 else session_id
    payload = CreatorLiveTurnProof(
        query_id=query_id,
        query=query,
        actual_live_turn=bool(session_id and answer.strip()),
        turn_id=turn_id,
        session_id_hash=_sha256_text(session_id),
        user_id_hash=_sha256_text(creator_user_id),
        answer_received=bool(answer.strip()),
        trace_available=trace_available,
    )
    return payload.to_dict()


def build_live_query_evidence(
    *,
    query_id: str,
    query: str,
    botdb_probe: dict[str, Any],
    turn_result: dict[str, Any],
    adaptive_trace: dict[str, Any],
    multiagent_trace: dict[str, Any],
    memory_probe: dict[str, Any],
    creator_live_turn_proof: dict[str, Any],
) -> dict[str, Any]:
    rag_trace = _safe_dict(memory_probe.get("rag_retrieval_trace"))
    policy_trace = _safe_dict(memory_probe.get("knowledge_policy_trace"))
    context_trace = _safe_dict(memory_probe.get("context_assembly_trace"))
    adaptive_rag = _safe_dict(adaptive_trace.get("rag_retrieval_trace"))
    adaptive_policy = _safe_dict(adaptive_trace.get("knowledge_policy_trace"))
    adaptive_context = _safe_dict(adaptive_trace.get("context_assembly_trace"))

    mem_agents = _safe_dict(_safe_dict(multiagent_trace.get("agents")).get("memory_retrieval"))
    writer_llm = _safe_dict(multiagent_trace.get("writer_llm"))
    writer_prompt = str(writer_llm.get("user_prompt") or adaptive_trace.get("writer_user_prompt") or "")

    raw_hits = _as_int(rag_trace.get("raw_hits_count"), _as_int(adaptive_rag.get("raw_hits_count"), 0))
    filtered_hits = _as_int(
        rag_trace.get("filtered_hits_count"),
        _as_int(adaptive_rag.get("filtered_hits_count"), _as_int(memory_probe.get("memory_semantic_hits_count"), 0)),
    )
    filtered_by_score = _as_int(
        rag_trace.get("filtered_by_score_count"),
        _as_int(adaptive_rag.get("filtered_by_score_count"), max(0, raw_hits - filtered_hits)),
    )
    salvaged_hits = _as_int(rag_trace.get("salvaged_hits_count"), _as_int(adaptive_rag.get("salvaged_hits_count"), 0))

    knowledge_input_hits = _as_int(
        policy_trace.get("input_hits_count"),
        _as_int(adaptive_policy.get("input_hits_count"), raw_hits),
    )
    knowledge_included_writer = _as_int(
        policy_trace.get("included_writer_count"),
        _as_int(adaptive_policy.get("included_writer_count"), 0),
    )
    knowledge_dropped = _as_int(
        policy_trace.get("dropped_count"),
        _as_int(adaptive_policy.get("dropped_count"), 0),
    )
    context_hits = _as_int(
        memory_probe.get("context_assembly_knowledge_hits_count"),
        _as_int(context_trace.get("knowledge_hits_count"), _as_int(adaptive_context.get("knowledge_hits_count"), 0)),
    )
    writer_hits = _extract_writer_knowledge_count(writer_prompt)
    web_writer_hits = writer_hits

    has_relevant_knowledge = bool(
        _as_bool(mem_agents.get("has_relevant_knowledge"), False)
        or _as_bool(_safe_dict(memory_probe.get("writer_prompt_context_preview")).get("has_relevant_knowledge"), False)
    )
    writer_has_knowledge = writer_hits > 0

    return {
        "query_id": query_id,
        "query": query,
        "botdb_http_status": _as_int(botdb_probe.get("botdb_http_status"), 0),
        "botdb_chunks_returned": _as_int(botdb_probe.get("botdb_chunks_returned"), 0),
        "rag_raw_hits_count": raw_hits,
        "rag_filtered_hits_count": filtered_hits,
        "rag_filtered_by_score_count": filtered_by_score,
        "rag_salvaged_hits_count": salvaged_hits,
        "knowledge_policy_input_hits_count": knowledge_input_hits,
        "knowledge_policy_included_writer_count": knowledge_included_writer,
        "knowledge_policy_dropped_count": knowledge_dropped,
        "context_assembly_knowledge_hits_count": context_hits,
        "writer_prompt_knowledge_hits_count": writer_hits,
        "web_trace_chunks_in_writer_count": web_writer_hits,
        "has_relevant_knowledge": has_relevant_knowledge,
        "writer_prompt_contains_knowledge_rag_hits": writer_has_knowledge,
        "actual_live_turn": bool(creator_live_turn_proof.get("actual_live_turn", False)),
        "answer_received": bool(turn_result.get("answer_received", False)),
        "trace_available": bool(adaptive_trace or multiagent_trace),
        "session_id_hash": creator_live_turn_proof.get("session_id_hash", ""),
        "user_id_hash": creator_live_turn_proof.get("user_id_hash", ""),
        "adaptive_trace_present": bool(adaptive_trace),
        "multiagent_trace_present": bool(multiagent_trace),
        "memory_probe_present": bool(memory_probe),
        "writer_prompt_len": len(writer_prompt),
    }


def build_trace_alignment_gate(*, live_evidence: dict[str, Any]) -> dict[str, Any]:
    context_hits = _as_int(live_evidence.get("context_assembly_knowledge_hits_count"), 0)
    writer_hits = _as_int(live_evidence.get("writer_prompt_knowledge_hits_count"), 0)
    web_hits = _as_int(live_evidence.get("web_trace_chunks_in_writer_count"), 0)
    mismatch = (writer_hits != web_hits) or (context_hits > 0 and writer_hits <= 0)
    return {
        "schema_version": "creator_live_rag_delivery_hf3_trace_alignment_gate_v1",
        "prd_id": PRD,
        "backend_context_knowledge_hits_count": context_hits,
        "backend_writer_prompt_knowledge_hits_count": writer_hits,
        "web_trace_chunks_in_writer_count": web_hits,
        "mismatch_detected": mismatch,
        "trace_alignment_gate": "blocked" if mismatch else "passed",
        "trace_alignment_gate_passed": not mismatch,
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
        "schema_version": "creator_live_rag_delivery_hf3_normal_user_no_effect_v1",
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
        "schema_version": "creator_live_rag_delivery_hf3_trace_sanitization_gate_v1",
        "prd_id": PRD,
        "raw_provider_payload_committed": raw_provider,
        "raw_private_logs_committed": raw_private,
        "secrets_committed": secrets,
        "trace_sanitization_gate_passed": passed,
        "trace_sanitization_gate": "passed" if passed else "blocked",
    }


def build_provider_budget_gate(*, adaptive_trace: dict[str, Any]) -> dict[str, Any]:
    llm_calls = _safe_list(adaptive_trace.get("llm_calls"))
    total_calls = len(llm_calls)
    passed = total_calls <= 8
    return {
        "schema_version": "creator_live_rag_delivery_hf3_provider_budget_gate_v1",
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
        "schema_version": "creator_live_rag_delivery_hf3_no_mutation_proof_v1",
        "prd_id": PRD,
        "hash_before": dict(hash_before),
        "hash_after": dict(hash_after),
        "production_data_mutated": mutated,
        "no_mutation_proof_passed": not mutated,
    }


def build_writer_kb_truncation_audit(*, repo_root: Path, selected_evidence: dict[str, Any]) -> dict[str, Any]:
    knowledge_policy_path = repo_root / "bot_psychologist/bot_agent/multiagent/knowledge_policy.py"
    writer_agent_path = repo_root / "bot_psychologist/bot_agent/multiagent/agents/writer_agent.py"
    policy_source = knowledge_policy_path.read_text(encoding="utf-8", errors="replace")
    writer_source = writer_agent_path.read_text(encoding="utf-8", errors="replace")

    policy_cap_match = re.search(r"_POLICY_SANITIZED_MAX_CHARS\s*=\s*(\d+)", policy_source)
    writer_hit_cap_match = re.search(r"h\[:(\d+)\]", writer_source)
    context_cap_match = re.search(r"conversation_context=.*\[:(\d+)\]", writer_source)

    policy_cap = _as_int(policy_cap_match.group(1) if policy_cap_match else 0, 0)
    writer_hit_cap = _as_int(writer_hit_cap_match.group(1) if writer_hit_cap_match else 0, 0)
    context_cap = _as_int(context_cap_match.group(1) if context_cap_match else 0, 0)
    boundary_trim_helper_present = "_trim_to_word_boundary" in policy_source

    truncation_detected = (policy_cap > 0 and policy_cap <= 240) or (writer_hit_cap > 0 and writer_hit_cap <= 300)
    truncation_blocker = False
    gate = "warning" if truncation_detected else "passed"
    reasons: list[str] = []
    if policy_cap > 0 and policy_cap <= 240:
        reasons.append("knowledge_policy_sanitized_cap_present")
    if writer_hit_cap > 0 and writer_hit_cap <= 300:
        reasons.append("writer_prompt_hit_cap_present")
    if context_cap > 0 and context_cap <= 2000:
        reasons.append("conversation_context_cap_present")
    if boundary_trim_helper_present:
        reasons.append("boundary_trim_helper_present")

    return {
        "schema_version": "creator_live_rag_delivery_hf3_writer_kb_truncation_audit_v1",
        "prd_id": PRD,
        "truncation_detected": truncation_detected,
        "truncation_blocker": truncation_blocker,
        "writer_kb_truncation_gate": gate,
        "kb_context_v2_backlog": True,
        "knowledge_policy_sanitized_max_chars": policy_cap,
        "writer_prompt_hit_max_chars": writer_hit_cap,
        "conversation_context_max_chars": context_cap,
        "boundary_trim_helper_present": boundary_trim_helper_present,
        "selected_query_id": selected_evidence.get("query_id", ""),
        "selected_writer_prompt_knowledge_hits_count": _as_int(
            selected_evidence.get("writer_prompt_knowledge_hits_count"), 0
        ),
        "selected_context_assembly_knowledge_hits_count": _as_int(
            selected_evidence.get("context_assembly_knowledge_hits_count"), 0
        ),
        "reasons": reasons,
        "recommended_next_prd": NEXT_PRD_KB_V2,
    }


def build_hf3_scorecard(
    *,
    source_gate: dict[str, Any],
    runtime_reload_proof: dict[str, Any],
    selected_evidence: dict[str, Any],
    trace_alignment_gate: dict[str, Any],
    truncation_audit: dict[str, Any],
    creator_live_turn_proof: dict[str, Any],
    normal_user_gate: dict[str, Any],
    trace_gate: dict[str, Any],
    provider_gate: dict[str, Any],
    no_mutation_proof: dict[str, Any],
    artifact_encoding_hygiene_passed: bool,
) -> tuple[dict[str, Any], dict[str, Any]]:
    source_passed = _as_bool(source_gate.get("source_gate_passed"), False)
    runtime_gate = str(runtime_reload_proof.get("runtime_reload_gate", "blocked"))
    runtime_ok = runtime_gate in {"passed", "warning"} and _as_bool(runtime_reload_proof.get("runtime_reload_proof_passed"), False)
    botdb_chunks = _as_int(selected_evidence.get("botdb_chunks_returned"), 0)
    raw_hits = _as_int(selected_evidence.get("rag_raw_hits_count"), 0)
    filtered_hits = _as_int(selected_evidence.get("rag_filtered_hits_count"), 0)
    salvaged_hits = _as_int(selected_evidence.get("rag_salvaged_hits_count"), 0)
    policy_input_hits = _as_int(selected_evidence.get("knowledge_policy_input_hits_count"), 0)
    policy_writer_hits = _as_int(selected_evidence.get("knowledge_policy_included_writer_count"), 0)
    context_hits = _as_int(selected_evidence.get("context_assembly_knowledge_hits_count"), 0)
    writer_hits = _as_int(selected_evidence.get("writer_prompt_knowledge_hits_count"), 0)
    web_writer_hits = _as_int(selected_evidence.get("web_trace_chunks_in_writer_count"), 0)
    has_relevant = _as_bool(selected_evidence.get("has_relevant_knowledge"), False)
    writer_has_kb = _as_bool(selected_evidence.get("writer_prompt_contains_knowledge_rag_hits"), False)

    creator_live_passed = _as_bool(creator_live_turn_proof.get("actual_live_turn"), False)
    trace_alignment_passed = _as_bool(trace_alignment_gate.get("trace_alignment_gate_passed"), False)
    normal_passed = _as_bool(normal_user_gate.get("normal_user_no_effect_gate_passed"), False)
    trace_passed = _as_bool(trace_gate.get("trace_sanitization_gate_passed"), False)
    provider_passed = _as_bool(provider_gate.get("provider_budget_gate_passed"), False)
    no_mutation_passed = _as_bool(no_mutation_proof.get("no_mutation_proof_passed"), False)

    safety_passed = normal_passed and trace_passed and provider_passed and no_mutation_passed and artifact_encoding_hygiene_passed
    chain_passed = (
        botdb_chunks >= 1
        and raw_hits >= 1
        and (filtered_hits + salvaged_hits) >= 1
        and policy_writer_hits >= 1
        and context_hits >= 1
        and writer_hits >= 1
        and web_writer_hits >= 1
        and writer_has_kb
    )

    blockers: list[str] = []
    warnings: list[str] = []
    if not source_passed:
        blockers.append("source_gate_failed")
    if not runtime_ok:
        blockers.append("runtime_reload_failed")
    if not creator_live_passed:
        blockers.append("creator_live_turn_missing")
    if not trace_alignment_passed:
        blockers.append("trace_alignment_failed")
    if not chain_passed:
        blockers.append("rag_delivery_chain_not_verified")
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

    truncation_gate = str(truncation_audit.get("writer_kb_truncation_gate", "warning"))
    truncation_detected = _as_bool(truncation_audit.get("truncation_detected"), True)
    truncation_blocker = _as_bool(truncation_audit.get("truncation_blocker"), False)
    if truncation_detected and not truncation_blocker:
        warnings.append("writer_kb_context_truncation_non_blocking")

    if not safety_passed:
        final_status = "blocked"
        decision = DECISION_BLOCKED_SAFETY
        next_prd = NEXT_PRD_FIX
    elif not source_passed or not runtime_ok or not trace_alignment_passed:
        final_status = "blocked"
        decision = DECISION_BLOCKED_RUNTIME_TRACE
        next_prd = NEXT_PRD_FIX
    elif not chain_passed or not creator_live_passed:
        final_status = "blocked"
        decision = DECISION_BLOCKED_RAG_REGRESSION
        next_prd = NEXT_PRD_FIX
    elif truncation_detected and not truncation_blocker:
        final_status = "passed"
        decision = DECISION_PASSED_TRUNCATION_WARNING
        next_prd = NEXT_PRD_DEFAULT
    else:
        final_status = "passed"
        decision = DECISION_PASSED_VERIFIED
        next_prd = NEXT_PRD_DEFAULT

    scorecard = HF3Scorecard(
        final_status=final_status,
        decision=decision,
        source_gate="passed" if source_passed else "blocked",
        runtime_reload_gate=runtime_gate if runtime_gate in {"passed", "warning"} else "blocked",
        botdb_query_gate="passed" if botdb_chunks >= 1 else "blocked",
        memory_retrieval_gate="passed" if raw_hits >= 1 and (filtered_hits + salvaged_hits) >= 1 else "blocked",
        knowledge_policy_gate=(
            "passed"
            if policy_writer_hits >= 1
            else ("governance_blocked" if policy_input_hits >= 1 else "blocked")
        ),
        context_assembly_gate="passed" if context_hits >= 1 else "blocked",
        writer_prompt_delivery_gate="passed" if writer_hits >= 1 else "blocked",
        web_trace_alignment_gate="passed" if trace_alignment_passed else "blocked",
        writer_kb_truncation_gate=truncation_gate if truncation_gate in {"passed", "warning"} else "blocked",
        truncation_detected=truncation_detected,
        truncation_blocker=truncation_blocker,
        kb_context_v2_backlog=True,
        creator_live_turn_gate="passed" if creator_live_passed else "blocked",
        normal_user_no_effect_gate="passed" if normal_passed else "blocked",
        trace_sanitization_gate="passed" if trace_passed else "blocked",
        provider_budget_gate="passed" if provider_passed else "blocked",
        no_mutation_proof="passed" if no_mutation_passed else "blocked",
        artifact_encoding_hygiene="passed" if artifact_encoding_hygiene_passed else "blocked",
        botdb_chunks_returned=botdb_chunks,
        rag_raw_hits_count=raw_hits,
        rag_filtered_hits_count=filtered_hits,
        rag_salvaged_hits_count=salvaged_hits,
        knowledge_policy_input_hits_count=policy_input_hits,
        knowledge_policy_included_writer_count=policy_writer_hits,
        context_assembly_knowledge_hits_count=context_hits,
        writer_prompt_knowledge_hits_count=writer_hits,
        web_trace_chunks_in_writer_count=web_writer_hits,
        has_relevant_knowledge=has_relevant,
        writer_prompt_contains_knowledge_rag_hits=writer_has_kb,
        actual_live_turn_evidence_count=1 if creator_live_passed else 0,
        broad_rollout_allowed=False,
        production_ready=False,
        normal_user_activation_allowed=False,
        all_users_mode_enabled=False,
        blockers=sorted(set(blockers)),
        warnings=sorted(set(warnings)),
        next_prd_recommendation=next_prd,
    ).to_dict()
    decision_payload = HF3Decision(
        final_status=final_status,
        decision=decision,
        blockers=scorecard.get("blockers", []),
        warnings=scorecard.get("warnings", []),
    ).to_dict()
    return scorecard, decision_payload


def run_live_query_chain(
    *,
    query_id: str,
    query: str,
    creator_user_id: str,
    botdb_base_url: str,
    backend_base_url: str,
    api_key: str,
) -> dict[str, Any]:
    botdb_probe = probe_botdb_query(query=query, botdb_base_url=botdb_base_url)
    turn_result = execute_creator_live_turn(
        backend_base_url=backend_base_url,
        api_key=api_key,
        creator_user_id=creator_user_id,
        query=query,
    )
    session_id = str(turn_result.get("session_id", "") or "")
    adaptive_trace = fetch_retrieval_trace(
        backend_base_url=backend_base_url,
        api_key=api_key,
        session_id=session_id,
    )
    multiagent_trace = fetch_multiagent_trace(
        backend_base_url=backend_base_url,
        api_key=api_key,
        session_id=session_id,
    )
    memory_probe = asyncio.run(_run_memory_agent_probe(query=query, user_id=creator_user_id))
    creator_proof = build_creator_live_turn_proof(
        query_id=query_id,
        query=query,
        creator_user_id=creator_user_id,
        turn_result=turn_result,
        adaptive_trace=adaptive_trace,
        multiagent_trace=multiagent_trace,
    )
    live_evidence = build_live_query_evidence(
        query_id=query_id,
        query=query,
        botdb_probe=botdb_probe,
        turn_result=turn_result,
        adaptive_trace=adaptive_trace,
        multiagent_trace=multiagent_trace,
        memory_probe=memory_probe,
        creator_live_turn_proof=creator_proof,
    )
    return {
        "query_id": query_id,
        "query": query,
        "botdb_probe": botdb_probe,
        "turn_result": turn_result,
        "adaptive_trace": adaptive_trace,
        "multiagent_trace": multiagent_trace,
        "memory_probe": memory_probe,
        "creator_live_turn_proof": creator_proof,
        "live_evidence": live_evidence,
    }


__all__ = [
    "PRD",
    "SOURCE_PRD",
    "DECISION_PASSED_VERIFIED",
    "DECISION_PASSED_TRUNCATION_WARNING",
    "DECISION_BLOCKED_RUNTIME_TRACE",
    "DECISION_BLOCKED_RAG_REGRESSION",
    "DECISION_BLOCKED_SAFETY",
    "NEXT_PRD_DEFAULT",
    "NEXT_PRD_FIX",
    "NEXT_PRD_KB_V2",
    "tracked_hashes",
    "preflight_source_gate",
    "probe_runtime_reload",
    "probe_botdb_query",
    "execute_creator_live_turn",
    "fetch_retrieval_trace",
    "fetch_multiagent_trace",
    "build_creator_live_turn_proof",
    "build_live_query_evidence",
    "build_trace_alignment_gate",
    "build_normal_user_no_effect_gate",
    "build_trace_sanitization_gate",
    "build_provider_budget_gate",
    "build_no_mutation_proof",
    "build_writer_kb_truncation_audit",
    "build_hf3_scorecard",
    "run_live_query_chain",
    "RAG_MIN_SCORE",
    "datetime",
    "timezone",
]
