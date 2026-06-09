from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
BOT_ROOT = ROOT / "bot_psychologist"
if str(BOT_ROOT) not in sys.path:
    sys.path.insert(0, str(BOT_ROOT))

from bot_agent.multiagent.contextual_retrieval_query_composer import (  # noqa: E402
    build_contextual_retrieval_query_composer_v1,
)

PRD_ID = "PRD-047.15-HF1"
LOG_DIR = ROOT / "TO_DO_LIST" / "logs" / PRD_ID
CASE_LIBRARY_JSON = LOG_DIR / "composer_calibration_cases.json"
CASE_LIBRARY_MD = LOG_DIR / "composer_calibration_cases.md"
SCHEMA_JSON = LOG_DIR / "composer_trace_schema.json"
SCHEMA_MD = LOG_DIR / "composer_trace_schema.md"
RESULTS_JSON = LOG_DIR / "composer_trace_review_results.json"
RESULTS_MD = LOG_DIR / "composer_trace_review_results.md"
OWNER_SHEET = LOG_DIR / "owner_trace_review_sheet.md"
DECISION_JSON = LOG_DIR / "llm_hybrid_decision_brief.json"
DECISION_MD = LOG_DIR / "llm_hybrid_decision_brief.md"

RAG_ACTIONS = {"query_kb", "query_memory", "query_kb_and_memory"}
NON_RAG_ACTIONS = {"suppress_rag", "use_current_context_only", "trace_only"}
SHORT_LITERALS = {
    "да",
    "да хорошо",
    "давай",
    "ок",
    "окей",
    "ага",
    "угу",
    "можно",
    "покажи",
    "продолжай",
    "хорошо дальше",
}
TRACE_SCHEMA_FIELDS = [
    "case_id",
    "user_message",
    "last_assistant_offer",
    "dialogue_act",
    "answer_obligation",
    "summary_request",
    "composer.version",
    "composer.mode",
    "composer.retrieval_need",
    "composer.retrieval_action",
    "composer.query_source",
    "composer.composed_query",
    "composer.query_terms",
    "composer.inherited_topic",
    "composer.inherited_offer_type",
    "composer.confidence",
    "composer.writer_can_ignore_rag",
    "composer.include_for_writer_if_found",
    "composer.reason",
    "composer.evidence",
    "composer.no_user_facing_text_created",
    "expected_category",
    "computed_category",
    "review_flags",
]


def _case(
    case_id: str,
    group: str,
    user_message: str,
    expected_category: str,
    expected_actions: list[str],
    **kwargs: Any,
) -> dict[str, Any]:
    payload = {
        "case_id": case_id,
        "group": group,
        "user_message": user_message,
        "expected_category": expected_category,
        "expected_retrieval_actions": expected_actions,
    }
    payload.update(kwargs)
    return payload


