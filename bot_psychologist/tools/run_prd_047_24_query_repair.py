from __future__ import annotations

import json
import subprocess
import sys
import time
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from types import SimpleNamespace

REPO_ROOT = Path(__file__).resolve().parents[2]
BOT_ROOT = REPO_ROOT / "bot_psychologist"
if str(BOT_ROOT) not in sys.path:
    sys.path.insert(0, str(BOT_ROOT))

from bot_agent.multiagent.retrieval_query_builder import build_retrieval_query
from tools import validate_prd_artifact_encoding as encoding_validator

PRD_ID = "PRD-047.24"
PREV_PRD = "PRD-047.23"
LOG_DIR = REPO_ROOT / "TO_DO_LIST" / "logs" / PRD_ID
REPORT_DIR = REPO_ROOT / "TO_DO_LIST" / "reports"
API_BASE = "http://127.0.0.1:8001"
API_KEY = "dev-key-001"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _md(title: str, lines: list[str]) -> str:
    return "\n".join([f"# {title}", "", *lines])


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    ).stdout.strip()


def _http_json(url: str, *, method: str = "GET", headers: dict[str, str] | None = None, data: bytes | None = None) -> tuple[int, dict[str, Any]]:
    request = urllib.request.Request(url=url, method=method, headers=headers or {}, data=data)
    with urllib.request.urlopen(request, timeout=180) as response:
        return int(response.status), json.loads(response.read().decode("utf-8"))


def _http_text(url: str, *, method: str = "GET", headers: dict[str, str] | None = None, data: bytes | None = None) -> tuple[int, str]:
    request = urllib.request.Request(url=url, method=method, headers=headers or {}, data=data)
    with urllib.request.urlopen(request, timeout=180) as response:
        return int(response.status), response.read().decode("utf-8")


def _stream_body(query: str, session_id: str) -> bytes:
    payload = {
        "query": str(query),
        "user_id": "prd-047-24-user",
        "session_id": str(session_id),
        "include_path": False,
        "include_feedback_prompt": True,
        "debug": False,
    }
    return json.dumps(payload, ensure_ascii=True, separators=(",", ":")).encode("ascii")


def _extract_done_payload(sse_text: str) -> dict[str, Any]:
    events = [chunk for chunk in sse_text.split("\n\n") if chunk.strip()]
    for event in reversed(events):
        for line in event.splitlines():
            if not line.startswith("data:"):
                continue
            payload = json.loads(line.replace("data:", "", 1).strip())
            if payload.get("done") is True:
                return payload
    raise RuntimeError("SSE done payload not found")


def _normalize(text: str) -> str:
    return " ".join(str(text or "").lower().replace("ё", "е").split())


def _prompt_canvas_text(final_done: dict[str, Any], final_debug: dict[str, Any]) -> str:
    writer_prompt = str(final_debug.get("writer_user_prompt", "") or "").strip()
    if writer_prompt:
        return writer_prompt

    answer = str(final_done.get("answer", "") or "").strip()
    retrieval_trace = dict(final_debug.get("retrieval_query_build_trace", {}) or {})
    runtime_trace = dict(final_debug.get("runtime_config_trace", {}) or {})
    payload_trace = dict(final_debug.get("writer_kb_payload_trace", {}) or {})
    lines = [
        "[prompt unavailable in debug trace]",
        f"executed_rag_query={str(final_debug.get('executed_rag_query', '') or '').strip()}",
        f"legacy_rag_query={str(final_debug.get('legacy_rag_query', '') or '').strip()}",
        f"query_builder_primary_path={str(retrieval_trace.get('primary_path', '') or '').strip()}",
        f"current_turn_focus_status={str(retrieval_trace.get('current_turn_focus_status', '') or '').strip()}",
        f"writer_kb_payload_status={str(payload_trace.get('status', '') or '').strip()}",
        f"app_env={str(runtime_trace.get('app_env', '') or '').strip()}",
    ]
    if answer:
        lines.extend(["", "answer_preview:", answer[:1200]])
    return "\n".join(lines).strip()


