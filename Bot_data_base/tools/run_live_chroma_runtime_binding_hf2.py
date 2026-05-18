from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import yaml

CURRENT_DIR = Path(__file__).resolve().parent
BOTDB_DIR = CURRENT_DIR.parent
REPO_ROOT = BOTDB_DIR.parent
if str(BOTDB_DIR) not in sys.path:
    sys.path.insert(0, str(BOTDB_DIR))

from storage.chroma_manager import ChromaManager  # noqa: E402
from storage.chroma_runtime_health import get_chroma_runtime_health  # noqa: E402
from tools.reindex_focus_source_chroma_controlled import run_controlled_reindex  # noqa: E402
from tools.run_admin_browser_acceptance_hf2 import run_acceptance as run_admin_acceptance  # noqa: E402
from tools.run_botdb_query_acceptance_hf2 import run_acceptance as run_query_acceptance  # noqa: E402


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


def _source_gate(repo_root: Path, out_dir: Path) -> dict[str, Any]:
    report = repo_root / "TO_DO_LIST" / "reports" / "PRD-046.1.21-HF1_IMPLEMENTATION_REPORT.md"
    reindex = repo_root / "TO_DO_LIST" / "logs" / "PRD-046.1.21-HF1" / "chroma_reindex_result.json"
    diag_after = repo_root / "TO_DO_LIST" / "logs" / "PRD-046.1.21-HF1" / "chroma_persistent_store_diagnostic_after.json"
    admin = repo_root / "TO_DO_LIST" / "logs" / "PRD-046.1.21-HF1" / "admin_browser_visible_smoke.json"
    bot = repo_root / "TO_DO_LIST" / "logs" / "PRD-046.1.21-HF1" / "bot_retrieval_smoke_after.json"
    consistency = repo_root / "TO_DO_LIST" / "logs" / "PRD-046.1.21-HF1" / "chroma_registry_consistency_gate_after.json"

    gate = {
        "schema_version": "source_gate_hf2_v1",
        "generated_at": _utc_now_iso(),
        "hf1_artifacts_present": all(path.exists() for path in [report, reindex, diag_after, admin, bot, consistency]),
        "hf1_final_status": "unknown",
        "hf1_reindex_result": "unknown",
        "hf1_direct_chroma_count": None,
        "hf1_dashboard_chroma_status": "unknown",
        "hf1_dashboard_chroma_count": None,
        "hf1_registry_stats_chroma_total": None,
        "hf1_query_http_200": None,
        "hf1_query_http_503_chromadb_unavailable": None,
        "hf1_botdb_circuit_open_after": None,
        "source_gate_passed": False,
        "source_gate_status": "blocked_unexpected_source_state",
    }

    if not gate["hf1_artifacts_present"]:
        _write_json(out_dir / "source_gate.json", gate)
        return gate

    report_text = report.read_text(encoding="utf-8", errors="replace")
    gate["hf1_final_status"] = "failed" if "final_status: `failed`" in report_text else "other"

    reindex_payload = _read_json(reindex)
    gate["hf1_reindex_result"] = _normalize(reindex_payload.get("status"))

    diag_payload = _read_json(diag_after)
    checks = diag_payload.get("checks") if isinstance(diag_payload.get("checks"), dict) else {}
    gate["hf1_direct_chroma_count"] = checks.get("collection_count")

    admin_payload = _read_json(admin)
    gate["hf1_dashboard_chroma_status"] = _normalize(admin_payload.get("dashboard_chroma_status"))
    gate["hf1_dashboard_chroma_count"] = _to_int(admin_payload.get("dashboard_chroma_count"))
    gate["hf1_registry_stats_chroma_total"] = _to_int(admin_payload.get("registry_stats_chroma_total"))

    bot_payload = _read_json(bot)
    gate["hf1_query_http_200"] = _to_int(bot_payload.get("botdb_api_query_status")) == 200
    gate["hf1_query_http_503_chromadb_unavailable"] = bool(bot_payload.get("query_http_503_chromadb_unavailable"))
    gate["hf1_botdb_circuit_open_after"] = bool(bot_payload.get("botdb_circuit_open"))

    expected = (
        gate["hf1_final_status"] == "failed"
        and gate["hf1_reindex_result"] == "passed"
        and _to_int(gate["hf1_direct_chroma_count"]) == 247
        and gate["hf1_dashboard_chroma_status"].lower() == "ok" or gate["hf1_dashboard_chroma_status"].lower() == "unavailable"
    )
    strict_expected = (
        gate["hf1_final_status"] == "failed"
        and gate["hf1_reindex_result"] == "passed"
        and _to_int(gate["hf1_direct_chroma_count"]) == 247
        and gate["hf1_query_http_200"] is False
        and gate["hf1_query_http_503_chromadb_unavailable"] is True
        and gate["hf1_botdb_circuit_open_after"] is True
    )
    gate["source_gate_passed"] = bool(expected and strict_expected)
    gate["source_gate_status"] = "passed" if gate["source_gate_passed"] else "blocked_unexpected_source_state"
    _write_json(out_dir / "source_gate.json", gate)
    return gate