def _default_cases() -> list[dict[str, Any]]:
    offer = lambda offer_type, summary: {  # noqa: E731
        "is_open": True,
        "offer_type": offer_type,
        "offer_text_summary": summary,
    }
    summary = {"dialogue_act_resolution": {"dialogue_act": "summary_request"}, "answer_obligation_resolution": {"answer_obligation": "summarize_current_conversation"}}
    knowledge = lambda concept: {"dialogue_act_resolution": {"dialogue_act": "knowledge_question"}, "knowledge_answer_guard": {"knowledge_answer": {"needed": True, "concept": concept}}}  # noqa: E731
    contextual = {"dialogue_pragmatics": {"is_contextual_followup": True}}
    return [
        _case("SF01", "short_contextual_followup", "Да", "inherit_concept_query", ["query_kb"], last_assistant_offer=offer("explain_concept", "Показать через нейросталкинг, автоматизм и внутренний шаг."), dialogue_pragmatics={"is_contextual_followup": True, "previous_assistant_offer_type": "explain_concept"}),
        _case("SF02", "short_contextual_followup", "Да, хорошо", "query_practice_context", ["query_kb"], last_assistant_offer=offer("practice_observation", "Показать практику наблюдения в нейросталкинге без давления."), dialogue_pragmatics={"is_contextual_followup": True, "previous_assistant_offer_type": "practice_observation"}),
        _case("SF03", "short_contextual_followup", "Давай", "suppress_short_support", ["suppress_rag"], last_assistant_offer=offer("short_support", "Могу просто коротко поддержать тебя без разбора.")),
        _case("SF04", "short_contextual_followup", "Покажи", "warning_needs_hybrid_or_more_context", ["query_kb"], last_assistant_offer=offer("example", "Показать пример нейросталкинга на обычной реакции."), **contextual),
        _case("SF05", "short_contextual_followup", "Продолжай", "warning_needs_hybrid_or_more_context", ["query_kb"], last_assistant_offer=offer("explain_concept", "Продолжить объяснение защитного механизма и автоматизма."), **contextual),
        _case("SF06", "short_contextual_followup", "Можно", "use_current_context_only", ["use_current_context_only", "trace_only"], last_assistant_offer=offer("summary", "Сделать короткое резюме текущей линии разговора."), **contextual),
        _case("SF07", "short_contextual_followup", "Ок", "inherit_concept_query", ["query_kb"], last_assistant_offer=offer("example", "Разобрать пример нейросталкинга через автоматизм.")),
        _case("SF08", "short_contextual_followup", "Хорошо, дальше", "warning_needs_hybrid_or_more_context", ["query_kb"], last_assistant_offer=offer("explanation", "Продолжить про самореализацию и внутренний выбор."), **contextual),
        _case("SF09", "short_contextual_followup", "Да", "suppress_short_support", ["suppress_rag"], last_assistant_offer=offer("one_step", "Дать один маленький шаг на сейчас.")),
        _case("SF10", "short_contextual_followup", "Да, хорошо", "use_current_context_only", ["use_current_context_only"], last_assistant_offer=offer("summary", "Собрать резюме текущей беседы без внешней теории.")),
        _case("SM01", "summary_request", "Подведи краткий итог нашей беседы.", "use_current_context_only", ["use_current_context_only"], **summary),
        _case("SM02", "summary_request", "Сделай резюме.", "use_current_context_only", ["use_current_context_only"], **summary),
        _case("SM03", "summary_request", "К чему мы пришли?", "use_current_context_only", ["use_current_context_only"], **summary),
        _case("SM04", "summary_request", "Что мы поняли?", "use_current_context_only", ["use_current_context_only"], **summary),
        _case("SM05", "summary_request", "Дай summary.", "use_current_context_only", ["use_current_context_only"], **summary),
        _case("SM06", "summary_request", "Собери всё вместе.", "use_current_context_only", ["use_current_context_only"], **summary),
        _case("KQ01", "knowledge_question", "Что такое нейросталкинг?", "query_kb", ["query_kb"], **knowledge("нейросталкинг")),
        _case("KQ02", "knowledge_question", "Объясни Кузницу Духа простыми словами.", "query_kb", ["query_kb"], **knowledge("кузница духа")),
        _case("KQ03", "knowledge_question", "Что значит автоматизм?", "query_kb", ["query_kb"], **knowledge("автоматизм")),
        _case("KQ04", "knowledge_question", "Как работает защитный механизм?", "query_kb", ["query_kb"], **knowledge("защитный механизм")),
        _case("KQ05", "knowledge_question", "Чем отличается наблюдение от контроля?", "query_kb", ["query_kb"], **knowledge("наблюдение")),
        _case("KQ06", "knowledge_question", "Расскажи про самореализацию.", "query_kb", ["query_kb"], **knowledge("самореализация")),
        _case("KQ07", "knowledge_question", "Как работает нейросталкинг в живом диалоге?", "query_kb", ["query_kb"], **knowledge("нейросталкинг")),
        _case("KQ08", "knowledge_question", "Что значит внутренняя наблюдательность?", "query_kb", ["query_kb"], **knowledge("наблюдение")),
        _case("MX01", "mixed_context", "Подведи итог и свяжи это с нейросталкингом.", "mixed_query_or_hybrid_needed", ["query_kb", "query_kb_and_memory"], current_concept="нейросталкинг", **summary),
        _case("MX02", "mixed_context", "Покажи это через Кузницу.", "mixed_query_or_hybrid_needed", ["query_kb"], current_concept="кузница духа", **contextual),
        _case("MX03", "mixed_context", "Да, но на моём примере.", "query_kb_and_memory_or_hybrid", ["query_kb_and_memory"], current_concept="нейросталкинг", last_assistant_offer=offer("explain_concept", "Пояснить нейросталкинг на примере пользователя."), **contextual),
        _case("MX04", "mixed_context", "А как это связано с автоматизмом?", "query_kb", ["query_kb"], dialogue_pragmatics={"is_contextual_followup": True}, knowledge_answer_guard={"knowledge_answer": {"needed": True, "concept": "автоматизм"}}),
        _case("MX05", "mixed_context", "Теперь дай практику по этому.", "query_practice_context", ["query_kb"], current_concept="нейросталкинг", **contextual),
        _case("MX06", "mixed_context", "Суммируй и дай практику по нейросталкингу.", "query_kb_and_memory_or_hybrid", ["query_kb_and_memory", "query_kb"], current_concept="нейросталкинг", **summary),
        _case("MX07", "mixed_context", "Объясни коротко, но с примером из нашей беседы.", "query_kb_and_memory_or_hybrid", ["query_kb_and_memory", "query_kb"], current_concept="нейросталкинг", **contextual),
        _case("MX08", "mixed_context", "Что из этого относится к защитному механизму?", "query_kb", ["query_kb"], dialogue_pragmatics={"is_contextual_followup": True}, knowledge_answer_guard={"knowledge_answer": {"needed": True, "concept": "защитный механизм"}}),
        _case("NS01", "noise_suppression", "Привет.", "suppress_rag", ["suppress_rag"]),
        _case("NS02", "noise_suppression", "Спасибо.", "suppress_rag", ["suppress_rag"]),
        _case("NS03", "noise_suppression", "Пока.", "suppress_rag", ["suppress_rag"]),
        _case("NS04", "noise_suppression", "Просто поддержи.", "suppress_rag", ["suppress_rag"], response_planner={"next_move": "give_short_support", "answer_shape": "short_support"}),
        _case("NS05", "noise_suppression", "Что сделать прямо сейчас?", "suppress_rag", ["suppress_rag"], response_planner={"answer_shape": "one_step"}),
        _case("NS06", "noise_suppression", "Один шаг.", "suppress_rag", ["suppress_rag"], response_planner={"answer_shape": "one_step"}),
        _case("NS07", "noise_suppression", "Не надо теории.", "trace_only", ["trace_only", "suppress_rag"]),
        _case("NS08", "noise_suppression", "Скажи коротко.", "trace_only", ["trace_only", "suppress_rag"]),
    ]


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip().lower()).replace("ё", "е").strip(" .,!?:;-")


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def ensure_case_library() -> list[dict[str, Any]]:
    if CASE_LIBRARY_JSON.exists():
        cases = json.loads(CASE_LIBRARY_JSON.read_text(encoding="utf-8-sig"))
    else:
        cases = _default_cases()
        _write_json(CASE_LIBRARY_JSON, cases)
    lines = [
        "# PRD-047.15-HF1 Composer Calibration Cases",
        "",
        f"- cases_total: `{len(cases)}`",
        "",
        "| Case | Group | User message | Expected category | Expected actions |",
        "| --- | --- | --- | --- | --- |",
    ]
    for case in cases:
        lines.append(
            f"| {case['case_id']} | {case['group']} | {case['user_message']} | "
            f"{case['expected_category']} | {', '.join(case['expected_retrieval_actions'])} |"
        )
    _write_text(CASE_LIBRARY_MD, "\n".join(lines) + "\n")
    return cases