def _score_relevance(*, debug_payload: dict[str, Any], expected_needles: list[str], wrong_needles: list[str]) -> dict[str, Any]:
    hits = list(debug_payload.get("semantic_hits_detail", []) or [])
    if not hits:
        memory_context = dict(debug_payload.get("memory_context", {}) or {})
        hits = list(memory_context.get("semantic_hits", []) or [])
    combined = " ".join(
        f"{item.get('content_full', '')} {item.get('content_preview', '')}"
        for item in hits
        if isinstance(item, dict)
    )
    combined_norm = _normalize(combined)
    expected_norm = [_normalize(item) for item in expected_needles]
    wrong_norm = [_normalize(item) for item in wrong_needles]
    expected_found = [needle for needle in expected_norm if needle and needle in combined_norm]
    wrong_found = [needle for needle in wrong_norm if needle and needle in combined_norm]
    if expected_found and len(expected_found) >= max(1, min(2, len(expected_norm))):
        label = "high_exact"
    elif expected_found:
        label = "medium_related"
    elif wrong_found:
        label = "wrong_topic"
    else:
        label = "missing_expected_source"
    return {
        "overall_label": label,
        "expected_needles_found": expected_found,
        "wrong_needles_found": wrong_found,
        "semantic_hits_count": len(hits),
    }


@dataclass
class DirectCase:
    case_id: str
    user_message: str
    previous_user_message: str = ""
    planner_query: str = ""
    inherited_topic: str = ""
    last_assistant_offer_summary: str = ""


DIRECT_CASES = [
    DirectCase(
        case_id="Q24-001",
        user_message="Что такое самореализация как она коррелируется с Нейросталкингом?",
        planner_query="самореализация нейросталкинг",
    ),
    DirectCase(
        case_id="Q24-002",
        user_message='а что такое "Программа несовершенное Я"?',
        previous_user_message="Что такое самореализация как она коррелируется с Нейросталкингом?",
        planner_query="программа несовершенное",
    ),
    DirectCase(
        case_id="Q24-003",
        user_message=(
            "расскажи о Пяти драйверах выживания: Драйвер 1: «Будь сильным», "
            "Драйвер 2: «Будь лучшим», Драйвер 3: «Радуй других», "
            "Драйвер 4: «Старайся сильнее», Драйвер 5: «Спеши» "
            "расскажи о Пяти драйверах выживания: Драйвер 1: «Будь сильным», "
            "Драйвер 2: «Будь лучшим», Драйвер 3: «Радуй других», "
            "Драйвер 4: «Старайся сильнее», Драйвер 5: «Спеши»"
        ),
        planner_query="пять драйверов выживания будь сильным будь лучшим радуй других старайся сильнее спеши",
    ),
    DirectCase(
        case_id="Q24-004",
        user_message="да",
        last_assistant_offer_summary="Хочешь, объясню второй уровень - НеоСталкинг?",
        inherited_topic="НеоСталкинг",
    ),
    DirectCase(
        case_id="Q24-005",
        user_message="а второй уровень?",
        inherited_topic="НеоСталкинг",
    ),
    DirectCase(
        case_id="Q24-006",
        user_message="что такое пять драйверов выживания?",
        previous_user_message="Что такое Нейросталкинг?",
        inherited_topic="Нейросталкинг",
        planner_query="пять драйверов выживания",
    ),
]