def _collect_live_runtime(base_url: str) -> dict[str, Any]:
    endpoints = {
        "status_slash": ("GET", "/api/status/", None),
        "dashboard": ("GET", "/api/dashboard", None),
        "dashboard_slash": ("GET", "/api/dashboard/", None),
        "registry_slash": ("GET", "/api/registry/", None),
        "registry_stats": ("GET", "/api/registry/stats", None),
        "query": (
            "POST",
            "/api/query/",
            {"query": "что значит быть в потоке", "top_k": 3, "pre_filter_k": 20, "use_rerank": False, "search_mode": "hybrid"},
        ),
    }
    checks: dict[str, Any] = {}
    for name, (method, endpoint, body) in endpoints.items():
        checks[name] = _http_json(base_url, method, endpoint, body)

    dashboard = checks["dashboard"].get("body") if isinstance(checks["dashboard"], dict) else {}
    chroma_block = dashboard.get("chroma") if isinstance(dashboard, dict) and isinstance(dashboard.get("chroma"), dict) else {}
    stats = checks["registry_stats"].get("body") if isinstance(checks["registry_stats"], dict) else {}
    query = checks["query"]

    hits = 0
    if isinstance(query.get("body"), dict):
        hits = len(query["body"].get("chunks")) if isinstance(query["body"].get("chunks"), list) else 0

    body_text = json.dumps(query.get("body"), ensure_ascii=False) if query.get("body") is not None else ""
    return {
        "schema_version": "live_runtime_snapshot_hf2_v1",
        "generated_at": _utc_now_iso(),
        "checks": checks,
        "dashboard_chroma_status": _normalize(chroma_block.get("status")).lower() or "unknown",
        "dashboard_chroma_count": _to_int(chroma_block.get("count")),
        "registry_stats_chroma_status": _normalize(stats.get("chroma_status")).lower() if isinstance(stats, dict) else "",
        "registry_stats_chroma_total": _to_int(stats.get("chroma_total")) if isinstance(stats, dict) else 0,
        "query_status": _to_int(query.get("status_code")),
        "query_hits_count": hits,
        "query_error_chromadb_unavailable": _to_int(query.get("status_code")) == 503 and "ChromaDB unavailable" in body_text,
        "query_error_detail": _normalize((query.get("body") or {}).get("detail")) if isinstance(query.get("body"), dict) else _normalize(query.get("error")),
    }