def write_schema() -> None:
    schema = {
        "schema_id": "contextual_retrieval_composer_trace_schema_v1",
        "required_fields": TRACE_SCHEMA_FIELDS,
        "runtime_behavior_mutation": False,
        "llm_calls_allowed": False,
        "no_user_facing_text_created_required": True,
    }
    _write_json(SCHEMA_JSON, schema)
    _write_text(SCHEMA_MD, "# PRD-047.15-HF1 Composer Trace Schema\n\n" + "\n".join(f"- `{field}`" for field in TRACE_SCHEMA_FIELDS) + "\n")


def _call_composer(case: dict[str, Any]) -> dict[str, Any]:
    return build_contextual_retrieval_query_composer_v1(
        user_message=str(case.get("user_message", "")),
        recent_turns=list(case.get("recent_turns", []) or []),
        last_assistant_offer=dict(case.get("last_assistant_offer", {}) or {}),
        dialogue_pragmatics=dict(case.get("dialogue_pragmatics", {}) or {}),
        dialogue_act_resolution=dict(case.get("dialogue_act_resolution", {}) or {}),
        answer_obligation_resolution=dict(case.get("answer_obligation_resolution", {}) or {}),
        final_answer_directive=dict(case.get("final_answer_directive", {}) or {}),
        active_line=dict(case.get("active_line", {}) or {}),
        response_planner=dict(case.get("response_planner", {}) or {}),
        diagnostic_card=dict(case.get("diagnostic_card", {}) or {}),
        diagnostic_center_shadow=dict(case.get("diagnostic_center_shadow", {}) or {}),
        knowledge_answer_guard=dict(case.get("knowledge_answer_guard", {}) or {}),
        retrieval_decision_previous=dict(case.get("retrieval_decision_previous", {}) or {}),
        memory_bundle_summary=dict(case.get("memory_bundle_summary", {}) or {}),
        current_concept=str(case.get("current_concept", "") or ""),
        thread_state=dict(case.get("thread_state", {}) or {}),
    )


