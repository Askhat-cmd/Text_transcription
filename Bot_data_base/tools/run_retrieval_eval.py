from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


REQUIRED_CATEGORIES = [
    "self_criticism_achievement",
    "guilt_boundaries",
    "low_resource_support",
    "avoidance_procrastination",
    "anger_relationships",
    "fear_rejection",
    "body_awareness_freeze",
    "meaning_identity",
    "practice_safe_use",
    "safety_boundary",
    "internal_style_not_quote",
    "enrichment_visibility",
]

FORBIDDEN_KEY_TOKENS = {
    "content_full",
    "full_text",
    "raw_text",
    "raw_chunk",
    "unredacted_source_block",
}
FORBIDDEN_TEXT_TOKENS = (
    "content_full",
    "full_text",
    "unredacted source block",
    "raw full chunk text",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _preview(text: str, limit: int = 240) -> str:
    cleaned = " ".join(str(text or "").strip().split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: max(0, limit - 1)].rstrip() + "…"


def _to_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    raw = str(value).strip()
    if not raw:
        return []
    return [part.strip() for part in raw.split(",") if part.strip()]


def _norm_set(values: Any) -> set[str]:
    return {item.strip().lower() for item in _to_list(values) if item.strip()}


def _contains_marker(text: str, markers: list[str]) -> bool:
    normalized_text = (text or "").strip().lower()
    for marker in markers:
        if marker.strip().lower() in normalized_text:
            return True
    return False


def _http_json(
    method: str,
    url: str,
    payload: dict[str, Any] | None = None,
    timeout: float = 15.0,
) -> dict[str, Any]:
    body = None
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = Request(
        url=url,
        data=body,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
            parsed = json.loads(raw) if raw else None
            return {
                "ok": True,
                "status_code": int(response.status),
                "body": parsed,
                "error": None,
            }
    except HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            parsed_error = json.loads(raw) if raw else None
        except Exception:
            parsed_error = {"raw_text": raw[:500]}
        return {
            "ok": False,
            "status_code": int(exc.code),
            "body": parsed_error,
            "error": str(exc),
        }
    except URLError as exc:
        return {"ok": False, "status_code": None, "body": None, "error": str(exc)}
    except Exception as exc:  # pragma: no cover - defensive path
        return {"ok": False, "status_code": None, "body": None, "error": str(exc)}


def load_dataset(dataset_path: Path) -> dict[str, Any]:
    payload = json.loads(dataset_path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        payload = {"schema_version": "retrieval_eval_v1", "cases": payload}
    if not isinstance(payload, dict):
        raise ValueError("dataset must be a JSON object or list")
    return payload


def validate_dataset_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    cases = payload.get("cases")
    if not isinstance(cases, list):
        return ["dataset.cases must be a list"]
    if len(cases) < 24:
        errors.append("dataset must contain at least 24 cases")

    category_counter: Counter[str] = Counter()
    required_fields = {"id", "query", "category", "expected_any_lens_family", "expected_any_chunk_type", "expected_any_allowed_use"}

    seen_ids: set[str] = set()
    for idx, case in enumerate(cases):
        if not isinstance(case, dict):
            errors.append(f"case[{idx}] must be an object")
            continue
        missing = [field for field in required_fields if not case.get(field)]
        if missing:
            errors.append(f"case[{idx}] missing fields: {', '.join(missing)}")
        case_id = str(case.get("id") or "").strip()
        if case_id:
            if case_id in seen_ids:
                errors.append(f"duplicate case id: {case_id}")
            seen_ids.add(case_id)
        category = str(case.get("category") or "").strip()
        if category:
            category_counter[category] += 1

    for category in REQUIRED_CATEGORIES:
        if category_counter.get(category, 0) < 2:
            errors.append(f"category {category} must have >= 2 cases")
    return errors


def sanitize_hit(chunk: dict[str, Any], *, include_preview: bool) -> dict[str, Any]:
    governance = chunk.get("governance") if isinstance(chunk.get("governance"), dict) else {}
    chunking_quality = governance.get("chunking_quality") if isinstance(governance.get("chunking_quality"), dict) else {}
    llm_enrichment = governance.get("llm_enrichment") if isinstance(governance.get("llm_enrichment"), dict) else {}
    row = {
        "id": str(chunk.get("chunk_id") or "").strip(),
        "score": chunk.get("score"),
        "source_title": chunk.get("block_title"),
        "chunk_type": str(governance.get("chunk_type") or "").strip(),
        "allowed_use": _to_list(governance.get("allowed_use")),
        "safety_flags": _to_list(governance.get("safety_flags")),
        "lens_family": _to_list(governance.get("lens_family")),
        "not_for_direct_quote": governance.get("not_for_direct_quote"),
        "source_style_not_user_facing": governance.get("source_style_not_user_facing"),
        "mixed_intent_severity": str(chunking_quality.get("mixed_intent_severity") or "").strip(),
        "llm_enrichment_summary": str(
            governance.get("llm_enrichment_summary") or llm_enrichment.get("summary") or ""
        ).strip(),
        "llm_enrichment_tags": _to_list(
            governance.get("llm_enrichment_tags") or llm_enrichment.get("tags")
        ),
        "llm_enrichment_use_when": _to_list(
            governance.get("llm_enrichment_use_when") or llm_enrichment.get("use_when")
        ),
        "llm_enrichment_avoid_when": _to_list(
            governance.get("llm_enrichment_avoid_when") or llm_enrichment.get("avoid_when")
        ),
        "llm_enrichment_review_status": str(
            governance.get("llm_enrichment_review_status") or llm_enrichment.get("review_status") or ""
        ).strip(),
        "llm_enrichment_needs_human_review": governance.get(
            "llm_enrichment_needs_human_review"
        )
        if governance.get("llm_enrichment_needs_human_review") is not None
        else llm_enrichment.get("needs_human_review"),
    }
    if include_preview:
        row["content_preview"] = _preview(str(chunk.get("content") or ""))
    return row


def _hit_semantic_match(hit: dict[str, Any], case: dict[str, Any]) -> bool:
    expected_lens = _norm_set(case.get("expected_any_lens_family"))
    expected_chunk_types = _norm_set(case.get("expected_any_chunk_type"))
    expected_allowed = _norm_set(case.get("expected_any_allowed_use"))
    expected_markers = _to_list(case.get("expected_enrichment_markers_any"))

    lens_family = _norm_set(hit.get("lens_family"))
    chunk_type = str(hit.get("chunk_type") or "").strip().lower()
    allowed_use = _norm_set(hit.get("allowed_use"))

    if expected_lens and lens_family.intersection(expected_lens):
        return True
    if expected_chunk_types and expected_allowed:
        if chunk_type in expected_chunk_types and allowed_use.intersection(expected_allowed):
            return True

    marker_text = " ".join(
        [
            " ".join(_to_list(hit.get("llm_enrichment_tags"))),
            " ".join(_to_list(hit.get("llm_enrichment_use_when"))),
            str(hit.get("llm_enrichment_summary") or ""),
            " ".join(_to_list(hit.get("lens_family"))),
            str(hit.get("chunk_type") or ""),
        ]
    )
    if expected_markers and _contains_marker(marker_text, expected_markers):
        return True
    return False


def _has_governance_minimum(hit: dict[str, Any]) -> bool:
    if not str(hit.get("chunk_type") or "").strip():
        return False
    if not _to_list(hit.get("allowed_use")):
        return False
    if not _to_list(hit.get("safety_flags")):
        return False
    marker = hit.get("not_for_direct_quote")
    if marker is None:
        return False
    return True


def _collect_case_evaluation(case: dict[str, Any], top_hits: list[dict[str, Any]], *, top_k: int) -> dict[str, Any]:
    clipped_hits = top_hits[: max(1, top_k)]
    top1_hits = clipped_hits[:1]
    top3_hits = clipped_hits[: min(3, len(clipped_hits))]
    top5_hits = clipped_hits[: min(5, len(clipped_hits))]

    semantic_top1 = any(_hit_semantic_match(hit, case) for hit in top1_hits)
    semantic_top3 = any(_hit_semantic_match(hit, case) for hit in top3_hits)
    semantic_top5 = any(_hit_semantic_match(hit, case) for hit in top5_hits)

    governance_present = all(_has_governance_minimum(hit) for hit in top5_hits) if top5_hits else False
    allowed_use_present = all(bool(_to_list(hit.get("allowed_use"))) for hit in top5_hits) if top5_hits else False
    safety_flags_present = all(bool(_to_list(hit.get("safety_flags"))) for hit in top5_hits) if top5_hits else False

    expected_safety = _norm_set(case.get("expected_safety_flags_any"))
    safety_marker_present = True
    if expected_safety:
        safety_marker_present = any(_norm_set(hit.get("safety_flags")).intersection(expected_safety) for hit in top5_hits)

    must_not_allowed_use = _norm_set(case.get("must_not_allowed_use"))
    disallowed_hits = []
    if must_not_allowed_use:
        for hit in top5_hits:
            allowed_use = _norm_set(hit.get("allowed_use"))
            matched = sorted(list(allowed_use.intersection(must_not_allowed_use)))
            if matched:
                disallowed_hits.append({"hit_id": hit.get("id"), "matched_allowed_use": matched})

    internal_unsafe = 0
    if str(case.get("category") or "").strip() != "safety_boundary":
        for hit in top5_hits:
            if "internal_only" in _norm_set(hit.get("allowed_use")):
                internal_unsafe += 1

    enrichment_seen = any(
        bool(str(hit.get("llm_enrichment_summary") or "").strip())
        or bool(_to_list(hit.get("llm_enrichment_tags")))
        or bool(_to_list(hit.get("llm_enrichment_use_when")))
        for hit in top5_hits
    )

    reasons = []
    if not semantic_top5:
        reasons.append("missing_semantic_match_top5")
    if not governance_present:
        reasons.append("governance_fields_missing")
    if not allowed_use_present:
        reasons.append("allowed_use_missing")
    if not safety_flags_present:
        reasons.append("safety_flags_missing")
    if not safety_marker_present:
        reasons.append("expected_safety_marker_missing")
    if disallowed_hits:
        reasons.append("disallowed_allowed_use_present")
    if internal_unsafe > 0:
        reasons.append("internal_only_exposure_non_safety_case")

    return {
        "semantic_top1": semantic_top1,
        "semantic_top3": semantic_top3,
        "semantic_top5": semantic_top5,
        "governance_present_top5": governance_present,
        "allowed_use_present_top5": allowed_use_present,
        "safety_flags_present_top5": safety_flags_present,
        "expected_safety_marker_present_top5": safety_marker_present,
        "disallowed_allowed_use_hits": disallowed_hits,
        "internal_only_unsafe_exposure_count": internal_unsafe,
        "enrichment_seen": enrichment_seen,
        "weak_reasons": reasons,
    }


def detect_raw_leak(payload: Any) -> bool:
    stack = [payload]
    while stack:
        current = stack.pop()
        if isinstance(current, dict):
            for key, value in current.items():
                key_norm = str(key).strip().lower()
                if key_norm in FORBIDDEN_KEY_TOKENS:
                    return True
                stack.append(value)
        elif isinstance(current, list):
            stack.extend(current)
        elif isinstance(current, str):
            normalized = current.strip().lower()
            for token in FORBIDDEN_TEXT_TOKENS:
                if token in normalized:
                    return True
    return False


def run_retrieval_eval(
    *,
    dataset: dict[str, Any],
    api_base_url: str,
    top_k: int,
    timeout_seconds: float,
    include_sanitized_previews: bool,
    fail_on_api_error: bool,
    http_client: Any = _http_json,
) -> dict[str, Any]:
    api_base = api_base_url.rstrip("/")
    status_response = http_client("GET", f"{api_base}/api/status/", timeout=timeout_seconds)
    registry_response = http_client("GET", f"{api_base}/api/registry/", timeout=timeout_seconds)

    status_ok = bool(status_response.get("ok"))
    registry_ok = bool(registry_response.get("ok"))
    if fail_on_api_error and (not status_ok or not registry_ok):
        raise RuntimeError("API status/registry preflight failed")

    cases: list[dict[str, Any]] = dataset.get("cases") or []
    case_rows: list[dict[str, Any]] = []
    weak_cases: list[dict[str, Any]] = []
    semantic_top1_hits = 0
    semantic_top3_hits = 0
    semantic_top5_hits = 0
    governance_top5_pass = 0
    allowed_top5_pass = 0
    safety_top5_pass = 0
    queries_ok = 0
    queries_failed = 0
    enrichment_seen_count = 0
    internal_only_unsafe_exposure_count = 0

    for case in cases:
        query = str(case.get("query") or "").strip()
        response = http_client(
            "POST",
            f"{api_base}/api/query/",
            payload={
                "query": query,
                "top_k": int(max(1, top_k)),
                "pre_filter_k": int(max(10, top_k * 2)),
                "use_rerank": False,
                "search_mode": "semantic",
            },
            timeout=timeout_seconds,
        )
        ok = bool(response.get("ok"))
        if ok:
            queries_ok += 1
        else:
            queries_failed += 1
            if fail_on_api_error:
                raise RuntimeError(f"/api/query failed for case {case.get('id')}: {response.get('error')}")

        body = response.get("body") if isinstance(response.get("body"), dict) else {}
        chunks = body.get("chunks") if isinstance(body, dict) else []
        if not isinstance(chunks, list):
            chunks = []
        top_hits = [sanitize_hit(chunk, include_preview=include_sanitized_previews) for chunk in chunks[:top_k]]
        eval_result = _collect_case_evaluation(case, top_hits, top_k=top_k) if ok else {
            "semantic_top1": False,
            "semantic_top3": False,
            "semantic_top5": False,
            "governance_present_top5": False,
            "allowed_use_present_top5": False,
            "safety_flags_present_top5": False,
            "expected_safety_marker_present_top5": False,
            "disallowed_allowed_use_hits": [],
            "internal_only_unsafe_exposure_count": 0,
            "enrichment_seen": False,
            "weak_reasons": ["api_error"],
        }

        semantic_top1_hits += 1 if eval_result["semantic_top1"] else 0
        semantic_top3_hits += 1 if eval_result["semantic_top3"] else 0
        semantic_top5_hits += 1 if eval_result["semantic_top5"] else 0
        governance_top5_pass += 1 if eval_result["governance_present_top5"] else 0
        allowed_top5_pass += 1 if eval_result["allowed_use_present_top5"] else 0
        safety_top5_pass += 1 if eval_result["safety_flags_present_top5"] else 0
        enrichment_seen_count += 1 if eval_result["enrichment_seen"] else 0
        internal_only_unsafe_exposure_count += int(eval_result["internal_only_unsafe_exposure_count"])

        row = {
            "id": case.get("id"),
            "query": query,
            "category": case.get("category"),
            "status": "ok" if ok else "error",
            "http_status": response.get("status_code"),
            "error": response.get("error"),
            "top_hits": top_hits,
            "checks": eval_result,
        }
        case_rows.append(row)
        if eval_result["weak_reasons"]:
            weak_cases.append(
                {
                    "id": row["id"],
                    "query": row["query"],
                    "category": row["category"],
                    "why_failed": eval_result["weak_reasons"],
                    "top_summaries": [
                        {
                            "hit_id": hit.get("id"),
                            "chunk_type": hit.get("chunk_type"),
                            "allowed_use": hit.get("allowed_use"),
                            "safety_flags": hit.get("safety_flags"),
                            "lens_family": hit.get("lens_family"),
                            "content_preview": hit.get("content_preview"),
                            "llm_enrichment_summary": hit.get("llm_enrichment_summary"),
                        }
                        for hit in top_hits[:3]
                    ],
                    "missing_expected": {
                        "lens_family": _to_list(case.get("expected_any_lens_family")),
                        "chunk_type": _to_list(case.get("expected_any_chunk_type")),
                        "allowed_use": _to_list(case.get("expected_any_allowed_use")),
                    },
                    "recommendation": "retrieval calibration needed",
                }
            )

    cases_total = len(cases)
    safe_denominator = max(1, cases_total)
    scorecard = {
        "cases_total": cases_total,
        "api_status_ok": status_ok,
        "api_registry_ok": registry_ok,
        "queries_ok": queries_ok,
        "queries_failed": queries_failed,
        "top1_semantic_match_rate": round(semantic_top1_hits / safe_denominator, 4),
        "top3_semantic_match_rate": round(semantic_top3_hits / safe_denominator, 4),
        "top5_semantic_match_rate": round(semantic_top5_hits / safe_denominator, 4),
        "top5_governance_present_rate": round(governance_top5_pass / safe_denominator, 4),
        "top5_allowed_use_present_rate": round(allowed_top5_pass / safe_denominator, 4),
        "top5_safety_flags_present_rate": round(safety_top5_pass / safe_denominator, 4),
        "raw_full_text_leak_detected": False,
        "internal_only_unsafe_exposure_count": internal_only_unsafe_exposure_count,
        "enrichment_metadata_seen_count": enrichment_seen_count,
        "weak_cases_count": len(weak_cases),
    }

    results_payload = {
        "generated_at": _utc_now(),
        "schema_version": "retrieval_eval_v1_results",
        "api_base_url": api_base,
        "dataset_path": dataset.get("dataset_path"),
        "dataset_version": dataset.get("schema_version") or "retrieval_eval_v1",
        "cases": case_rows,
    }
    leak_detected = detect_raw_leak(results_payload)
    scorecard["raw_full_text_leak_detected"] = bool(leak_detected)

    status_body = status_response.get("body") if isinstance(status_response.get("body"), dict) else {}
    registry_body = registry_response.get("body") if isinstance(registry_response.get("body"), dict) else {}
    status_snapshot = {
        "generated_at": _utc_now(),
        "ok": status_ok,
        "status_code": status_response.get("status_code"),
        "error": status_response.get("error"),
        "service_status": status_body.get("status"),
    }
    registry_snapshot = {
        "generated_at": _utc_now(),
        "ok": registry_ok,
        "status_code": registry_response.get("status_code"),
        "error": registry_response.get("error"),
        "total": registry_body.get("total"),
    }
    return {
        "status_snapshot": status_snapshot,
        "registry_snapshot": registry_snapshot,
        "results": results_payload,
        "scorecard": scorecard,
        "weak_cases": weak_cases,
    }


def write_eval_artifacts(result: dict[str, Any], *, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "api_status_snapshot.json").write_text(
        json.dumps(result["status_snapshot"], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_dir / "api_registry_snapshot.json").write_text(
        json.dumps(result["registry_snapshot"], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_dir / "retrieval_eval_results.json").write_text(
        json.dumps(result["results"], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_dir / "retrieval_eval_scorecard.json").write_text(
        json.dumps(result["scorecard"], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_dir / "weak_cases.json").write_text(
        json.dumps(result["weak_cases"], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run deterministic retrieval eval against BotDB API.")
    parser.add_argument("--dataset", default="Bot_data_base/eval/retrieval_eval_v1.json")
    parser.add_argument("--api-base-url", default="http://127.0.0.1:8013")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--timeout-seconds", type=float, default=15.0)
    parser.add_argument("--output-dir", default="TO_DO_LIST/logs/PRD-046.0.6")
    parser.add_argument("--fail-on-api-error", action="store_true")
    parser.add_argument("--include-sanitized-previews", action="store_true")
    args = parser.parse_args()

    dataset_path = Path(args.dataset)
    payload = load_dataset(dataset_path)
    payload["dataset_path"] = str(dataset_path.as_posix())
    dataset_errors = validate_dataset_payload(payload)
    if dataset_errors:
        print(json.dumps({"dataset_validation_errors": dataset_errors}, ensure_ascii=False, indent=2))
        return 2

    eval_result = run_retrieval_eval(
        dataset=payload,
        api_base_url=args.api_base_url,
        top_k=max(1, int(args.top_k)),
        timeout_seconds=float(args.timeout_seconds),
        include_sanitized_previews=bool(args.include_sanitized_previews),
        fail_on_api_error=bool(args.fail_on_api_error),
    )
    write_eval_artifacts(eval_result, output_dir=Path(args.output_dir))

    print(
        json.dumps(
            {
                "dataset_cases": len(payload.get("cases") or []),
                "scorecard": eval_result["scorecard"],
                "output_dir": str(Path(args.output_dir).as_posix()),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

