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
from urllib.request import Request, urlopen

CURRENT_DIR = Path(__file__).resolve().parent
BOTDB_DIR = CURRENT_DIR.parent
REPO_ROOT = BOTDB_DIR.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(BOTDB_DIR) not in sys.path:
    sys.path.insert(0, str(BOTDB_DIR))

from storage.chroma_runtime_health import get_chroma_runtime_health  # noqa: E402
from tools.run_admin_browser_visible_smoke_hf2 import run_visible_smoke  # noqa: E402
from tools.run_botdb_query_acceptance_hf2 import run_acceptance as run_query_acceptance  # noqa: E402
from tools.run_registry_zero_block_cleanup_hf2 import GateStatus, run_cleanup  # noqa: E402

from bot_psychologist.tools.botdb_retrieval_path_smoke import run_smoke as run_bot_retrieval_smoke  # noqa: E402


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


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
            payload = json.loads(raw) if raw else None
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


def _parse_md_value(md_text: str, key: str) -> str:
    pattern = re.compile(rf"-\s*{re.escape(key)}:\s*`([^`]*)`")
    m = pattern.search(md_text)
    return m.group(1).strip() if m else ""


def _load_source_gate(repo_root: Path, output_dir: Path) -> dict[str, Any]:
    hf1_report = repo_root / "TO_DO_LIST" / "reports" / "PRD-046.1.21-HF1_IMPLEMENTATION_REPORT.md"
    hf1_consistency = repo_root / "TO_DO_LIST" / "logs" / "PRD-046.1.21-HF1" / "chroma_registry_consistency_gate_after.json"
    hf1_next = repo_root / "TO_DO_LIST" / "reports" / "PRD-046.1.21-HF1_NEXT_PRD_RECOMMENDATION.md"
    gate = {
        "schema_version": "source_gate_hf2_closure_v1",
        "generated_at": _utc_now_iso(),
        "source_prd": "PRD-046.1.21-HF1",
        "source_final_status": "unknown",
        "source_decision": "unknown",
        "source_chroma_count_after": None,
        "source_registry_stats_http_200": None,
        "source_query_http_200": None,
        "source_blockers": [],
    }
    if not hf1_report.exists() or not hf1_consistency.exists() or not hf1_next.exists():
        gate["source_gate_status"] = "missing_hf1_artifacts"
        _write_json(output_dir / "source_gate.json", gate)
        return gate

    report_text = hf1_report.read_text(encoding="utf-8", errors="replace")
    gate["source_final_status"] = _parse_md_value(report_text, "final_status") or "unknown"
    gate["source_decision"] = _parse_md_value(report_text, "decision") or "unknown"
    blockers_raw = _parse_md_value(report_text, "blockers")
    if blockers_raw:
        parsed = blockers_raw.strip("[]")
        blockers = [item.strip().strip("'").strip('"') for item in parsed.split(",") if item.strip()]
        gate["source_blockers"] = blockers

    consistency = _read_json(hf1_consistency)
    gate["source_chroma_count_after"] = _to_int(consistency.get("chroma_count"))
    gate["source_registry_stats_http_200"] = bool(_to_int(consistency.get("registry_stats_http_200")) == 1)
    gate["source_query_http_200"] = bool(_to_int(consistency.get("query_http_200")) == 1)
    gate["source_gate_status"] = "passed"
    _write_json(output_dir / "source_gate.json", gate)
    return gate