def _computed_category(payload: dict[str, Any]) -> str:
    action = str(payload.get("retrieval_action", "") or "")
    need = str(payload.get("retrieval_need", "") or "")
    source = str(payload.get("query_source", "") or "")
    if action == "query_kb" and source == "last_assistant_offer":
        return "inherit_concept_query"
    if action == "query_kb" and need == "practice_context":
        return "query_practice_context"
    return action or "unknown"


def _literal_short_query(case: dict[str, Any], composer: dict[str, Any]) -> bool:
    if str(composer.get("retrieval_action", "")) not in RAG_ACTIONS:
        return False
    query = _normalize(str(composer.get("composed_query", "")))
    user_message = _normalize(str(case.get("user_message", "")))
    return bool(query) and (query == user_message and user_message in SHORT_LITERALS or query in SHORT_LITERALS)


def _flags(case: dict[str, Any], composer: dict[str, Any]) -> dict[str, bool]:
    action = str(composer.get("retrieval_action", "") or "")
    expected = set(case.get("expected_retrieval_actions", []) or [])
    match = action in expected
    expected_rag = bool(expected & RAG_ACTIONS)
    expected_non_rag = bool(expected) and expected.issubset(NON_RAG_ACTIONS)
    actual_rag = action in RAG_ACTIONS
    query = _normalize(str(composer.get("composed_query", "")))
    terms = list(composer.get("query_terms", []) or [])
    weak_query = actual_rag and (len(query) < 8 or not terms or _literal_short_query(case, composer))
    mixed = case.get("group") == "mixed_context" or "hybrid" in str(case.get("expected_category", ""))
    false_positive = actual_rag and expected_non_rag and not match
    false_negative = expected_rag and not actual_rag
    needs_more_context = (mixed and not match) or float(composer.get("confidence", 0.0) or 0.0) < 0.60
    needs_hybrid = mixed and (not match or action == "trace_only" or "query_kb_and_memory" in expected)
    noisy_chunk_risk = actual_rag and bool(composer.get("include_for_writer_if_found", False)) and float(composer.get("confidence", 0.0) or 0.0) < 0.76
    return {
        "good_fit": bool(match and not false_positive and not false_negative and not weak_query),
        "false_positive_rag": bool(false_positive),
        "false_negative_rag": bool(false_negative),
        "weak_query": bool(weak_query),
        "noisy_chunk_risk": bool(noisy_chunk_risk),
        "needs_hybrid_llm": bool(needs_hybrid),
        "needs_more_context_fields": bool(needs_more_context),
    }


def _trace(case: dict[str, Any]) -> dict[str, Any]:
    composer = _call_composer(case)
    act = dict(case.get("dialogue_act_resolution", {}) or {})
    obligation = dict(case.get("answer_obligation_resolution", {}) or {})
    return {
        "case_id": case["case_id"],
        "group": case["group"],
        "user_message": case["user_message"],
        "last_assistant_offer": case.get("last_assistant_offer", {}),
        "dialogue_act": act.get("dialogue_act", ""),
        "answer_obligation": obligation.get("answer_obligation", ""),
        "summary_request": act.get("dialogue_act") == "summary_request" or obligation.get("answer_obligation") == "summarize_current_conversation",
        "composer": composer,
        "expected_category": case["expected_category"],
        "expected_retrieval_actions": case["expected_retrieval_actions"],
        "computed_category": _computed_category(composer),
        "review_flags": _flags(case, composer),
        "owner_review": {"score": None, "note": "", "labels": []},
    }