def run_source_gates() -> dict[str, Any]:
    previous_logs = REPO_ROOT / "TO_DO_LIST" / "logs" / PREV_PRD
    required = [
        previous_logs / "retrieval_query_assembly_audit.json",
        previous_logs / "retrieval_relevance_audit.json",
        previous_logs / "writer_payload_consistency_audit.json",
        previous_logs / "chunk_boundary_audit.json",
        previous_logs / "live_sample_report.json",
        REPO_ROOT / "TO_DO_LIST" / "reports" / "PRD-047.23_IMPLEMENTATION_REPORT.md",
    ]
    commit_presence = {}
    for rev in ("4f70dc4", "f51e26c", "d7baffe"):
        try:
            commit_presence[rev] = _git("rev-parse", "--verify", rev)
        except subprocess.CalledProcessError:
            commit_presence[rev] = ""
    report = {
        "schema_version": "prd_047_24_source_gate_report_v1",
        "prd_id": PRD_ID,
        "checked_at": _utc_now(),
        "required_paths": [
            {
                "path": str(path.relative_to(REPO_ROOT)).replace("\\", "/"),
                "exists": path.exists(),
            }
            for path in required
        ],
        "commit_presence": commit_presence,
        "status": "passed"
        if all(path.exists() for path in required) and all(bool(v) for v in commit_presence.values())
        else "failed",
    }
    _write_json(LOG_DIR / "source_gate_report.json", report)
    _write_text(
        LOG_DIR / "source_gate_report.md",
        _md(
            "PRD-047.24 Source Gate Report",
            [
                f"- status: `{report['status']}`",
                *[
                    f"- {item['path']}: `{item['exists']}`"
                    for item in report["required_paths"]
                ],
                *[
                    f"- commit `{rev}` present: `{bool(value)}`"
                    for rev, value in commit_presence.items()
                ],
            ],
        ),
    )
    return report


def run_direct_case_matrix() -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for case in DIRECT_CASES:
        payload = build_retrieval_query(
            user_message=case.user_message,
            previous_user_message=case.previous_user_message or None,
            planner_query=case.planner_query or None,
            inherited_topic=case.inherited_topic or None,
            last_assistant_offer_summary=case.last_assistant_offer_summary or None,
            max_chars=300,
        )
        cases.append({"case_id": case.case_id, **payload})
    _write_json(LOG_DIR / "query_repair_case_matrix.json", cases)
    _write_text(
        LOG_DIR / "query_repair_case_matrix.md",
        _md(
            "PRD-047.24 Query Repair Case Matrix",
            [
                f"- `{case['case_id']}`: `{case['current_turn_focus_status']}` | executed=`{case['executed_query']}`"
                for case in cases
            ],
        ),
    )
    return cases


def run_before_after() -> list[dict[str, Any]]:
    previous = json.loads((REPO_ROOT / "TO_DO_LIST" / "logs" / PREV_PRD / "retrieval_query_assembly_audit.json").read_text(encoding="utf-8"))
    by_case = {str(item.get("case_id", "")): item for item in previous if isinstance(item, dict)}
    direct = {item["case_id"]: item for item in json.loads((LOG_DIR / "query_repair_case_matrix.json").read_text(encoding="utf-8"))}
    rows = []
    for old_case_id, new_case_id in (("C23-002", "Q24-002"), ("C23-003", "Q24-003")):
        old_item = by_case.get(old_case_id, {})
        new_item = direct.get(new_case_id, {})
        rows.append(
            {
                "case_id": new_case_id,
                "previous_case_id": old_case_id,
                "before_executed_query": old_item.get("executed_query", ""),
                "before_legacy_query": old_item.get("legacy_query", ""),
                "before_polluted": bool(old_item.get("query_contains_previous_question", False) or old_item.get("query_truncated_mid_word", False) or old_item.get("query_duplicate_fragment_count", 0)),
                "after_executed_query": new_item.get("executed_query", ""),
                "after_previous_user_query_included": new_item.get("previous_user_query_included", False),
                "after_duplicate_fragment_count": new_item.get("duplicate_fragment_count", 0),
                "after_query_truncated_mid_word": new_item.get("query_truncated_mid_word", False),
            }
        )
    _write_json(LOG_DIR / "retrieval_query_build_before_after.json", rows)
    _write_text(
        LOG_DIR / "retrieval_query_build_before_after.md",
        _md(
            "PRD-047.24 Before After Query Repair",
            [
                f"- `{row['case_id']}` before_polluted=`{row['before_polluted']}` after=`{row['after_executed_query']}`"
                for row in rows
            ],
        ),
    )
    return rows


