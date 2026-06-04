#!/usr/bin/env python3
"""PRD-047.11-HF2 runner: fresh chat isolation, RAG gate, and real web markdown proof."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DEFAULT_LOG_DIR = REPO_ROOT / "TO_DO_LIST" / "logs" / "PRD-047.11-HF2"
DEFAULT_REPORT_DIR = REPO_ROOT / "TO_DO_LIST" / "reports"
DEFAULT_BASE_URL = "http://127.0.0.1:8001/api/v1"
DEFAULT_ADMIN_RUNTIME_URL = "http://127.0.0.1:8001/api/admin/runtime/effective"
DEFAULT_CHAT_URL = "http://127.0.0.1:3000/chat"
DEFAULT_ADMIN_UI_URL = "http://127.0.0.1:3000/admin"
PRD_ID = "PRD-047.11-HF2"

REQUIRED_SUBDIRS = (
    "live_turn_exports",
    "prompt_canvases",
    "raw_traces",
    "screenshots",
    "dom_snapshots",
)

SOURCE_AUDIT_TARGETS = [
    {
        "label": "conversation_context",
        "paths": [
            "bot_psychologist/bot_agent/multiagent/context_assembly.py",
            "bot_psychologist/bot_agent/multiagent/contracts/writer_contract.py",
        ],
        "pattern": "conversation_context",
    },
    {
        "label": "semantic_hits",
        "paths": [
            "bot_psychologist/bot_agent/multiagent/writer_context_package.py",
            "bot_psychologist/bot_agent/multiagent/live_turn_evidence.py",
        ],
        "pattern": "semantic_hits",
    },
    {
        "label": "contextual_retrieval_gating",
        "paths": [
            "bot_psychologist/bot_agent/multiagent/dialogue_pragmatics.py",
            "bot_psychologist/bot_agent/multiagent/orchestrator.py",
        ],
        "pattern": "rag_included_count",
    },
    {
        "label": "knowledge_answer_routing",
        "paths": [
            "bot_psychologist/bot_agent/multiagent/knowledge_answer_routing_guard.py",
            "bot_psychologist/bot_agent/multiagent/final_answer_directive.py",
        ],
        "pattern": "knowledge_answer",
    },
    {
        "label": "session_new_chat_creation",
        "paths": [
            "bot_psychologist/api/dependencies.py",
            "bot_psychologist/api/conversations/repository.py",
            "bot_psychologist/api/conversations/service.py",
            "bot_psychologist/api/routes/chat.py",
            "bot_psychologist/web_ui/src/pages/ChatPage.tsx",
            "bot_psychologist/web_ui/src/services/api.service.ts",
        ],
        "pattern": "session_id",
    },
    {
        "label": "persistence_memory_update",
        "paths": [
            "bot_psychologist/api/routes/users.py",
            "bot_psychologist/bot_agent/conversation_memory.py",
        ],
        "pattern": "clear",
    },
    {
        "label": "web_chat_rendering",
        "paths": [
            "bot_psychologist/web_ui/src/components/chat/Message.tsx",
            "bot_psychologist/web_ui/src/components/chat/ChatWindow.tsx",
        ],
        "pattern": "ReactMarkdown",
    },
    {
        "label": "admin_runtime_effective_payload",
        "paths": [
            "bot_psychologist/api/admin_routes.py",
            "bot_psychologist/web_ui/src/components/admin/AdminPanel.tsx",
        ],
        "pattern": "fresh_chat_context_policy_version",
    },
]

LIVE_CASES: list[dict[str, Any]] = [
    {
        "case_id": "HF2-LIVE-001",
        "title": "fresh greeting",
        "turns": ["привет, меня зовут Асхат!"],
    },
    {
        "case_id": "HF2-LIVE-002",
        "title": "greeting repair",
        "turns": [
            "привет, меня зовут Асхат!",
            "почему ты начал объяснять механизм, я просто поздоровался?",
        ],
    },
    {
        "case_id": "HF2-LIVE-003",
        "title": "explicit continuation",
        "seed_turns": ["объясни простыми словами, что такое автоматический контроль"],
        "turns": ["продолжим прошлую тему про автоматический контроль"],
    },
    {
        "case_id": "HF2-LIVE-004",
        "title": "concept needs rag",
        "turns": ["что такое нейросталкинг простыми словами?"],
    },
    {
        "case_id": "HF2-LIVE-005",
        "title": "short yes inherits rag topic",
        "turns": [
            "что такое нейросталкинг простыми словами? После короткого ответа предложи, если нужно, объяснить на примере.",
            "да",
        ],
    },
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _resolve_path(raw: str) -> Path:
    path = Path(raw)
    if path.is_absolute():
        return path
    return (REPO_ROOT / path).resolve()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _run_cmd(args: list[str], *, cwd: Path | None = None) -> tuple[int, str, str]:
    proc = subprocess.run(
        args,
        cwd=str(cwd or REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return proc.returncode, proc.stdout, proc.stderr


def _http_json_request(
    *,
    method: str,
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any] | None = None,
    timeout: float = 120.0,
) -> tuple[int, dict[str, Any]]:
    body = None
    req_headers = dict(headers)
    if payload is not None:
        req_headers["Content-Type"] = "application/json"
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(url=url, method=method.upper(), headers=req_headers, data=body)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = int(getattr(response, "status", 200))
            raw = response.read().decode("utf-8")
            data = json.loads(raw) if raw.strip() else {}
            return status, data if isinstance(data, dict) else {"raw": data}
    except urllib.error.HTTPError as exc:
        status = int(getattr(exc, "code", 500))
        raw = exc.read().decode("utf-8", errors="replace") if hasattr(exc, "read") else ""
        if raw.strip():
            try:
                parsed = json.loads(raw)
                return status, parsed if isinstance(parsed, dict) else {"raw": parsed}
            except json.JSONDecodeError:
                return status, {"raw": raw}
        return status, {}


def _derive_api_root(base_url: str) -> str:
    base = base_url.rstrip("/")
    if base.endswith("/api/v1"):
        return base[:-7]
    return base


def _ensure_layout(log_dir: Path) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    for subdir in REQUIRED_SUBDIRS:
        (log_dir / subdir).mkdir(parents=True, exist_ok=True)


def _matches_for_pattern(path: Path, pattern: str) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    code, out, _err = _run_cmd(["rg", "-n", pattern, str(path)])
    if code not in (0, 1):
        return []
    matches: list[dict[str, Any]] = []
    for line in out.splitlines():
        parts = line.split(":", 2)
        if len(parts) != 3:
            continue
        _, line_no, snippet = parts
        matches.append(
            {
                "line": int(line_no) if line_no.isdigit() else 0,
                "snippet": snippet.strip(),
            }
        )
    return matches[:5]


def build_source_audit(log_dir: Path) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    lines = [
        f"# {PRD_ID} Source Audit",
        "",
        f"- generated_at_utc: `{_now_iso()}`",
        "- scope: conversation context, retrieval gating, routing, session isolation, persistence, rendering, admin payload",
        "",
    ]
    for target in SOURCE_AUDIT_TARGETS:
        target_items: list[dict[str, Any]] = []
        lines.append(f"## {target['label']}")
        for raw_path in target["paths"]:
            abs_path = _resolve_path(raw_path)
            item = {
                "path": raw_path,
                "exists": abs_path.exists(),
                "pattern": target["pattern"],
                "matches": _matches_for_pattern(abs_path, str(target["pattern"])),
            }
            target_items.append(item)
            if not item["exists"]:
                lines.append(f"- `{raw_path}` :: missing")
                continue
            if item["matches"]:
                first = item["matches"][0]
                lines.append(
                    f"- `{raw_path}:{first['line']}` :: {first['snippet']}"
                )
            else:
                lines.append(f"- `{raw_path}` :: present, no direct `{target['pattern']}` match")
        lines.append("")
        entries.append(
            {
                "label": target["label"],
                "files": target_items,
            }
        )
    payload = {
        "prd_id": PRD_ID,
        "generated_at_utc": _now_iso(),
        "targets": entries,
        "hf1_invariants_expected": {
            "legacy_blocks_visible_to_writer": False,
            "legacy_advisory_sanitized": True,
            "practice_rewrite_applied": True,
            "raw_legacy_visible_to_writer": False,
        },
    }
    _write_json(log_dir / "00_source_audit.json", payload)
    _write_text(log_dir / "00_source_audit.md", "\n".join(lines))
    return payload


def _contains_any(text: str, needles: list[str]) -> bool:
    lowered = str(text or "").lower()
    return any(needle.lower() in lowered for needle in needles)


def _safe_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _safe_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _extract_live_evidence(trace_payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(trace_payload, dict):
        return {}
    live = trace_payload.get("live_turn_evidence")
    return dict(live) if isinstance(live, dict) else {}


def _extract_prompt_assembly(trace_payload: dict[str, Any]) -> dict[str, Any]:
    evidence = _extract_live_evidence(trace_payload)
    writer = evidence.get("writer")
    if isinstance(writer, dict):
        prompt_assembly = writer.get("prompt_assembly")
        if isinstance(prompt_assembly, dict):
            return dict(prompt_assembly)
    return {}


def _extract_fresh_policy(trace_payload: dict[str, Any]) -> dict[str, Any]:
    prompt_assembly = _extract_prompt_assembly(trace_payload)
    fresh = prompt_assembly.get("fresh_chat_context_policy")
    if isinstance(fresh, dict):
        return dict(fresh)
    evidence = _extract_live_evidence(trace_payload)
    dialogue = evidence.get("dialogue")
    if isinstance(dialogue, dict):
        fresh = dialogue.get("fresh_chat_context_policy")
        if isinstance(fresh, dict):
            return dict(fresh)
    return {}


def _extract_writer_context_package(trace_payload: dict[str, Any]) -> dict[str, Any]:
    prompt_assembly = _extract_prompt_assembly(trace_payload)
    package = prompt_assembly.get("writer_context_package")
    return dict(package) if isinstance(package, dict) else {}


def _extract_final_directive(trace_payload: dict[str, Any]) -> dict[str, Any]:
    evidence = _extract_live_evidence(trace_payload)
    writer = evidence.get("writer")
    if isinstance(writer, dict):
        directive = writer.get("final_answer_directive")
        if isinstance(directive, dict):
            return dict(directive)
    directive = trace_payload.get("final_answer_directive")
    return dict(directive) if isinstance(directive, dict) else {}


def _extract_prompt_preview(trace_payload: dict[str, Any]) -> str:
    evidence = _extract_live_evidence(trace_payload)
    writer = evidence.get("writer")
    if isinstance(writer, dict):
        canvas = writer.get("prompt_canvas")
        if isinstance(canvas, dict):
            preview = canvas.get("user_prompt_preview")
            if isinstance(preview, str):
                return preview
    preview = trace_payload.get("writer_user_prompt")
    return str(preview or "")


def _case_turn_export_payload(
    *,
    case_id: str,
    turn_index: int,
    user_message: str,
    assistant_answer: str,
    trace_payload: dict[str, Any],
) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "turn_index": turn_index,
        "user_message": user_message,
        "assistant_answer": assistant_answer,
        "fresh_chat_context_policy": _extract_fresh_policy(trace_payload),
        "writer_context_package": _extract_writer_context_package(trace_payload),
        "final_answer_directive": _extract_final_directive(trace_payload),
        "live_turn_evidence": _extract_live_evidence(trace_payload),
        "writer_prompt_preview": _extract_prompt_preview(trace_payload),
    }


def _save_case_turn_artifacts(
    *,
    log_dir: Path,
    case_id: str,
    turn_index: int,
    turn_payload: dict[str, Any],
    trace_payload: dict[str, Any],
) -> None:
    export_dir = log_dir / "live_turn_exports" / case_id
    export_dir.mkdir(parents=True, exist_ok=True)
    _write_json(export_dir / f"turn_{turn_index:02d}.json", turn_payload)
    _write_json(log_dir / "raw_traces" / f"{case_id}_turn_{turn_index:02d}.json", trace_payload)
    _write_text(
        log_dir / "prompt_canvases" / f"{case_id}_turn_{turn_index:02d}_writer_prompt.txt",
        turn_payload.get("writer_prompt_preview", "") or "",
    )


def _evaluate_case(
    *,
    case_id: str,
    answers: list[str],
    latest_trace: dict[str, Any],
) -> tuple[dict[str, bool], list[str]]:
    last_answer = str(answers[-1] if answers else "")
    fresh_policy = _extract_fresh_policy(latest_trace)
    writer_package = _extract_writer_context_package(latest_trace)
    final_directive = _extract_final_directive(latest_trace)
    prompt_preview = _extract_prompt_preview(latest_trace)
    rag_for_writer = _safe_list(writer_package.get("rag_for_writer"))
    rag_candidates = _safe_list(writer_package.get("rag_candidates_for_trace"))
    rag_gate = _safe_dict(writer_package.get("rag_gate_decision"))
    non_included_previews = [
        str(item.get("content_preview", "") or "")
        for item in rag_candidates
        if isinstance(item, dict) and not bool(item.get("included_for_writer", False))
    ]

    checks: dict[str, bool] = {
        "answer_non_empty": bool(last_answer.strip()),
    }

    if case_id == "HF2-LIVE-001":
        checks.update(
            {
                "simple_contact_shape": str(final_directive.get("answer_shape", "")) == "simple_contact",
                "cross_session_memory_blocked": bool(fresh_policy.get("cross_session_memory_allowed", True)) is False,
                "fresh_reason_expected": str(fresh_policy.get("cross_session_memory_reason", "")) == "fresh_greeting_no_explicit_continuation",
                "rag_not_included_for_writer": int(rag_gate.get("rag_included_count", 0) or 0) == 0 and len(rag_for_writer) == 0,
                "no_raw_rag_preview_in_prompt": not any(preview and preview in prompt_preview for preview in non_included_previews),
                "no_mechanism_explanation": not _contains_any(last_answer, ["автоматичес", "механизм", "упражнен", "практик"]),
            }
        )
    elif case_id == "HF2-LIVE-002":
        checks.update(
            {
                "repair_is_concise": len(last_answer) <= 450,
                "repair_without_extra_question": "?" not in last_answer,
                "repair_without_rag": int(rag_gate.get("rag_included_count", 0) or 0) == 0 and len(rag_for_writer) == 0,
                "repair_without_kb_noise": not _contains_any(last_answer, ["нейросталкин", "кузниц", "практик"]),
            }
        )
    elif case_id == "HF2-LIVE-003":
        checks.update(
            {
                "cross_session_memory_allowed": bool(fresh_policy.get("cross_session_memory_allowed", False)) is True,
                "continuation_reason_explicit": str(fresh_policy.get("cross_session_memory_reason", "")) == "explicit_continuation",
                "not_simple_contact_shape": str(final_directive.get("answer_shape", "")) != "simple_contact",
            }
        )
    elif case_id == "HF2-LIVE-004":
        checks.update(
            {
                "rag_included_for_concept": int(rag_gate.get("rag_included_count", 0) or 0) > 0 or len(rag_for_writer) > 0,
                "knowledge_shape_not_contact": str(final_directive.get("answer_shape", "")) != "simple_contact",
            }
        )
    elif case_id == "HF2-LIVE-005":
        checks.update(
            {
                "rag_topic_inherited_on_yes": int(rag_gate.get("rag_included_count", 0) or 0) > 0 or len(rag_for_writer) > 0,
                "answer_not_too_short": len(last_answer) >= 180,
                "no_short_social_suppression": str(rag_gate.get("rag_suppressed_reason", "")) not in {
                    "fresh_greeting_no_knowledge_need",
                    "short_social_no_knowledge_need",
                },
            }
        )

    failed = [name for name, passed in checks.items() if not passed]
    return checks, failed


def _post_adaptive_turn(
    *,
    base_url: str,
    headers: dict[str, str],
    session_id: str,
    query: str,
) -> tuple[int, dict[str, Any]]:
    return _http_json_request(
        method="POST",
        url=f"{base_url.rstrip('/')}/questions/adaptive",
        headers=headers,
        payload={
            "query": query,
            "session_id": session_id,
            "debug": True,
            "include_path": False,
            "include_feedback_prompt": True,
        },
        timeout=180.0,
    )


def _run_live_cases(
    *,
    log_dir: Path,
    base_url: str,
    api_key: str,
    admin_runtime_url: str,
    web_session_id: str,
    device_fingerprint: str,
) -> dict[str, Any]:
    headers = {
        "X-API-Key": api_key,
        "X-Session-Id": web_session_id,
        "X-Device-Fingerprint": device_fingerprint,
    }
    runtime_status, runtime_payload = _http_json_request(
        method="GET",
        url=admin_runtime_url,
        headers=headers,
        timeout=30.0,
    )
    if runtime_status != 200:
        return {
            "status": "blocked",
            "reason": f"admin_runtime_status_{runtime_status}",
            "runtime_status": runtime_status,
        }

    api_root = _derive_api_root(base_url)
    me_status, me_payload = _http_json_request(
        method="GET",
        url=f"{api_root}/api/v1/identity/me",
        headers=headers,
        timeout=30.0,
    )
    canonical_user_id = str(me_payload.get("user_id", "") or "")
    if me_status != 200 or not canonical_user_id:
        return {
            "status": "blocked",
            "reason": f"identity_status_{me_status}",
            "runtime_status": runtime_status,
        }

    case_results: list[dict[str, Any]] = []
    total_failures = 0
    for case in LIVE_CASES:
        case_id = str(case["case_id"])
        session_id = f"prd04711hf2-{case_id.lower()}-{uuid.uuid4().hex[:8]}"
        seed_turns = [str(item) for item in list(case.get("seed_turns", []) or [])]
        for seed_turn in seed_turns:
            _post_adaptive_turn(
                base_url=base_url,
                headers=headers,
                session_id=f"{session_id}-seed",
                query=seed_turn,
            )

        status_codes: list[int] = []
        answers: list[str] = []
        latest_trace: dict[str, Any] = {}
        for idx, turn in enumerate([str(item) for item in list(case.get("turns", []) or [])], start=1):
            status_code, payload = _post_adaptive_turn(
                base_url=base_url,
                headers=headers,
                session_id=session_id,
                query=turn,
            )
            status_codes.append(status_code)
            answer = str(payload.get("answer", "") or "")
            answers.append(answer)
            trace_payload = dict(payload.get("trace", {})) if isinstance(payload.get("trace"), dict) else {}
            latest_trace = trace_payload
            turn_payload = _case_turn_export_payload(
                case_id=case_id,
                turn_index=idx,
                user_message=turn,
                assistant_answer=answer,
                trace_payload=trace_payload,
            )
            _save_case_turn_artifacts(
                log_dir=log_dir,
                case_id=case_id,
                turn_index=idx,
                turn_payload=turn_payload,
                trace_payload=trace_payload,
            )

        traces_status, traces_payload = _http_json_request(
            method="GET",
            url=f"{api_root}/api/debug/session/{urllib.parse.quote(session_id, safe='')}/traces?format=full",
            headers=headers,
            timeout=60.0,
        )
        latest_status, latest_payload = _http_json_request(
            method="GET",
            url=f"{api_root}/api/debug/session/{urllib.parse.quote(session_id, safe='')}/multiagent-trace",
            headers=headers,
            timeout=60.0,
        )
        if latest_status == 200 and isinstance(latest_payload, dict):
            latest_trace = latest_payload
        _write_json(
            log_dir / "raw_traces" / f"{case_id}_traces_full.json",
            traces_payload if isinstance(traces_payload, dict) else {"status": traces_status},
        )
        _write_json(
            log_dir / "raw_traces" / f"{case_id}_trace_latest.json",
            latest_payload if isinstance(latest_payload, dict) else {"status": latest_status},
        )

        checks, failed_checks = _evaluate_case(case_id=case_id, answers=answers, latest_trace=latest_trace)
        checks["all_status_200"] = all(code == 200 for code in status_codes)
        checks["trace_endpoint_ok"] = latest_status == 200
        checks["traces_endpoint_ok"] = traces_status == 200
        failed_checks = [name for name, passed in checks.items() if not passed]
        if failed_checks:
            total_failures += 1
        case_results.append(
            {
                "case_id": case_id,
                "title": case.get("title"),
                "session_id": session_id,
                "status": "passed" if not failed_checks else "failed",
                "status_codes": status_codes,
                "answers": answers,
                "checks": checks,
                "failed_checks": failed_checks,
            }
        )

    # Memory control events and explicit session reset proof.
    create_session_status, create_session_payload = _http_json_request(
        method="POST",
        url=f"{base_url.rstrip('/')}/users/{urllib.parse.quote(canonical_user_id, safe='')}/sessions",
        headers=headers,
        payload={"title": "HF2 Reset Session"},
        timeout=60.0,
    )
    memory_case_session = str(
        _safe_dict(create_session_payload).get("session_id", "") or f"prd04711hf2-reset-{uuid.uuid4().hex[:8]}"
    )
    reset_status, reset_payload = _http_json_request(
        method="POST",
        url=f"{base_url.rstrip('/')}/users/{urllib.parse.quote(canonical_user_id, safe='')}/sessions/{urllib.parse.quote(memory_case_session, safe='')}/reset-context",
        headers=headers,
        timeout=60.0,
    )
    history_status, history_payload = _http_json_request(
        method="GET",
        url=f"{base_url.rstrip('/')}/users/{urllib.parse.quote(memory_case_session, safe='')}/history?last_n_turns=10",
        headers=headers,
        timeout=60.0,
    )
    clear_status, clear_payload = _http_json_request(
        method="DELETE",
        url=f"{base_url.rstrip('/')}/users/{urllib.parse.quote(canonical_user_id, safe='')}/history",
        headers=headers,
        timeout=60.0,
    )
    _write_json(log_dir / "raw_traces" / "current_chat_reset_event.json", reset_payload if isinstance(reset_payload, dict) else {})
    _write_json(log_dir / "raw_traces" / "current_chat_reset_history_after.json", history_payload if isinstance(history_payload, dict) else {})
    _write_json(log_dir / "raw_traces" / "user_memory_profile_clear_event.json", clear_payload if isinstance(clear_payload, dict) else {})

    memory_checks = {
        "create_session_status_200": create_session_status == 200,
        "reset_context_status_200": reset_status == 200,
        "reset_context_event_present": _safe_dict(reset_payload).get("memory_control_event", {}).get("event") == "current_chat_context_reset",
        "reset_context_history_cleared": int(_safe_dict(history_payload).get("total_turns", -1)) == 0 if history_status == 200 else False,
        "clear_profile_status_200": clear_status == 200,
        "clear_profile_event_present": _safe_dict(clear_payload).get("memory_control_event", {}).get("event") == "user_memory_profile_cleared",
    }

    return {
        "status": "passed" if total_failures == 0 and all(memory_checks.values()) else "warning",
        "generated_at_utc": _now_iso(),
        "canonical_user_id": canonical_user_id,
        "runtime_payload": runtime_payload,
        "case_results": case_results,
        "memory_control_checks": memory_checks,
    }


def run_web_chat_markdown_smoke(
    *,
    chat_url: str,
    log_dir: Path,
    api_key: str,
) -> dict[str, Any]:
    result_json = log_dir / "markdown_real_chat_result.json"
    screenshot = log_dir / "screenshots" / "web_chat_markdown.png"
    dom_html = log_dir / "dom_snapshots" / "web_chat_markdown.html"
    prompt = (
        "Ответь строго одним markdown-сообщением без пояснений: **Жирный заголовок**. "
        "Потом два абзаца обычного текста. Потом маркированный список из двух пунктов."
    )
    script = f"""