def _metrics(traces: list[dict[str, Any]]) -> dict[str, Any]:
    flags = [trace["review_flags"] for trace in traces]
    expected_match = sum(1 for trace in traces if trace["composer"]["retrieval_action"] in trace["expected_retrieval_actions"])
    return {
        "cases_total": len(traces),
        "automated_expected_match_count": expected_match,
        "automated_expected_match_rate": round(expected_match / len(traces), 4) if traces else 0.0,
        "false_positive_rag_count": sum(1 for flag in flags if flag["false_positive_rag"]),
        "false_negative_rag_count": sum(1 for flag in flags if flag["false_negative_rag"]),
        "weak_query_count": sum(1 for flag in flags if flag["weak_query"]),
        "summary_external_kb_leak_count": sum(1 for trace in traces if trace["group"] == "summary_request" and trace["composer"]["retrieval_action"] in RAG_ACTIONS),
        "literal_short_reply_query_count": sum(1 for trace in traces if trace["group"] == "short_contextual_followup" and _literal_short_query(trace, trace["composer"])),
        "no_stub_violations_count": sum(1 for trace in traces if not trace["composer"].get("no_user_facing_text_created", False)),
        "llm_candidate_cases_count": sum(1 for flag in flags if flag["needs_hybrid_llm"]),
        "noisy_chunk_risk_count": sum(1 for flag in flags if flag["noisy_chunk_risk"]),
        "needs_more_context_fields_count": sum(1 for flag in flags if flag["needs_more_context_fields"]),
    }