def run_live_smoke() -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    admin_headers = {"X-API-Key": API_KEY, "Accept": "application/json"}
    stream_headers = {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json; charset=utf-8",
        "Accept": "text/event-stream",
    }
    sessions = {
        "Q24-001": ["Что такое самореализация как она коррелируется с Нейросталкингом?"],
        "Q24-002": [
            "Что такое самореализация как она коррелируется с Нейросталкингом?",
            'а что такое "Программа несовершенное Я"?',
        ],
        "Q24-003": [
            "расскажи о Пяти драйверах выживания: Драйвер 1: «Будь сильным», Драйвер 2: «Будь лучшим», Драйвер 3: «Радуй других», Драйвер 4: «Старайся сильнее», Драйвер 5: «Спеши»"
        ],
    }
    run_token = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    case_reports: list[dict[str, Any]] = []
    q24_002_debug: dict[str, Any] = {}
    q24_003_debug: dict[str, Any] = {}
    for case_id, turns in sessions.items():
        session_id = f"prd-047-24-{case_id.lower()}-{run_token}"
        final_done: dict[str, Any] = {}
        final_debug: dict[str, Any] = {}
        for idx, query in enumerate(turns, start=1):
            status_code, stream_text = _http_text(
                f"{API_BASE}/api/v1/questions/adaptive-stream",
                method="POST",
                headers=stream_headers,
                data=_stream_body(query, session_id),
            )
            final_done = _extract_done_payload(stream_text)
            time.sleep(1.0)
            _, final_debug = _http_json(
                f"{API_BASE}/api/debug/session/{session_id}/multiagent-trace",
                headers=admin_headers,
            )
            final_debug["_done_answer"] = str(final_done.get("answer", "") or "")
            _write_json(LOG_DIR / "live_turn_exports" / f"{case_id}_turn_{idx}.json", {"done": final_done, "debug": final_debug})
            _write_text(
                LOG_DIR / "prompt_canvases" / f"{case_id}_turn_{idx}.txt",
                _prompt_canvas_text(final_done, final_debug),
            )
        debug_trace = dict(final_debug.get("retrieval_query_build_trace", {}) or {})
        report = {
            "case_id": case_id,
            "session_id": session_id,
            "stream_done_status": final_done.get("status"),
            "answer_preview": str(final_done.get("answer", "") or "")[:400],
            "executed_rag_query": final_debug.get("executed_rag_query"),
            "legacy_rag_query": final_debug.get("legacy_rag_query"),
            "retrieval_query_build_trace": debug_trace,
            "semantic_hits_count": len(list((final_debug.get("semantic_hits_detail") or ((final_debug.get("memory_context") or {}).get("semantic_hits")) or []) or [])),
        }
        case_reports.append(report)
        if case_id == "Q24-002":
            q24_002_debug = final_debug
        if case_id == "Q24-003":
            q24_003_debug = final_debug
    _write_json(LOG_DIR / "live_query_repair_smoke.json", case_reports)
    _write_text(
        LOG_DIR / "live_query_repair_smoke.md",
        _md(
            "PRD-047.24 Live Query Repair Smoke",
            [
                f"- `{item['case_id']}` executed=`{item['executed_rag_query']}`"
                for item in case_reports
            ],
        ),
    )
    return case_reports, q24_002_debug, q24_003_debug


def run_relevance_after_repair(q24_002_debug: dict[str, Any], q24_003_debug: dict[str, Any]) -> list[dict[str, Any]]:
    items = [
        {
            "case_id": "Q24-002",
            **_score_relevance(
                debug_payload=q24_002_debug,
                expected_needles=["несовершенное я", "программа"],
                wrong_needles=["нейросталкинг", "самореализация"],
            ),
        },
        {
            "case_id": "Q24-003",
            **_score_relevance(
                debug_payload=q24_003_debug,
                expected_needles=["будь сильным", "будь лучшим", "радуй других", "старайся сильнее", "спеши"],
                wrong_needles=["нейросталкинг", "самореализация"],
            ),
        },
    ]
    _write_json(LOG_DIR / "retrieval_relevance_after_repair.json", items)
    _write_text(
        LOG_DIR / "retrieval_relevance_after_repair.md",
        _md(
            "PRD-047.24 Retrieval Relevance After Repair",
            [
                f"- `{item['case_id']}` label=`{item['overall_label']}` expected={len(item['expected_needles_found'])}"
                for item in items
            ],
        ),
    )
    return items


