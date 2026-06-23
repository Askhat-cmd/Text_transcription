"""Isolated PRD-047.28 thin-spine experiment runner."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any
import uuid

from ..config import config
from ..multiagent.agents.agent_llm_client import create_agent_completion
from ..multiagent.agents.agent_llm_config import get_model_for_agent, get_temperature_for_agent
from ..multiagent.runtime_adapter import run_multiagent_adaptive_sync
from .experiment_reporter import (
    build_comparative_report,
    build_owner_review_sheet,
    build_trace_noise_comparison,
    compute_answer_metrics,
    json_dumps,
)
from .live_turn_note import build_live_turn_note
from .thin_context_collector import collect_thin_context
from .thin_safety_check import run_thin_safety_check
from .thin_spine_cases import ExperimentCase, _resolve_cases_path, load_cases_jsonl


_DISABLED_HEAVY_LAYERS = [
    "state_analyzer_control",
    "thread_manager_control",
    "diagnostic_center_control",
    "overlay_route",
    "semantic_cards_route",
    "rigid_user_request_contract",
]
_SUPPORTED_VARIANTS = {"A_current", "B_thin", "C_thin_note", "all"}


@dataclass
class ExperimentConfig:
    cases_path: str
    variant: str = "all"
    model: str | None = None
    temperature: float | None = None
    max_tokens: int = 900
    recent_turn_count: int = 4
    include_kb: bool = True
    include_live_turn_note: bool = True
    output_dir: str = ""
    debug: bool = False
    force_mock: bool = False


def run_prd_047_28_experiment(**kwargs: Any) -> dict[str, Any]:
    config_obj = ExperimentConfig(**kwargs)
    if config_obj.variant not in _SUPPORTED_VARIANTS:
        raise ValueError(f"unsupported variant: {config_obj.variant}")

    output_dir = Path(config_obj.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    cases = load_cases_jsonl(config_obj.cases_path)
    live_available = _live_llm_available() and not config_obj.force_mock

    run_config = {
        "prd": "PRD-047.28",
        "generated_at": _utc_now(),
        "cases_path": config_obj.cases_path,
        "variant": config_obj.variant,
        "model": config_obj.model or get_model_for_agent("writer"),
        "temperature": (
            float(config_obj.temperature)
            if config_obj.temperature is not None
            else float(get_temperature_for_agent("writer"))
        ),
        "max_tokens": int(config_obj.max_tokens),
        "recent_turn_count": int(config_obj.recent_turn_count),
        "include_kb": bool(config_obj.include_kb),
        "include_live_turn_note": bool(config_obj.include_live_turn_note),
        "live_llm_available": live_available,
        "force_mock": bool(config_obj.force_mock),
    }
    fixture_copy_source = _resolve_cases_path(config_obj.cases_path)
    _write_text(output_dir / "thin_spine_cases_ru.jsonl.copy", fixture_copy_source.read_text(encoding="utf-8"))
    _write_json(output_dir / "experiment_run_config.json", run_config)

    requested_variants = (
        ["A_current", "B_thin", "C_thin_note"]
        if config_obj.variant == "all"
        else [config_obj.variant]
    )
    rows = _run_all_variants(
        cases=cases,
        requested_variants=requested_variants,
        config_obj=config_obj,
        live_available=live_available,
    )

    _write_jsonl(output_dir / "variant_outputs.jsonl", rows)

    trace_noise = build_trace_noise_comparison(rows)
    _write_json(output_dir / "trace_noise_comparison.json", trace_noise)
    comparative_report = build_comparative_report(rows, _resolve_final_status(rows))
    _write_text(output_dir / "thin_spine_comparative_report.md", comparative_report)
    _write_text(output_dir / "owner_review_sheet.md", build_owner_review_sheet(rows))
    _write_text(output_dir / "retirement_candidates_after_experiment.md", _build_retirement_candidates(rows))
    _write_text(output_dir / "next_prd_recommendation.md", _build_next_prd_recommendation(rows))
    _write_text(output_dir / "implementation_report.md", _build_implementation_report(rows, run_config))

    summary = {
        "prd": "PRD-047.28",
        "generated_at": _utc_now(),
        "final_status": _resolve_final_status(rows),
        "case_count": len(cases),
        "variant_count": len(requested_variants),
        "live_llm_available": live_available,
        "rows": len(rows),
    }
    return summary


def _run_all_variants(
    *,
    cases: list[ExperimentCase],
    requested_variants: list[str],
    config_obj: ExperimentConfig,
    live_available: bool,
) -> list[dict[str, Any]]:
    return asyncio.run(
        _run_all_variants_async(
            cases=cases,
            requested_variants=requested_variants,
            config_obj=config_obj,
            live_available=live_available,
        )
    )


async def _run_all_variants_async(
    *,
    cases: list[ExperimentCase],
    requested_variants: list[str],
    config_obj: ExperimentConfig,
    live_available: bool,
) -> list[dict[str, Any]]:
    client: Any | None = None
    if live_available:
        try:
            from openai import AsyncOpenAI
        except Exception as exc:  # pragma: no cover - dependency guard
            raise RuntimeError("openai_async_client_unavailable") from exc
        client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
    try:
        rows: list[dict[str, Any]] = []
        for case in cases:
            for variant in requested_variants:
                row = await _run_variant(
                    case=case,
                    variant=variant,
                    config_obj=config_obj,
                    live_available=live_available,
                    async_client=client,
                )
                rows.append(row)
        return rows
    finally:
        if client is not None:
            await client.close()


async def _run_variant(
    *,
    case: ExperimentCase,
    variant: str,
    config_obj: ExperimentConfig,
    live_available: bool,
    async_client: Any | None,
) -> dict[str, Any]:
    if variant == "A_current":
        result = _run_variant_a(case=case, debug=config_obj.debug, live_available=live_available)
    else:
        result = await _run_variant_thin(
            case=case,
            variant=variant,
            config_obj=config_obj,
            live_available=live_available,
            async_client=async_client,
        )
    metrics = compute_answer_metrics(
        case_payload=result["case_payload"],
        answer=result["answer"],
        trace=result["trace"],
    )
    result["metrics"] = metrics
    return result


def _run_variant_a(*, case: ExperimentCase, debug: bool, live_available: bool) -> dict[str, Any]:
    case_payload = _case_payload(case)
    if not live_available:
        trace = {
            "trace_version": "thin_spine_experiment_trace_v1",
            "prd": "PRD-047.28",
            "variant": "A_current",
            "case_id": case.case_id,
            "production_runtime_mutated": False,
            "trace_step_count": 0,
            "trace_char_count": 0,
            "disabled_heavy_layers": [],
            "safety_check": {"passed": True, "warnings": [], "internal_leak_count": 0, "raw_kb_dump_count": 0, "practice_forced": False, "safety_warning_count": 0},
        }
        return {
            "case_id": case.case_id,
            "group": case.group,
            "title": case.title,
            "variant": "A_current",
            "status": "skipped",
            "answer": "[skipped: live credentials unavailable for current runtime baseline]",
            "trace": trace,
            "case_payload": case_payload,
        }

    runtime_user_id = f"prd_047_28_{case.case_id}_{uuid.uuid4().hex[:8]}"
    assistant_turn_injection_unsupported = any(
        str(item.get("role", "") or "").strip() == "assistant" for item in case.messages
    )
    latest_result: dict[str, Any] = {}
    warnings: list[str] = []
    for message in case.messages:
        if str(message.get("role", "") or "").strip() != "user":
            continue
        latest_result = run_multiagent_adaptive_sync(
            query=str(message.get("content", "") or ""),
            user_id=runtime_user_id,
            debug=debug,
        )
    answer = str(latest_result.get("answer", "") or "")
    debug_payload = dict(latest_result.get("debug", {}) or {})
    trace_blob = debug_payload if debug_payload else dict(latest_result.get("metadata", {}) or {})
    if assistant_turn_injection_unsupported:
        warnings.append("assistant_turn_injection_unsupported_for_variant_a")
    trace = {
        "trace_version": "thin_spine_experiment_trace_v1",
        "prd": "PRD-047.28",
        "variant": "A_current",
        "case_id": case.case_id,
        "production_runtime_mutated": False,
        "runtime_entrypoint": str(((latest_result.get("metadata") or {}).get("runtime_entrypoint")) or "multiagent_adapter"),
        "warnings": warnings,
        "trace_step_count": len(trace_blob),
        "trace_char_count": len(json.dumps(trace_blob, ensure_ascii=False)),
        "disabled_heavy_layers": [],
        "safety_check": run_thin_safety_check(
            answer=answer,
            allow_practice=(case.expected_behavior.practice_allowed != "forbidden"),
        ),
    }
    return {
        "case_id": case.case_id,
        "group": case.group,
        "title": case.title,
        "variant": "A_current",
        "status": "completed",
        "answer": answer,
        "trace": trace,
        "case_payload": case_payload,
    }


async def _run_variant_thin(
    *,
    case: ExperimentCase,
    variant: str,
    config_obj: ExperimentConfig,
    live_available: bool,
    async_client: Any | None,
) -> dict[str, Any]:
    case_payload = _case_payload(case)
    context = collect_thin_context(
        case=case,
        recent_turn_count=config_obj.recent_turn_count,
        include_kb=config_obj.include_kb,
    )
    note_text = None
    if variant == "C_thin_note" and config_obj.include_live_turn_note:
        note_text = build_live_turn_note(context)
    if live_available:
        if async_client is None:
            raise RuntimeError("async_client_required_for_live_thin_variant")
        answer = await _generate_live_thin_answer(
            client=async_client,
            context=context,
            variant=variant,
            live_turn_note=note_text,
            model=config_obj.model or get_model_for_agent("writer"),
            temperature=(
                float(config_obj.temperature)
                if config_obj.temperature is not None
                else float(get_temperature_for_agent("writer"))
            ),
            max_tokens=config_obj.max_tokens,
        )
        status = "completed"
    else:
        answer = _generate_mock_answer(case=case, context=context, note_text=note_text)
        status = "mock_completed"

    safety_check = run_thin_safety_check(
        answer=answer,
        allow_practice=(case.expected_behavior.practice_allowed != "forbidden"),
    )
    trace = {
        "trace_version": "thin_spine_experiment_trace_v1",
        "prd": "PRD-047.28",
        "variant": variant,
        "case_id": case.case_id,
        "production_runtime_mutated": False,
        "context_gathering": {
            "recent_turn_count": int(context.get("recent_turn_count", 0) or 0),
            "summary_present": bool(context.get("case_summary")),
            "explicit_constraints": list(context.get("explicit_constraints", []) or []),
        },
        "live_turn_note": {
            "present": bool(note_text),
            "text": note_text,
        },
        "knowledge_package": {
            "present": bool(context.get("knowledge_package_present", False)),
            "reason": str(context.get("knowledge_package_reason", "") or ""),
        },
        "writer": {
            "model": config_obj.model or get_model_for_agent("writer"),
            "temperature": (
                float(config_obj.temperature)
                if config_obj.temperature is not None
                else float(get_temperature_for_agent("writer"))
            ),
            "max_tokens": int(config_obj.max_tokens),
            "mode": "live_llm" if live_available else "mock",
        },
        "disabled_heavy_layers": list(_DISABLED_HEAVY_LAYERS),
        "safety_check": safety_check,
    }
    trace["trace_step_count"] = 5 + (1 if note_text else 0)
    trace["trace_char_count"] = len(json.dumps(trace, ensure_ascii=False))

    return {
        "case_id": case.case_id,
        "group": case.group,
        "title": case.title,
        "variant": variant,
        "status": status,
        "answer": answer,
        "trace": trace,
        "case_payload": case_payload,
    }


async def _generate_live_thin_answer(
    *,
    client: Any,
    context: dict[str, Any],
    variant: str,
    live_turn_note: str | None,
    model: str,
    temperature: float,
    max_tokens: int,
) -> str:
    user_prompt = _build_thin_writer_prompt(context=context, variant=variant, live_turn_note=live_turn_note)
    result = await create_agent_completion(
        client=client,
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are NEO, a warm and direct psychological support bot. "
                    "Answer the user's current turn in Russian. "
                    "Respect explicit constraints. "
                    "Do not mention internal tools, internal database, traces, or hidden process. "
                    "Do not dump raw knowledge. "
                    "Do not force breathing or practice unless clearly invited. "
                    "If the situation has safety or medical uncertainty, stay within a safe non-diagnostic boundary."
                ),
            },
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return str(result.text or "").strip()


def _build_thin_writer_prompt(
    *,
    context: dict[str, Any],
    variant: str,
    live_turn_note: str | None,
) -> str:
    recent_block = "\n".join(
        f"- {item.get('role')}: {item.get('content')}"
        for item in list(context.get("recent_messages", []) or [])
    ) or "[none]"
    kb_block = "\n".join(
        f"- {item.get('title')}: {item.get('content')}"
        for item in list(context.get("knowledge_package", []) or [])
    ) or "[none]"
    constraints_block = "\n".join(
        f"- {item}" for item in list(context.get("explicit_constraints", []) or [])
    ) or "[none]"
    note_block = live_turn_note or "[absent]"
    return (
        f"Variant: {variant}\n"
        f"Case: {context.get('case_id')}\n"
        f"Title: {context.get('title')}\n\n"
        f"Current user message:\n{context.get('current_user_message')}\n\n"
        f"Recent dialogue context:\n{recent_block}\n\n"
        f"Compact case summary:\n{context.get('case_summary') or '[none]'}\n\n"
        f"Explicit constraints:\n{constraints_block}\n\n"
        f"Knowledge package:\n{kb_block}\n\n"
        f"Live Turn Note:\n{note_block}\n\n"
        "Write one direct user-facing answer now."
    )


def _generate_mock_answer(
    *,
    case: ExperimentCase,
    context: dict[str, Any],
    note_text: str | None,
) -> str:
    group = case.group
    if group == "greeting_personal_question":
        return "Да, можешь. Задавай свой вопрос, и я отвечу по-человечески и без лишней сложности."
    if group == "resistance":
        return "Сопротивление часто появляется не потому, что с тобой что-то не так, а потому что внутри есть часть, которая боится давления или провала. Полезно не ломать себя, а заметить: от чего именно эта часть тебя сейчас защищает."
    if group == "anger_at_boss":
        return "Твоя злость здесь понятна: дело не только во лжи, а ещё в бессилии, когда ты видишь ложь и не можешь ответить так, как хотелось бы. Сначала полезно отделить сам факт лжи от вопроса, что ты реально хочешь защитить: границы, репутацию или чувство собственного достоинства."
    if group == "simplify_after_complexity":
        return "Проще так: внутри тебя сталкиваются две части. Одна хочет удержать контроль и не ошибиться, другая уже устала жить в постоянном напряжении."
    if group == "practice_pushback":
        return "Понял, без практики. Тогда суть такая: тебя раздражает не сама идея помощи, а то, что вместо ответа на живой вопрос тебе снова дают универсальный рецепт."
    if group == "long_term_perspective":
        return "В долгосрочной перспективе с гневом помогает не только разряжаться, а понимать его повторяющийся механизм: где ты терпишь лишнее, где проглатываешь злость, и где потом она накапливается до взрыва. Тогда работа идёт не с симптомом, а с источником."
    if group == "no_kb_request":
        return "Если без внутренней базы, то я бы сказал так: злость на начальника часто усиливается там, где приходится одновременно видеть несправедливость и сдерживать себя. Важно не спорить с этой злостью, а понять, что именно она хочет защитить в тебе."
    if group == "alternatives_to_breathing":
        return "Да, кроме дыхания есть и другие способы. Можно замедлить ответ действием, а не телом: выйти из переписки на паузу, записать несказанное на черновик, сократить контакт на время или заранее продумать одну спокойную границу."
    if group == "direct_kb_question":
        kb = list(context.get("knowledge_package", []) or [])
        if kb:
            return f"{kb[0].get('content')} Если коротко, здесь речь о внутреннем механизме, а не о формальной теории."
        return "Это вопрос из базы знаний, но в текущем запуске у меня нет подготовленного KB-пакета для него."
    if group == "safety_boundary":
        return "Если это похоже на паническую атаку, важно не спорить с собой и не пытаться срочно всё объяснить. Но если есть сильная боль, онемение, ощущение, что состояние физически опасно, лучше не сводить это только к тревоге и обратиться за медицинской помощью."
    fallback = "Я услышал твой запрос. Отвечу прямо, коротко и без лишнего давления."
    if note_text:
        return fallback + " " + note_text[:120]
    return fallback


def _case_payload(case: ExperimentCase) -> dict[str, Any]:
    return {
        "case_id": case.case_id,
        "group": case.group,
        "title": case.title,
        "messages": [dict(item) for item in case.messages],
        "expected_behavior": {
            "must_answer_directly": case.expected_behavior.must_answer_directly,
            "kb_allowed": case.expected_behavior.kb_allowed,
            "practice_allowed": case.expected_behavior.practice_allowed,
            "must_not": list(case.expected_behavior.must_not),
            "preferred_mode": case.expected_behavior.preferred_mode,
        },
        "quality_focus": list(case.quality_focus),
        "case_summary": case.case_summary,
        "explicit_constraints": list(case.explicit_constraints),
        "knowledge_package": [
            {"title": item.title, "content": item.content, "source": item.source}
            for item in case.knowledge_package
        ],
    }


def _resolve_final_status(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "BLOCKED"
    if any(int(row.get("metrics", {}).get("internal_leak_count", 0) or 0) > 0 for row in rows):
        return "BLOCKED"
    if any(bool(row.get("metrics", {}).get("kb_used_when_forbidden", False)) for row in rows):
        return "BLOCKED"
    if any(bool(row.get("metrics", {}).get("practice_forced", False)) for row in rows):
        return "BLOCKED"
    if any(str(row.get("status")) == "skipped" for row in rows if str(row.get("variant")) == "A_current"):
        return "ACCEPTED WITH WARNING"
    return "ACCEPTED"


def _build_retirement_candidates(rows: list[dict[str, Any]]) -> str:
    return "\n".join(
        [
            "# Retirement Candidates After Experiment",
            "",
            "## 1. Candidate to retire soon",
            "- `legacy_query_builder_fallback` once current-turn-focused retrieval remains stable across future PRDs.",
            "- Trace-only surfaces that duplicate the same runtime truth and add noise without changing answers.",
            "- Stale `must_answer` sources that survive only as compatibility residue.",
            "",
            "## 2. Candidate to keep as advisory",
            "- Safety floor and minimal answer-boundary checks.",
            "- `overlay_shadow_trace` as non-authoritative observability only.",
            "- `semantic_cards_pilot_v1` only as optional advisory grounding, not as a route.",
            "",
            "## 3. Candidate to keep temporarily until more evidence",
            "- Diagnostic Center advisory visibility.",
            "- Heavy dialogue-act / answer-obligation path until simplification can prove no regression.",
            "- `legacy_semantic_hits_fallback` until no-fallback evidence is sustained by later cleanup PRD.",
            "",
            "## 4. Candidate to leave untouched",
            "- Canonical `multiagent_adapter` production-like path until owner review decides otherwise.",
            "- `writer_kb_payload_v1` as canonical knowledge-to-Writer path.",
            "- `current_turn_focus_v1` as canonical retrieval query builder.",
            "",
            "## 5. Candidate requiring separate risk PRD",
            "- Any live replacement of the current runtime with thin spine.",
            "- Any deletion of heavy layers from production code.",
            "- Any removal of the old compatibility graph/surface without dedicated reproducibility review.",
            "",
            f"- evaluated_rows: `{len(rows)}`",
        ]
    ).rstrip() + "\n"


def _build_next_prd_recommendation(rows: list[dict[str, Any]]) -> str:
    if any(str(row.get("status")) == "skipped" for row in rows if str(row.get("variant")) == "A_current"):
        recommendation = "PRD-047.29 - Thin Spine Experiment Round 2 / Owner Scored Live Cases v1"
        rationale = "Variant A baseline could not be compared fully in live mode, so the result is evidence-bearing but inconclusive."
    else:
        b_scores = _average_score(rows, "B_thin")
        c_scores = _average_score(rows, "C_thin_note")
        a_scores = _average_score(rows, "A_current")
        if c_scores > max(a_scores, b_scores):
            recommendation = "PRD-047.29 - Thin Spine Controlled Pilot / Live Turn Note Limited Apply v1"
            rationale = "Variant C has the strongest direct-answer score among compared variants."
        elif b_scores > max(a_scores, c_scores):
            recommendation = "PRD-047.29 - Thin Spine Controlled Pilot / No Live Turn Note v1"
            rationale = "Variant B beats both A and C without the extra note layer."
        elif a_scores >= max(b_scores, c_scores):
            recommendation = "PRD-047.29 - Current Pipeline Simplification Targets / Layer Noise Reduction v1"
            rationale = "The current pipeline remains strongest or tied, so the next move is reduction of confirmed noise layers."
        else:
            recommendation = "PRD-047.29 - Thin Spine Experiment Round 2 / Owner Scored Live Cases v1"
            rationale = "Results are mixed."
    return "\n".join(
        [
            "# Next PRD Recommendation",
            "",
            f"- recommended_next_prd: `{recommendation}`",
            f"- rationale: {rationale}",
        ]
    ).rstrip() + "\n"


def _build_implementation_report(rows: list[dict[str, Any]], run_config: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# PRD-047.28 Implementation Report",
            "",
            f"- status: `{_resolve_final_status(rows)}`",
            f"- generated_at: `{_utc_now()}`",
            f"- live_llm_available: `{run_config.get('live_llm_available')}`",
            f"- force_mock: `{run_config.get('force_mock')}`",
            f"- case_count: `{len({str(row.get('case_id')) for row in rows})}`",
            f"- row_count: `{len(rows)}`",
            f"- implementation_commit: `PENDING_MAIN_COMMIT`",
            f"- metadata_commit: `PENDING_METADATA_COMMIT`",
            "",
            "## Outcome",
            "- Experiment code is isolated from the production runtime path.",
            "- Variant A reuses the existing runtime adapter when live credentials are available.",
            "- Variants B/C use a separate thin writer path and post-answer safety/leak checks.",
            "",
            "## Evidence Summary",
            f"- average_direct_answer_score_A: `{_average_score(rows, 'A_current')}`",
            f"- average_direct_answer_score_B: `{_average_score(rows, 'B_thin')}`",
            f"- average_direct_answer_score_C: `{_average_score(rows, 'C_thin_note')}`",
            "",
            "## Final Recommendation",
            _build_next_prd_recommendation(rows).strip(),
        ]
    ).rstrip() + "\n"


def _average_score(rows: list[dict[str, Any]], variant: str) -> float:
    scores = [
        int(row.get("metrics", {}).get("direct_answer_score", 0) or 0)
        for row in rows
        if str(row.get("variant")) == variant and str(row.get("status")) != "skipped"
    ]
    if not scores:
        return 0.0
    return round(sum(scores) / len(scores), 3)


def _live_llm_available() -> bool:
    return bool(getattr(config, "OPENAI_API_KEY", None))


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json_dumps(payload) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
