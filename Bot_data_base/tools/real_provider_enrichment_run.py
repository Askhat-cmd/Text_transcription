from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None

from tools.llm_enrichment_post_reprocess import (
    _load_json,
    _normalize_list,
    _sha256_file,
    _source_id,
    _tokenize,
    _write_json,
    build_inventory,
    build_retrieval_preview,
    build_review_queue_rebaseline,
    evaluate_preflight,
    generate_overlay,
    validate_overlay,
)
from tools.kb_quality_audit import load_processed_blocks


RUN1_TAG = "PRD-046.0.9-RUN1"
EXPECTED_BLOCKS = 247
DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_INPUT_PRICE_PER_1K = 0.00015
DEFAULT_OUTPUT_PRICE_PER_1K = 0.0006


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _estimate_tokens_from_text(text: str) -> int:
    return max(1, len(_tokenize(text)))


def _estimate_inventory_tokens(inventory: dict[str, Any]) -> tuple[int, int]:
    total_in = 0
    total_out = 0
    for row in inventory.get("items") or []:
        if not isinstance(row, dict):
            continue
        preview = str(row.get("safe_preview") or "")
        total_in += _estimate_tokens_from_text(preview) + 140
        total_out += 220
    return total_in, total_out


def _provider_test_call(model: str, timeout_seconds: float) -> tuple[bool, int, int, str]:
    if OpenAI is None:
        return False, 0, 0, "openai_package_unavailable"
    api_key = str(os.getenv("OPENAI_API_KEY") or "").strip()
    if not api_key:
        return False, 0, 0, "api_key_missing"
    try:
        client = OpenAI(timeout=timeout_seconds)
        response = client.chat.completions.create(
            model=model,
            temperature=0.0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "Return JSON object only."},
                {"role": "user", "content": "Return {\"ok\":true}"},
            ],
        )
        usage = response.usage
        in_t = int(getattr(usage, "prompt_tokens", 0) or 0)
        out_t = int(getattr(usage, "completion_tokens", 0) or 0)
        _ = json.loads(str(response.choices[0].message.content or "{}"))
        return True, in_t, out_t, ""
    except Exception as exc:  # pragma: no cover - network/runtime dependent
        return False, 0, 0, f"test_call_failed:{type(exc).__name__}"


def run_provider_preflight(
    *,
    inventory: dict[str, Any],
    model: str,
    configured_budget_usd: float,
    hard_stop_budget_usd: float,
    timeout_seconds: float,
    input_price_per_1k: float,
    output_price_per_1k: float,
) -> dict[str, Any]:
    est_in, est_out = _estimate_inventory_tokens(inventory)
    est_cost = ((est_in / 1000.0) * input_price_per_1k) + ((est_out / 1000.0) * output_price_per_1k)
    api_key_present = bool(str(os.getenv("OPENAI_API_KEY") or "").strip())
    blockers: list[str] = []

    if not model.strip():
        blockers.append("model_missing")
    if configured_budget_usd <= 0:
        blockers.append("configured_budget_missing")
    if hard_stop_budget_usd <= 0:
        blockers.append("hard_stop_budget_missing")
    if configured_budget_usd > 0 and hard_stop_budget_usd > 0 and hard_stop_budget_usd < configured_budget_usd:
        blockers.append("hard_stop_lower_than_configured_budget")

    client_init_ok = OpenAI is not None and api_key_present
    test_ok = False
    test_in = 0
    test_out = 0
    test_error = ""
    if api_key_present and OpenAI is not None and model.strip():
        test_ok, test_in, test_out, test_error = _provider_test_call(model=model, timeout_seconds=timeout_seconds)
        if not test_ok:
            blockers.append(test_error or "test_call_failed")
    else:
        if not api_key_present:
            blockers.append("api_key_missing")
        if OpenAI is None:
            blockers.append("openai_package_unavailable")

    if configured_budget_usd > 0 and est_cost > configured_budget_usd:
        blockers.append("estimated_cost_exceeds_configured_budget")

    return {
        "schema_version": "provider_preflight_v1",
        "source_prd": RUN1_TAG,
        "generated_at": _utc_now(),
        "passed": len(blockers) == 0,
        "provider": "openai",
        "model": model,
        "api_key_present": api_key_present,
        "client_init_ok": client_init_ok,
        "test_call_ok": test_ok,
        "test_call_tokens_input": test_in,
        "test_call_tokens_output": test_out,
        "estimated_blocks_to_process": len(inventory.get("items") or []),
        "estimated_max_input_tokens": est_in,
        "estimated_max_output_tokens": est_out,
        "configured_budget_usd": round(configured_budget_usd, 4),
        "hard_stop_budget_usd": round(hard_stop_budget_usd, 4),
        "estimated_cost_usd": round(est_cost, 6),
        "blockers": blockers,
    }