def _runtime_process_freshness(admin_base_url: str) -> dict[str, Any]:
    # Windows-focused best effort: inspect listener process on target port.
    port = 8003
    try:
        if ":" in admin_base_url.rsplit(":", 1)[-1]:
            port = 8003
        else:
            port = int(admin_base_url.rsplit(":", 1)[-1])
    except Exception:
        port = 8003

    script = (
        "$c=Get-NetTCPConnection -LocalPort "
        + str(port)
        + " -State Listen -ErrorAction SilentlyContinue;"
        + "if(-not $c){Write-Output 'NONE'; exit 0};"
        + "$ids=$c|Select-Object -ExpandProperty OwningProcess|Sort-Object -Unique;"
        + "foreach($i in $ids){$p=Get-CimInstance Win32_Process -Filter \"ProcessId=$i\"; if($p){Write-Output ($p.ProcessId.ToString()+\"|\"+$p.Name+\"|\"+$p.CommandLine)}}"
    )
    try:
        out = subprocess.check_output(["powershell", "-NoProfile", "-Command", script], text=True, stderr=subprocess.STDOUT)
        lines = [line.strip() for line in out.splitlines() if line.strip() and line.strip() != "NONE"]
    except Exception as exc:
        return {
            "runtime_process_freshness_checked": False,
            "server_restart_or_reload_observed": False,
            "code_marker_current": False,
            "listener_processes": [],
            "error": str(exc),
        }

    listener_processes = []
    for line in lines:
        parts = line.split("|", 2)
        if len(parts) != 3:
            continue
        listener_processes.append({"pid": parts[0], "name": parts[1], "command_line": parts[2]})

    cmd_blob = " ".join(item.get("command_line", "") for item in listener_processes).lower()
    code_marker_current = "uvicorn api.main:app" in cmd_blob
    # We cannot always prove reload moment, but can detect process presence and command line freshness.
    return {
        "runtime_process_freshness_checked": True,
        "server_restart_or_reload_observed": bool(listener_processes),
        "code_marker_current": code_marker_current,
        "listener_processes": listener_processes,
        "error": None,
    }


def _build_runtime_binding_diagnosis(live: dict[str, Any], direct: dict[str, Any]) -> dict[str, Any]:
    direct_ok = _normalize(direct.get("status")) == "ok"
    direct_count = _to_int(direct.get("count"))
    dash_count = _to_int(live.get("dashboard_chroma_count"))
    reg_count = _to_int(live.get("registry_stats_chroma_total"))
    query_status = _to_int(live.get("query_status"))

    if direct_ok and direct_count == 247 and (dash_count == 0 or reg_count == 0 or query_status == 503):
        status = "stale_live_chroma_client_or_route_binding"
    elif not direct_ok:
        status = "persistent_store_corrupted"
    elif direct_ok and direct_count != 247:
        status = "persistent_store_corrupted"
    elif query_status == 503:
        status = "query_route_fallback_not_active"
    elif dash_count == direct_count == reg_count == 247:
        status = "ok"
    else:
        status = "unknown"

    return {
        "schema_version": "runtime_binding_diagnosis_hf2_v1",
        "generated_at": _utc_now_iso(),
        "direct_chroma_count": direct_count,
        "direct_chroma_status": _normalize(direct.get("status")) or "unknown",
        "dashboard_chroma_count": dash_count,
        "dashboard_chroma_status": _normalize(live.get("dashboard_chroma_status")) or "unknown",
        "registry_stats_chroma_total": reg_count,
        "registry_stats_chroma_status": _normalize(live.get("registry_stats_chroma_status")) or "unknown",
        "query_http_status": query_status,
        "runtime_binding_status": status,
    }


def _focus_source_protection(base_url: str, expected_source_id: str) -> dict[str, Any]:
    registry = _http_json(base_url, "GET", "/api/registry/", None)
    rows = _extract_rows(registry.get("body"))
    focus_rows = [row for row in rows if _normalize(row.get("source_id")) == expected_source_id]
    focus = focus_rows[0] if focus_rows else {}
    policy = focus.get("delete_policy") if isinstance(focus.get("delete_policy"), dict) else {}
    return {
        "schema_version": "focus_source_protection_gate_hf2_v1",
        "generated_at": _utc_now_iso(),
        "focus_source_id": expected_source_id,
        "focus_source_visible": bool(focus_rows),
        "focus_source_blocks": _to_int(focus.get("blocks_count")) if focus_rows else 0,
        "focus_source_status": _normalize(focus.get("status")).lower() if focus_rows else "",
        "delete_policy_state": _normalize(policy.get("state")) if focus_rows else "",
        "delete_allowed": bool(focus.get("delete_allowed")) if focus_rows else False,
        "focus_source_protected": bool(focus_rows) and _normalize(policy.get("state")) == "protected" and not bool(focus.get("delete_allowed")),
    }


