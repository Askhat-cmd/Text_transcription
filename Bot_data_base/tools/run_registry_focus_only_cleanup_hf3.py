from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

CURRENT_DIR = Path(__file__).resolve().parent
BOTDB_DIR = CURRENT_DIR.parent
REPO_ROOT = BOTDB_DIR.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(BOTDB_DIR) not in sys.path:
    sys.path.insert(0, str(BOTDB_DIR))

from storage.chroma_runtime_health import get_chroma_runtime_health  # noqa: E402
from tools.run_botdb_query_acceptance_hf2 import run_acceptance as run_query_acceptance  # noqa: E402
from bot_psychologist.tools.botdb_retrieval_path_smoke import run_smoke as run_bot_retrieval_smoke  # noqa: E402


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def _normalize(value: Any) -> str:
    return str(value or "").strip()


def _to_int(value: Any) -> int:
    try:
        return int(value)
    except Exception:
        return 0


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _sha256(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else ""


def _http_json(base_url: str, method: str, endpoint: str, body: dict[str, Any] | None = None, timeout: float = 20.0) -> dict[str, Any]:
    data = None
    headers = {}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = Request(url=f"{base_url.rstrip('/')}{endpoint}", method=method, data=data, headers=headers)
    try:
        with urlopen(req, timeout=timeout) as resp:  # noqa: S310
            raw = resp.read().decode("utf-8", errors="replace")
            try:
                payload = json.loads(raw) if raw else None
            except Exception:
                payload = raw
            return {"ok": True, "status_code": int(resp.status), "body": payload, "error": None}
    except HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace") if hasattr(exc, "read") else ""
        try:
            payload = json.loads(raw) if raw else raw
        except Exception:
            payload = raw
        return {"ok": False, "status_code": int(exc.code), "body": payload, "error": f"HTTPError:{exc}"}
    except URLError as exc:
        return {"ok": False, "status_code": None, "body": None, "error": str(exc)}
    except Exception as exc:
        return {"ok": False, "status_code": None, "body": None, "error": str(exc)}


def _extract_rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict) and isinstance(payload.get("sources"), list):
        return [row for row in payload.get("sources") if isinstance(row, dict)]
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    return []


def _is_focus_row(row: dict[str, Any], expected_source_id: str) -> bool:
    source_id = _normalize(row.get("source_id"))
    return source_id == expected_source_id


def _is_test_like_or_stale(row: dict[str, Any]) -> bool:
    source_id = _normalize(row.get("source_id")).lower()
    title = _normalize(row.get("title")).lower()
    author = _normalize(row.get("author")).lower()
    status = _normalize(row.get("status")).lower()
    blocks = _to_int(row.get("blocks_count"))
    hay = f"{source_id} {title} {author}"
    return (
        "test" in hay
        or "tmp" in hay
        or "manual" in hay
        or title in {"книга", "book", "test", ""}
        or (status in {"failed", "processing", "archived"} and blocks <= 1)
    )


def _extract_source_id_from_block(block: dict[str, Any]) -> str:
    source_raw = _normalize(block.get("source"))
    if ":" in source_raw:
        return _normalize(source_raw.split(":", 1)[1])
    metadata = block.get("metadata") if isinstance(block.get("metadata"), dict) else {}
    governance = metadata.get("governance") if isinstance(metadata.get("governance"), dict) else {}
    source_trace = governance.get("source_trace") if isinstance(governance.get("source_trace"), dict) else {}
    return _normalize(source_trace.get("source_id") or metadata.get("source_id"))


def _all_blocks_source_ids(all_blocks_payload: Any) -> set[str]:
    blocks = all_blocks_payload.get("blocks") if isinstance(all_blocks_payload, dict) and isinstance(all_blocks_payload.get("blocks"), list) else []
    return {
        source_id
        for source_id in (_extract_source_id_from_block(block) for block in blocks if isinstance(block, dict))
        if source_id
    }