def _pick_pilot_inventory(inventory: dict[str, Any], limit: int = 5) -> dict[str, Any]:
    items = inventory.get("items") if isinstance(inventory.get("items"), list) else []
    by_type: dict[str, list[dict[str, Any]]] = {}
    for row in items:
        if not isinstance(row, dict):
            continue
        by_type.setdefault(str(row.get("chunk_type") or "").lower(), []).append(row)

    selected: list[dict[str, Any]] = []
    selected_ids: set[str] = set()
    preferred = ("practice", "lens", "quote", "case", "theory")
    for typ in preferred:
        for row in by_type.get(typ, []):
            bid = str(row.get("block_id") or "")
            if bid and bid not in selected_ids:
                selected.append(row)
                selected_ids.add(bid)
                break
        if len(selected) >= limit:
            break

    if len(selected) < limit:
        for row in items:
            bid = str(row.get("block_id") or "")
            if bid and bid not in selected_ids:
                selected.append(row)
                selected_ids.add(bid)
            if len(selected) >= limit:
                break

    return {
        "schema_version": inventory.get("schema_version"),
        "source_prd": RUN1_TAG,
        "generated_at": _utc_now(),
        "blocks_total": len(selected),
        "items": selected[:limit],
    }


def _estimate_usage_from_overlay(overlay: dict[str, Any], input_price_per_1k: float, output_price_per_1k: float) -> dict[str, Any]:
    rows = overlay.get("items") if isinstance(overlay.get("items"), list) else []
    req = 0
    in_tokens = 0
    out_tokens = 0
    completed = 0
    failed = 0
    missing = 0
    for row in rows:
        if not isinstance(row, dict):
            continue
        req += 1
        preview = str(row.get("advisory", {}).get("summary") if isinstance(row.get("advisory"), dict) else "")
        in_tokens += 140
        out_tokens += max(20, _estimate_tokens_from_text(preview))
        reasons = _normalize_list((row.get("quality") or {}).get("review_reasons")) if isinstance(row.get("quality"), dict) else []
        if any(r.startswith("provider_error:") for r in reasons):
            failed += 1
        elif "provider_unavailable" in reasons:
            failed += 1
            missing += 1
        elif "missing_real_provider_output" in reasons:
            missing += 1
        else:
            completed += 1
    cost = ((in_tokens / 1000.0) * input_price_per_1k) + ((out_tokens / 1000.0) * output_price_per_1k)
    return {
        "input_tokens": int(in_tokens),
        "output_tokens": int(out_tokens),
        "requests": int(req),
        "estimated_cost_usd": round(cost, 6),
        "items_completed": int(completed),
        "items_failed": int(failed),
        "missing_real_provider_output_count": int(missing),
    }