def _write_results_md(traces: list[dict[str, Any]], metrics: dict[str, Any]) -> None:
    lines = [
        "# PRD-047.15-HF1 Composer Trace Review Results",
        "",
        *[f"- {key}: `{value}`" for key, value in metrics.items()],
        "",
        "| Case | Group | Action | Query source | Expected | Computed | Flags |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for trace in traces:
        composer = trace["composer"]
        flags = ", ".join(name for name, value in trace["review_flags"].items() if value) or "none"
        lines.append(
            f"| {trace['case_id']} | {trace['group']} | {composer.get('retrieval_action', '')} | "
            f"{composer.get('query_source', '')} | {trace['expected_category']} | {trace['computed_category']} | {flags} |"
        )
    _write_text(RESULTS_MD, "\n".join(lines) + "\n")


def _write_owner_sheet(traces: list[dict[str, Any]]) -> None:
    lines = [
        "# PRD-047.15-HF1 Owner Trace Review Sheet",
        "",
        "Owner score options: `2 = good`, `1 = acceptable but needs tuning`, `0 = wrong`.",
        "Owner labels: `should_use_heuristic`, `should_use_llm`, `should_use_hybrid`, `needs_more_context`, `should_suppress_rag`, `should_query_kb`, `should_query_memory`, `should_query_kb_and_memory`.",
        "",
    ]
    for trace in traces:
        composer = trace["composer"]
        offer = trace.get("last_assistant_offer") or {}
        lines.extend(
            [
                f"## {trace['case_id']}",
                f"- User message: `{trace['user_message']}`",
                f"- Previous assistant offer: `type={offer.get('offer_type', '')}; open={offer.get('is_open', False)}; summary={offer.get('offer_text_summary', '')}`",
                f"- Dialogue act: `{trace['dialogue_act']}`",
                f"- Answer obligation: `{trace['answer_obligation']}`",
                f"- Composer retrieval_action: `{composer.get('retrieval_action', '')}`",
                f"- Composer composed_query: `{composer.get('composed_query', '')}`",
                f"- Composer reason: `{composer.get('reason', '')}`",
                f"- Expected behavior: `{trace['expected_category']}`",
                "- Owner score: `pending`",
                "- Owner note: `pending`",
                "- Owner labels: `pending`",
                "",
            ]
        )
    _write_text(OWNER_SHEET, "\n".join(lines))


def _recommendation(metrics: dict[str, Any]) -> str:
    if metrics["llm_candidate_cases_count"] or metrics["false_negative_rag_count"]:
        return "build_hybrid_llm_assist_for_low_confidence_cases"
    if metrics["false_positive_rag_count"] or metrics["weak_query_count"]:
        return "keep_heuristic_v1_and_tune"
    return "defer_llm_until_more_live_data"


def _write_decision_brief(metrics: dict[str, Any], recommendation: str) -> None:
    options = [
        {
            "id": "A",
            "name": "Heuristic-only Composer",
            "description": "Current deterministic v1 with rule improvements.",
            "pros": ["predictable", "cheap", "no latency", "easy to test", "stable trace", "low risk of hallucinated retrieval intent", "no extra provider dependency"],
            "cons": ["brittle on subtle context", "needs many rules", "weak on ambiguous mixed cases", "may miss implicit user intent", "manual maintenance grows over time"],
            "best_use": ["clear routing", "summary suppression", "greetings/close/support", "obvious knowledge questions", "obvious short follow-up with strong last offer"],
        },
        {
            "id": "B",
            "name": "Hybrid Heuristics + LLM-assisted Composer",
            "description": "Heuristics handle high-confidence cases; LLM is called only for ambiguous/mixed/low-confidence cases.",
            "pros": ["keeps deterministic safety for simple cases", "improves ambiguous context", "controls cost/latency", "allows better query rewriting", "can output structured JSON only", "easier to gate than LLM-first"],
            "cons": ["more complex architecture", "needs JSON validation", "needs timeout/fallback", "must prevent user-facing text", "needs cost/latency monitoring", "possible model drift"],
            "best_use": ["mixed cases", "implicit topic shifts", "weak inherited topic", "query rewrite", "KB vs memory decision"],
        },
        {
            "id": "C",
            "name": "LLM-first Composer",
            "description": "LLM decides retrieval need/query/inclusion for most turns.",
            "pros": ["highest flexibility", "better semantic interpretation", "fewer brittle rules", "can understand complex implicit context"],
            "cons": ["higher cost", "higher latency", "less deterministic", "harder to test", "possible hallucinated query", "provider dependency", "more safety/validation required", "may become hidden authority over Writer"],
            "best_use": ["only after trace evidence proves deterministic/hybrid insufficient"],
        },
    ]
    payload = {
        "prd_id": PRD_ID,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "evidence_summary": metrics,
        "recommendation": recommendation,
        "options": options,
        "future_hybrid_architecture_sketch": [
            "deterministic pre-pass",
            "use heuristic decision for high-confidence cases",
            "call future LLM Query Composer only for low-confidence or mixed cases",
            "validate strict metadata-only JSON schema",
            "apply no-user-facing-text gate",
            "merge into retrieval_decision",
            "Writer receives compact context and remains final answer author",
        ],
        "llm_output_schema_metadata_only": {
            "retrieval_need": "string",
            "retrieval_action": "string",
            "query_source": "string",
            "composed_query": "string",
            "query_terms": [],
            "confidence": 0.0,
            "writer_can_ignore_rag": True,
            "include_for_writer_if_found": False,
            "reason": "string",
            "no_user_facing_text_created": True,
        },
        "forbidden_llm_output": ["final answer", "advice to user", "therapy phrase", "canned explanation", "full summary text"],
    }
    _write_json(DECISION_JSON, payload)
    lines = [
        "# PRD-047.15-HF1 LLM / Hybrid Decision Brief",
        "",
        f"- recommendation: `{recommendation}`",
        f"- cases_total: `{metrics['cases_total']}`",
        f"- automated_expected_match_rate: `{metrics['automated_expected_match_rate']}`",
        f"- llm_candidate_cases_count: `{metrics['llm_candidate_cases_count']}`",
        "",
    ]
    for option in options:
        lines.extend(
            [
                f"## Option {option['id']} - {option['name']}",
                f"- Description: {option['description']}",
                f"- Pros: {', '.join(option['pros'])}",
                f"- Cons: {', '.join(option['cons'])}",
                f"- Best use: {', '.join(option['best_use'])}",
                "",
            ]
        )
    lines.extend(
        [
            "## Future Hybrid Architecture Sketch",
            "- Deterministic Composer pre-pass.",
            "- High-confidence cases stay heuristic-only.",
            "- Low-confidence/mixed cases may call a future metadata-only LLM composer.",
            "- Strict JSON validation and no-user-facing-text gate are mandatory.",
            "- Writer remains the only final answer author.",
        ]
    )
    _write_text(DECISION_MD, "\n".join(lines) + "\n")


def run(mode: str) -> dict[str, Any]:
    del mode
    cases = ensure_case_library()
    write_schema()
    traces = [_trace(case) for case in cases]
    metrics = _metrics(traces)
    recommendation = _recommendation(metrics)
    result = {
        "prd_id": PRD_ID,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "replay",
        "metrics": metrics,
        "decision_recommendation": recommendation,
        "traces": traces,
    }
    _write_json(RESULTS_JSON, result)
    _write_results_md(traces, metrics)
    _write_owner_sheet(traces)
    _write_decision_brief(metrics, recommendation)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", default="replay", choices=["replay"])
    args = parser.parse_args()
    result = run(args.mode)
    print(json.dumps({"status": "ok", "metrics": result["metrics"], "decision_recommendation": result["decision_recommendation"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