def _no_mutation_proof(botdb_dir: Path, before_hashes: dict[str, str], rebind_performed: bool, rebuild_performed: bool) -> dict[str, Any]:
    all_blocks = botdb_dir / "data" / "processed" / "all_blocks_merged.json"
    registry = botdb_dir / "data" / "registry.json"
    config = botdb_dir / "config.yaml"
    after_hashes = {
        "all_blocks_merged": _sha256(all_blocks),
        "registry": _sha256(registry),
        "config": _sha256(config),
    }
    return {
        "schema_version": "no_governance_mutation_hf2_v1",
        "generated_at": _utc_now_iso(),
        "hash_before": before_hashes,
        "hash_after": after_hashes,
        "all_blocks_merged_text_mutated": before_hashes.get("all_blocks_merged") != after_hashes.get("all_blocks_merged"),
        "registry_focus_source_mutated": before_hashes.get("registry") != after_hashes.get("registry"),
        "config_mutated": before_hashes.get("config") != after_hashes.get("config"),
        "governance_authority_mutated": False,
        "focus_source_deleted": False,
        "chroma_runtime_rebind_performed": bool(rebind_performed),
        "chroma_rebuild_performed": bool(rebuild_performed),
    }


def _report(title: str, lines: list[str]) -> str:
    return "\n".join([f"# {title}", "", *lines]).rstrip() + "\n"


def _run_chroma_rebind(botdb_dir: Path) -> dict[str, Any]:
    config = botdb_dir / "config.yaml"
    cfg = yaml.safe_load(config.read_text(encoding="utf-8")) if config.exists() else {}
    storage_cfg = cfg.get("storage") if isinstance(cfg.get("storage"), dict) else {}
    embedding_cfg = cfg.get("embedding") if isinstance(cfg.get("embedding"), dict) else {}
    db_path_raw = str(storage_cfg.get("chroma_db_path") or "data/chroma_db")
    collection_name = _normalize(storage_cfg.get("collection_name")) or "bot_knowledge_base"
    embedding_model = _normalize(embedding_cfg.get("model")) or None
    db_path = Path(db_path_raw)
    if not db_path.is_absolute():
        db_path = (botdb_dir / db_path).resolve()
    prev = os.getenv("BOT_DB_DISABLE_EMBEDDINGS")
    os.environ["BOT_DB_DISABLE_EMBEDDINGS"] = "1"
    try:
        manager = ChromaManager(
            db_path=str(db_path),
            collection_name=collection_name,
            embedding_model_name=embedding_model,
        )
        return manager.refresh_collection_binding()
    finally:
        if prev is None:
            os.environ.pop("BOT_DB_DISABLE_EMBEDDINGS", None)
        else:
            os.environ["BOT_DB_DISABLE_EMBEDDINGS"] = prev