def _reason_counts(queue: dict[str, Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in queue.get("items") or []:
        if not isinstance(item, dict):
            continue
        for reason in item.get("review_reasons") or []:
            token = str(reason)
            counts[token] = counts.get(token, 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))


def _write_run1_reports(
    *,
    reports_dir: Path,
    preflight: dict[str, Any],
    provider_preflight: dict[str, Any],
    pilot: dict[str, Any] | None,
    validation: dict[str, Any] | None,
    queue: dict[str, Any] | None,
    scorecard: dict[str, Any] | None,
    retrieval_preview: dict[str, Any] | None,
    no_mutation: dict[str, Any] | None,
    status: str,
    next_prd: str,
) -> None:
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "PRD-046.0.9-RUN1_PROVIDER_PREFLIGHT_REPORT.md").write_text(
        "\n".join(
            [
                "# PRD-046.0.9-RUN1 PROVIDER PREFLIGHT REPORT",
                "",
                f"- passed: `{provider_preflight.get('passed')}`",
                f"- model: `{provider_preflight.get('model')}`",
                f"- api_key_present: `{provider_preflight.get('api_key_present')}`",
                f"- test_call_ok: `{provider_preflight.get('test_call_ok')}`",
                f"- configured_budget_usd: `{provider_preflight.get('configured_budget_usd')}`",
                f"- hard_stop_budget_usd: `{provider_preflight.get('hard_stop_budget_usd')}`",
                f"- estimated_cost_usd: `{provider_preflight.get('estimated_cost_usd')}`",
                f"- blockers: `{provider_preflight.get('blockers')}`",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (reports_dir / "PRD-046.0.9-RUN1_PILOT_REPORT.md").write_text(
        "\n".join(
            [
                "# PRD-046.0.9-RUN1 PILOT REPORT",
                "",
                f"- pilot_executed: `{pilot is not None}`",
                f"- pilot_status: `{(pilot or {}).get('status', 'not_run')}`",
                f"- pilot_validation_errors: `{((pilot or {}).get('validation') or {}).get('validation_errors_count', 0)}`",
                f"- pilot_provider_status: `{((pilot or {}).get('overlay_meta') or {}).get('provider_status', '')}`",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (reports_dir / "PRD-046.0.9-RUN1_REAL_ENRICHMENT_VALIDATION_REPORT.md").write_text(
        "\n".join(
            [
                "# PRD-046.0.9-RUN1 REAL ENRICHMENT VALIDATION REPORT",
                "",
                f"- status: `{status}`",
                f"- validation_errors_count: `{(validation or {}).get('validation_errors_count', 0)}`",
                f"- validation_warnings_count: `{(validation or {}).get('validation_warnings_count', 0)}`",
                f"- raw_full_text_leak_detected: `{(validation or {}).get('raw_full_text_leak_detected', False)}`",
                f"- governance_authority_mutated: `{(validation or {}).get('governance_authority_mutated', False)}`",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (reports_dir / "PRD-046.0.9-RUN1_REVIEW_QUEUE_REPORT.md").write_text(
        "\n".join(
            [
                "# PRD-046.0.9-RUN1 REVIEW QUEUE REPORT",
                "",
                f"- review_queue_items_count: `{(queue or {}).get('items_count', 0)}`",
                f"- priority_counts: `{(queue or {}).get('priority_counts', {})}`",
                f"- top_reason_counts: `{dict(list(((queue or {}).get('reason_counts') or {}).items())[:10])}`",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (reports_dir / "PRD-046.0.9-RUN1_RETRIEVAL_PREVIEW_REPORT.md").write_text(
        "\n".join(
            [
                "# PRD-046.0.9-RUN1 RETRIEVAL PREVIEW REPORT",
                "",
                f"- queries_total: `{(retrieval_preview or {}).get('queries_total', 0)}`",
                f"- top_k_before_summary_available: `{(retrieval_preview or {}).get('top_k_before_summary_available', 0)}`",
                f"- top_k_overlay_summary_available: `{(retrieval_preview or {}).get('top_k_overlay_summary_available', 0)}`",
                f"- useful: `{(retrieval_preview or {}).get('overlay_candidate_useful_count', 0)}`",
                f"- noise: `{(retrieval_preview or {}).get('overlay_candidate_noise_count', 0)}`",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (reports_dir / "PRD-046.0.9-RUN1_NEXT_PRD_RECOMMENDATION.md").write_text(
        "\n".join(
            [
                "# PRD-046.0.9-RUN1 NEXT PRD RECOMMENDATION",
                "",
                f"- Recommended: `{next_prd}`",
                f"- status: `{status}`",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    impl = reports_dir / "PRD-046.0.9-RUN1_IMPLEMENTATION_REPORT.md"
    impl.write_text(
        "\n".join(
            [
                "# PRD-046.0.9-RUN1 IMPLEMENTATION REPORT",
                "",
                "## Status",
                f"- Implementation: `{status}`",
                "- Branch: `main`",
                "- Runtime behavior changed: false",
                "- Writer changed: false",
                "- DiagnosticCard changed: false",
                "- Thread Manager changed: false",
                "- State Analyzer changed: false",
                "- Context Assembly changed: false",
                "- Production knowledge blocks mutated: false",
                "- Registry mutated: false",
                "- Chroma reindex performed: false",
                "- Production enrichment apply performed: false",
                "",
                "## Provider",
                f"- provider_status: `{(scorecard or {}).get('provider_status', '')}`",
                f"- model: `{provider_preflight.get('model')}`",
                f"- pilot_called: `{pilot is not None}`",
                f"- real_run_called: `{scorecard is not None}`",
                f"- input_tokens: `{((scorecard or {}).get('provider_usage') or {}).get('input_tokens', 0)}`",
                f"- output_tokens: `{((scorecard or {}).get('provider_usage') or {}).get('output_tokens', 0)}`",
                f"- requests: `{((scorecard or {}).get('provider_usage') or {}).get('requests', 0)}`",
                f"- estimated_cost_usd: `{((scorecard or {}).get('provider_usage') or {}).get('estimated_cost_usd', 0.0)}`",
                f"- budget_status: `{'ok' if provider_preflight.get('passed') else 'blocked'}`",
                "",
                "## Enrichment",
                f"- blocks_total: `{(scorecard or {}).get('blocks_total', 0)}`",
                f"- items_attempted: `{(scorecard or {}).get('items_attempted', 0)}`",
                f"- items_completed: `{(scorecard or {}).get('items_completed', 0)}`",
                f"- items_failed: `{(scorecard or {}).get('items_failed', 0)}`",
                f"- missing_real_provider_output_count: `{(scorecard or {}).get('missing_real_provider_output_count', 0)}`",
                f"- validation_errors_count: `{(scorecard or {}).get('validation_errors_count', 0)}`",
                f"- validation_warnings_count: `{(scorecard or {}).get('validation_warnings_count', 0)}`",
                "",
                "## Review Queue",
                f"- review_queue_items_count: `{(queue or {}).get('items_count', 0)}`",
                f"- P0: `{((queue or {}).get('priority_counts') or {}).get('P0', 0)}`",
                f"- P1: `{((queue or {}).get('priority_counts') or {}).get('P1', 0)}`",
                f"- P2: `{((queue or {}).get('priority_counts') or {}).get('P2', 0)}`",
                f"- top_reason_counts: `{dict(list(((queue or {}).get('reason_counts') or {}).items())[:10])}`",
                "",
                "## No Mutation",
                f"- all_blocks_merged_mutated: `{(no_mutation or {}).get('all_blocks_merged_mutated', False)}`",
                f"- registry_mutated: `{(no_mutation or {}).get('registry_mutated', False)}`",
                f"- chroma_mutated: `{(no_mutation or {}).get('chroma_mutated', False)}`",
                "",
                "## Tests",
                "- summary: see `TO_DO_LIST/logs/PRD-046.0.9-RUN1/test_command_output.txt`",
                "",
                "## Commit / Push",
                "- Commit hash: `pending`",
                "- Push status: `pending`",
                "- Report sync: `pending`",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def run_real_provider_cycle(
    *,
    mode: str,
    model: str,
    blocks_path: Path,
    registry_path: Path,
    base_rebaseline_logs_dir: Path,
    logs_dir: Path,
    reports_dir: Path,
    overlay_input_path: Path | None,
    batch_size: int,
    resume: bool,
    limit: int,
    force: bool,
    timeout_seconds: float,
    configured_budget_usd: float,
    hard_stop_budget_usd: float,
    input_price_per_1k: float,
    output_price_per_1k: float,
) -> dict[str, Any]:
    logs_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)
    all_blocks_before = _sha256_file(blocks_path) if blocks_path.exists() else ""
    registry_before = _sha256_file(registry_path) if registry_path.exists() else ""

    preflight = evaluate_preflight(
        blocks_path=blocks_path,
        registry_path=registry_path,
        chroma_reindex_result_path=Path("TO_DO_LIST/logs/PRD-046.0.8.1/chroma_reindex_result.json"),
        review_queue_staleness_path=Path("TO_DO_LIST/logs/PRD-046.0.8.1/review_queue_staleness_report.json"),
        review_queue_new_baseline_path=Path("TO_DO_LIST/logs/PRD-046.0.8.1/review_queue_new_baseline.json"),
        retrieval_eval_path=Path("TO_DO_LIST/logs/PRD-046.0.8.1/retrieval_eval_after_reprocess.json"),
        legacy_sd_usage_report_path=Path("TO_DO_LIST/logs/PRD-046.0.8.1/post_apply_legacy_sd_usage_report.json"),
    )
    _write_json(logs_dir / "enrichment_preflight.json", preflight)
    if not preflight.get("passed"):
        return {"status": "blocked", "reason": "preflight_failed", "blockers": preflight.get("blockers")}

    baseline_overlay = base_rebaseline_logs_dir / "enrichment_candidate_overlay.json"
    baseline_inventory = base_rebaseline_logs_dir / "enrichment_inventory.json"
    baseline_score = base_rebaseline_logs_dir / "enrichment_scorecard.json"
    if not (baseline_overlay.exists() and baseline_inventory.exists() and baseline_score.exists()):
        return {"status": "blocked", "reason": "missing_prd_046_0_9_baseline"}

    blocks = load_processed_blocks(blocks_path)
    inventory = build_inventory(blocks)
    _write_json(logs_dir / "enrichment_inventory_snapshot.json", inventory)

    provider_preflight = run_provider_preflight(
        inventory=inventory,
        model=model,
        configured_budget_usd=configured_budget_usd,
        hard_stop_budget_usd=hard_stop_budget_usd,
        timeout_seconds=timeout_seconds,
        input_price_per_1k=input_price_per_1k,
        output_price_per_1k=output_price_per_1k,
    )
    _write_json(logs_dir / "provider_preflight.json", provider_preflight)
    if mode == "preflight":
        _write_run1_reports(
            reports_dir=reports_dir,
            preflight=preflight,
            provider_preflight=provider_preflight,
            pilot=None,
            validation=None,
            queue=None,
            scorecard=None,
            retrieval_preview=None,
            no_mutation=None,
            status="done" if provider_preflight.get("passed") else "blocked_by_provider",
            next_prd="PRD-046.0.9-RUN1-FIX" if not provider_preflight.get("passed") else "PRD-046.0.9-RUN1",
        )
        return {"status": "done" if provider_preflight.get("passed") else "blocked_by_provider", "provider_preflight": provider_preflight}

    if not provider_preflight.get("passed"):
        _write_json(
            logs_dir / "pilot_enrichment_overlay.json",
            {
                "schema_version": "pilot_enrichment_overlay_v1",
                "source_prd": RUN1_TAG,
                "status": "blocked_by_provider",
                "reason": "provider_preflight_failed",
                "items": [],
            },
        )
        _write_json(
            logs_dir / "real_enrichment_candidate_overlay.json",
            {
                "schema_version": "real_enrichment_candidate_overlay_v1",
                "source_prd": RUN1_TAG,
                "status": "blocked_by_provider",
                "reason": "provider_preflight_failed",
                "items": [],
            },
        )
        _write_json(
            logs_dir / "real_enrichment_validation.json",
            {
                "schema_version": "real_enrichment_validation_v1",
                "source_prd": RUN1_TAG,
                "validation_status": "blocked_by_provider",
                "validation_errors_count": 0,
                "validation_warnings_count": 0,
                "missing_real_provider_output_count": len(inventory.get("items") or []),
            },
        )
        _write_json(
            logs_dir / "review_queue_after_real_enrichment.json",
            {
                "schema_version": "post_reprocess_review_queue_after_real_enrichment_v1",
                "source_prd": RUN1_TAG,
                "items_count": 0,
                "priority_counts": {"P0": 0, "P1": 0, "P2": 0},
                "reason_counts": {},
                "items": [],
            },
        )
        _write_json(
            logs_dir / "real_enrichment_scorecard.json",
            {
                "schema_version": "real_enrichment_scorecard_v1",
                "source_prd": RUN1_TAG,
                "blocks_total": len(inventory.get("items") or []),
                "provider_status": "blocked_by_provider",
                "items_attempted": 0,
                "items_completed": 0,
                "items_failed": 0,
                "validation_errors_count": 0,
                "validation_warnings_count": 0,
                "missing_real_provider_output_count": len(inventory.get("items") or []),
                "needs_human_review_count": len(inventory.get("items") or []),
                "review_queue_items_count": 0,
                "avg_confidence": 0.0,
                "avg_self_contained_score": 0.0,
                "summary_present_rate": 0.0,
                "tags_present_rate": 0.0,
                "use_when_present_rate": 0.0,
                "avoid_when_present_rate": 0.0,
                "lens_family_candidates_present_rate": 0.0,
                "raw_full_text_leak_detected": False,
                "governance_authority_mutated": False,
                "production_apply_performed": False,
                "chroma_reindex_performed": False,
                "provider_usage": {"input_tokens": 0, "output_tokens": 0, "requests": 0, "estimated_cost_usd": 0.0},
            },
        )
        _write_json(
            logs_dir / "real_enrichment_retrieval_preview.json",
            {
                "schema_version": "real_enrichment_retrieval_preview_v1",
                "source_prd": RUN1_TAG,
                "status": "blocked_by_provider",
                "queries_total": 0,
                "queries_ok": 0,
                "top_k_before_summary_available": 0,
                "top_k_overlay_summary_available": 0,
                "overlay_candidate_useful_count": 0,
                "overlay_candidate_noise_count": 0,
                "examples": [],
            },
        )
        _write_run1_reports(
            reports_dir=reports_dir,
            preflight=preflight,
            provider_preflight=provider_preflight,
            pilot=None,
            validation=None,
            queue=None,
            scorecard=None,
            retrieval_preview=None,
            no_mutation=None,
            status="blocked_by_provider",
            next_prd="PRD-046.0.9-RUN1-FIX",
        )
        return {"status": "blocked_by_provider", "provider_preflight": provider_preflight}

    pilot_data: dict[str, Any] | None = None
    if mode in {"pilot", "real"}:
        pilot_inventory = _pick_pilot_inventory(inventory=inventory, limit=max(1, min(5, limit if limit > 0 else 5)))
        pilot_overlay_path = logs_dir / "pilot_enrichment_overlay.json"
        pilot_overlay, pilot_meta = generate_overlay(
            inventory=pilot_inventory,
            mode="real",
            overlay_path_for_validation=pilot_overlay_path,
            batch_size=max(1, batch_size),
            resume=False,
            model=model,
            timeout_seconds=timeout_seconds,
        )
        _write_json(pilot_overlay_path, pilot_overlay)
        pilot_validation = validate_overlay(overlay=pilot_overlay, inventory=pilot_inventory)
        _write_json(logs_dir / "pilot_enrichment_validation.json", pilot_validation)
        pilot_usage = _estimate_usage_from_overlay(pilot_overlay, input_price_per_1k=input_price_per_1k, output_price_per_1k=output_price_per_1k)
        pilot_data = {"status": "done", "overlay_meta": pilot_meta, "validation": pilot_validation, "usage": pilot_usage}
        if pilot_meta.get("provider_status") != "ok" or int(pilot_validation.get("validation_errors_count") or 0) > 0:
            _write_run1_reports(
                reports_dir=reports_dir,
                preflight=preflight,
                provider_preflight=provider_preflight,
                pilot=pilot_data,
                validation=pilot_validation,
                queue=None,
                scorecard=None,
                retrieval_preview=None,
                no_mutation=None,
                status="blocked_by_provider",
                next_prd="PRD-046.0.9-RUN1-FIX",
            )
            return {"status": "blocked_by_provider", "pilot": pilot_data}
        if mode == "pilot":
            _write_run1_reports(
                reports_dir=reports_dir,
                preflight=preflight,
                provider_preflight=provider_preflight,
                pilot=pilot_data,
                validation=pilot_validation,
                queue=None,
                scorecard=None,
                retrieval_preview=None,
                no_mutation=None,
                status="done",
                next_prd="PRD-046.0.9-RUN1",
            )
            return {"status": "done", "pilot": pilot_data}

    if mode not in {"real", "validate-existing"}:
        return {"status": "blocked", "reason": f"unsupported_mode:{mode}"}

    if mode == "validate-existing":
        if overlay_input_path is None:
            overlay_input_path = logs_dir / "real_enrichment_candidate_overlay.json"
    else:
        overlay_input_path = None if force else (logs_dir / "real_enrichment_candidate_overlay.json")

    run_inventory = inventory
    if limit > 0 and limit < len(inventory.get("items") or []):
        run_inventory = {
            **inventory,
            "items": (inventory.get("items") or [])[:limit],
            "blocks_total": limit,
        }

    overlay_path = logs_dir / "real_enrichment_candidate_overlay.json"
    overlay, overlay_meta = generate_overlay(
        inventory=run_inventory,
        mode="validate-existing" if mode == "validate-existing" else "real",
        overlay_path_for_validation=overlay_input_path if mode == "validate-existing" else overlay_path,
        batch_size=max(1, batch_size),
        resume=resume,
        model=model,
        timeout_seconds=timeout_seconds,
    )
    _write_json(overlay_path, overlay)

    validation = validate_overlay(overlay=overlay, inventory=run_inventory)
    usage = _estimate_usage_from_overlay(overlay, input_price_per_1k=input_price_per_1k, output_price_per_1k=output_price_per_1k)
    review_queue_base = build_review_queue_rebaseline(overlay=overlay, inventory=run_inventory, validation=validation)
    queue = {
        "schema_version": "post_reprocess_review_queue_after_real_enrichment_v1",
        "source_prd": RUN1_TAG,
        "generated_at": _utc_now(),
        "items_count": int(review_queue_base.get("review_items_count") or 0),
        "priority_counts": review_queue_base.get("priority_counts") or {"P0": 0, "P1": 0, "P2": 0},
        "reason_counts": _reason_counts(review_queue_base),
        "items": review_queue_base.get("items") or [],
    }
    _write_json(logs_dir / "review_queue_after_real_enrichment.json", queue)

    retrieval_preview = build_retrieval_preview(
        overlay=overlay,
        retrieval_eval_after_reprocess_path=Path("TO_DO_LIST/logs/PRD-046.0.8.1/retrieval_eval_after_reprocess.json"),
    )
    _write_json(logs_dir / "real_enrichment_retrieval_preview.json", retrieval_preview)

    validation_status = "passed"
    if int(validation.get("validation_errors_count") or 0) > 0:
        validation_status = "failed"
    elif queue.get("items_count", 0) > 0:
        validation_status = "passed_with_review_queue"
    if overlay_meta.get("provider_status") != "ok" and mode != "validate-existing":
        validation_status = "blocked_by_provider"
    if usage.get("estimated_cost_usd", 0.0) > hard_stop_budget_usd > 0:
        validation_status = "blocked_by_budget"

    real_validation = {
        **validation,
        "schema_version": "real_enrichment_validation_v1",
        "source_prd": RUN1_TAG,
        "provider_status": "called" if overlay_meta.get("provider_status") == "ok" else overlay_meta.get("provider_status"),
        "validation_status": validation_status,
        "items_attempted": usage.get("requests", 0),
        "items_completed": usage.get("items_completed", 0),
        "items_failed": usage.get("items_failed", 0),
        "missing_real_provider_output_count": usage.get("missing_real_provider_output_count", 0),
    }
    _write_json(logs_dir / "real_enrichment_validation.json", real_validation)

    scorecard = {
        "schema_version": "real_enrichment_scorecard_v1",
        "source_prd": RUN1_TAG,
        "generated_at": _utc_now(),
        "blocks_total": len(run_inventory.get("items") or []),
        "provider_status": "called" if overlay_meta.get("provider_status") == "ok" else overlay_meta.get("provider_status"),
        "items_attempted": usage.get("requests", 0),
        "items_completed": usage.get("items_completed", 0),
        "items_failed": usage.get("items_failed", 0),
        "validation_errors_count": int(real_validation.get("validation_errors_count") or 0),
        "validation_warnings_count": int(real_validation.get("validation_warnings_count") or 0),
        "missing_real_provider_output_count": int(real_validation.get("missing_real_provider_output_count") or 0),
        "needs_human_review_count": sum(
            1
            for row in overlay.get("items") or []
            if isinstance(row, dict) and bool((row.get("quality") or {}).get("needs_human_review"))
        ),
        "review_queue_items_count": int(queue.get("items_count") or 0),
        "avg_confidence": round(
            sum(
                float((row.get("quality") or {}).get("confidence") or 0.0)
                for row in overlay.get("items") or []
                if isinstance(row, dict)
            )
            / max(1, len(overlay.get("items") or [])),
            4,
        ),
        "avg_self_contained_score": round(
            sum(
                float((row.get("quality") or {}).get("self_contained_score") or 0.0)
                for row in overlay.get("items") or []
                if isinstance(row, dict)
            )
            / max(1, len(overlay.get("items") or [])),
            4,
        ),
        "summary_present_rate": round(
            sum(
                1
                for row in overlay.get("items") or []
                if isinstance(row, dict) and str((row.get("advisory") or {}).get("summary") or "").strip()
            )
            / max(1, len(overlay.get("items") or [])),
            4,
        ),
        "tags_present_rate": round(
            sum(
                1
                for row in overlay.get("items") or []
                if isinstance(row, dict) and _normalize_list((row.get("advisory") or {}).get("tags"))
            )
            / max(1, len(overlay.get("items") or [])),
            4,
        ),
        "use_when_present_rate": round(
            sum(
                1
                for row in overlay.get("items") or []
                if isinstance(row, dict) and _normalize_list((row.get("advisory") or {}).get("use_when"))
            )
            / max(1, len(overlay.get("items") or [])),
            4,
        ),
        "avoid_when_present_rate": round(
            sum(
                1
                for row in overlay.get("items") or []
                if isinstance(row, dict) and _normalize_list((row.get("advisory") or {}).get("avoid_when"))
            )
            / max(1, len(overlay.get("items") or [])),
            4,
        ),
        "lens_family_candidates_present_rate": round(
            sum(
                1
                for row in overlay.get("items") or []
                if isinstance(row, dict) and _normalize_list((row.get("advisory") or {}).get("lens_family_candidates"))
            )
            / max(1, len(overlay.get("items") or [])),
            4,
        ),
        "raw_full_text_leak_detected": bool(real_validation.get("raw_full_text_leak_detected")),
        "governance_authority_mutated": bool(real_validation.get("governance_authority_mutated")),
        "production_apply_performed": False,
        "chroma_reindex_performed": False,
        "provider_usage": {
            "input_tokens": usage.get("input_tokens", 0),
            "output_tokens": usage.get("output_tokens", 0),
            "requests": usage.get("requests", 0),
            "estimated_cost_usd": usage.get("estimated_cost_usd", 0.0),
        },
    }
    _write_json(logs_dir / "real_enrichment_scorecard.json", scorecard)

    all_blocks_after = _sha256_file(blocks_path) if blocks_path.exists() else ""
    registry_after = _sha256_file(registry_path) if registry_path.exists() else ""
    no_mutation = {
        "schema_version": "real_provider_no_mutation_check_v1",
        "source_prd": RUN1_TAG,
        "generated_at": _utc_now(),
        "all_blocks_merged_mutated": all_blocks_before != all_blocks_after,
        "registry_mutated": registry_before != registry_after,
        "chroma_mutated": False,
    }
    _write_json(logs_dir / "no_mutation_check.json", no_mutation)

    status = "done"
    next_prd = "PRD-046.0.9.1"
    if validation_status == "blocked_by_provider":
        status = "blocked_by_provider"
        next_prd = "PRD-046.0.9-RUN1-FIX"
    elif validation_status == "blocked_by_budget":
        status = "blocked_by_budget"
        next_prd = "PRD-046.0.9-RUN1-FIX"
    elif validation_status == "failed":
        status = "failed"
        next_prd = "PRD-046.0.9-RUN1-HF1"
    elif usage.get("items_completed", 0) < len(run_inventory.get("items") or []):
        status = "partial"
        next_prd = "PRD-046.0.9-RUN2"
    elif int(queue.get("items_count") or 0) == 0:
        next_prd = "PRD-046.0.9.2"

    _write_run1_reports(
        reports_dir=reports_dir,
        preflight=preflight,
        provider_preflight=provider_preflight,
        pilot=pilot_data,
        validation=real_validation,
        queue=queue,
        scorecard=scorecard,
        retrieval_preview=retrieval_preview,
        no_mutation=no_mutation,
        status=status,
        next_prd=next_prd,
    )

    return {
        "status": status,
        "validation_status": validation_status,
        "provider_status": scorecard.get("provider_status"),
        "items_attempted": scorecard.get("items_attempted"),
        "items_completed": scorecard.get("items_completed"),
        "items_failed": scorecard.get("items_failed"),
        "missing_real_provider_output_count": scorecard.get("missing_real_provider_output_count"),
        "review_queue_items_count": queue.get("items_count"),
        "next_prd": next_prd,
    }
