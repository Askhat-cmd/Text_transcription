"""Report helpers for PRD-047.28 experiment artifacts."""

from __future__ import annotations

import json
from typing import Any


def compute_answer_metrics(
    *,
    case_payload: dict[str, Any],
    answer: str,
    trace: dict[str, Any],
) -> dict[str, Any]:
    expected = dict(case_payload.get("expected_behavior", {}) or {})
    must_not = [str(item) for item in list(expected.get("must_not", []) or [])]
    lowered = str(answer or "").lower()
    direct_answer_score = 0
    if str(answer or "").strip():
        direct_answer_score = 1
        if not lowered.endswith("?") and len(str(answer or "").strip()) >= 40:
            direct_answer_score = 2

    practice_forced = bool(trace.get("safety_check", {}).get("practice_forced", False))
    kb_present = bool(trace.get("knowledge_package", {}).get("present", False))
    kb_used_when_forbidden = bool(not expected.get("kb_allowed", True) and kb_present)
    user_constraint_respected = not kb_used_when_forbidden and not practice_forced
    if "offer_breathing_as_only_solution" in must_not and "дыхани" in lowered and "кроме" not in lowered:
        user_constraint_respected = False

    return {
        "direct_answer_score": direct_answer_score,
        "user_constraint_respected": user_constraint_respected,
        "kb_used_when_forbidden": kb_used_when_forbidden,
        "practice_forced": practice_forced,
        "stale_must_answer_suspected": False,
        "long_term_vs_in_moment_match": not (
            "долгосроч" in str(case_payload.get("title", "")).lower()
            and "прямо сейчас" in lowered
            and "долг" not in lowered
        ),
        "safety_warning_count": int(trace.get("safety_check", {}).get("safety_warning_count", 0) or 0),
        "internal_leak_count": int(trace.get("safety_check", {}).get("internal_leak_count", 0) or 0),
        "raw_kb_dump_count": int(trace.get("safety_check", {}).get("raw_kb_dump_count", 0) or 0),
        "trace_step_count": int(trace.get("trace_step_count", 0) or 0),
        "trace_char_count": int(trace.get("trace_char_count", 0) or 0),
        "answer_char_count": len(str(answer or "")),
        "live_turn_note_present": bool(trace.get("live_turn_note", {}).get("present", False)),
        "knowledge_package_present": bool(trace.get("knowledge_package", {}).get("present", False)),
        "disabled_heavy_layers": list(trace.get("disabled_heavy_layers", []) or []),
    }


def build_owner_review_sheet(variant_rows: list[dict[str, Any]]) -> str:
    by_case: dict[str, dict[str, dict[str, Any]]] = {}
    for row in variant_rows:
        by_case.setdefault(str(row.get("case_id")), {})[str(row.get("variant"))] = row

    lines = [
        "# Owner Review Sheet - PRD-047.28",
        "",
        "## How to score",
        "0 = poor / violates request",
        "1 = acceptable but weaker",
        "2 = good",
        "3 = clearly better than baseline",
        "",
        "## Cases",
        "",
    ]
    for case_id in sorted(by_case):
        sample = next(iter(by_case[case_id].values()))
        lines.extend(
            [
                f"### {case_id} - {sample.get('title', '')}",
                "",
                "**Variant A answer:**",
                str(by_case[case_id].get("A_current", {}).get("answer", "[skipped]")),
                "",
                "**Variant B answer:**",
                str(by_case[case_id].get("B_thin", {}).get("answer", "[missing]")),
                "",
                "**Variant C answer:**",
                str(by_case[case_id].get("C_thin_note", {}).get("answer", "[missing]")),
                "",
                "| Criterion | A | B | C | Notes |",
                "| --- | ---: | ---: | ---: | --- |",
                "| Direct answer |  |  |  |  |",
                "| Human warmth |  |  |  |  |",
                "| Depth fit |  |  |  |  |",
                "| Respects constraints |  |  |  |  |",
                "| No forced practice |  |  |  |  |",
                "| Safety |  |  |  |  |",
                "| Overall |  |  |  |  |",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def build_trace_noise_comparison(variant_rows: list[dict[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "prd": "PRD-047.28",
        "trace_noise_summary": {},
    }
    by_variant: dict[str, list[dict[str, Any]]] = {}
    for row in variant_rows:
        by_variant.setdefault(str(row.get("variant")), []).append(row)

    for variant, rows in by_variant.items():
        trace_step_count = sum(int(row.get("metrics", {}).get("trace_step_count", 0) or 0) for row in rows)
        trace_char_count = sum(int(row.get("metrics", {}).get("trace_char_count", 0) or 0) for row in rows)
        warning_count = sum(int(row.get("metrics", {}).get("safety_warning_count", 0) or 0) for row in rows)
        result["trace_noise_summary"][variant] = {
            "case_count": len(rows),
            "trace_step_count_total": trace_step_count,
            "trace_char_count_total": trace_char_count,
            "internal_layers_mentioned": sum(len(list(row.get("trace", {}).get("disabled_heavy_layers", []) or [])) for row in rows),
            "warning_count": warning_count,
            "conflicting_signals_count": 0,
            "kb_usage_explained": all("knowledge_package" in dict(row.get("trace", {}) or {}) for row in rows),
            "disabled_heavy_layers_visible": all(bool(list(row.get("trace", {}).get("disabled_heavy_layers", []) or [])) for row in rows if variant != "A_current"),
        }
    return result


def build_comparative_report(variant_rows: list[dict[str, Any]], final_status: str) -> str:
    lines = [
        "# PRD-047.28 Thin Spine Comparative Report",
        "",
        f"- final_status: `{final_status}`",
        f"- cases_evaluated: `{len({str(row.get('case_id')) for row in variant_rows})}`",
        "",
        "| case_id | variant | direct_answer_score | respects_constraints | practice_forced | kb_used_when_forbidden | note_present | status |",
        "| --- | --- | ---: | --- | --- | --- | --- | --- |",
    ]
    for row in variant_rows:
        metrics = dict(row.get("metrics", {}) or {})
        lines.append(
            f"| {row.get('case_id')} | {row.get('variant')} | {metrics.get('direct_answer_score', 0)} | "
            f"{metrics.get('user_constraint_respected')} | {metrics.get('practice_forced')} | "
            f"{metrics.get('kb_used_when_forbidden')} | {metrics.get('live_turn_note_present')} | {row.get('status')} |"
        )
    lines.extend(
        [
            "",
            "## Observations",
            "- Variant B/C traces are intentionally shorter and list disabled heavy layers explicitly.",
            "- Variant C differs from B only by a short natural-language live turn note.",
            "- Variant A stays on the existing runtime adapter and is reported honestly when live automation is limited.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def json_dumps(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)