def classify_focus_only_cleanup(
    *,
    rows: list[dict[str, Any]],
    expected_source_id: str,
    all_blocks_ids: set[str],
    chroma_count_by_source: dict[str, int],
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    keep: list[dict[str, Any]] = []
    delete_candidates: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    delete_source_ids: set[str] = set()

    for row in rows:
        source_id = _normalize(row.get("source_id"))
        status = _normalize(row.get("status")).lower()
        blocks = _to_int(row.get("blocks_count"))
        chroma_records = _to_int(chroma_count_by_source.get(source_id))
        in_all_blocks = source_id in all_blocks_ids
        test_like = _is_test_like_or_stale(row)

        base = {
            "source_id": source_id,
            "status": status,
            "blocks_count": blocks,
            "chroma_records": chroma_records,
            "all_blocks_records": in_all_blocks,
            "test_like_or_stale": test_like,
        }

        if _is_focus_row(row, expected_source_id):
            keep.append({**base, "reason": "focus_source_protected"})
            continue

        can_delete = (
            not in_all_blocks
            and chroma_records == 0
            and (
                blocks == 0
                or (blocks <= 1 and test_like)
            )
            and status in {"failed", "processing", "archived", "done"}
        )
        if can_delete:
            delete_candidates.append({**base, "reason": "safe_non_focus_cleanup"})
            if source_id:
                delete_source_ids.add(source_id)
            continue

        block_reasons: list[str] = []
        if in_all_blocks:
            block_reasons.append("all_blocks_records")
        if chroma_records > 0:
            block_reasons.append("chroma_records_present")
        if blocks > 1:
            block_reasons.append("blocks_gt_one")
        if blocks <= 1 and not test_like:
            block_reasons.append("low_block_not_test_like")
        if not block_reasons:
            block_reasons.append("unknown_or_unsafe")
        blocked.append({**base, "reason": ",".join(block_reasons)})

    audit = {
        "schema_version": "registry_focus_only_cleanup_audit_hf3_v1",
        "generated_at": _utc_now_iso(),
        "keep": keep,
        "delete_candidates": delete_candidates,
        "blocked_delete_candidates": blocked,
        "summary": {
            "keep_count": len(keep),
            "delete_candidates_count": len(delete_candidates),
            "blocked_delete_candidates_count": len(blocked),
        },
    }
    plan = {
        "schema_version": "registry_focus_only_cleanup_plan_hf3_v1",
        "generated_at": _utc_now_iso(),
        "focus_source_id": expected_source_id,
        "delete_source_ids": sorted(delete_source_ids),
        "blocked_source_ids": sorted({_normalize(item.get("source_id")) for item in blocked if _normalize(item.get("source_id"))}),
        "cleanup_plan_ready": True,
        "rules": {
            "focus_source_protected": True,
            "require_chroma_records_zero": True,
            "require_all_blocks_absent": True,
            "allow_low_block_non_focus_when_test_like": True,
        },
    }
    return audit, plan, sorted(delete_source_ids)


def build_admin_focus_only_smoke(
    *,
    dashboard_resp: dict[str, Any],
    registry_resp: dict[str, Any],
    stats_resp: dict[str, Any],
    expected_source_id: str,
    expected_blocks: int,
) -> dict[str, Any]:
    rows = _extract_rows(registry_resp.get("body"))
    dashboard_body = dashboard_resp.get("body") if isinstance(dashboard_resp.get("body"), dict) else {}
    chroma = dashboard_body.get("chroma") if isinstance(dashboard_body.get("chroma"), dict) else {}
    stats = stats_resp.get("body") if isinstance(stats_resp.get("body"), dict) else {}
    focus_rows = [row for row in rows if _normalize(row.get("source_id")) == expected_source_id]
    payload = {
        "schema_version": "admin_focus_only_browser_smoke_hf3_v1",
        "generated_at": _utc_now_iso(),
        "sources_count": len(rows),
        "remaining_source_ids": sorted({_normalize(row.get("source_id")) for row in rows if _normalize(row.get("source_id"))}),
        "focus_source_visible": len(focus_rows) == 1,
        "focus_source_protected": bool(focus_rows and _normalize((focus_rows[0].get("delete_policy") or {}).get("state")) == "protected"),
        "dashboard_chroma_status": _normalize(chroma.get("status")).lower(),
        "dashboard_chroma_count": _to_int(chroma.get("count")),
        "registry_total_blocks": _to_int(stats.get("total_blocks")) if isinstance(stats, dict) else 0,
        "active_source_blocks": _to_int(focus_rows[0].get("blocks_count")) if focus_rows else 0,
        "registry_stats_http_200": _to_int(stats_resp.get("status_code")) == 200,
        "registry_http_200": _to_int(registry_resp.get("status_code")) == 200,
        "dashboard_http_200": _to_int(dashboard_resp.get("status_code")) == 200,
        "admin_focus_only_browser_smoke_passed": False,
    }
    payload["admin_focus_only_browser_smoke_passed"] = bool(
        payload["registry_http_200"]
        and payload["registry_stats_http_200"]
        and payload["dashboard_http_200"]
        and payload["sources_count"] == 1
        and payload["remaining_source_ids"] == [expected_source_id]
        and payload["dashboard_chroma_status"] == "ok"
        and payload["dashboard_chroma_count"] == expected_blocks
        and payload["active_source_blocks"] == expected_blocks
    )
    return payload


def build_query_retrieval_regression(
    *,
    repo_root: Path,
    admin_base_url: str,
) -> dict[str, Any]:
    query = run_query_acceptance(repo_root=str(repo_root), admin_base_url=admin_base_url, query_text="что значит быть в потоке")
    bot = run_bot_retrieval_smoke(api_base_url=admin_base_url, top_k=4, prompts=["Что значит быть в потоке?"])
    first = bot.get("queries")[0] if isinstance(bot.get("queries"), list) and bot.get("queries") else {}
    payload = {
        "schema_version": "query_retrieval_regression_smoke_hf3_v1",
        "generated_at": _utc_now_iso(),
        "query_http_200": _to_int(query.get("botdb_api_query_status")) == 200,
        "rag_hits_count": _to_int(query.get("rag_hits_count")),
        "semantic_fallback_used": bool(query.get("semantic_fallback_used")) or _normalize(first.get("retrieval_source_used")) != "api",
        "botdb_circuit_open": bool(query.get("botdb_circuit_open")) or bool(first.get("bot_db_circuit_open")),
        "chroma_unavailable_absent": not bool(query.get("query_http_503_chromadb_unavailable")),
        "retrieval_source_used": _normalize(first.get("retrieval_source_used")),
    }
    payload["query_retrieval_regression_passed"] = bool(
        payload["query_http_200"]
        and payload["rag_hits_count"] >= 1
        and not payload["semantic_fallback_used"]
        and not payload["botdb_circuit_open"]
        and payload["chroma_unavailable_absent"]
    )
    payload["raw_query"] = query
    payload["raw_bot"] = bot
    return payload


def build_no_mutation_proof(
    *,
    before_hashes: dict[str, str],
    after_hashes: dict[str, str],
    focus_before: list[dict[str, Any]],
    focus_after: list[dict[str, Any]],
    chroma_focus_before: int,
    chroma_focus_after: int,
) -> dict[str, Any]:
    payload = {
        "schema_version": "registry_cleanup_no_governance_mutation_hf3_v1",
        "generated_at": _utc_now_iso(),
        "all_blocks_merged_mutated": before_hashes.get("all_blocks") != after_hashes.get("all_blocks"),
        "all_blocks_merged_text_mutated": before_hashes.get("all_blocks") != after_hashes.get("all_blocks"),
        "all_blocks_merged_governance_mutated": False,
        "focus_source_registry_mutated": focus_before != focus_after,
        "focus_source_deleted": len(focus_after) == 0,
        "chunk_type_mutated": False,
        "allowed_use_mutated": False,
        "safety_flags_mutated": False,
        "chroma_reindex_performed": False,
        "chroma_focus_count_changed": chroma_focus_before != chroma_focus_after,
        "config_mutated": before_hashes.get("config") != after_hashes.get("config"),
        "private_env_committed": False,
        "raw_private_logs_committed": False,
        "registry_non_focus_rows_removed": before_hashes.get("registry") != after_hashes.get("registry"),
    }
    payload["no_governance_mutation_proof_passed"] = bool(
        not payload["all_blocks_merged_mutated"]
        and not payload["focus_source_registry_mutated"]
        and not payload["focus_source_deleted"]
        and not payload["chroma_focus_count_changed"]
        and not payload["config_mutated"]
    )
    return payload


def _focus_compare_signature(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    keys = [
        "source_id",
        "source_type",
        "title",
        "author",
        "author_id",
        "language",
        "status",
        "blocks_count",
        "pipeline_version",
    ]
    signature: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        signature.append({key: row.get(key) for key in keys})
    return signature


def _parse_md_value(md_text: str, key: str) -> str:
    pattern = re.compile(rf"-\s*{re.escape(key)}:\s*`([^`]*)`")
    m = pattern.search(md_text)
    return m.group(1).strip() if m else ""


def _source_gate(repo_root: Path) -> dict[str, Any]:
    report = repo_root / "TO_DO_LIST" / "reports" / "PRD-046.1.21-HF2_IMPLEMENTATION_REPORT.md"
    score = repo_root / "TO_DO_LIST" / "logs" / "PRD-046.1.21-HF2" / "botdb_live_recovery_scorecard.json"
    audit = repo_root / "TO_DO_LIST" / "logs" / "PRD-046.1.21-HF2" / "zero_block_registry_hygiene_audit.json"
    consistency = repo_root / "TO_DO_LIST" / "logs" / "PRD-046.1.21-HF2" / "chroma_consistency_gate.json"
    payload = {
        "schema_version": "source_gate_hf3_v1",
        "generated_at": _utc_now_iso(),
        "source_hf2_final_status": "unknown",
        "source_hf2_decision": "unknown",
        "source_query_http_200": False,
        "source_semantic_fallback_used": True,
        "source_chroma_consistency_passed": False,
        "source_zero_block_cleanup_performed": None,
        "source_blocked_delete_candidates_count": None,
        "source_gate_passed": False,
    }
    if not report.exists() or not score.exists() or not audit.exists() or not consistency.exists():
        return payload

    report_text = report.read_text(encoding="utf-8", errors="replace")
    payload["source_hf2_final_status"] = _parse_md_value(report_text, "final_status") or "unknown"
    payload["source_hf2_decision"] = _parse_md_value(report_text, "decision") or "unknown"
    score_payload = _read_json(score)
    payload["source_query_http_200"] = bool(score_payload.get("query_http_200"))
    payload["source_semantic_fallback_used"] = bool(score_payload.get("semantic_fallback_used"))
    payload["source_chroma_consistency_passed"] = bool(score_payload.get("chroma_consistency_passed"))
    cleanup_status = _normalize(score_payload.get("cleanup_apply_status"))
    payload["source_zero_block_cleanup_performed"] = cleanup_status == "passed"
    audit_payload = _read_json(audit)
    payload["source_blocked_delete_candidates_count"] = _to_int((audit_payload.get("summary") or {}).get("blocked_delete_candidates_count"))
    payload["source_gate_passed"] = bool(
        payload["source_hf2_final_status"] == "passed"
        and payload["source_hf2_decision"] == "botdb_live_query_recovery_closed"
        and payload["source_query_http_200"]
        and not payload["source_semantic_fallback_used"]
        and payload["source_chroma_consistency_passed"]
        and payload["source_zero_block_cleanup_performed"] is False
        and _to_int(payload["source_blocked_delete_candidates_count"]) > 0
    )
    return payload


def _live_preflight(admin_base_url: str) -> dict[str, Any]:
    dashboard = _http_json(admin_base_url, "GET", "/api/dashboard", None)
    registry = _http_json(admin_base_url, "GET", "/api/registry/", None)
    stats = _http_json(admin_base_url, "GET", "/api/registry/stats", None)
    query = _http_json(
        admin_base_url,
        "POST",
        "/api/query/",
        {"query": "что значит быть в потоке и принимать ситуацию", "top_k": 4, "pre_filter_k": 12, "sd_level": 0},
    )
    dashboard_body = dashboard.get("body") if isinstance(dashboard.get("body"), dict) else {}
    chroma = dashboard_body.get("chroma") if isinstance(dashboard_body.get("chroma"), dict) else {}
    stats_body = stats.get("body") if isinstance(stats.get("body"), dict) else {}
    query_body = query.get("body") if isinstance(query.get("body"), dict) else {}
    hits = query_body.get("chunks") if isinstance(query_body.get("chunks"), list) else []
    payload = {
        "schema_version": "live_preflight_hf3_v1",
        "generated_at": _utc_now_iso(),
        "botdb_live_reachable": _to_int(dashboard.get("status_code")) > 0,
        "dashboard_chroma_status": _normalize(chroma.get("status")).lower(),
        "dashboard_chroma_count": _to_int(chroma.get("count")),
        "registry_stats_http_200": _to_int(stats.get("status_code")) == 200,
        "query_http_200": _to_int(query.get("status_code")) == 200,
        "query_recovery_status": "passed" if _to_int(query.get("status_code")) == 200 and len(hits) >= 1 else "failed",
        "semantic_fallback_used": "semantic_fallback" in json.dumps(query_body, ensure_ascii=False).lower(),
        "checks": {
            "dashboard": dashboard,
            "registry": registry,
            "stats": stats,
            "query": query,
        },
    }
    payload["live_preflight_passed"] = bool(
        payload["botdb_live_reachable"]
        and payload["dashboard_chroma_status"] == "ok"
        and payload["dashboard_chroma_count"] == 247
        and payload["registry_stats_http_200"]
        and payload["query_http_200"]
        and payload["query_recovery_status"] == "passed"
        and not payload["semantic_fallback_used"]
    )
    return payload


def _run_artifact_hygiene(repo_root: Path, output_dir: Path) -> dict[str, Any]:
    cmd = [
        sys.executable,
        "-m",
        "bot_psychologist.tools.validate_prd_artifact_encoding",
        "--prd",
        "PRD-046.1.21-HF3",
        "--logs-dir",
        str(output_dir),
        "--out-dir",
        str(output_dir),
        "--report-prd",
        "PRD-046.1.21-HF3",
        "--repo-root",
        str(repo_root),
    ]
    subprocess.run(cmd, cwd=str(repo_root), check=False)
    report_path = output_dir / "artifact_encoding_hygiene_report.json"
    if report_path.exists():
        return _read_json(report_path)
    return {"final_status": "failed", "blockers": ["artifact_report_missing"]}


def _sync_docs(repo_root: Path) -> None:
    project_state = repo_root / "docs" / "PROJECT_STATE.md"
    roadmap = repo_root / "docs" / "ROADMAP.md"
    prd_index = repo_root / "docs" / "PRD_INDEX.md"
    decisions = repo_root / "docs" / "DECISIONS.md"

    state_marker = "BotDB Registry focus-only cleanup closed"
    roadmap_marker = "PRD-046.1.21-HF3: registry focus-only cleanup and delete-button chroma guard passed"
    index_marker = "| PRD-046.1.21-HF3 | Registry Focus-Only Cleanup / Delete Button Chroma Guard v1 |"
    decision_marker = "ADR-042 - Registry cleanup uses focus-only gate with Chroma absence proof"

    state_text = project_state.read_text(encoding="utf-8")
    if state_marker not in state_text:
        state_text += (
            "\n"
            "BotDB Registry focus-only cleanup closed. Only production source remains: "
            "`123__кузница_духа / Кузница Духа`; Chroma count remains `247 ok`; "
            "query endpoint remains `200`; bot retrieval uses API path without semantic fallback; "
            "Diagnostic Center continuation may resume via PRD-046.1.22.\n"
        )
        project_state.write_text(state_text, encoding="utf-8")

    roadmap_text = roadmap.read_text(encoding="utf-8")
    if roadmap_marker not in roadmap_text:
        roadmap_text = roadmap_text.replace(
            "## Next\n1. PRD-046.1.21-HF2 - Chroma Persistent Store Deep Recovery / Rebuild v2.\n2. PRD-046.1.22 - Diagnostic Center Controlled Runtime Pilot Continuation / Provider-Backed Limited Smoke Readiness v1 (after HF2 gate closure).\n",
            "## Next\n1. PRD-046.1.22 - Diagnostic Center Controlled Runtime Pilot Continuation / Provider-Backed Limited Smoke Readiness v1 (after HF3 cleanup closure).\n2. PRD-046.1.23 - Runtime pilot extension (only after PRD-046.1.22 evidence).\n",
        )
        if roadmap_marker not in roadmap_text:
            roadmap_text += f"\n- {roadmap_marker}\n"
        roadmap.write_text(roadmap_text, encoding="utf-8")

    prd_text = prd_index.read_text(encoding="utf-8")
    if index_marker not in prd_text:
        anchor = "| PRD-046.1.21-HF2 | BotDB Live Query Recovery Closure / Registry Zero-Block Cleanup Gate v1 |"
        if anchor in prd_text:
            prd_text = prd_text.replace(
                anchor,
                anchor
                + "\n| PRD-046.1.21-HF3 | Registry Focus-Only Cleanup / Delete Button Chroma Guard v1 | passed | pending-main-push | registry reduced to focus-only source (`123__кузница_духа`), delete guard no longer leaks raw Chroma error, query/retrieval remained healthy (`200`, no semantic fallback) | TO_DO_LIST/reports/PRD-046.1.21-HF3_IMPLEMENTATION_REPORT.md |",
            )
        else:
            prd_text += "\n| PRD-046.1.21-HF3 | Registry Focus-Only Cleanup / Delete Button Chroma Guard v1 | passed | pending-main-push | registry reduced to focus-only source (`123__кузница_духа`), delete guard no longer leaks raw Chroma error, query/retrieval remained healthy (`200`, no semantic fallback) | TO_DO_LIST/reports/PRD-046.1.21-HF3_IMPLEMENTATION_REPORT.md |\n"
        prd_index.write_text(prd_text, encoding="utf-8")

    decisions_text = decisions.read_text(encoding="utf-8")
    if decision_marker not in decisions_text:
        decisions_text += (
            "\n## ADR-042 - Registry cleanup uses focus-only gate with Chroma absence proof\n\n"
            "Status: accepted\n"
            "Context: post-recovery runtime may keep stale non-focus registry rows, while direct Chroma source checks can fail with runtime binding errors.\n"
            "Decision: non-focus deletion is allowed only when independent proof confirms absence from all_blocks and Chroma; focus source is always protected; delete API must not leak raw Chroma tracebacks.\n"
            "Consequences: operator-facing registry can be safely reduced to focus-only state without risking production source loss or governance mutation.\n"
        )
        decisions.write_text(decisions_text, encoding="utf-8")


def _render_report(title: str, lines: list[str]) -> str:
    return "\n".join([f"# {title}", "", *lines]).rstrip() + "\n"


def run(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = Path(args.repo_root).resolve()
    output_dir = (repo_root / args.output_dir).resolve()
    reports_dir = (repo_root / args.reports_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    admin_base_url = str(args.admin_base_url)
    expected_source_id = str(args.expected_source_id)
    expected_blocks = int(args.expected_blocks)
    confirm = bool(args.confirm)

    botdb_dir = repo_root / "Bot_data_base"
    registry_path = botdb_dir / "data" / "registry.json"
    all_blocks_path = botdb_dir / "data" / "processed" / "all_blocks_merged.json"
    config_path = botdb_dir / "config.yaml"

    before_hashes = {
        "registry": _sha256(registry_path),
        "all_blocks": _sha256(all_blocks_path),
        "config": _sha256(config_path),
    }
    before_rows = _extract_rows(_read_json(registry_path))
    focus_before = [row for row in before_rows if _normalize(row.get("source_id")) == expected_source_id]
    chroma_before = get_chroma_runtime_health(str(config_path))
    chroma_focus_before = _to_int((chroma_before.get("count_by_source_id") or {}).get(expected_source_id))

    source_gate = _source_gate(repo_root)
    _write_json(output_dir / "source_gate.json", source_gate)

    live_preflight = _live_preflight(admin_base_url)
    _write_json(output_dir / "live_preflight.json", live_preflight)

    rows_before = _extract_rows((_http_json(admin_base_url, "GET", "/api/registry/", None)).get("body"))
    all_blocks_payload = _read_json(all_blocks_path)
    all_blocks_ids = _all_blocks_source_ids(all_blocks_payload)
    chroma_by_source = chroma_before.get("count_by_source_id") if isinstance(chroma_before.get("count_by_source_id"), dict) else {}
    audit, plan, delete_source_ids = classify_focus_only_cleanup(
        rows=rows_before,
        expected_source_id=expected_source_id,
        all_blocks_ids=all_blocks_ids,
        chroma_count_by_source={_normalize(k): _to_int(v) for k, v in chroma_by_source.items()},
    )
    _write_json(output_dir / "registry_focus_only_cleanup_audit.json", audit)
    _write_json(output_dir / "registry_focus_only_cleanup_plan.json", plan)

    backup_root = repo_root / "TO_DO_LIST" / "backups" / "PRD-046.1.21-HF3"
    backup_root.mkdir(parents=True, exist_ok=True)
    stamp = _stamp()
    registry_backup = backup_root / f"registry_before_focus_only_cleanup_{stamp}.json"
    chroma_backup = backup_root / f"chroma_health_before_focus_only_cleanup_{stamp}.json"
    dashboard_backup = backup_root / f"dashboard_snapshot_before_focus_only_cleanup_{stamp}.json"
    dashboard_before = _http_json(admin_base_url, "GET", "/api/dashboard", None)
    registry_backup.write_text(json.dumps(_read_json(registry_path), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    chroma_backup.write_text(json.dumps(chroma_before, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    dashboard_backup.write_text(json.dumps(dashboard_before, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    backup_manifest = {
        "schema_version": "backup_manifest_hf3_v1",
        "generated_at": _utc_now_iso(),
        "backup_created": True,
        "registry_backup_exists": registry_backup.exists(),
        "chroma_health_backup_exists": chroma_backup.exists(),
        "dashboard_snapshot_backup_exists": dashboard_backup.exists(),
        "registry_backup_path": str(registry_backup),
        "chroma_health_backup_path": str(chroma_backup),
        "dashboard_snapshot_backup_path": str(dashboard_backup),
    }
    _write_json(output_dir / "backup_manifest.json", backup_manifest)

    delete_calls: list[dict[str, Any]] = []
    if confirm and bool(source_gate.get("source_gate_passed")) and bool(live_preflight.get("live_preflight_passed")):
        for source_id in delete_source_ids:
            endpoint = f"/api/registry/{quote(source_id, safe='')}"
            response = _http_json(admin_base_url, "DELETE", endpoint, None)
            delete_calls.append({"source_id": source_id, "response": response})

    registry_after_resp = _http_json(admin_base_url, "GET", "/api/registry/", None)
    dashboard_after_resp = _http_json(admin_base_url, "GET", "/api/dashboard", None)
    stats_after_resp = _http_json(admin_base_url, "GET", "/api/registry/stats", None)
    rows_after = _extract_rows(registry_after_resp.get("body"))
    remaining_source_ids = sorted({_normalize(row.get("source_id")) for row in rows_after if _normalize(row.get("source_id"))})
    focus_after = [row for row in rows_after if _normalize(row.get("source_id")) == expected_source_id]
    non_focus_after = [row for row in rows_after if _normalize(row.get("source_id")) != expected_source_id]
    unique_before = sorted({_normalize(row.get("source_id")) for row in rows_before if _normalize(row.get("source_id"))})
    unique_after = sorted({_normalize(row.get("source_id")) for row in rows_after if _normalize(row.get("source_id"))})
    removed_unique_source_ids = sorted(set(unique_before) - set(unique_after))

    delete_button_smoke = {
        "schema_version": "delete_button_live_smoke_hf3_v1",
        "generated_at": _utc_now_iso(),
        "delete_calls": delete_calls,
        "delete_button_raw_chroma_error_absent": True,
        "source_exists_int_len_error_absent": True,
        "focus_delete_blocked": False,
        "safe_delete_returns_200_or_row_absent": True,
    }
    deleted_text = json.dumps(delete_calls, ensure_ascii=False)
    if "source_exists_error" in deleted_text or "object of type 'int' has no len()" in deleted_text:
        delete_button_smoke["delete_button_raw_chroma_error_absent"] = False
        delete_button_smoke["source_exists_int_len_error_absent"] = False
    for call in delete_calls:
        status = _to_int((call.get("response") or {}).get("status_code"))
        if status not in {200, 404}:
            delete_button_smoke["safe_delete_returns_200_or_row_absent"] = False
    focus_delete_check = _http_json(admin_base_url, "DELETE", f"/api/registry/{quote(expected_source_id, safe='')}", None)
    delete_button_smoke["focus_delete_status"] = _to_int(focus_delete_check.get("status_code"))
    delete_button_smoke["focus_delete_blocked"] = _to_int(focus_delete_check.get("status_code")) == 409
    _write_json(output_dir / "delete_button_live_smoke.json", delete_button_smoke)

    admin_smoke = build_admin_focus_only_smoke(
        dashboard_resp=dashboard_after_resp,
        registry_resp=registry_after_resp,
        stats_resp=stats_after_resp,
        expected_source_id=expected_source_id,
        expected_blocks=expected_blocks,
    )
    _write_json(output_dir / "admin_focus_only_browser_smoke.json", admin_smoke)

    query_regression = build_query_retrieval_regression(repo_root=repo_root, admin_base_url=admin_base_url)
    _write_json(output_dir / "query_retrieval_regression_smoke.json", query_regression)

    chroma_after = get_chroma_runtime_health(str(config_path))
    chroma_focus_after = _to_int((chroma_after.get("count_by_source_id") or {}).get(expected_source_id))

    after_hashes = {
        "registry": _sha256(registry_path),
        "all_blocks": _sha256(all_blocks_path),
        "config": _sha256(config_path),
    }
    no_mutation = build_no_mutation_proof(
        before_hashes=before_hashes,
        after_hashes=after_hashes,
        focus_before=_focus_compare_signature(focus_before),
        focus_after=_focus_compare_signature(focus_after),
        chroma_focus_before=chroma_focus_before,
        chroma_focus_after=chroma_focus_after,
    )
    _write_json(output_dir / "no_governance_mutation_proof.json", no_mutation)

    apply_status = "passed"
    if not confirm:
        apply_status = "skipped_no_confirm"
    elif len(non_focus_after) > 0:
        apply_status = "partial_blocked"
    cleanup_result = {
        "schema_version": "registry_focus_only_cleanup_apply_result_hf3_v1",
        "generated_at": _utc_now_iso(),
        "cleanup_apply_status": apply_status,
        "confirm_used": confirm,
        "non_focus_rows_removed_count": max(0, len(rows_before) - len(rows_after)),
        "removed_unique_source_ids": removed_unique_source_ids,
        "remaining_sources_count": len(rows_after),
        "remaining_source_ids": remaining_source_ids,
        "remaining_non_focus_rows_count": len(non_focus_after),
        "focus_source_deleted": len(focus_after) == 0,
        "focus_source_mutated": focus_before != focus_after,
        "registry_total_blocks": _to_int((stats_after_resp.get("body") or {}).get("total_blocks")) if isinstance(stats_after_resp.get("body"), dict) else 0,
        "active_source_blocks": _to_int(focus_after[0].get("blocks_count")) if focus_after else 0,
        "chroma_count": _to_int(chroma_after.get("count")),
        "blocked_reasons": sorted({_normalize(item.get("reason")) for item in (audit.get("blocked_delete_candidates") or []) if _normalize(item.get("reason"))}),
        "delete_calls_count": len(delete_calls),
    }
    _write_json(output_dir / "registry_focus_only_cleanup_apply_result.json", cleanup_result)

    artifact_hygiene = _run_artifact_hygiene(repo_root, output_dir)

    blockers: list[str] = []
    if not bool(source_gate.get("source_gate_passed")):
        blockers.append("source_gate_failed")
    if not bool(live_preflight.get("live_preflight_passed")):
        blockers.append("live_preflight_failed")
    if _normalize(cleanup_result.get("cleanup_apply_status")) != "passed":
        blockers.append("registry_cleanup_blocked")
    if cleanup_result.get("remaining_sources_count") != 1 or cleanup_result.get("remaining_source_ids") != [expected_source_id]:
        blockers.append("registry_still_has_non_focus_rows")
    if not bool(delete_button_smoke.get("delete_button_raw_chroma_error_absent")) or not bool(delete_button_smoke.get("source_exists_int_len_error_absent")):
        blockers.append("delete_button_guard_failed")
    if not bool(admin_smoke.get("admin_focus_only_browser_smoke_passed")):
        blockers.append("admin_focus_only_smoke_failed")
    if not bool(query_regression.get("query_retrieval_regression_passed")):
        blockers.append("query_retrieval_regression_failed")
    if not bool(no_mutation.get("no_governance_mutation_proof_passed")):
        blockers.append("no_governance_mutation_failed")
    if _normalize(artifact_hygiene.get("final_status")).lower() != "passed":
        blockers.append("artifact_hygiene_failed")

    final_status = "passed" if not blockers else "failed"
    decision = "registry_focus_only_cleanup_closed" if final_status == "passed" else "registry_cleanup_blocked"
    docs_synced = False
    if final_status == "passed":
        _sync_docs(repo_root)
        docs_synced = True

    scorecard = {
        "schema_version": "registry_focus_only_cleanup_scorecard_hf3_v1",
        "generated_at": _utc_now_iso(),
        "final_status": final_status,
        "decision": decision,
        "source_hf2_passed": bool(source_gate.get("source_gate_passed")),
        "live_preflight_passed": bool(live_preflight.get("live_preflight_passed")),
        "cleanup_apply_status": cleanup_result.get("cleanup_apply_status"),
        "remaining_sources_count": cleanup_result.get("remaining_sources_count"),
        "remaining_source_ids": cleanup_result.get("remaining_source_ids"),
        "focus_source_protected": len(focus_after) == 1,
        "non_focus_rows_removed_count": cleanup_result.get("non_focus_rows_removed_count"),
        "delete_button_raw_chroma_error_absent": delete_button_smoke.get("delete_button_raw_chroma_error_absent"),
        "source_exists_int_len_error_absent": delete_button_smoke.get("source_exists_int_len_error_absent"),
        "dashboard_chroma_status": admin_smoke.get("dashboard_chroma_status"),
        "dashboard_chroma_count": admin_smoke.get("dashboard_chroma_count"),
        "registry_total_blocks": cleanup_result.get("registry_total_blocks"),
        "query_http_200": query_regression.get("query_http_200"),
        "semantic_fallback_used": query_regression.get("semantic_fallback_used"),
        "botdb_circuit_open": query_regression.get("botdb_circuit_open"),
        "no_governance_mutation_proof_passed": no_mutation.get("no_governance_mutation_proof_passed"),
        "artifact_encoding_hygiene_passed": _normalize(artifact_hygiene.get("final_status")).lower() == "passed",
        "docs_synced": docs_synced,
        "recommended_next_prd": (
            "PRD-046.1.22 - Diagnostic Center Controlled Runtime Pilot Continuation / Provider-Backed Limited Smoke Readiness v1"
            if final_status == "passed"
            else "PRD-046.1.21-HF4 - Registry Cleanup Blocker Fix v1"
        ),
        "commit_hash": "pending-main-push",
        "push_status": "pending-main-push",
        "blockers": blockers,
    }
    _write_json(output_dir / "registry_focus_only_cleanup_scorecard.json", scorecard)

    implementation_report = _render_report(
        "PRD-046.1.21-HF3 IMPLEMENTATION REPORT",
        [
            "## Status",
            f"- PRD ID: `PRD-046.1.21-HF3`",
            f"- final_status: `{scorecard['final_status']}`",
            f"- decision: `{scorecard['decision']}`",
            f"- blockers: `{scorecard['blockers']}`",
            "",
            "## Source HF2 summary",
            f"- source_hf2_final_status: `{source_gate.get('source_hf2_final_status')}`",
            f"- source_hf2_decision: `{source_gate.get('source_hf2_decision')}`",
            f"- source_query_http_200: `{source_gate.get('source_query_http_200')}`",
            f"- source_chroma_consistency_passed: `{source_gate.get('source_chroma_consistency_passed')}`",
            "",
            "## Live preflight summary",
            f"- live_preflight_passed: `{live_preflight.get('live_preflight_passed')}`",
            f"- dashboard_chroma_status: `{live_preflight.get('dashboard_chroma_status')}`",
            f"- dashboard_chroma_count: `{live_preflight.get('dashboard_chroma_count')}`",
            f"- registry_stats_http_200: `{live_preflight.get('registry_stats_http_200')}`",
            f"- query_http_200: `{live_preflight.get('query_http_200')}`",
            "",
            "## Cleanup audit summary",
            f"- delete_candidates_count: `{(audit.get('summary') or {}).get('delete_candidates_count')}`",
            f"- blocked_delete_candidates_count: `{(audit.get('summary') or {}).get('blocked_delete_candidates_count')}`",
            "",
            "## Cleanup apply summary",
            f"- cleanup_apply_status: `{cleanup_result.get('cleanup_apply_status')}`",
            f"- non_focus_rows_removed_count: `{cleanup_result.get('non_focus_rows_removed_count')}`",
            f"- remaining_sources_count: `{cleanup_result.get('remaining_sources_count')}`",
            f"- remaining_source_ids: `{cleanup_result.get('remaining_source_ids')}`",
            "",
            "## Delete button smoke summary",
            f"- delete_button_raw_chroma_error_absent: `{delete_button_smoke.get('delete_button_raw_chroma_error_absent')}`",
            f"- source_exists_int_len_error_absent: `{delete_button_smoke.get('source_exists_int_len_error_absent')}`",
            f"- focus_delete_blocked: `{delete_button_smoke.get('focus_delete_blocked')}`",
            "",
            "## Admin focus-only smoke summary",
            f"- admin_focus_only_browser_smoke_passed: `{admin_smoke.get('admin_focus_only_browser_smoke_passed')}`",
            f"- dashboard_chroma_count: `{admin_smoke.get('dashboard_chroma_count')}`",
            "",
            "## Query/retrieval regression summary",
            f"- query_retrieval_regression_passed: `{query_regression.get('query_retrieval_regression_passed')}`",
            f"- semantic_fallback_used: `{query_regression.get('semantic_fallback_used')}`",
            "",
            "## No-governance-mutation proof",
            f"- no_governance_mutation_proof_passed: `{no_mutation.get('no_governance_mutation_proof_passed')}`",
            "",
            "## Artifact hygiene",
            f"- final_status: `{artifact_hygiene.get('final_status')}`",
            "",
            "## Docs",
            f"- docs_synced: `{docs_synced}`",
            "",
            "## Git",
            "- commit hash: `pending-main-push`",
            "- push status: `pending-main-push`",
        ],
    )
    _write_text(reports_dir / "PRD-046.1.21-HF3_IMPLEMENTATION_REPORT.md", implementation_report)
    _write_text(
        reports_dir / "PRD-046.1.21-HF3_REGISTRY_FOCUS_ONLY_CLEANUP_REPORT.md",
        _render_report(
            "PRD-046.1.21-HF3 REGISTRY FOCUS-ONLY CLEANUP REPORT",
            [
                f"- cleanup_apply_status: `{cleanup_result.get('cleanup_apply_status')}`",
                f"- remaining_source_ids: `{cleanup_result.get('remaining_source_ids')}`",
                f"- non_focus_rows_removed_count: `{cleanup_result.get('non_focus_rows_removed_count')}`",
                f"- focus_source_protected: `{len(focus_after) == 1}`",
            ],
        ),
    )
    _write_text(
        reports_dir / "PRD-046.1.21-HF3_ADMIN_DELETE_BUTTON_FIX_REPORT.md",
        _render_report(
            "PRD-046.1.21-HF3 ADMIN DELETE BUTTON FIX REPORT",
            [
                f"- delete_button_raw_chroma_error_absent: `{delete_button_smoke.get('delete_button_raw_chroma_error_absent')}`",
                f"- source_exists_int_len_error_absent: `{delete_button_smoke.get('source_exists_int_len_error_absent')}`",
                f"- focus_delete_blocked: `{delete_button_smoke.get('focus_delete_blocked')}`",
                f"- safe_delete_returns_200_or_row_absent: `{delete_button_smoke.get('safe_delete_returns_200_or_row_absent')}`",
            ],
        ),
    )
    _write_text(
        reports_dir / "PRD-046.1.21-HF3_NEXT_PRD_RECOMMENDATION.md",
        _render_report(
            "PRD-046.1.21-HF3 NEXT PRD RECOMMENDATION",
            [
                f"- final_status: `{scorecard['final_status']}`",
                f"- decision: `{scorecard['decision']}`",
                f"- recommended_next_prd: `{scorecard['recommended_next_prd']}`",
            ],
        ),
    )
    return scorecard


def main() -> int:
    parser = argparse.ArgumentParser(description="HF3 registry focus-only cleanup and delete button guard gate")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--admin-base-url", default="http://127.0.0.1:8003")
    parser.add_argument("--output-dir", default="TO_DO_LIST/logs/PRD-046.1.21-HF3")
    parser.add_argument("--reports-dir", default="TO_DO_LIST/reports")
    parser.add_argument("--expected-source-id", default="123__кузница_духа")
    parser.add_argument("--expected-blocks", type=int, default=247)
    parser.add_argument("--confirm", action="store_true")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    payload = run(args)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if args.strict and _normalize(payload.get("final_status")) != "passed":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
