from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.error import URLError
from urllib.request import Request, urlopen

from .review_sanitizer import contains_secret_like_value


EXPECTED_APPLY_COUNTS = {
    "safe_non_review_apply_candidates": 160,
    "review_approved_apply_candidates": 28,
    "review_needs_edit_apply_candidates": 12,
    "review_rejected_skip": 1,
    "review_defer_skip": 46,
    "updated_blocks": 200,
}

FORBIDDEN_LLM_KEYS = {
    "text",
    "content",
    "content_full",
    "full_text",
    "raw_text",
    "source_raw",
    "embedding",
    "vector",
    "governance",
    "source_id",
    "block_id",
    "allowed_use",
    "safety_flags",
    "chunk_type",
}

ADVISORY_MARKER_KEYS = {
    "applied_by_prd",
    "apply_route",
    "review_decision",
    "source_overlay_prd",
}

RETRIEVAL_TERMS = ["страх", "тень", "границы", "практика", "внутренний голос"]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def render_markdown_report(title: str, lines: list[str]) -> str:
    return "\n".join([f"# {title}", "", *lines]).rstrip() + "\n"


def _extract_blocks(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        rows = payload.get("blocks")
        if isinstance(rows, list):
            return [row for row in rows if isinstance(row, dict)]
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    return []


def _normalize_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    raw = str(value).strip()
    if not raw:
        return []
    return [part.strip() for part in raw.split(",") if part.strip()]


def _source_id(block: dict[str, Any]) -> str:
    meta = block.get("metadata") if isinstance(block.get("metadata"), dict) else {}
    source_id = str(meta.get("source_id") or "").strip()
    if source_id:
        return source_id
    source = str(block.get("source") or "").strip()
    if ":" in source:
        return source.split(":", 1)[1]
    return source


def _block_id(block: dict[str, Any]) -> str:
    return str(block.get("id") or block.get("chunk_id") or "").strip()


def _governance(block: dict[str, Any]) -> dict[str, Any]:
    meta = block.get("metadata") if isinstance(block.get("metadata"), dict) else {}
    gov = meta.get("governance")
    return gov if isinstance(gov, dict) else {}


def _llm_enrichment(block: dict[str, Any]) -> dict[str, Any]:
    meta = block.get("metadata") if isinstance(block.get("metadata"), dict) else {}
    llm = meta.get("llm_enrichment")
    return llm if isinstance(llm, dict) else {}


def _registry_focus_blocks(registry_payload: Any, expected_source_id: str) -> int:
    if not isinstance(registry_payload, list):
        return 0
    focus_done = [
        row
        for row in registry_payload
        if isinstance(row, dict)
        and str(row.get("source_id") or "").strip() == expected_source_id
        and str(row.get("status") or "").strip() == "done"
    ]
    return int((focus_done[0].get("blocks_count") if focus_done else 0) or 0)


def build_data_consistency_gate(
    *,
    blocks_payload: Any,
    registry_payload: Any,
    apply_result_payload: dict[str, Any],
    expected_blocks_total: int,
    expected_source_id: str,
) -> dict[str, Any]:
    blocks = _extract_blocks(blocks_payload)
    source_ids = sorted({_source_id(block) for block in blocks if _source_id(block)})
    gov_present = 0
    allowed_use_present = 0
    safety_flags_present = 0
    for block in blocks:
        gov = _governance(block)
        if gov:
            gov_present += 1
        if _normalize_list(gov.get("allowed_use")):
            allowed_use_present += 1
        if _normalize_list(gov.get("safety_flags")):
            safety_flags_present += 1

    total = max(1, len(blocks))
    rates = {
        "governance_present_rate": round(gov_present / total, 6),
        "allowed_use_present_rate": round(allowed_use_present / total, 6),
        "safety_flags_present_rate": round(safety_flags_present / total, 6),
    }

    apply_summary = apply_result_payload.get("apply_summary") if isinstance(apply_result_payload.get("apply_summary"), dict) else {}
    authority_checks = {
        "text_changed_count": int(apply_summary.get("text_changed_count") or 0),
        "chunk_type_changed_count": int(apply_summary.get("chunk_type_changed_count") or 0),
        "allowed_use_changed_count": int(apply_summary.get("allowed_use_changed_count") or 0),
        "safety_flags_changed_count": int(apply_summary.get("safety_flags_changed_count") or 0),
        "source_id_changed_count": int(apply_summary.get("source_id_changed_count") or 0),
        "block_id_changed_count": int(apply_summary.get("block_id_changed_count") or 0),
        "governance_invariant_violations": int(apply_summary.get("governance_invariant_violations") or 0),
    }
    no_authority_mutation = all(value == 0 for value in authority_checks.values())

    data_consistency_passed = (
        len(blocks) == expected_blocks_total
        and _registry_focus_blocks(registry_payload, expected_source_id) == expected_blocks_total
        and source_ids == [expected_source_id]
        and rates["governance_present_rate"] == 1.0
        and rates["allowed_use_present_rate"] == 1.0
        and rates["safety_flags_present_rate"] == 1.0
        and no_authority_mutation
    )

    return {
        "schema_version": "post_apply_data_consistency_gate_v1",
        "generated_at": utc_now_iso(),
        "blocks_total": len(blocks),
        "registry_focus_blocks": _registry_focus_blocks(registry_payload, expected_source_id),
        "source_ids": source_ids,
        **rates,
        **authority_checks,
        "data_consistency_passed": data_consistency_passed,
    }


def build_apply_route_consistency(
    *,
    blocks_payload: Any,
    apply_result_payload: dict[str, Any],
    decisions_overlay_payload: dict[str, Any],
    review_queue_payload: dict[str, Any],
    expected_counts: dict[str, int] | None = None,
) -> dict[str, Any]:
    expected = dict(EXPECTED_APPLY_COUNTS)
    if isinstance(expected_counts, dict):
        expected.update({k: int(v) for k, v in expected_counts.items()})

    plan = apply_result_payload.get("plan") if isinstance(apply_result_payload.get("plan"), dict) else {}
    apply_summary = apply_result_payload.get("apply_summary") if isinstance(apply_result_payload.get("apply_summary"), dict) else {}
    route_counts = (
        apply_summary.get("applied_route_counts")
        if isinstance(apply_summary.get("applied_route_counts"), dict)
        else {}
    )

    decisions = (
        decisions_overlay_payload.get("decisions")
        if isinstance(decisions_overlay_payload.get("decisions"), list)
        else []
    )
    decision_counts = Counter(
        str(item.get("decision") or "").strip()
        for item in decisions
        if isinstance(item, dict)
    )
    queue_items = review_queue_payload.get("items") if isinstance(review_queue_payload.get("items"), list) else []

    blocks = _extract_blocks(blocks_payload)
    marker_count = 0
    marker_samples: list[str] = []
    forbidden_route_markers: list[str] = []
    for block in blocks:
        llm = _llm_enrichment(block)
        if not llm:
            continue
        block_id = _block_id(block)
        marker_keys = sorted(set(llm.keys()).intersection(ADVISORY_MARKER_KEYS))
        if marker_keys:
            marker_count += 1
            if len(marker_samples) < 20 and block_id:
                marker_samples.append(block_id)
            route = str(llm.get("apply_route") or "").strip()
            if route in {"review_rejected_apply", "review_defer_apply"}:
                forbidden_route_markers.append(block_id)

    warnings: list[str] = []
    if marker_count == 0:
        warnings.append("no_apply_provenance_markers_found")

    plan_matches_expected = (
        int(plan.get("safe_non_review_apply_candidates") or 0) == expected["safe_non_review_apply_candidates"]
        and int(plan.get("review_approved_apply_candidates") or 0) == expected["review_approved_apply_candidates"]
        and int(plan.get("review_needs_edit_apply_candidates") or 0) == expected["review_needs_edit_apply_candidates"]
        and int(plan.get("review_rejected_skip") or 0) == expected["review_rejected_skip"]
        and int(plan.get("review_defer_skip") or 0) == expected["review_defer_skip"]
        and int(apply_summary.get("updated_blocks") or 0) == expected["updated_blocks"]
    )

    route_consistency_passed = (
        len(queue_items) == 87
        and len(decisions) == 87
        and int(decision_counts.get("approved", 0)) == expected["review_approved_apply_candidates"]
        and int(decision_counts.get("needs_edit", 0)) == expected["review_needs_edit_apply_candidates"]
        and int(decision_counts.get("rejected", 0)) == expected["review_rejected_skip"]
        and int(decision_counts.get("defer", 0)) == expected["review_defer_skip"]
        and int(route_counts.get("review_approved_apply", 0)) == expected["review_approved_apply_candidates"]
        and int(route_counts.get("review_needs_edit_apply", 0)) == expected["review_needs_edit_apply_candidates"]
        and int(route_counts.get("safe_non_review_apply", 0)) == expected["safe_non_review_apply_candidates"]
        and int(route_counts.get("review_rejected_apply", 0)) == 0
        and int(route_counts.get("review_defer_apply", 0)) == 0
        and plan_matches_expected
        and not forbidden_route_markers
    )

    return {
        "schema_version": "post_apply_route_consistency_v1",
        "generated_at": utc_now_iso(),
        "queue_items_count": len(queue_items),
        "decisions_count": len(decisions),
        "decision_counts": dict(sorted(decision_counts.items())),
        "plan_counts": {
            "safe_non_review_apply_candidates": int(plan.get("safe_non_review_apply_candidates") or 0),
            "review_approved_apply_candidates": int(plan.get("review_approved_apply_candidates") or 0),
            "review_needs_edit_apply_candidates": int(plan.get("review_needs_edit_apply_candidates") or 0),
            "review_rejected_skip": int(plan.get("review_rejected_skip") or 0),
            "review_defer_skip": int(plan.get("review_defer_skip") or 0),
            "updated_blocks": int(apply_summary.get("updated_blocks") or 0),
        },
        "applied_route_counts": dict(sorted((route_counts or {}).items())),
        "rejected_applied_count": int(route_counts.get("review_rejected_apply", 0)),
        "defer_applied_count": int(route_counts.get("review_defer_apply", 0)),
        "provenance_markers_found_count": marker_count,
        "provenance_marker_block_ids_sample": marker_samples,
        "forbidden_route_markers": sorted(set(forbidden_route_markers)),
        "warnings": sorted(set(warnings)),
        "apply_route_consistency_passed": route_consistency_passed,
    }


def build_retrieval_quality_smoke(
    *,
    blocks_payload: Any,
    expected_source_id: str,
    required_terms: list[str] | None = None,
) -> dict[str, Any]:
    terms = required_terms or RETRIEVAL_TERMS
    blocks = _extract_blocks(blocks_payload)
    source_ids = sorted({_source_id(block) for block in blocks if _source_id(block)})
    query_results: dict[str, dict[str, Any]] = {}

    forbidden_key_hits: list[str] = []
    secret_like_hits: list[str] = []
    quote_violation_ids: list[str] = []
    practice_guardrail_missing_ids: list[str] = []
    internal_only_unsafe_exposure_count = 0

    for term in terms:
        term_norm = term.lower()
        hits: list[str] = []
        for block in blocks:
            text = str(block.get("text") or "").lower()
            llm = _llm_enrichment(block)
            summary = str(llm.get("summary") or "").lower()
            tag_blob = " ".join(_normalize_list(llm.get("tags"))).lower()
            if term_norm in text or term_norm in summary or term_norm in tag_blob:
                block_id = _block_id(block)
                if block_id:
                    hits.append(block_id)
            if len(hits) >= 20:
                break
        query_results[term] = {"hits_count": len(hits), "block_ids_sample": hits[:10]}

    for block in blocks:
        block_id = _block_id(block)
        gov = _governance(block)
        llm = _llm_enrichment(block)
        if not llm:
            continue

        forbidden_keys = sorted(set(llm.keys()).intersection(FORBIDDEN_LLM_KEYS))
        for key in forbidden_keys:
            forbidden_key_hits.append(f"{block_id}:{key}")
        for key, value in llm.items():
            if isinstance(value, str) and contains_secret_like_value(value):
                secret_like_hits.append(f"{block_id}:{key}")

        chunk_type = str(gov.get("chunk_type") or "").strip().lower()
        allowed_use = [item.lower() for item in _normalize_list(gov.get("allowed_use"))]
        summary = str(llm.get("summary") or "")
        avoid_when_blob = " ".join(_normalize_list(llm.get("avoid_when"))).lower()

        if chunk_type == "quote":
            # Quote chunks are allowed in KB; treat as violation only if summary is rendered as directive doctrine.
            if re.search(r"(ты должен|обязан|единственно верно|истинный путь|делай так)", summary.lower()):
                quote_violation_ids.append(block_id)
        if chunk_type == "practice":
            has_guardrail = any(marker in avoid_when_blob for marker in ("дистресс", "паник", "суиц", "психоз", "специалист"))
            has_directive = bool(re.search(r"(сделай|выполни|повтори|начни|должен)", summary.lower()))
            if has_directive and not has_guardrail:
                practice_guardrail_missing_ids.append(block_id)
        if "internal_only" in allowed_use and summary.strip():
            internal_only_unsafe_exposure_count += 1

    required_hits_ok = all(int((query_results.get(term) or {}).get("hits_count") or 0) > 0 for term in terms)
    raw_full_text_leak_detected = bool(forbidden_key_hits or secret_like_hits)
    retrieval_quality_passed = (
        source_ids == [expected_source_id]
        and required_hits_ok
        and not quote_violation_ids
        and not practice_guardrail_missing_ids
        and internal_only_unsafe_exposure_count == 0
        and not raw_full_text_leak_detected
    )

    return {
        "schema_version": "post_apply_retrieval_quality_smoke_v1",
        "generated_at": utc_now_iso(),
        "source_ids": source_ids,
        "query_results": query_results,
        "quote_violation_ids": sorted(set([x for x in quote_violation_ids if x])),
        "practice_guardrail_missing_ids": sorted(set([x for x in practice_guardrail_missing_ids if x])),
        "internal_only_unsafe_exposure_count": internal_only_unsafe_exposure_count,
        "forbidden_key_hits": sorted(set(forbidden_key_hits)),
        "secret_like_hits": sorted(set(secret_like_hits)),
        "raw_full_text_leak_detected": raw_full_text_leak_detected,
        "retrieval_quality_passed": retrieval_quality_passed,
    }


def build_writer_kb_policy_smoke(*, blocks_payload: Any) -> dict[str, Any]:
    try:
        import sys

        project_root = Path(__file__).resolve().parents[2]
        bot_psychologist_root = project_root / "bot_psychologist"
        if str(bot_psychologist_root) not in sys.path:
            sys.path.insert(0, str(bot_psychologist_root))

        from bot_agent.multiagent.contracts.memory_bundle import SemanticHit
        from bot_agent.multiagent.knowledge_policy import apply_knowledge_policy_v1
    except Exception as exc:
        return {
            "schema_version": "post_apply_writer_kb_policy_smoke_v1",
            "generated_at": utc_now_iso(),
            "writer_kb_policy_passed": False,
            "status": "dependency_error",
            "error": str(exc),
        }

    blocks = _extract_blocks(blocks_payload)
    hits: list[Any] = []
    for block in blocks:
        gov = _governance(block)
        llm = _llm_enrichment(block)
        content = str(llm.get("summary") or block.get("text") or "").strip()
        if not content:
            continue
        hits.append(
            SemanticHit(
                chunk_id=_block_id(block),
                source=str(block.get("source") or "book"),
                score=0.9,
                content=content,
                governance=gov,
                chunking_quality={},
            )
        )
        if len(hits) >= 120:
            break

    decisions, trace = apply_knowledge_policy_v1(hits)
    direct_quote_risk_count = 0
    internal_only_exposed_count = 0
    practice_without_guardrail_count = 0
    snippet_midword_cut_count = 0
    authority_reference_count = 0

    for decision in decisions:
        gov = decision.governance if isinstance(decision.governance, dict) else {}
        safety_flags = [item.lower() for item in _normalize_list(gov.get("safety_flags"))]
        allowed_use = [item.lower() for item in _normalize_list(gov.get("allowed_use"))]
        sanitized = str(decision.sanitized_content or "")
        chunk_type = str(gov.get("chunk_type") or "").strip().lower()
        if decision.allowed_for_writer and chunk_type == "quote":
            if re.search(r"(ты должен|обязан|истинный путь|делай так|единственно верно)", sanitized.lower()):
                direct_quote_risk_count += 1
        if decision.allowed_for_writer and "internal_only" in allowed_use:
            internal_only_exposed_count += 1
        if decision.allowed_for_practice and "practice_requires_low_resource_check" not in decision.risk_flags:
            practice_without_guardrail_count += 1
        tail = sanitized[:-1] if sanitized.endswith("…") else sanitized
        if sanitized.endswith("…") and re.search(r"\b[А-Яа-яЁё]{1,2}$", tail):
            snippet_midword_cut_count += 1
        if decision.allowed_for_writer and re.search(r"(кузниц[аы]|автор\s+утверждает|источник\s+доказывает)", sanitized.lower()):
            authority_reference_count += 1

    writer_kb_policy_passed = (
        direct_quote_risk_count == 0
        and internal_only_exposed_count == 0
        and practice_without_guardrail_count == 0
        and snippet_midword_cut_count <= 2
        and authority_reference_count == 0
    )
    return {
        "schema_version": "post_apply_writer_kb_policy_smoke_v1",
        "generated_at": utc_now_iso(),
        "evaluated_hits_count": len(hits),
        "policy_trace_version": str(trace.get("version") or ""),
        "direct_quote_risk_count": direct_quote_risk_count,
        "internal_only_exposed_count": internal_only_exposed_count,
        "practice_without_guardrail_count": practice_without_guardrail_count,
        "snippet_midword_cut_count": snippet_midword_cut_count,
        "authority_reference_count": authority_reference_count,
        "writer_kb_policy_passed": writer_kb_policy_passed,
        "status": "ok",
    }


def _http_json(url: str, timeout: float = 6.0) -> dict[str, Any]:
    req = Request(url=url, method="GET")
    try:
        with urlopen(req, timeout=timeout) as resp:  # noqa: S310
            raw = resp.read().decode("utf-8", errors="replace")
            body = json.loads(raw) if raw else None
            return {"ok": True, "status_code": int(resp.status), "body": body, "error": None}
    except URLError as exc:
        return {"ok": False, "status_code": None, "body": None, "error": str(exc)}
    except Exception as exc:
        return {"ok": False, "status_code": None, "body": None, "error": str(exc)}


def build_admin_api_runtime_smoke(
    *,
    admin_base_url: str,
    expected_source_id: str,
    expected_blocks_total: int,
    allow_offline_admin_checks: bool,
    require_admin_api: bool,
    http_get: Callable[[str], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    fetch = http_get or _http_json
    base = admin_base_url.rstrip("/")
    endpoints = ["/api/status", "/api/registry", "/api/dashboard", "/api/dashboard/"]
    checks: dict[str, dict[str, Any]] = {}
    for endpoint in endpoints:
        checks[endpoint] = fetch(f"{base}{endpoint}")

    reachable = [key for key, value in checks.items() if bool(value.get("ok"))]
    unreachable = [key for key, value in checks.items() if not bool(value.get("ok"))]
    all_unreachable = len(unreachable) == len(endpoints)

    status = "failed"
    admin_consistency_passed = False
    issues: list[str] = []
    warnings: list[str] = []

    if all_unreachable:
        if allow_offline_admin_checks:
            status = "skipped_offline_explicit"
            warnings.append("admin_api_unavailable_offline_mode")
        else:
            status = "blocked_admin_api_unavailable" if require_admin_api else "failed"
            issues.append("admin_api_unavailable")
    else:
        invalid_http = [key for key, value in checks.items() if not value.get("ok") or int(value.get("status_code") or 0) != 200]
        if invalid_http:
            status = "failed"
            issues.append("admin_api_partial_or_http_non_200")
            issues.extend([f"endpoint_invalid:{item}" for item in invalid_http])
        else:
            registry_body = checks["/api/registry"].get("body")
            dashboard_body = checks["/api/dashboard"].get("body")
            dashboard_slash_body = checks["/api/dashboard/"].get("body")
            focus_blocks = 0
            if isinstance(registry_body, dict):
                rows = registry_body.get("sources") if isinstance(registry_body.get("sources"), list) else []
                for row in rows:
                    if (
                        isinstance(row, dict)
                        and str(row.get("source_id") or "").strip() == expected_source_id
                        and str(row.get("status") or "").strip() == "done"
                    ):
                        focus_blocks = int(row.get("blocks_count") or 0)
                        break
            elif isinstance(registry_body, list):
                for row in registry_body:
                    if (
                        isinstance(row, dict)
                        and str(row.get("source_id") or "").strip() == expected_source_id
                        and str(row.get("status") or "").strip() == "done"
                    ):
                        focus_blocks = int(row.get("blocks_count") or 0)
                        break

            dashboard_schema_ok = isinstance(dashboard_body, dict) and isinstance(dashboard_slash_body, dict)
            if focus_blocks != expected_blocks_total:
                issues.append("registry_focus_blocks_mismatch")
            if not dashboard_schema_ok:
                issues.append("dashboard_payload_invalid")

            if not issues:
                status = "passed"
                admin_consistency_passed = True
            else:
                status = "failed"

    return {
        "schema_version": "post_apply_admin_api_runtime_smoke_v1",
        "generated_at": utc_now_iso(),
        "admin_base_url": admin_base_url,
        "require_admin_api": require_admin_api,
        "allow_offline_admin_checks": allow_offline_admin_checks,
        "api_checks": checks,
        "reachable_endpoints": reachable,
        "unreachable_endpoints": unreachable,
        "admin_runtime_status": status,
        "admin_consistency_passed": admin_consistency_passed,
        "issues": sorted(set(issues)),
        "warnings": sorted(set(warnings)),
    }


def build_no_mutation_proof(
    *,
    source_prd: str,
    blocks_hash_before: str,
    blocks_hash_after: str,
    registry_hash_before: str,
    registry_hash_after: str,
) -> dict[str, Any]:
    return {
        "schema_version": "post_apply_quality_gate_no_mutation_proof_v1",
        "source_prd": source_prd,
        "generated_at": utc_now_iso(),
        "all_blocks_merged_hash_before": blocks_hash_before,
        "all_blocks_merged_hash_after": blocks_hash_after,
        "registry_hash_before": registry_hash_before,
        "registry_hash_after": registry_hash_after,
        "all_blocks_merged_mutated": blocks_hash_before != blocks_hash_after,
        "registry_mutated": registry_hash_before != registry_hash_after,
        "provider_called": False,
        "chroma_reindex_performed": False,
        "production_apply_performed": False,
    }


def build_runtime_log_lines(values: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for key, value in values.items():
        line = re.sub(r"\s+", " ", f"{key}={value}".strip())
        if not line:
            continue
        if contains_secret_like_value(line):
            lines.append("[redacted_secret_like_line]")
            continue
        lines.append(line)
    return lines


def build_quality_gate_snapshot(
    *,
    source_prd: str,
    data_consistency: dict[str, Any],
    apply_route_consistency: dict[str, Any],
    retrieval_quality: dict[str, Any],
    writer_policy: dict[str, Any],
    admin_runtime: dict[str, Any],
    no_mutation_proof: dict[str, Any],
) -> dict[str, Any]:
    quality_gate_passed = (
        bool(data_consistency.get("data_consistency_passed"))
        and bool(apply_route_consistency.get("apply_route_consistency_passed"))
        and bool(retrieval_quality.get("retrieval_quality_passed"))
        and bool(writer_policy.get("writer_kb_policy_passed"))
        and bool(admin_runtime.get("admin_consistency_passed"))
    )
    admin_runtime_status = str(admin_runtime.get("admin_runtime_status") or "failed")
    diagnostic_center_ready = quality_gate_passed and admin_runtime_status == "passed"

    final_status = "failed"
    if quality_gate_passed:
        final_status = "passed"
    elif admin_runtime_status == "blocked_admin_api_unavailable":
        final_status = "done_with_admin_api_blocker"
    elif admin_runtime_status == "blocked_admin_launch_failed":
        final_status = "done_with_admin_launch_blocker"
    elif admin_runtime_status == "failed_schema_validation":
        final_status = "done_with_admin_schema_blocker"
    elif admin_runtime_status == "blocked_chroma_count_mismatch":
        final_status = "done_with_chroma_count_blocker"
    elif admin_runtime_status == "skipped_offline_explicit":
        final_status = "done_with_admin_api_blocker"

    return {
        "schema_version": "post_apply_quality_gate_snapshot_v1",
        "source_prd": source_prd,
        "generated_at": utc_now_iso(),
        "data_consistency_passed": bool(data_consistency.get("data_consistency_passed")),
        "apply_route_consistency_passed": bool(apply_route_consistency.get("apply_route_consistency_passed")),
        "retrieval_quality_passed": bool(retrieval_quality.get("retrieval_quality_passed")),
        "writer_kb_policy_passed": bool(writer_policy.get("writer_kb_policy_passed")),
        "admin_consistency_passed": bool(admin_runtime.get("admin_consistency_passed")),
        "admin_runtime_status": admin_runtime_status,
        "quality_gate_passed": quality_gate_passed,
        "diagnostic_center_ready": diagnostic_center_ready,
        "all_blocks_merged_mutated": bool(no_mutation_proof.get("all_blocks_merged_mutated")),
        "registry_mutated": bool(no_mutation_proof.get("registry_mutated")),
        "provider_called": False,
        "chroma_reindex_performed": False,
        "final_status": final_status,
    }