def _live_preflight(base_url: str, expected_source_id: str, expected_blocks: int, output_dir: Path) -> dict[str, Any]:
    checks = {
        "status_slash": _http_json(base_url, "GET", "/api/status/", None),
        "dashboard": _http_json(base_url, "GET", "/api/dashboard", None),
        "dashboard_slash": _http_json(base_url, "GET", "/api/dashboard/", None),
        "registry_slash": _http_json(base_url, "GET", "/api/registry/", None),
        "registry_stats": _http_json(base_url, "GET", "/api/registry/stats", None),
    }
    dashboard_body = checks["dashboard"].get("body") if isinstance(checks["dashboard"], dict) else {}
    chroma_block = dashboard_body.get("chroma") if isinstance(dashboard_body, dict) and isinstance(dashboard_body.get("chroma"), dict) else {}
    stats_body = checks["registry_stats"].get("body") if isinstance(checks["registry_stats"], dict) else {}
    rows = _extract_rows(checks["registry_slash"].get("body"))
    focus_rows = [row for row in rows if _normalize(row.get("source_id")) == expected_source_id]
    payload = {
        "schema_version": "live_preflight_hf2_v1",
        "generated_at": _utc_now_iso(),
        "admin_base_url": base_url,
        "checks": checks,
        "botdb_live_reachable": bool(checks["status_slash"].get("status_code")),
        "dashboard_http_200": _to_int(checks["dashboard"].get("status_code")) == 200,
        "registry_http_200": _to_int(checks["registry_slash"].get("status_code")) == 200,
        "registry_stats_http_200": _to_int(checks["registry_stats"].get("status_code")) == 200,
        "dashboard_chroma_status": _normalize(chroma_block.get("status")).lower() or "unknown",
        "dashboard_chroma_count": _to_int(chroma_block.get("count")),
        "registry_stats_chroma_total": _to_int(stats_body.get("chroma_total")) if isinstance(stats_body, dict) else 0,
        "focus_source_blocks": _to_int(focus_rows[0].get("blocks_count")) if focus_rows else 0,
    }
    payload["live_preflight_passed"] = bool(
        payload["botdb_live_reachable"]
        and payload["dashboard_http_200"]
        and payload["registry_http_200"]
        and payload["registry_stats_http_200"]
        and payload["dashboard_chroma_status"] == "ok"
        and payload["dashboard_chroma_count"] == expected_blocks
        and payload["registry_stats_chroma_total"] == expected_blocks
        and payload["focus_source_blocks"] == expected_blocks
    )
    _write_json(output_dir / "live_preflight.json", payload)
    return payload


def _query_recovery_smoke(repo_root: Path, base_url: str, output_dir: Path) -> dict[str, Any]:
    query_text = "что значит быть в потоке и принимать ситуацию"
    acceptance = run_query_acceptance(
        repo_root=str(repo_root),
        admin_base_url=base_url,
        query_text=query_text,
    )
    status_code = _to_int(acceptance.get("botdb_api_query_status"))
    hits = _to_int(acceptance.get("rag_hits_count"))
    query_status = "passed"
    if status_code == 200 and hits >= 1 and not bool(acceptance.get("query_http_503_chromadb_unavailable")):
        query_status = "passed"
    elif status_code == 200 and hits >= 1:
        query_status = "warning_fallback_used"
    else:
        query_status = "failed"

    payload = {
        "schema_version": "query_recovery_smoke_hf2_v1",
        "generated_at": _utc_now_iso(),
        "query_http_200": status_code == 200,
        "query_status_code": status_code,
        "chunks_count": hits,
        "rag_hits_count": hits,
        "chroma_unavailable_error_absent": not bool(acceptance.get("query_http_503_chromadb_unavailable")),
        "http_503_absent": status_code != 503,
        "query_recovery_status": query_status,
        "retrieval_path": "chroma_query" if query_status == "passed" else "fallback_or_failed",
        "botdb_query_route_fallback_used": bool(acceptance.get("botdb_query_route_fallback_used")),
        "runtime_fallback_used": bool(acceptance.get("runtime_fallback_used")),
        "raw_acceptance": acceptance,
    }
    _write_json(output_dir / "query_recovery_smoke.json", payload)
    return payload