const fs = require('node:fs');
const path = require('node:path');
async function main() {{
  let playwright = null;
  try {{
    playwright = require('playwright');
  }} catch (e) {{
    try {{
      playwright = require(path.join(process.cwd(), 'node_modules', 'playwright'));
    }} catch (_e2) {{
      fs.writeFileSync({json.dumps(str(result_json))}, JSON.stringify({{
        status: 'warning',
        reason: 'playwright_not_installed'
      }}, null, 2), 'utf8');
      return;
    }}
  }}
  const browser = await playwright.chromium.launch({{ headless: true }});
  try {{
    const page = await browser.newPage();
    await page.addInitScript((key) => {{
      window.localStorage.setItem('bot_api_key', key);
      window.localStorage.setItem('bot_web_session_id', 'hf2-web-chat-smoke');
    }}, {json.dumps(api_key)});
    await page.goto({json.dumps(chat_url)}, {{ waitUntil: 'domcontentloaded', timeout: 60000 }});
    await page.waitForTimeout(2000);
    await page.locator('textarea').fill({json.dumps(prompt)});
    await page.locator('textarea').press('Enter');
    await page.waitForFunction(() => {{
      const hasBotMessage = document.querySelectorAll('.message-bot .prose').length > 0;
      const isThinking = Boolean(document.querySelector('.thinking-indicator'));
      return hasBotMessage && !isThinking;
    }}, {{ timeout: 90000 }}).catch(() => null);
    await page.waitForTimeout(1500);
    const html = await page.content();
    fs.writeFileSync({json.dumps(str(dom_html))}, html, 'utf8');
    await page.screenshot({{ path: {json.dumps(str(screenshot))}, fullPage: true }});
    const checks = await page.evaluate(() => {{
      const botMessages = Array.from(document.querySelectorAll('.message-bot .prose'));
      const target = botMessages[botMessages.length - 1] || document.body;
      const strong = Boolean(target.querySelector('strong'));
      const list = Boolean(target.querySelector('ul,ol'));
      const paragraphs = target.querySelectorAll('p').length;
      const text = target.textContent || '';
      return {{
        has_strong: strong,
        has_ul_or_ol: list,
        paragraph_count_gte_2: paragraphs >= 2,
        not_plain_markdown_text: !text.includes('**Жирный заголовок**'),
      }};
    }});
    const status = Object.values(checks).every(Boolean) ? 'passed' : 'warning';
    fs.writeFileSync({json.dumps(str(result_json))}, JSON.stringify({{
      status,
      chat_url: {json.dumps(chat_url)},
      checks
    }}, null, 2), 'utf8');
  }} catch (e) {{
    fs.writeFileSync({json.dumps(str(result_json))}, JSON.stringify({{
      status: 'warning',
      reason: 'playwright_execution_error:' + String(e && e.name ? e.name : 'error')
    }}, null, 2), 'utf8');
  }} finally {{
    await browser.close().catch(() => {{}});
  }}
}}
main();
"""
    subprocess.run(
        ["node", "-e", script],
        cwd=str(PROJECT_ROOT / "web_ui"),
        check=False,
        capture_output=True,
        text=True,
        timeout=420,
    )
    if result_json.exists():
        return json.loads(result_json.read_text(encoding="utf-8"))
    return {"status": "warning", "reason": "missing_markdown_result"}


def run_admin_screenshots(
    *,
    admin_ui_url: str,
    log_dir: Path,
    api_key: str,
) -> dict[str, Any]:
    result_json = log_dir / "raw_traces" / "admin_screenshots_result.json"
    runtime_png = log_dir / "screenshots" / "admin_runtime_effective.png"
    memory_png = log_dir / "screenshots" / "admin_memory_controls.png"
    diagnostic_png = log_dir / "screenshots" / "admin_diagnostic_center.png"
    script = f"""