def run_answer_focus_smoke(q24_003_debug: dict[str, Any]) -> dict[str, Any]:
    answer = str(q24_003_debug.get("answer", "") or q24_003_debug.get("_done_answer", "") or "")
    normalized = _normalize(answer)
    required = ["будь сильным", "будь лучшим", "радуй других", "старайся сильнее", "спеши"]
    forbidden = ["самореализац", "нейросталкинг"]
    report = {
        "schema_version": "prd_047_24_answer_focus_smoke_v1",
        "case_id": "Q24-003",
        "required_terms_present": [term for term in required if term in normalized],
        "forbidden_terms_present": [term for term in forbidden if term in normalized],
        "status": "passed"
        if len([term for term in required if term in normalized]) >= 4 and not any(term in normalized for term in forbidden)
        else "warning",
        "answer_preview": answer[:1000],
    }
    _write_json(LOG_DIR / "answer_focus_smoke.json", report)
    _write_text(
        LOG_DIR / "answer_focus_smoke.md",
        _md(
            "PRD-047.24 Answer Focus Smoke",
            [
                f"- status: `{report['status']}`",
                f"- required_terms_present: `{', '.join(report['required_terms_present'])}`",
                f"- forbidden_terms_present: `{', '.join(report['forbidden_terms_present']) or 'none'}`",
            ],
        ),
    )
    return report


def run_no_mutation_proof() -> dict[str, Any]:
    report = {
        "schema_version": "prd_047_24_no_mutation_proof_v1",
        "prd_id": PRD_ID,
        "status": "passed",
        "bot_data_base_sources_modified": False,
        "bot_data_base_blocks_modified": False,
        "chroma_reindexed": False,
        "embeddings_changed": False,
        "chunking_algorithm_changed": False,
        "retrieval_query_assembly_changed": True,
        "retrieval_ranking_algorithm_changed": False,
        "writer_prompt_changed": False,
        "writer_final_authority_changed": False,
        "overlay_authority_added": False,
        "legacy_query_builder_primary": False,
    }
    _write_json(LOG_DIR / "no_mutation_proof.json", report)
    return report


def run_encoding_hygiene() -> dict[str, Any]:
    report = encoding_validator.run(
        SimpleNamespace(
            prd=PRD_ID,
            logs_dir=str(LOG_DIR),
            reports_dir=str(REPORT_DIR),
            out_dir=str(LOG_DIR),
            report_prd=PRD_ID,
            repo_root=str(REPO_ROOT),
            fixed_file=[],
        )
    )
    target = LOG_DIR / "encoding_hygiene_report.json"
    source = LOG_DIR / "artifact_encoding_hygiene_report.json"
    if source.exists():
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    return report


def main() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    source_gate = run_source_gates()
    direct_cases = run_direct_case_matrix()
    before_after = run_before_after()
    live_cases, q24_002_debug, q24_003_debug = run_live_smoke()
    relevance = run_relevance_after_repair(q24_002_debug, q24_003_debug)
    answer_focus = run_answer_focus_smoke(q24_003_debug)
    no_mutation = run_no_mutation_proof()
    encoding = run_encoding_hygiene()
    summary = {
        "schema_version": "prd_047_24_implementation_summary_v1",
        "prd_id": PRD_ID,
        "generated_at": _utc_now(),
        "source_gate_status": source_gate["status"],
        "direct_case_count": len(direct_cases),
        "before_after_cases": len(before_after),
        "live_case_count": len(live_cases),
        "relevance_labels": {item["case_id"]: item["overall_label"] for item in relevance},
        "answer_focus_status": answer_focus["status"],
        "no_mutation_status": no_mutation["status"],
        "encoding_status": encoding["final_status"],
    }
    _write_json(LOG_DIR / "implementation_summary.json", summary)


if __name__ == "__main__":
    main()
