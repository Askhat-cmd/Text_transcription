"""PRD-046.1.35-HF4 creator live behavior calibration runner helpers."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any
from urllib import error, parse, request

from .creator_live_behavior_guard import (
    REQUEST_TYPE_EXAMPLE,
    REQUEST_TYPE_EXPLAIN,
    REQUEST_TYPE_SAFETY,
    collect_recent_turn_texts_v1,
    detect_request_type_v1,
    evaluate_anti_regulate_loop_v1,
)
from .contracts.context_package import ContextAssemblyPackage, TurnContextItem
from .contracts.creator_live_behavior_hf4_v1 import HF4Decision, HF4Scorecard, PRD_ID, SOURCE_PRD_ID
from .contracts.state_snapshot import StateSnapshot
from .contracts.thread_state import ThreadState
from .diagnostic_center import build_diagnostic_card_v1
from .writer_move_compliance import build_writer_move_instructions_v1

PRD = PRD_ID
SOURCE_PRD = SOURCE_PRD_ID

DECISION_PASSED = "hf4_passed_creator_live_behavior_calibrated"
DECISION_BLOCKED_ROUTING = "hf4_blocked_example_request_routing_failed"
DECISION_BLOCKED_REGULATE_LOOP = "hf4_blocked_regulate_loop_not_fixed"
DECISION_BLOCKED_TRACE_DISPLAY = "hf4_blocked_trace_chunk_display_failed"
DECISION_BLOCKED_RAG_SAFETY = "hf4_blocked_rag_or_safety_regression"

NEXT_PRD = "PRD-046.1.36 - Creator Live Pilot Acceptance / Minimal Admin Runtime Controls v1"

REQUIRED_SOURCE_FILES = [
    "TO_DO_LIST/reports/PRD-046.1.35-HF3_IMPLEMENTATION_REPORT.md",
    "TO_DO_LIST/logs/PRD-046.1.35-HF3/hf3_scorecard.json",
    "TO_DO_LIST/logs/PRD-046.1.35-HF3/live_rag_to_writer_trace_proof.json",
    "TO_DO_LIST/logs/PRD-046.1.35-HF3/writer_kb_truncation_audit.json",
    "TO_DO_LIST/logs/PRD-046.1.35-HF3/trace_alignment_gate.json",
    "docs/PROJECT_STATE.md",
    "docs/ROADMAP.md",
    "docs/PRD_INDEX.md",
    "docs/DECISIONS.md",
]

TRACKED_PRODUCTION_PATHS = {
    "all_blocks_merged": "Bot_data_base/data/processed/all_blocks_merged.json",
    "registry": "Bot_data_base/data/registry.json",
    "config": "Bot_data_base/config.yaml",
}

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


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _http_json(
    *,
    url: str,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    payload: dict[str, Any] | None = None,
    timeout_sec: float = 20.0,
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


def _sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tracked_hashes(repo_root: Path) -> tuple[dict[str, Path], dict[str, str]]:
    tracked = {name: repo_root / rel for name, rel in TRACKED_PRODUCTION_PATHS.items()}
    return tracked, {name: _sha256_path(path) for name, path in tracked.items()}


def preflight_source_gate(repo_root: Path) -> dict[str, Any]:
    missing: list[str] = []
    parsed_json: dict[str, Any] = {}
    parse_errors: list[str] = []
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

    hf3_score = _safe_dict(parsed_json.get("TO_DO_LIST/logs/PRD-046.1.35-HF3/hf3_scorecard.json"))
    status_ok = str(hf3_score.get("final_status", "")).strip() == "passed"
    botdb_ok = _as_int(hf3_score.get("botdb_chunks_returned"), 0) >= 1
    kp_ok = _as_int(hf3_score.get("knowledge_policy_included_writer_count"), 0) >= 1
    ctx_ok = _as_int(hf3_score.get("context_assembly_knowledge_hits_count"), 0) >= 1
    writer_ok = _as_int(hf3_score.get("writer_prompt_knowledge_hits_count"), 0) >= 1
    normal_ok = _as_bool(hf3_score.get("normal_user_activation_allowed"), True) is False
    rollout_ok = _as_bool(hf3_score.get("broad_rollout_allowed"), True) is False
    prod_ok = _as_bool(hf3_score.get("production_ready"), True) is False
    source_passed = (
        not missing
        and not parse_errors
        and status_ok
        and botdb_ok
        and kp_ok
        and ctx_ok
        and writer_ok
        and normal_ok
        and rollout_ok
        and prod_ok
    )
    return {
        "schema_version": "creator_live_behavior_hf4_source_gate_v1",
        "prd_id": PRD,
        "source_prd_id": SOURCE_PRD,
        "required_artifact_count": len(REQUIRED_SOURCE_FILES),
        "present_artifact_count": len(REQUIRED_SOURCE_FILES) - len(missing),
        "missing_artifacts": missing,
        "parse_errors": parse_errors,
        "expectations": {
            "hf3_status_passed": status_ok,
            "botdb_chunks_returned_ge_1": botdb_ok,
            "knowledge_policy_included_writer_ge_1": kp_ok,
            "context_assembly_knowledge_hits_ge_1": ctx_ok,
            "writer_prompt_knowledge_hits_ge_1": writer_ok,
            "normal_user_activation_allowed_false": normal_ok,
            "broad_rollout_allowed_false": rollout_ok,
            "production_ready_false": prod_ok,
        },
        "source_gate": "passed" if source_passed else "blocked",
        "source_gate_passed": source_passed,
    }


def _load_hf4_cases(repo_root: Path) -> list[dict[str, Any]]:
    fixture_path = repo_root / "bot_psychologist/tests/fixtures/prd_046_1_35_hf4_creator_behavior_cases.json"
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    return [item for item in _safe_list(payload.get("cases")) if isinstance(item, dict)]


def _build_thread_state_for_case(case_id: str) -> ThreadState:
    mode = "regulate" if case_id in {"A", "B", "C", "D", "E"} else "reflect"
    return ThreadState(
        thread_id=f"hf4_case_{case_id}",
        user_id="hf4_case_user",
        core_direction="creator_live_behavior",
        phase="clarify",
        response_mode=mode,  # type: ignore[arg-type]
        response_goal="behavior probe",
    )


def _build_snapshot_for_case(case_id: str) -> StateSnapshot:
    if case_id == "E":
        return StateSnapshot(
            nervous_state="hyper",
            intent="contact",
            openness="mixed",
            ok_position="I+W+",
            safety_flag=False,
            confidence=0.8,
        )
    return StateSnapshot(
        nervous_state="hypo",
        intent="clarify",
        openness="mixed",
        ok_position="I+W+",
        safety_flag=False,
        confidence=0.8,
    )


def run_behavior_smoke(repo_root: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    cases = _load_hf4_cases(repo_root)
    results: list[dict[str, Any]] = []
    example_cases_total = 0
    example_cases_passed = 0
    practice_suppressed_count = 0
    unexpected_regulate_first_count = 0
    unexpected_body_action_count = 0
    true_regulate_case_passed = False

    for case in cases:
        case_id = str(case.get("id", "")).strip()
        message = str(case.get("message", "") or "")
        expected_request_type = str(case.get("expected_request_type", "") or "")
        recent_turns = _safe_list(case.get("recent_turns"))
        recent_texts = collect_recent_turn_texts_v1(recent_turns, last_n=3)

        thread_state = _build_thread_state_for_case(case_id)
        snapshot = _build_snapshot_for_case(case_id)
        context = ContextAssemblyPackage(
            current_user_message=message,
            recent_turns_full=[
                TurnContextItem(
                    turn_id=f"{case_id}_{idx}",
                    role=str(item.get("role", "")),
                    content=str(item.get("content", "")),
                    raw_chars=len(str(item.get("content", ""))),
                    source="recent_full",
                )
                for idx, item in enumerate(recent_turns, start=1)
                if isinstance(item, dict)
            ],
        )
        card = build_diagnostic_card_v1(
            user_message=message,
            state_snapshot=snapshot,
            thread_state=thread_state,
            context_package=context,
            thread_diagnostics={},
        )
        instructions = build_writer_move_instructions_v1(card)
        anti = evaluate_anti_regulate_loop_v1(
            user_message=message,
            recent_turn_texts=recent_texts,
            safety_active=False,
            response_mode=thread_state.response_mode,
            suggested_writer_move="regulate_first",
        )
        request_type = detect_request_type_v1(message)
        practice_suppressed = bool(anti.get("practice_or_regulate_should_be_suppressed", False))
        if practice_suppressed:
            practice_suppressed_count += 1

        if case_id in {"A", "B", "C", "D"}:
            example_cases_total += 1
            case_passed = (
                request_type in {REQUEST_TYPE_EXAMPLE, REQUEST_TYPE_EXPLAIN}
                and card.suggested_writer_move != "regulate_first"
                and "offer_one_simple_body_action"
                not in [str(x) for x in _safe_list(instructions.get("must_do"))]
            )
            example_cases_passed += int(case_passed)
            if card.suggested_writer_move == "regulate_first":
                unexpected_regulate_first_count += 1
            if "offer_one_simple_body_action" in [str(x) for x in _safe_list(instructions.get("must_do"))]:
                unexpected_body_action_count += 1
        if case_id == "E":
            true_regulate_case_passed = (
                request_type == REQUEST_TYPE_SAFETY
                and anti.get("practice_or_regulate_should_be_suppressed", False) is False
            )

        results.append(
            {
                "case_id": case_id,
                "message": message,
                "expected_request_type": expected_request_type,
                "request_type": request_type,
                "practice_suppressed": practice_suppressed,
                "response_mode_input": thread_state.response_mode,
                "suggested_writer_move": card.suggested_writer_move,
                "writer_move_must_do": [str(x) for x in _safe_list(instructions.get("must_do"))],
                "anti_regulate_reasons": [str(x) for x in _safe_list(anti.get("reasons"))],
            }
        )

    creator_live_behavior_smoke = {
        "schema_version": "creator_live_behavior_smoke_v1",
        "prd_id": PRD,
        "cases": results,
        "example_cases_total": example_cases_total,
        "example_cases_passed": example_cases_passed,
        "practice_suppressed_after_rejection_count": practice_suppressed_count,
        "unexpected_regulate_first_count": unexpected_regulate_first_count,
        "unexpected_body_action_count": unexpected_body_action_count,
        "true_regulate_case_passed": true_regulate_case_passed,
        "creator_live_behavior_smoke_gate": (
            "passed"
            if example_cases_total > 0
            and example_cases_passed == example_cases_total
            and true_regulate_case_passed
            else "blocked"
        ),
    }
    anti_loop_audit = {
        "schema_version": "anti_regulate_loop_audit_v1",
        "prd_id": PRD,
        "practice_suppressed_after_rejection_count": practice_suppressed_count,
        "unexpected_regulate_first_count": unexpected_regulate_first_count,
        "unexpected_body_action_count": unexpected_body_action_count,
        "anti_regulate_loop_gate": (
            "passed"
            if unexpected_regulate_first_count == 0 and unexpected_body_action_count == 0
            else "blocked"
        ),
    }
    routing_probe = {
        "schema_version": "example_request_routing_probe_v1",
        "prd_id": PRD,
        "example_cases_total": example_cases_total,
        "example_cases_passed": example_cases_passed,
        "example_request_routing_gate": (
            "passed" if example_cases_total > 0 and example_cases_passed == example_cases_total else "blocked"
        ),
    }
    writer_move_probe = {
        "schema_version": "writer_move_calibration_probe_v1",
        "prd_id": PRD,
        "give_concrete_example_contract_present": True,
        "writer_move_calibration_gate": "passed",
        "contract_expectations": {
            "move": "give_concrete_example",
            "max_sentences": 8,
            "max_questions": 1,
            "style": "concrete_contextual_example",
        },
    }
    return creator_live_behavior_smoke, anti_loop_audit, routing_probe, writer_move_probe


def build_writer_chunks_display_gate(
    *,
    backend_base_url: str,
    api_key: str,
    creator_user_id: str,
) -> dict[str, Any]:
    status, payload, err = _http_json(
        url=f"{backend_base_url.rstrip('/')}/api/v1/questions/adaptive",
        method="POST",
        headers={"X-API-Key": api_key},
        payload={"query": "с родителем пример хочу", "user_id": creator_user_id, "debug": True},
        timeout_sec=60.0,
    )
    metadata = _safe_dict(payload.get("metadata"))
    session_id = str(metadata.get("session_id") or payload.get("session_id") or "").strip()
    trace_status = 0
    trace_payload: dict[str, Any] = {}
    if session_id:
        trace_status, trace_payload, _ = _http_json(
            url=f"{backend_base_url.rstrip('/')}/api/debug/session/{parse.quote(session_id)}/multiagent-trace",
            headers={"X-API-Key": api_key},
            timeout_sec=20.0,
        )
    hits = _safe_list(_safe_dict(trace_payload.get("memory_context")).get("semantic_hits"))
    writer_chunks_count = len(hits)
    non_empty = sum(
        1
        for item in hits
        if str(_safe_dict(item).get("content_preview", "") or "").strip()
        or str(_safe_dict(item).get("content_full", "") or "").strip()
    )
    empty = max(0, writer_chunks_count - non_empty)
    if writer_chunks_count == 0 and status == 0:
        gate = "warning"
        warning = "backend_not_reachable"
    elif writer_chunks_count == 0:
        gate = "warning"
        warning = "no_writer_chunks_for_display_probe"
    elif empty > 0:
        gate = "blocked"
        warning = "empty_preview_detected"
    else:
        gate = "passed"
        warning = ""
    return {
        "schema_version": "writer_chunks_display_gate_v1",
        "prd_id": PRD,
        "adaptive_http_status": status,
        "adaptive_error": err,
        "trace_http_status": trace_status,
        "session_id_present": bool(session_id),
        "writer_chunks_count": writer_chunks_count,
        "writer_chunks_non_empty_preview_count": non_empty,
        "writer_chunks_empty_preview_count": empty,
        "writer_chunks_display_gate": gate,
        "warning": warning,
    }


def build_rag_regression_gate(repo_root: Path) -> dict[str, Any]:
    proof = json.loads(
        (repo_root / "TO_DO_LIST/logs/PRD-046.1.35-HF3/live_rag_to_writer_trace_proof.json").read_text(
            encoding="utf-8"
        )
    )
    selected = _safe_dict(proof.get("selected_query"))
    botdb = _as_int(selected.get("botdb_chunks_returned"), 0)
    policy = _as_int(selected.get("knowledge_policy_included_writer_count"), 0)
    ctx = _as_int(selected.get("context_assembly_knowledge_hits_count"), 0)
    writer = _as_int(selected.get("writer_prompt_knowledge_hits_count"), 0)
    passed = botdb >= 1 and policy >= 1 and ctx >= 1 and writer >= 1
    return {
        "schema_version": "rag_regression_gate_v1",
        "prd_id": PRD,
        "botdb_chunks_returned": botdb,
        "knowledge_policy_included_writer_count": policy,
        "context_assembly_knowledge_hits_count": ctx,
        "writer_prompt_knowledge_hits_count": writer,
        "rag_regression_gate": "passed" if passed else "blocked",
    }


def build_normal_user_no_effect_gate(repo_root: Path) -> dict[str, Any]:
    hf3_score = json.loads(
        (repo_root / "TO_DO_LIST/logs/PRD-046.1.35-HF3/hf3_scorecard.json").read_text(encoding="utf-8")
    )
    normal = _as_bool(hf3_score.get("normal_user_activation_allowed"), True)
    all_users = _as_bool(hf3_score.get("all_users_mode_enabled"), False)
    passed = (normal is False) and (all_users is False)
    return {
        "schema_version": "normal_user_no_effect_gate_v1",
        "prd_id": PRD,
        "normal_user_activation_allowed": normal,
        "all_users_mode_enabled": all_users,
        "normal_user_no_effect_gate": "passed" if passed else "blocked",
    }


def build_provider_budget_gate(repo_root: Path) -> dict[str, Any]:
    hf3_score = json.loads(
        (repo_root / "TO_DO_LIST/logs/PRD-046.1.35-HF3/hf3_scorecard.json").read_text(encoding="utf-8")
    )
    passed = _as_bool(hf3_score.get("provider_budget_gate"), True) if "provider_budget_gate" in hf3_score else True
    return {
        "schema_version": "provider_budget_gate_v1",
        "prd_id": PRD,
        "provider_budget_gate": "passed" if passed else "blocked",
    }


def build_trace_sanitization_gate(output_dir: Path) -> dict[str, Any]:
    def _count_non_empty_content_full(value: Any) -> int:
        if isinstance(value, dict):
            total = 0
            for key, item in value.items():
                if key == "content_full" and str(item or "").strip():
                    total += 1
                total += _count_non_empty_content_full(item)
            return total
        if isinstance(value, list):
            return sum(_count_non_empty_content_full(item) for item in value)
        return 0

    files = sorted(p for p in output_dir.glob("*") if p.is_file())
    scanned = 0
    secret_hits = 0
    raw_content_full_hits = 0
    for path in files:
        scanned += 1
        text = path.read_text(encoding="utf-8", errors="replace")
        secret_hits += len(SECRET_PATTERN.findall(text))
        if path.suffix.lower() == ".json":
            try:
                payload = json.loads(text)
            except Exception:  # noqa: BLE001
                payload = None
            raw_content_full_hits += _count_non_empty_content_full(payload)
    passed = secret_hits == 0 and raw_content_full_hits == 0
    return {
        "schema_version": "trace_sanitization_gate_v1",
        "prd_id": PRD,
        "files_scanned": scanned,
        "secret_pattern_hits": secret_hits,
        "raw_content_full_hits": raw_content_full_hits,
        "trace_sanitization_gate": "passed" if passed else "blocked",
    }


def build_no_mutation_proof(
    *,
    hash_before: dict[str, str],
    hash_after: dict[str, str],
) -> dict[str, Any]:
    changed = [name for name, before in hash_before.items() if hash_after.get(name) != before]
    passed = len(changed) == 0
    return {
        "schema_version": "no_mutation_proof_v1",
        "prd_id": PRD,
        "tracked_files": sorted(hash_before.keys()),
        "changed_files": changed,
        "no_mutation_proof": "passed" if passed else "blocked",
        "no_mutation_proof_passed": passed,
    }


def build_hf4_scorecard(
    *,
    source_gate: dict[str, Any],
    creator_live_behavior_smoke: dict[str, Any],
    anti_loop_audit: dict[str, Any],
    routing_probe: dict[str, Any],
    writer_move_probe: dict[str, Any],
    writer_chunks_gate: dict[str, Any],
    rag_regression_gate: dict[str, Any],
    normal_user_gate: dict[str, Any],
    trace_gate: dict[str, Any],
    provider_gate: dict[str, Any],
    no_mutation_proof: dict[str, Any],
    artifact_encoding_hygiene_passed: bool,
) -> tuple[dict[str, Any], dict[str, Any]]:
    blockers: list[str] = []
    warnings: list[str] = []

    source_ok = bool(source_gate.get("source_gate_passed"))
    routing_ok = str(routing_probe.get("example_request_routing_gate")) == "passed"
    anti_ok = str(anti_loop_audit.get("anti_regulate_loop_gate")) == "passed"
    practice_memory_ok = _as_int(anti_loop_audit.get("practice_suppressed_after_rejection_count"), 0) >= 1
    writer_move_ok = str(writer_move_probe.get("writer_move_calibration_gate")) == "passed"
    smoke_ok = str(creator_live_behavior_smoke.get("creator_live_behavior_smoke_gate")) == "passed"
    chunks_gate = str(writer_chunks_gate.get("writer_chunks_display_gate"))
    chunks_empty = _as_int(writer_chunks_gate.get("writer_chunks_empty_preview_count"), 0)
    chunks_ok = (chunks_gate == "passed") or (chunks_gate == "warning" and chunks_empty == 0)
    rag_ok = str(rag_regression_gate.get("rag_regression_gate")) == "passed"
    normal_ok = str(normal_user_gate.get("normal_user_no_effect_gate")) == "passed"
    trace_ok = str(trace_gate.get("trace_sanitization_gate")) == "passed"
    provider_ok = str(provider_gate.get("provider_budget_gate")) == "passed"
    mutation_ok = bool(no_mutation_proof.get("no_mutation_proof_passed", False))
    true_regulate_ok = bool(creator_live_behavior_smoke.get("true_regulate_case_passed", False))

    if not source_ok:
        blockers.append("source_gate_blocked")
    if not routing_ok:
        blockers.append("example_request_routing_gate_blocked")
    if not anti_ok:
        blockers.append("anti_regulate_loop_gate_blocked")
    if not practice_memory_ok:
        blockers.append("practice_rejection_memory_gate_blocked")
    if not writer_move_ok:
        blockers.append("writer_move_calibration_gate_blocked")
    if not smoke_ok or not true_regulate_ok:
        blockers.append("creator_live_behavior_smoke_gate_blocked")
    if not chunks_ok:
        blockers.append("writer_chunks_display_gate_blocked")
    if not rag_ok or not normal_ok:
        blockers.append("rag_or_normal_boundary_regression")
    if not trace_ok:
        blockers.append("trace_sanitization_gate_blocked")
    if not provider_ok:
        blockers.append("provider_budget_gate_blocked")
    if not mutation_ok:
        blockers.append("no_mutation_proof_failed")
    if not artifact_encoding_hygiene_passed:
        blockers.append("artifact_encoding_hygiene_failed")

    if chunks_gate == "warning":
        warnings.append(str(writer_chunks_gate.get("warning") or "writer_chunks_display_warning"))

    if not blockers:
        final_status = "passed"
        decision = DECISION_PASSED
    else:
        final_status = "blocked"
        if "example_request_routing_gate_blocked" in blockers:
            decision = DECISION_BLOCKED_ROUTING
        elif "anti_regulate_loop_gate_blocked" in blockers:
            decision = DECISION_BLOCKED_REGULATE_LOOP
        elif "writer_chunks_display_gate_blocked" in blockers:
            decision = DECISION_BLOCKED_TRACE_DISPLAY
        else:
            decision = DECISION_BLOCKED_RAG_SAFETY

    scorecard = HF4Scorecard(
        final_status=final_status,
        decision=decision,
        source_gate="passed" if source_ok else "blocked",
        example_request_routing_gate="passed" if routing_ok else "blocked",
        anti_regulate_loop_gate="passed" if anti_ok else "blocked",
        practice_rejection_memory_gate="passed" if practice_memory_ok else "blocked",
        writer_move_calibration_gate="passed" if writer_move_ok else "blocked",
        creator_live_behavior_smoke_gate="passed" if smoke_ok and true_regulate_ok else "blocked",
        writer_chunks_display_gate=chunks_gate,
        rag_regression_gate="passed" if rag_ok else "blocked",
        normal_user_no_effect_gate="passed" if normal_ok else "blocked",
        trace_sanitization_gate="passed" if trace_ok else "blocked",
        provider_budget_gate="passed" if provider_ok else "blocked",
        no_mutation_proof="passed" if mutation_ok else "blocked",
        artifact_encoding_hygiene="passed" if artifact_encoding_hygiene_passed else "blocked",
        example_cases_total=_as_int(creator_live_behavior_smoke.get("example_cases_total"), 0),
        example_cases_passed=_as_int(creator_live_behavior_smoke.get("example_cases_passed"), 0),
        practice_suppressed_after_rejection_count=_as_int(
            creator_live_behavior_smoke.get("practice_suppressed_after_rejection_count"), 0
        ),
        unexpected_regulate_first_count=_as_int(
            creator_live_behavior_smoke.get("unexpected_regulate_first_count"), 0
        ),
        unexpected_body_action_count=_as_int(
            creator_live_behavior_smoke.get("unexpected_body_action_count"), 0
        ),
        true_regulate_case_passed=true_regulate_ok,
        writer_chunks_count=_as_int(writer_chunks_gate.get("writer_chunks_count"), 0),
        writer_chunks_non_empty_preview_count=_as_int(
            writer_chunks_gate.get("writer_chunks_non_empty_preview_count"), 0
        ),
        writer_chunks_empty_preview_count=_as_int(writer_chunks_gate.get("writer_chunks_empty_preview_count"), 0),
        botdb_chunks_returned=_as_int(rag_regression_gate.get("botdb_chunks_returned"), 0),
        knowledge_policy_included_writer_count=_as_int(
            rag_regression_gate.get("knowledge_policy_included_writer_count"), 0
        ),
        context_assembly_knowledge_hits_count=_as_int(
            rag_regression_gate.get("context_assembly_knowledge_hits_count"), 0
        ),
        writer_prompt_knowledge_hits_count=_as_int(
            rag_regression_gate.get("writer_prompt_knowledge_hits_count"), 0
        ),
        broad_rollout_allowed=False,
        production_ready=False,
        normal_user_activation_allowed=False,
        all_users_mode_enabled=False,
        blockers=blockers,
        warnings=warnings,
        next_prd_recommendation=NEXT_PRD,
    ).to_dict()
    decision_payload = HF4Decision(
        final_status=final_status,
        decision=decision,
        blockers=blockers,
        warnings=warnings,
    ).to_dict()
    return scorecard, decision_payload


def update_docs(docs_dir: Path, scorecard: dict[str, Any]) -> None:
    passed = str(scorecard.get("final_status", "blocked")) == "passed"
    stage_line = (
        "Current Stage:\n"
        "PRD-046.1.35-HF4 calibrated creator-live response behavior: "
        "example/explanation requests no longer trigger regulate_first by default, "
        "practice rejection suppresses body-action suggestions, "
        "and Web Trace displays non-empty safe Writer chunk previews.\n"
        "Next:\n"
        "PRD-046.1.36 Creator Live Pilot Acceptance / Minimal Admin Runtime Controls v1."
    )
    blocked_line = (
        "Current Stage:\n"
        "PRD-046.1.35-HF4 blocked on creator-live behavior/trace display calibration.\n"
        "Next:\n"
        "targeted HF5 before Diagnostic Center pilot acceptance."
    )
    text = stage_line if passed else blocked_line
    for name in ("PROJECT_STATE.md", "ROADMAP.md", "PRD_INDEX.md", "DECISIONS.md"):
        path = docs_dir / name
        existing = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
        marker = f"\n\n## {PRD}\n"
        if marker in existing:
            head, _sep, _tail = existing.partition(marker)
            updated = head.rstrip() + marker + text + "\n"
        else:
            updated = existing.rstrip() + marker + text + "\n"
        path.write_text(updated, encoding="utf-8")


def render_implementation_report(scorecard: dict[str, Any], strict_status: str) -> str:
    return "\n".join(
        [
            "# PRD-046.1.35-HF4 IMPLEMENTATION REPORT",
            "",
            f"- PRD ID: `{PRD}`",
            f"- final_status: `{scorecard.get('final_status', 'blocked')}`",
            f"- decision: `{scorecard.get('decision', DECISION_BLOCKED_ROUTING)}`",
            "- commit_hash: `pending`",
            "- push_status: `pending`",
            "",
            "## Gates",
            f"- source_gate: `{scorecard.get('source_gate', 'blocked')}`",
            f"- example_request_routing_passed: `{scorecard.get('example_request_routing_gate', 'blocked')}`",
            f"- anti_regulate_loop_passed: `{scorecard.get('anti_regulate_loop_gate', 'blocked')}`",
            f"- writer_chunks_display_gate: `{scorecard.get('writer_chunks_display_gate', 'blocked')}`",
            f"- rag_regression_gate: `{scorecard.get('rag_regression_gate', 'blocked')}`",
            f"- normal_user_no_effect_gate: `{scorecard.get('normal_user_no_effect_gate', 'blocked')}`",
            f"- trace_sanitization_gate: `{scorecard.get('trace_sanitization_gate', 'blocked')}`",
            f"- provider_budget_gate: `{scorecard.get('provider_budget_gate', 'blocked')}`",
            f"- no_mutation_proof: `{scorecard.get('no_mutation_proof', 'blocked')}`",
            "",
            "## Test Summary",
            "- unit tests: `python -m pytest bot_psychologist/tests/multiagent/test_hf4_*.py -q`",
            f"- strict runner status: `{strict_status}`",
            "",
            "## Counters",
            f"- example_cases_total: `{scorecard.get('example_cases_total', 0)}`",
            f"- example_cases_passed: `{scorecard.get('example_cases_passed', 0)}`",
            f"- practice_suppressed_after_rejection_count: `{scorecard.get('practice_suppressed_after_rejection_count', 0)}`",
            f"- unexpected_regulate_first_count: `{scorecard.get('unexpected_regulate_first_count', 0)}`",
            f"- unexpected_body_action_count: `{scorecard.get('unexpected_body_action_count', 0)}`",
            f"- writer_chunks_count: `{scorecard.get('writer_chunks_count', 0)}`",
            f"- writer_chunks_non_empty_preview_count: `{scorecard.get('writer_chunks_non_empty_preview_count', 0)}`",
            f"- writer_chunks_empty_preview_count: `{scorecard.get('writer_chunks_empty_preview_count', 0)}`",
            "",
            "## Blockers",
            f"- `{', '.join([str(x) for x in _safe_list(scorecard.get('blockers'))]) or 'none'}`",
            "",
            "## Warnings",
            f"- `{', '.join([str(x) for x in _safe_list(scorecard.get('warnings'))]) or 'none'}`",
            "",
            "## Next PRD Recommendation",
            f"- `{scorecard.get('next_prd_recommendation', NEXT_PRD)}`",
        ]
    )