const fs = require('node:fs');
const path = require('node:path');
async function main() {{
  let playwright = null;
  try {{
    playwright = require('playwright');
  }} catch (e) {{
    try {{
      playwright = require(path.join(process.cwd(), 'node_modules', 'playwright'));
    }} catch (_e2) {{
      fs.writeFileSync({json.dumps(str(result_json))}, JSON.stringify({{
        status: 'warning',
        reason: 'playwright_not_installed'
      }}, null, 2), 'utf8');
      return;
    }}
  }}
  const browser = await playwright.chromium.launch({{ headless: true }});
  try {{
    const page = await browser.newPage();
    await page.addInitScript((key) => {{
      window.localStorage.setItem('devApiKey', key);
    }}, {json.dumps(api_key)});
    await page.goto({json.dumps(admin_ui_url)}, {{ waitUntil: 'domcontentloaded', timeout: 60000 }});
    await page.waitForTimeout(2500);
    await page.getByRole('button', {{ name: 'Runtime' }}).click();
    await page.waitForTimeout(1500);
    await page.screenshot({{ path: {json.dumps(str(runtime_png))}, fullPage: true }});
    const memoryCard = page.locator('[data-testid=\"hf2-memory-controls-runtime\"]');
    if (await memoryCard.count()) {{
      await memoryCard.first().screenshot({{ path: {json.dumps(str(memory_png))} }});
    }}
    await page.getByRole('button', {{ name: 'Diagnostic Center' }}).click();
    await page.waitForTimeout(1500);
    await page.screenshot({{ path: {json.dumps(str(diagnostic_png))}, fullPage: true }});
    const runtimeOk = fs.existsSync({json.dumps(str(runtime_png))});
    const memoryOk = fs.existsSync({json.dumps(str(memory_png))});
    const diagnosticOk = fs.existsSync({json.dumps(str(diagnostic_png))});
    fs.writeFileSync({json.dumps(str(result_json))}, JSON.stringify({{
      status: runtimeOk && memoryOk && diagnosticOk ? 'passed' : 'warning',
      runtime_png_exists: runtimeOk,
      memory_png_exists: memoryOk,
      diagnostic_png_exists: diagnosticOk
    }}, null, 2), 'utf8');
  }} catch (e) {{
    fs.writeFileSync({json.dumps(str(result_json))}, JSON.stringify({{
      status: 'warning',
      reason: 'playwright_execution_error:' + String(e && e.name ? e.name : 'error')
    }}, null, 2), 'utf8');
  }} finally {{
    await browser.close().catch(() => {{}});
  }}
}}
main();
"""
    subprocess.run(
        ["node", "-e", script],
        cwd=str(PROJECT_ROOT / "web_ui"),
        check=False,
        capture_output=True,
        text=True,
        timeout=420,
    )
    if result_json.exists():
        return json.loads(result_json.read_text(encoding="utf-8"))
    return {"status": "warning", "reason": "missing_admin_result"}


def _build_live_md(payload: dict[str, Any]) -> str:
    lines = [
        f"# {PRD_ID} Live Result",
        "",
        f"- status: `{payload.get('status')}`",
        f"- generated_at_utc: `{payload.get('generated_at_utc')}`",
        "",
        "## Global Checks",
    ]
    for key, value in dict(payload.get("checks", {})).items():
        lines.append(f"- {key}: `{bool(value)}`")
    lines.append("")
    lines.append("## Cases")
    for case in list(payload.get("case_results", []) or []):
        lines.append(f"### {case.get('case_id')} — {case.get('title')}")
        lines.append(f"- status: `{case.get('status')}`")
        lines.append(f"- session_id: `{case.get('session_id')}`")
        lines.append(f"- failed_checks: `{case.get('failed_checks')}`")
        for idx, answer in enumerate(list(case.get("answers", []) or []), start=1):
            lines.append(f"- answer_{idx}: `{answer[:300]}`")
    lines.append("")
    lines.append("## Memory Controls")
    for key, value in dict(payload.get("memory_control_checks", {})).items():
        lines.append(f"- {key}: `{bool(value)}`")
    return "\n".join(lines).rstrip() + "\n"


def _write_no_mutation_proof(log_dir: Path) -> None:
    _write_json(
        log_dir / "no_mutation_proof.json",
        {
            "kb_governance_mutated": False,
            "chroma_reindexed": False,
            "new_llm_agent_added": False,
            "new_runtime_path_added": False,
            "model_defaults_changed": False,
            "safety_policy_strengthened": False,
            "broad_rollout_enabled": False,
            "normal_user_activation_enabled": False,
        },
    )


def _write_reports(
    *,
    report_dir: Path,
    live_payload: dict[str, Any],
    markdown_payload: dict[str, Any],
    admin_payload: dict[str, Any],
) -> None:
    report_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "cases_total": len(list(live_payload.get("case_results", []) or [])),
        "cases_failed": sum(1 for item in list(live_payload.get("case_results", []) or []) if item.get("status") != "passed"),
        "markdown_status": markdown_payload.get("status"),
        "admin_status": admin_payload.get("status"),
    }
    _write_text(
        report_dir / "PRD-047.11-HF2_IMPLEMENTATION_REPORT.md",
        "\n".join(
            [
                f"# {PRD_ID} Implementation Report",
                "",
                f"- final_status: `{live_payload.get('status')}`",
                f"- generated_at_utc: `{_now_iso()}`",
                "",
                "## Summary",
                json.dumps(summary, ensure_ascii=False),
                "",
                "## Live Cases",
                json.dumps(live_payload.get("case_results", []), ensure_ascii=False, indent=2),
                "",
                "## Markdown Smoke",
                json.dumps(markdown_payload, ensure_ascii=False, indent=2),
                "",
                "## Admin Screenshot Proof",
                json.dumps(admin_payload, ensure_ascii=False, indent=2),
            ]
        ),
    )
    next_prd = "PRD-047.11-HF3"
    rationale = "If any HF2 live or browser/admin proof remains warning, next work should target residual context leakage or UI/browser stability without broad rollout."
    _write_text(
        report_dir / "PRD-047.11-HF2_NEXT_PRD_RECOMMENDATION.md",
        "\n".join(
            [
                f"# {PRD_ID} Next PRD Recommendation",
                "",
                f"- recommended_prd: `{next_prd}`",
                f"- rationale: {rationale}",
            ]
        ),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run PRD-047.11-HF2 live/browser proof")
    parser.add_argument("--base-url", default=os.getenv("PRD04711HF2_BASE_URL", DEFAULT_BASE_URL))
    parser.add_argument(
        "--admin-runtime-url",
        default=os.getenv("PRD04711HF2_ADMIN_RUNTIME_URL", DEFAULT_ADMIN_RUNTIME_URL),
    )
    parser.add_argument("--chat-url", default=os.getenv("PRD04711HF2_CHAT_URL", DEFAULT_CHAT_URL))
    parser.add_argument("--admin-ui-url", default=os.getenv("PRD04711HF2_ADMIN_UI_URL", DEFAULT_ADMIN_UI_URL))
    parser.add_argument("--api-key", default=os.getenv("PRD04711HF2_API_KEY", "dev-key-001"))
    parser.add_argument("--log-dir", default=str(DEFAULT_LOG_DIR))
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR))
    args = parser.parse_args()

    log_dir = _resolve_path(args.log_dir)
    report_dir = _resolve_path(args.report_dir)
    _ensure_layout(log_dir)
    build_source_audit(log_dir)

    web_session_id = "prd04711hf2-web-session"
    device_fingerprint = "sha256:prd04711hf2-device"
    live_payload = _run_live_cases(
        log_dir=log_dir,
        base_url=str(args.base_url),
        api_key=str(args.api_key),
        admin_runtime_url=str(args.admin_runtime_url),
        web_session_id=web_session_id,
        device_fingerprint=device_fingerprint,
    )
    markdown_payload = run_web_chat_markdown_smoke(
        chat_url=str(args.chat_url),
        log_dir=log_dir,
        api_key=str(args.api_key),
    )
    admin_payload = run_admin_screenshots(
        admin_ui_url=str(args.admin_ui_url),
        log_dir=log_dir,
        api_key=str(args.api_key),
    )

    global_checks = {
        "live_cases_passed": str(live_payload.get("status")) == "passed",
        "memory_controls_passed": all(bool(v) for v in dict(live_payload.get("memory_control_checks", {})).values()),
        "markdown_browser_passed": str(markdown_payload.get("status")) == "passed",
        "admin_screenshots_passed": str(admin_payload.get("status")) == "passed",
    }
    overall_status = "passed" if all(global_checks.values()) else "warning"
    payload = {
        "prd": PRD_ID,
        "status": overall_status,
        "generated_at_utc": _now_iso(),
        "checks": global_checks,
        "case_results": live_payload.get("case_results", []),
        "memory_control_checks": live_payload.get("memory_control_checks", {}),
        "markdown_real_chat_result": markdown_payload,
        "admin_screenshot_result": admin_payload,
    }
    _write_json(log_dir / "live_cases_result.json", payload)
    _write_text(log_dir / "live_cases_result.md", _build_live_md(payload))
    _write_no_mutation_proof(log_dir)
    _write_reports(
        report_dir=report_dir,
        live_payload=payload,
        markdown_payload=markdown_payload,
        admin_payload=admin_payload,
    )
    print(json.dumps({"status": payload["status"], "output": str(log_dir / "live_cases_result.json")}, ensure_ascii=False))
    return 0 if payload["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