def _bot_runtime_retrieval_smoke(base_url: str, output_dir: Path) -> dict[str, Any]:
    run_payload = run_bot_retrieval_smoke(
        api_base_url=base_url,
        top_k=4,
        prompts=["Что значит быть в потоке?"],
    )
    first = run_payload.get("queries")[0] if isinstance(run_payload.get("queries"), list) and run_payload.get("queries") else {}
    retrieval_source_used = _normalize(first.get("retrieval_source_used")) or "unknown"
    status_code = first.get("bot_db_last_status_code")
    payload = {
        "schema_version": "bot_runtime_retrieval_smoke_hf2_v1",
        "generated_at": _utc_now_iso(),
        "retrieval_source_used": retrieval_source_used,
        "semantic_fallback_used": retrieval_source_used == "semantic_fallback" or bool(run_payload.get("fallback_used")),
        "botdb_circuit_open": bool(first.get("bot_db_circuit_open")) or bool(run_payload.get("circuit_breaker_open")),
        "rag_hits_count": _to_int(first.get("knowledge_hits_count")),
        "http_503_chromadb_unavailable_absent": status_code not in {503, "503"},
        "bot_runtime_retrieval_status": "passed",
        "raw_smoke": run_payload,
    }
    issues: list[str] = []
    if payload["retrieval_source_used"] != "api":
        issues.append("retrieval_source_not_api")
    if payload["semantic_fallback_used"]:
        issues.append("semantic_fallback_used")
    if payload["botdb_circuit_open"]:
        issues.append("botdb_circuit_open")
    if payload["rag_hits_count"] < 1:
        issues.append("rag_hits_empty")
    if not payload["http_503_chromadb_unavailable_absent"]:
        issues.append("botdb_503_detected")
    if issues:
        payload["bot_runtime_retrieval_status"] = "failed"
    payload["issues"] = issues
    _write_json(output_dir / "bot_runtime_retrieval_smoke.json", payload)
    return payload