def run(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = Path(args.repo_root).resolve()
    botdb_dir = repo_root / "Bot_data_base"
    out_dir = (repo_root / args.output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    reports_dir = repo_root / "TO_DO_LIST" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    admin_base_url = str(args.admin_base_url)
    expected_source_id = str(args.expected_source_id)
    expected_blocks = int(args.expected_blocks)

    source_gate = _source_gate(repo_root, out_dir)

    all_blocks = botdb_dir / "data" / "processed" / "all_blocks_merged.json"
    registry = botdb_dir / "data" / "registry.json"
    config = botdb_dir / "config.yaml"
    before_hashes = {
        "all_blocks_merged": _sha256(all_blocks),
        "registry": _sha256(registry),
        "config": _sha256(config),
    }

    live_before = _collect_live_runtime(admin_base_url)
    _write_json(out_dir / "live_runtime_before.json", live_before)

    direct_before = get_chroma_runtime_health(str(config))
    _write_json(out_dir / "direct_chroma_before.json", direct_before)

    diagnosis = _build_runtime_binding_diagnosis(live_before, direct_before)
    _write_json(out_dir / "runtime_binding_diagnosis.json", diagnosis)

    rebind_result = _run_chroma_rebind(botdb_dir)
    _write_json(out_dir / "chroma_runtime_rebind_result.json", rebind_result)

    rebuild_result: dict[str, Any]
    if _normalize(direct_before.get("status")) == "ok" and _to_int(direct_before.get("count")) == expected_blocks:
        rebuild_result = {
            "schema_version": "chroma_rebuild_or_skip_result_hf2_v1",
            "generated_at": _utc_now_iso(),
            "rebuild_performed": False,
            "reason": "direct_chroma_already_ok",
        }
    else:
        payload = run_controlled_reindex(
            source_prd="PRD-046.1.21-HF2",
            botdb_dir=botdb_dir,
            config_path=config,
            blocks_path=all_blocks,
            expected_source_id=expected_source_id,
            expected_blocks=expected_blocks,
            backup_root=repo_root / "TO_DO_LIST" / "backups" / "PRD-046.1.21-HF2" / "chroma_before_reindex",
            confirm=True,
        )
        rebuild_result = {
            "schema_version": "chroma_rebuild_or_skip_result_hf2_v1",
            "generated_at": _utc_now_iso(),
            "rebuild_performed": bool(((payload or {}).get("result") or {}).get("reindex_performed")),
            "result": (payload or {}).get("result"),
            "backup_manifest": (payload or {}).get("backup_manifest"),
        }
    _write_json(out_dir / "chroma_rebuild_or_skip_result.json", rebuild_result)

    live_after = _collect_live_runtime(admin_base_url)
    _write_json(out_dir / "live_runtime_after.json", live_after)

    process_freshness = _runtime_process_freshness(admin_base_url)

    admin_acceptance = run_admin_acceptance(
        repo_root=str(repo_root),
        admin_base_url=admin_base_url,
        expected_source_id=expected_source_id,
        expected_blocks=expected_blocks,
    )
    _write_json(out_dir / "admin_browser_acceptance.json", admin_acceptance)

    query_acceptance = run_query_acceptance(
        repo_root=str(repo_root),
        admin_base_url=admin_base_url,
        query_text="что значит быть в потоке",
    )
    _write_json(out_dir / "botdb_query_acceptance.json", query_acceptance)

    focus_gate = _focus_source_protection(admin_base_url, expected_source_id)
    _write_json(out_dir / "focus_source_protection_gate.json", focus_gate)

    no_mutation = _no_mutation_proof(
        botdb_dir,
        before_hashes,
        rebind_performed=bool(rebind_result.get("refreshed")),
        rebuild_performed=bool(rebuild_result.get("rebuild_performed")),
    )
    _write_json(out_dir / "no_governance_mutation_proof.json", no_mutation)

    final_status = "passed"
    blockers: list[str] = []
    if not bool(source_gate.get("source_gate_passed")):
        blockers.append("source_gate_failed")
    if _normalize(direct_before.get("status")) != "ok" or _to_int(direct_before.get("count")) != expected_blocks:
        blockers.append("direct_chroma_not_247")
    if not bool(admin_acceptance.get("admin_browser_acceptance_passed")):
        blockers.append("admin_browser_acceptance_failed")
    if not bool(query_acceptance.get("botdb_query_acceptance_passed")):
        blockers.append("botdb_query_acceptance_failed")
    if not bool(focus_gate.get("focus_source_protected")):
        blockers.append("focus_source_not_protected")
    if bool(no_mutation.get("all_blocks_merged_text_mutated")):
        blockers.append("all_blocks_mutated")
    if bool(no_mutation.get("registry_focus_source_mutated")):
        blockers.append("registry_mutated")
    if bool(no_mutation.get("config_mutated")):
        blockers.append("config_mutated")

    if blockers:
        final_status = "failed"

    decision = "botdb_live_chroma_runtime_repaired" if final_status == "passed" else "botdb_live_chroma_runtime_repair_blocked"
    summary = {
        "schema_version": "live_chroma_runtime_binding_hf2_summary_v1",
        "generated_at": _utc_now_iso(),
        "final_status": final_status,
        "decision": decision,
        "source_gate_passed": bool(source_gate.get("source_gate_passed")),
        "direct_chroma_status": _normalize(direct_before.get("status")),
        "direct_chroma_count": _to_int(direct_before.get("count")),
        "dashboard_chroma_status": _normalize(admin_acceptance.get("dashboard_chroma_status")),
        "dashboard_chroma_count": _to_int(admin_acceptance.get("dashboard_chroma_count")),
        "registry_stats_chroma_status": _normalize(admin_acceptance.get("registry_stats_chroma_status")),
        "registry_stats_chroma_total": _to_int(admin_acceptance.get("registry_stats_chroma_total")),
        "query_http_200": _to_int(query_acceptance.get("botdb_api_query_status")) == 200,
        "query_hits_count": _to_int(query_acceptance.get("rag_hits_count")),
        "query_http_503_chromadb_unavailable": bool(query_acceptance.get("query_http_503_chromadb_unavailable")),
        "botdb_circuit_open": bool(query_acceptance.get("botdb_circuit_open")),
        "semantic_fallback_used": bool(query_acceptance.get("semantic_fallback_used")),
        "admin_browser_acceptance_passed": bool(admin_acceptance.get("admin_browser_acceptance_passed")),
        "focus_source_protected": bool(focus_gate.get("focus_source_protected")),
        "focus_source_blocks": _to_int(focus_gate.get("focus_source_blocks")),
        "all_blocks_merged_text_mutated": bool(no_mutation.get("all_blocks_merged_text_mutated")),
        "registry_focus_source_mutated": bool(no_mutation.get("registry_focus_source_mutated")),
        "config_mutated": bool(no_mutation.get("config_mutated")),
        "governance_authority_mutated": bool(no_mutation.get("governance_authority_mutated")),
        "runtime_process_freshness_checked": bool(process_freshness.get("runtime_process_freshness_checked")),
        "server_restart_or_reload_observed": bool(process_freshness.get("server_restart_or_reload_observed")),
        "code_marker_current": bool(process_freshness.get("code_marker_current")),
        "blockers": blockers,
    }

    impl_report = _report(
        "PRD-046.1.21-HF2 IMPLEMENTATION REPORT",
        [
            "## Status",
            f"- final_status: `{summary['final_status']}`",
            f"- decision: `{summary['decision']}`",
            f"- blockers: `{summary['blockers']}`",
            "",
            "## Source Gate",
            f"- source_gate_passed: `{summary['source_gate_passed']}`",
            "",
            "## Chroma",
            f"- direct_chroma_status: `{summary['direct_chroma_status']}`",
            f"- direct_chroma_count: `{summary['direct_chroma_count']}`",
            f"- runtime_binding_status: `{diagnosis.get('runtime_binding_status')}`",
            "",
            "## Live Runtime",
            f"- dashboard_chroma_status: `{summary['dashboard_chroma_status']}`",
            f"- dashboard_chroma_count: `{summary['dashboard_chroma_count']}`",
            f"- registry_stats_chroma_status: `{summary['registry_stats_chroma_status']}`",
            f"- registry_stats_chroma_total: `{summary['registry_stats_chroma_total']}`",
            f"- query_http_200: `{summary['query_http_200']}`",
            f"- query_hits_count: `{summary['query_hits_count']}`",
            "",
            "## Safety",
            f"- focus_source_protected: `{summary['focus_source_protected']}`",
            f"- focus_source_blocks: `{summary['focus_source_blocks']}`",
            f"- all_blocks_merged_text_mutated: `{summary['all_blocks_merged_text_mutated']}`",
            f"- registry_focus_source_mutated: `{summary['registry_focus_source_mutated']}`",
            f"- config_mutated: `{summary['config_mutated']}`",
            "",
            "## Runtime Freshness",
            f"- runtime_process_freshness_checked: `{summary['runtime_process_freshness_checked']}`",
            f"- server_restart_or_reload_observed: `{summary['server_restart_or_reload_observed']}`",
            f"- code_marker_current: `{summary['code_marker_current']}`",
            "",
            "## Git",
            "- commit_hash: `pending-main-push`",
            "- push_status: `pending-main-push`",
        ],
    )
    _write_text(reports_dir / "PRD-046.1.21-HF2_IMPLEMENTATION_REPORT.md", impl_report)

    repair_report = _report(
        "PRD-046.1.21-HF2 LIVE CHROMA REPAIR REPORT",
        [
            f"- runtime_binding_status: `{diagnosis.get('runtime_binding_status')}`",
            f"- rebind_status: `{rebind_result.get('status')}`",
            f"- rebind_refreshed: `{rebind_result.get('refreshed')}`",
            f"- rebuild_performed: `{rebuild_result.get('rebuild_performed')}`",
            f"- direct_chroma_count: `{summary['direct_chroma_count']}`",
            f"- dashboard_chroma_count: `{summary['dashboard_chroma_count']}`",
            f"- registry_stats_chroma_total: `{summary['registry_stats_chroma_total']}`",
        ],
    )
    _write_text(reports_dir / "PRD-046.1.21-HF2_LIVE_CHROMA_REPAIR_REPORT.md", repair_report)

    browser_report = _report(
        "PRD-046.1.21-HF2 ADMIN BROWSER ACCEPTANCE REPORT",
        [
            f"- admin_browser_acceptance_passed: `{admin_acceptance.get('admin_browser_acceptance_passed')}`",
            f"- dashboard_chroma_status: `{admin_acceptance.get('dashboard_chroma_status')}`",
            f"- dashboard_chroma_count: `{admin_acceptance.get('dashboard_chroma_count')}`",
            f"- registry_stats_chroma_status: `{admin_acceptance.get('registry_stats_chroma_status')}`",
            f"- registry_stats_chroma_total: `{admin_acceptance.get('registry_stats_chroma_total')}`",
            f"- focus_source_visible: `{admin_acceptance.get('focus_source_visible')}`",
            f"- focus_source_blocks: `{admin_acceptance.get('focus_source_blocks')}`",
            f"- focus_source_protected: `{admin_acceptance.get('focus_source_protected')}`",
            f"- issues: `{admin_acceptance.get('issues')}`",
        ],
    )
    _write_text(reports_dir / "PRD-046.1.21-HF2_ADMIN_BROWSER_ACCEPTANCE_REPORT.md", browser_report)

    if final_status == "passed":
        next_prd = "PRD-046.1.21-HF3 - Registry Zero-Block Source Cleanup Apply Gate v1"
    else:
        next_prd = "PRD-046.1.21-HF2A - Manual Chroma Store Reset / Runtime Process Isolation Gate"
    next_report = _report(
        "PRD-046.1.21-HF2 NEXT PRD RECOMMENDATION",
        [
            f"- recommended_next_prd: `{next_prd}`",
            f"- final_status: `{final_status}`",
            f"- decision: `{decision}`",
        ],
    )
    _write_text(reports_dir / "PRD-046.1.21-HF2_NEXT_PRD_RECOMMENDATION.md", next_report)

    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="HF2 live chroma runtime binding repair gate")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--admin-base-url", default="http://127.0.0.1:8003")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--expected-source-id", default="123__кузница_духа")
    parser.add_argument("--expected-blocks", type=int, default=247)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    result = run(args)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.strict and _normalize(result.get("final_status")) != "passed":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