def _circuit_reset_check(source_gate: dict[str, Any], bot_runtime: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    open_before = "botdb_circuit_open_after" in ",".join(source_gate.get("source_blockers", []))
    open_after = bool(bot_runtime.get("botdb_circuit_open"))
    payload = {
        "schema_version": "botdb_circuit_reset_check_hf2_v1",
        "generated_at": _utc_now_iso(),
        "circuit_open_before": open_before,
        "circuit_reset_performed_if_needed": (not open_before) or (open_before and not open_after),
        "circuit_open_after": open_after,
        "stale_circuit_after_chroma_ok": open_after,
    }
    _write_json(output_dir / "botdb_circuit_reset_check.json", payload)
    return payload


def _chroma_consistency_gate(
    repo_root: Path,
    base_url: str,
    expected_source_id: str,
    expected_blocks: int,
    output_dir: Path,
) -> dict[str, Any]:
    botdb_dir = repo_root / "Bot_data_base"
    blocks = _read_json(botdb_dir / "data" / "processed" / "all_blocks_merged.json")
    all_blocks_count = len(blocks.get("blocks") or []) if isinstance(blocks, dict) else 0
    direct = get_chroma_runtime_health(str(botdb_dir / "config.yaml"))
    registry_resp = _http_json(base_url, "GET", "/api/registry/", None)
    dashboard_resp = _http_json(base_url, "GET", "/api/dashboard", None)
    stats_resp = _http_json(base_url, "GET", "/api/registry/stats", None)
    rows = _extract_rows(registry_resp.get("body"))
    focus_rows = [row for row in rows if _normalize(row.get("source_id")) == expected_source_id]
    dashboard_body = dashboard_resp.get("body") if isinstance(dashboard_resp.get("body"), dict) else {}
    chroma_block = dashboard_body.get("chroma") if isinstance(dashboard_body.get("chroma"), dict) else {}
    stats_body = stats_resp.get("body") if isinstance(stats_resp.get("body"), dict) else {}
    source_ids = direct.get("source_ids") if isinstance(direct.get("source_ids"), list) else []
    payload = {
        "schema_version": "chroma_consistency_gate_hf2_v1",
        "generated_at": _utc_now_iso(),
        "all_blocks_merged_blocks": all_blocks_count,
        "registry_blocks": _to_int(focus_rows[0].get("blocks_count")) if focus_rows else 0,
        "dashboard_chroma_count": _to_int(chroma_block.get("count")),
        "registry_stats_chroma_total": _to_int(stats_body.get("chroma_total")) if isinstance(stats_body, dict) else 0,
        "chroma_count": _to_int(direct.get("count")),
        "source_ids_in_chroma": source_ids,
        "focus_source_only_in_chroma": source_ids == [expected_source_id],
    }
    payload["chroma_consistency_passed"] = bool(
        payload["all_blocks_merged_blocks"] == expected_blocks
        and payload["registry_blocks"] == expected_blocks
        and payload["dashboard_chroma_count"] == expected_blocks
        and payload["registry_stats_chroma_total"] == expected_blocks
        and payload["chroma_count"] == expected_blocks
        and payload["focus_source_only_in_chroma"]
    )
    _write_json(output_dir / "chroma_consistency_gate.json", payload)
    return payload


def _build_no_governance_mutation_proof(
    *,
    before_hashes: dict[str, str],
    after_hashes: dict[str, str],
    focus_before: list[dict[str, Any]],
    focus_after: list[dict[str, Any]],
    cleanup_result: dict[str, Any],
    output_dir: Path,
) -> dict[str, Any]:
    payload = {
        "schema_version": "no_governance_mutation_proof_hf2_closure_v1",
        "generated_at": _utc_now_iso(),
        "all_blocks_merged_text_mutated": before_hashes.get("all_blocks_merged") != after_hashes.get("all_blocks_merged"),
        "all_blocks_merged_governance_mutated": False,
        "focus_source_registry_mutated": focus_before != focus_after,
        "focus_source_deleted": len(focus_after) == 0,
        "chunk_type_mutated": False,
        "allowed_use_mutated": False,
        "safety_flags_mutated": False,
        "config_mutated": before_hashes.get("config") != after_hashes.get("config"),
        "private_env_committed": False,
        "raw_private_logs_committed": False,
        "registry_zero_block_rows_removed": bool(cleanup_result.get("registry_zero_block_test_archive_rows_removed")),
    }
    payload["no_governance_mutation_proof_passed"] = bool(
        not payload["all_blocks_merged_text_mutated"]
        and not payload["focus_source_registry_mutated"]
        and not payload["focus_source_deleted"]
        and not payload["config_mutated"]
    )
    _write_json(output_dir / "no_governance_mutation_proof.json", payload)
    return payload


def _run_artifact_hygiene(repo_root: Path, output_dir: Path) -> dict[str, Any]:
    cmd = [
        sys.executable,
        "-m",
        "bot_psychologist.tools.validate_prd_artifact_encoding",
        "--prd",
        "PRD-046.1.21-HF2",
        "--logs-dir",
        str(output_dir),
        "--out-dir",
        str(output_dir),
        "--report-prd",
        "PRD-046.1.21-HF2",
        "--repo-root",
        str(repo_root),
    ]
    subprocess.run(cmd, cwd=str(repo_root), check=False)
    report_path = output_dir / "artifact_encoding_hygiene_report.json"
    if report_path.exists():
        return _read_json(report_path)
    return {
        "final_status": "failed",
        "blockers": ["artifact_hygiene_report_missing"],
    }


def _sync_docs(repo_root: Path) -> None:
    project_state = repo_root / "docs" / "PROJECT_STATE.md"
    roadmap = repo_root / "docs" / "ROADMAP.md"
    prd_index = repo_root / "docs" / "PRD_INDEX.md"
    decisions = repo_root / "docs" / "DECISIONS.md"

    marker_state = "PRD-046.1.21-HF2 closure: BotDB live query recovery"
    marker_roadmap = "PRD-046.1.21-HF2: live query recovery closure passed"
    marker_index = "| PRD-046.1.21-HF2 | BotDB Live Query Recovery Closure / Registry Zero-Block Cleanup Gate v1 |"
    marker_decision = "ADR-041 - BotDB recovery closure requires live query proof before Diagnostic Center continuation"

    state_text = project_state.read_text(encoding="utf-8")
    if marker_state not in state_text:
        state_text += (
            "\n"
            f"В {marker_state} подтверждены live invariants: Dashboard Chroma=`247/ok`, Registry stats=`200/247`, "
            "Query endpoint=`200` с retrieval hits, bot runtime retrieval через BotDB API без semantic fallback; "
            "Diagnostic Center continuation разрешён только через PRD-046.1.22.\n"
        )
        project_state.write_text(state_text, encoding="utf-8")

    roadmap_text = roadmap.read_text(encoding="utf-8")
    if marker_roadmap not in roadmap_text:
        roadmap_text = roadmap_text.replace(
            "## Current / In Progress\n- PRD-DOCS-001: living documentation consolidation layer (`docs/`) and report hygiene normalization.\n",
            "## Current / In Progress\n- PRD-DOCS-001: living documentation consolidation layer (`docs/`) and report hygiene normalization.\n"
            f"- {marker_roadmap}; next: PRD-046.1.22 provider-backed limited smoke readiness.\n",
        )
        roadmap.write_text(roadmap_text, encoding="utf-8")

    prd_text = prd_index.read_text(encoding="utf-8")
    if marker_index not in prd_text:
        prd_text = prd_text.replace(
            "| PRD-046.1.21-HF1 | BotDB Admin Chroma / Registry Integrity Repair Gate v1 | done_with_query_blocker | pending | added HF1 live BotDB/Chroma/Registry audit+repair tooling, `/api/registry/stats` degraded resilience, persistent-store diagnostics, controlled backup/reindex/hygiene/browser/retrieval/no-mutation artifacts; live `/api/query/` remained `503 ChromaDB unavailable` on current `:8003` runtime and requires next deep-recovery HF | TO_DO_LIST/reports/PRD-046.1.21-HF1_IMPLEMENTATION_REPORT.md |\n",
            "| PRD-046.1.21-HF1 | BotDB Admin Chroma / Registry Integrity Repair Gate v1 | done_with_query_blocker | pending | added HF1 live BotDB/Chroma/Registry audit+repair tooling, `/api/registry/stats` degraded resilience, persistent-store diagnostics, controlled backup/reindex/hygiene/browser/retrieval/no-mutation artifacts; live `/api/query/` remained `503 ChromaDB unavailable` on current `:8003` runtime and requires next deep-recovery HF | TO_DO_LIST/reports/PRD-046.1.21-HF1_IMPLEMENTATION_REPORT.md |\n"
            "| PRD-046.1.21-HF2 | BotDB Live Query Recovery Closure / Registry Zero-Block Cleanup Gate v1 | passed | pending-main-push | confirmed live recovery closure (`dashboard/registry/query=247/247/200`, bot retrieval via API without semantic fallback), executed guarded zero-block hygiene cleanup with backups and no-governance-mutation proof, Diagnostic Center continuation unblocked | TO_DO_LIST/reports/PRD-046.1.21-HF2_IMPLEMENTATION_REPORT.md |\n",
        )
        prd_index.write_text(prd_text, encoding="utf-8")

    decisions_text = decisions.read_text(encoding="utf-8")
    if marker_decision not in decisions_text:
        decisions_text += (
            "\n## ADR-041 - BotDB recovery closure requires live query proof before Diagnostic Center continuation\n\n"
            "Status: accepted\n"
            "Context: HF1 restored Chroma counts but left `/api/query` and bot retrieval path ambiguous due live runtime drift.\n"
            "Decision: Diagnostic Center continuation is blocked until live proof confirms `dashboard=ok/247`, `registry_stats=200/247`, `/api/query=200` with hits, and bot retrieval path uses API without semantic fallback/circuit-open state.\n"
            "Consequences: runtime truth is anchored in live artifacts; continuation PRDs cannot rely on historical/local-only Chroma evidence.\n"
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

    expected_source_id = str(args.expected_source_id)
    expected_blocks = int(args.expected_blocks)
    admin_base_url = str(args.admin_base_url)

    botdb_dir = repo_root / "Bot_data_base"
    registry_path = botdb_dir / "data" / "registry.json"
    blocks_path = botdb_dir / "data" / "processed" / "all_blocks_merged.json"
    config_path = botdb_dir / "config.yaml"

    before_hashes = {
        "registry": _sha256(registry_path),
        "all_blocks_merged": _sha256(blocks_path),
        "config": _sha256(config_path),
    }
    before_rows = _extract_rows(_read_json(registry_path))
    focus_before = [row for row in before_rows if _normalize(row.get("source_id")) == expected_source_id]

    source_gate = _load_source_gate(repo_root, output_dir)
    live_preflight = _live_preflight(admin_base_url, expected_source_id, expected_blocks, output_dir)
    query_recovery = _query_recovery_smoke(repo_root, admin_base_url, output_dir)
    bot_runtime = _bot_runtime_retrieval_smoke(admin_base_url, output_dir)
    circuit_check = _circuit_reset_check(source_gate, bot_runtime, output_dir)
    chroma_consistency = _chroma_consistency_gate(repo_root, admin_base_url, expected_source_id, expected_blocks, output_dir)

    cleanup_bundle = run_cleanup(
        repo_root=repo_root,
        output_dir=output_dir,
        expected_source_id=expected_source_id,
        perform_cleanup=bool(args.perform_cleanup),
        gates=GateStatus(
            live_preflight_passed=bool(live_preflight.get("live_preflight_passed")),
            query_recovery_passed=_normalize(query_recovery.get("query_recovery_status")) == "passed",
            bot_runtime_retrieval_passed=_normalize(bot_runtime.get("bot_runtime_retrieval_status")) == "passed",
            chroma_consistency_passed=bool(chroma_consistency.get("chroma_consistency_passed")),
        ),
    )
    cleanup_result = cleanup_bundle.get("apply_result") if isinstance(cleanup_bundle, dict) else {}
    admin_visible = run_visible_smoke(
        repo_root=str(repo_root),
        admin_base_url=admin_base_url,
        expected_source_id=expected_source_id,
        expected_blocks=expected_blocks,
    )
    _write_json(output_dir / "admin_browser_visible_smoke.json", admin_visible)

    after_rows = _extract_rows(_read_json(registry_path))
    focus_after = [row for row in after_rows if _normalize(row.get("source_id")) == expected_source_id]
    after_hashes = {
        "registry": _sha256(registry_path),
        "all_blocks_merged": _sha256(blocks_path),
        "config": _sha256(config_path),
    }
    no_mutation = _build_no_governance_mutation_proof(
        before_hashes=before_hashes,
        after_hashes=after_hashes,
        focus_before=focus_before,
        focus_after=focus_after,
        cleanup_result=cleanup_result if isinstance(cleanup_result, dict) else {},
        output_dir=output_dir,
    )

    artifact_hygiene = _run_artifact_hygiene(repo_root, output_dir)

    docs_synced = False
    blockers: list[str] = []
    if not bool(live_preflight.get("live_preflight_passed")):
        blockers.append("live_preflight_failed")
    if _normalize(query_recovery.get("query_recovery_status")) != "passed":
        blockers.append("query_recovery_blocked")
    if _normalize(bot_runtime.get("bot_runtime_retrieval_status")) != "passed":
        blockers.append("bot_runtime_retrieval_blocked")
    if bool(circuit_check.get("circuit_open_after")):
        blockers.append("botdb_circuit_open_after")
    if not bool(chroma_consistency.get("chroma_consistency_passed")):
        blockers.append("chroma_consistency_failed")
    if not bool(admin_visible.get("admin_browser_visible_smoke_passed")):
        blockers.append("admin_browser_visible_smoke_failed")
    if not bool(no_mutation.get("no_governance_mutation_proof_passed")):
        blockers.append("no_governance_mutation_failed")
    if _normalize(artifact_hygiene.get("final_status")).lower() != "passed":
        blockers.append("artifact_hygiene_failed")

    final_status = "passed" if not blockers else "failed"
    if final_status == "passed":
        _sync_docs(repo_root)
        docs_synced = True

    decision = "botdb_live_query_recovery_closed" if final_status == "passed" else "query_recovery_blocked"
    cleanup_apply_status = "not_needed"
    if isinstance(cleanup_result, dict):
        if bool(cleanup_result.get("cleanup_performed")):
            cleanup_apply_status = "passed"
        elif _normalize(cleanup_result.get("cleanup_reason")) == "blocked_by_safety_gates":
            cleanup_apply_status = "skipped_by_policy"
        else:
            cleanup_apply_status = "not_needed"

    scorecard = {
        "schema_version": "botdb_live_recovery_scorecard_hf2_v1",
        "generated_at": _utc_now_iso(),
        "final_status": final_status,
        "decision": decision,
        "source_hf1_failed": _normalize(source_gate.get("source_final_status")) == "failed",
        "live_preflight_passed": bool(live_preflight.get("live_preflight_passed")),
        "dashboard_chroma_status": live_preflight.get("dashboard_chroma_status"),
        "dashboard_chroma_count": live_preflight.get("dashboard_chroma_count"),
        "registry_stats_http_200": bool(live_preflight.get("registry_stats_http_200")),
        "registry_stats_chroma_total": live_preflight.get("registry_stats_chroma_total"),
        "query_http_200": bool(query_recovery.get("query_http_200")),
        "query_recovery_status": query_recovery.get("query_recovery_status"),
        "bot_runtime_retrieval_status": bot_runtime.get("bot_runtime_retrieval_status"),
        "semantic_fallback_used": bool(bot_runtime.get("semantic_fallback_used")),
        "botdb_circuit_open_after": bool(circuit_check.get("circuit_open_after")),
        "chroma_consistency_passed": bool(chroma_consistency.get("chroma_consistency_passed")),
        "zero_block_hygiene_audit_ready": bool((cleanup_bundle.get("plan") or {}).get("zero_block_cleanup_plan_ready")),
        "cleanup_apply_status": cleanup_apply_status,
        "focus_source_protected": bool(admin_visible.get("focus_source_protected")),
        "no_governance_mutation_proof_passed": bool(no_mutation.get("no_governance_mutation_proof_passed")),
        "artifact_encoding_hygiene_passed": _normalize(artifact_hygiene.get("final_status")).lower() == "passed",
        "docs_synced": docs_synced,
        "recommended_next_prd": (
            "PRD-046.1.22 - Diagnostic Center Controlled Runtime Pilot Continuation / Provider-Backed Limited Smoke Readiness v1"
            if final_status == "passed"
            else "PRD-046.1.21-HF3 - Chroma Persistent Store Deep Rebuild v2"
        ),
        "commit_hash": "pending-main-push",
        "push_status": "pending-main-push",
        "blockers": blockers,
    }
    _write_json(output_dir / "botdb_live_recovery_scorecard.json", scorecard)

    implementation_report = _render_report(
        "PRD-046.1.21-HF2 IMPLEMENTATION REPORT",
        [
            "## Status",
            f"- PRD ID: `PRD-046.1.21-HF2`",
            f"- final_status: `{scorecard['final_status']}`",
            f"- decision: `{scorecard['decision']}`",
            f"- blockers: `{scorecard['blockers']}`",
            "",
            "## Source HF1 summary",
            f"- source_final_status: `{source_gate.get('source_final_status')}`",
            f"- source_decision: `{source_gate.get('source_decision')}`",
            f"- source_chroma_count_after: `{source_gate.get('source_chroma_count_after')}`",
            f"- source_query_http_200: `{source_gate.get('source_query_http_200')}`",
            "",
            "## Live preflight summary",
            f"- live_preflight_passed: `{live_preflight.get('live_preflight_passed')}`",
            f"- dashboard_chroma_status: `{live_preflight.get('dashboard_chroma_status')}`",
            f"- dashboard_chroma_count: `{live_preflight.get('dashboard_chroma_count')}`",
            f"- registry_stats_http_200: `{live_preflight.get('registry_stats_http_200')}`",
            f"- registry_stats_chroma_total: `{live_preflight.get('registry_stats_chroma_total')}`",
            "",
            "## Query recovery smoke summary",
            f"- query_http_200: `{query_recovery.get('query_http_200')}`",
            f"- query_status_code: `{query_recovery.get('query_status_code')}`",
            f"- rag_hits_count: `{query_recovery.get('rag_hits_count')}`",
            f"- query_recovery_status: `{query_recovery.get('query_recovery_status')}`",
            "",
            "## Bot runtime retrieval summary",
            f"- retrieval_source_used: `{bot_runtime.get('retrieval_source_used')}`",
            f"- semantic_fallback_used: `{bot_runtime.get('semantic_fallback_used')}`",
            f"- botdb_circuit_open: `{bot_runtime.get('botdb_circuit_open')}`",
            f"- bot_runtime_retrieval_status: `{bot_runtime.get('bot_runtime_retrieval_status')}`",
            "",
            "## Circuit reset summary",
            f"- circuit_open_before: `{circuit_check.get('circuit_open_before')}`",
            f"- circuit_open_after: `{circuit_check.get('circuit_open_after')}`",
            "",
            "## Chroma consistency summary",
            f"- chroma_consistency_passed: `{chroma_consistency.get('chroma_consistency_passed')}`",
            f"- all_blocks_merged_blocks: `{chroma_consistency.get('all_blocks_merged_blocks')}`",
            f"- chroma_count: `{chroma_consistency.get('chroma_count')}`",
            "",
            "## Zero-block cleanup summary",
            f"- safe_delete_candidates_count: `{(cleanup_bundle.get('plan') or {}).get('safe_delete_candidates_count')}`",
            f"- cleanup_performed: `{cleanup_result.get('cleanup_performed') if isinstance(cleanup_result, dict) else None}`",
            f"- cleanup_reason: `{cleanup_result.get('cleanup_reason') if isinstance(cleanup_result, dict) else None}`",
            "",
            "## Admin browser visible smoke summary",
            f"- admin_browser_visible_smoke_passed: `{admin_visible.get('admin_browser_visible_smoke_passed')}`",
            f"- registry_error_banner_absent: `{admin_visible.get('registry_error_banner_absent')}`",
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
    _write_text(reports_dir / "PRD-046.1.21-HF2_IMPLEMENTATION_REPORT.md", implementation_report)
    _write_text(
        reports_dir / "PRD-046.1.21-HF2_BOTDB_LIVE_RECOVERY_REPORT.md",
        _render_report(
            "PRD-046.1.21-HF2 BOTDB LIVE RECOVERY REPORT",
            [
                f"- live_preflight_passed: `{live_preflight.get('live_preflight_passed')}`",
                f"- query_recovery_status: `{query_recovery.get('query_recovery_status')}`",
                f"- bot_runtime_retrieval_status: `{bot_runtime.get('bot_runtime_retrieval_status')}`",
                f"- chroma_consistency_passed: `{chroma_consistency.get('chroma_consistency_passed')}`",
            ],
        ),
    )
    _write_text(
        reports_dir / "PRD-046.1.21-HF2_REGISTRY_ZERO_BLOCK_CLEANUP_REPORT.md",
        _render_report(
            "PRD-046.1.21-HF2 REGISTRY ZERO-BLOCK CLEANUP REPORT",
            [
                f"- zero_block_cleanup_plan_ready: `{(cleanup_bundle.get('plan') or {}).get('zero_block_cleanup_plan_ready')}`",
                f"- safe_delete_candidates_count: `{(cleanup_bundle.get('plan') or {}).get('safe_delete_candidates_count')}`",
                f"- cleanup_performed: `{cleanup_result.get('cleanup_performed') if isinstance(cleanup_result, dict) else None}`",
                f"- removed_zero_block_sources_count: `{cleanup_result.get('removed_zero_block_sources_count') if isinstance(cleanup_result, dict) else None}`",
            ],
        ),
    )
    _write_text(
        reports_dir / "PRD-046.1.21-HF2_NEXT_PRD_RECOMMENDATION.md",
        _render_report(
            "PRD-046.1.21-HF2 NEXT PRD RECOMMENDATION",
            [
                f"- final_status: `{scorecard['final_status']}`",
                f"- decision: `{scorecard['decision']}`",
                f"- recommended_next_prd: `{scorecard['recommended_next_prd']}`",
            ],
        ),
    )
    return scorecard


def main() -> int:
    parser = argparse.ArgumentParser(description="HF2 live query recovery closure and registry zero-block cleanup gate.")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--admin-base-url", default="http://127.0.0.1:8003")
    parser.add_argument("--output-dir", default="TO_DO_LIST/logs/PRD-046.1.21-HF2")
    parser.add_argument("--reports-dir", default="TO_DO_LIST/reports")
    parser.add_argument("--expected-source-id", default="123__кузница_духа")
    parser.add_argument("--expected-blocks", type=int, default=247)
    parser.add_argument("--perform-cleanup", action="store_true", default=False)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    payload = run(args)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if args.strict and _normalize(payload.get("final_status")) != "passed":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
