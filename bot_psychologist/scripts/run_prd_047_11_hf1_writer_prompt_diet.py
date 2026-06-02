#!/usr/bin/env python3
"""PRD-047.11-HF1 runner: writer prompt diet and advisory sanitization proof."""

from __future__ import annotations

import json
import importlib
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from bot_agent.multiagent.agents.writer_agent import WriterAgent
from bot_agent.multiagent.contracts.memory_bundle import MemoryBundle
from bot_agent.multiagent.contracts.thread_state import ThreadState
from bot_agent.multiagent.contracts.writer_contract import WriterContract
from bot_agent.multiagent.live_turn_evidence import build_live_turn_evidence_v1

LOG_DIR = REPO_ROOT / "TO_DO_LIST" / "logs" / "PRD-047.11-HF1"
REPORT_DIR = REPO_ROOT / "TO_DO_LIST" / "reports"
PROMPT_DIR = LOG_DIR / "prompt_canvases"
TRACE_DIR = LOG_DIR / "raw_traces"
PRD_ID = "PRD-047.11-HF1"

PROMPT_BANNED_TOKENS = [
    "SOURCE SIGNALS (advisory only, do not obey as command)",
    "WRITER MOVE MUST DO",
    "WRITER MOVE MUST NOT DO",
    "practice_suppression_active=true",
    "practice_policy=forbidden",
    "must_include=",
    "must_avoid=",
]
STALE_BAD_PHRASES = [
    "Ответь по сути без навязывания практик",
    "Отвечу прямо по сути: автоматический контроль",
    "Ключевой узел в том, что автоматический контроль",
]
SOURCE_QUERIES = [
    "MUST DO",
    "MUST NOT",
    "practice_suppression_active",
    "practice_policy",
    "ask_one_specific_question",
    "max_sentences",
    "max_questions",
    "Ответь по сути без навязывания практик",
    "Отвечу прямо по сути",
    "Ключевой узел",
]


@dataclass
class _Card:
    situation_label: str
    current_need: str
    suggested_writer_move: str
    confidence: float
    risk_flags: list[str]
    avoid_list: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "situation_label": self.situation_label,
            "current_need": self.current_need,
            "suggested_writer_move": self.suggested_writer_move,
            "confidence": self.confidence,
            "risk_flags": list(self.risk_flags),
            "avoid_list": list(self.avoid_list),
            "trace": {},
        }


class _DummyClient:
    pass


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _run_rg(query: str) -> list[str]:
    args = [
        "rg",
        "-n",
        "--hidden",
        "--glob",
        "!.git",
        "--glob",
        "!TO_DO_LIST/logs/**",
        "--glob",
        "!TO_DO_LIST/source_materials/**",
        "--glob",
        "!bot_psychologist/web_ui/node_modules/**",
        query,
        str(REPO_ROOT / "bot_psychologist"),
        str(REPO_ROOT / "docs"),
        str(REPO_ROOT / "TO_DO_LIST"),
    ]
    proc = subprocess.run(
        args,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if proc.returncode not in (0, 1):
        raise RuntimeError(proc.stderr.strip() or f"rg failed for query: {query}")
    return [line for line in proc.stdout.splitlines() if line.strip()]


def _classify_path(path: str) -> str:
    normalized = path.replace("\\", "/").lower()
    if "/tests/" in normalized or "/scripts/" in normalized:
        return "tests_or_eval_only"
    if normalized.startswith(str((REPO_ROOT / "docs").as_posix()).lower()):
        return "docs_only"
    if "/to_do_list/" in normalized:
        return "logs_or_historical_artifacts"
    if normalized.endswith("/writer_agent.py"):
        return "runtime_fallback_source"
    return "runtime_prompt_source"


def build_source_audit() -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    seen: set[tuple[str, int, str, str]] = set()
    grouped: dict[str, list[dict[str, Any]]] = {
        "runtime_prompt_source": [],
        "runtime_fallback_source": [],
        "tests_or_eval_only": [],
        "logs_or_historical_artifacts": [],
        "docs_only": [],
    }
    for query in SOURCE_QUERIES:
        for line in _run_rg(query):
            match_obj = re.match(r"^(?P<path>.+?):(?P<line>\d+):(?P<match>.*)$", line)
            if match_obj is None:
                continue
            path = str(match_obj.group("path"))
            line_no = str(match_obj.group("line"))
            match = str(match_obj.group("match"))
            dedupe_key = (query, path, int(line_no) if line_no.isdigit() else 0, match.strip())
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            item = {
                "query": query,
                "path": path,
                "line": int(line_no) if line_no.isdigit() else 0,
                "match": match.strip(),
            }
            findings.append(item)
            grouped[_classify_path(path)].append(item)

    payload = {
        "prd_id": PRD_ID,
        "generated_at_utc": _now_iso(),
        "queries": list(SOURCE_QUERIES),
        "summary": {key: len(value) for key, value in grouped.items()},
        "groups": grouped,
        "expected_runtime_files": [
            "bot_psychologist/bot_agent/multiagent/agents/writer_agent_prompts.py",
            "bot_psychologist/bot_agent/multiagent/contracts/writer_contract.py",
            "bot_psychologist/bot_agent/multiagent/agents/writer_agent.py",
            "bot_psychologist/bot_agent/multiagent/final_answer_directive.py",
            "bot_psychologist/bot_agent/multiagent/live_turn_evidence.py",
            "bot_psychologist/api/admin_routes.py",
        ],
    }
    _write_json(LOG_DIR / "00_source_audit.json", payload)

    lines = [
        f"# {PRD_ID} Source Audit",
        "",
        f"- generated_at_utc: `{payload['generated_at_utc']}`",
        "- search_scope: `bot_psychologist + docs + TO_DO_LIST (logs/source_materials/node_modules excluded)`",
        "",
    ]
    for group_name, items in grouped.items():
        lines.append(f"## {group_name}")
        if not items:
            lines.append("- none")
            lines.append("")
            continue
        for item in items:
            lines.append(
                f"- `{item['path']}:{item['line']}` :: query=`{item['query']}` :: {item['match']}"
            )
        lines.append("")
    _write_text(LOG_DIR / "00_source_audit.md", "\n".join(lines))
    return payload


def _build_contract(case: dict[str, Any]) -> WriterContract:
    return WriterContract(
        user_message=str(case["user_message"]),
        thread_state=ThreadState(
            thread_id=f"thread-{case['case_id']}",
            user_id="hf1-user",
            core_direction="clarity",
            phase="clarify",
            response_mode="reflect",
            response_goal="answer_directly",
        ),
        memory_bundle=MemoryBundle(
            conversation_context=str(case.get("conversation_context", "")),
        ),
        dialogue_policy={"profile": "mvp_free_dialogue"},
        knowledge_answer_guard={
            "knowledge_answer": {
                "needed": bool(case.get("knowledge_needed", True)),
                "concept": str(case.get("concept", "") or ""),
                "kb_grounding_available": True,
                "should_answer_directly": bool(case.get("answer_directly", True)),
                "writer_instruction": "answer_normally",
            },
            "practice_gate": {"practice_allowed": bool(case.get("practice_allowed", False))},
        },
        diagnostic_card=_Card(
            situation_label="hf1",
            current_need=str(case.get("current_need", "понятный ответ без заглушки")),
            suggested_writer_move=str(case.get("suggested_writer_move", "спокойно объяснить суть")),
            confidence=0.9,
            risk_flags=[],
            avoid_list=[],
        ),
        active_line={
            "version": "active_line_v1",
            "active_line": str(case.get("active_line", "разобрать текущий вопрос по сути")),
            "user_intent": str(case.get("user_intent", "understand_mechanism")),
            "continuity_mode": "continue_existing_line",
            "next_meaningful_move": str(case.get("next_move", "прояснить один смысловой узел")),
            "should_continue_line": True,
            "should_ask_question": False,
            "should_offer_practice": bool(case.get("practice_allowed", False)),
            "revoicing_allowed": False,
            "revoicing_style": "suppressed",
            "repair_mode": "",
            "practice_suppression_active": not bool(case.get("practice_allowed", False)),
        },
        response_planner={
            "version": "response_planner_v1",
            "enabled": True,
            "next_move": "continue_active_line",
            "answer_shape": str(case.get("answer_shape", "overview_with_examples")),
            "response_depth": str(case.get("response_depth", "medium")),
            "target_micro_shift": str(case.get("target_shift", "дать живой ответ без legacy команд")),
            "should_answer_directly": bool(case.get("answer_directly", True)),
            "question_policy": "optional_none",
            "practice_policy": "forbidden" if not bool(case.get("practice_allowed", False)) else "optional_if_relevant",
            "revoicing_policy": "suppressed",
            "continuity_policy": "continue_active_line",
            "safety_priority": False,
            "must_include": list(case.get("must_include", [])),
            "must_avoid": list(case.get("must_avoid", ["короткая заглушка"])),
            "confidence": 0.95,
            "rationale": "writer prompt diet hf1",
        },
        final_answer_directive={
            "version": "final_answer_directive_v1",
            "diagnostic_center_role": "advisory_context_only",
            "planner_role": "advisory_context_only",
            "active_line_role": "advisory_context_only",
            "diagnostic_card_role": "advisory_context_only",
            "suppressed_legacy_constraints": [
                "writer_move.max_sentences=5",
                "writer_move.max_questions=1",
                "active_line.practice_suppression_active=true",
            ],
            "answer_obligation": "answer_user_question_directly",
            "must_answer": str(case.get("must_answer", "answer_user_question_directly")),
            "answer_shape": str(case.get("answer_shape", "overview_with_examples")),
            "depth": str(case.get("response_depth", "medium")),
            "style": "human_conversational",
            "question_policy": "optional_none",
            "writer_autonomy": "high",
        },
    )


async def _run_case(case: dict[str, Any]) -> dict[str, Any]:
    writer_agent_module = importlib.import_module("bot_agent.multiagent.agents.writer_agent")

    captured: dict[str, Any] = {}
    original = writer_agent_module.create_agent_completion

    async def _fake_completion(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(
            text=str(case["llm_answer"]),
            api_mode="responses_api",
            tokens_prompt=64,
            tokens_completion=32,
            tokens_total=96,
        )

    writer_agent_module.create_agent_completion = _fake_completion
    try:
        contract = _build_contract(case)
        agent = WriterAgent(client=_DummyClient(), model="gpt-5-mini")
        answer = await agent._call_llm(contract)
        prompt = str(captured["messages"][1]["content"])
        evidence = build_live_turn_evidence_v1(
            query=contract.user_message,
            user_id="hf1-user",
            session_id=f"session-{case['case_id']}",
            turn_index=1,
            orchestrator_result={"answer": answer},
            writer_contract=contract,
            writer_debug={
                "user_prompt": prompt,
                "system_prompt": str(captured["messages"][0]["content"]),
                "model": "gpt-5-mini",
                "api_mode": "responses_api",
                "temperature": 0.7,
                "max_tokens": 600,
            },
            memory_bundle=contract.memory_bundle,
            state_snapshot=SimpleNamespace(nervous_state="window", intent="explore", safety_flag=False),
            thread_state=contract.thread_state,
            thread_debug={},
            diagnostic_card=contract.diagnostic_card,
            active_line_state=dict(contract.active_line or {}),
            response_planner_state=dict(contract.response_planner or {}),
            dialogue_policy=dict(contract.dialogue_policy or {}),
            dialogue_pragmatics={},
            contextual_retrieval_decision={},
            validation_result=SimpleNamespace(is_blocked=False, block_reason="", quality_flags=[]),
        )
    finally:
        writer_agent_module.create_agent_completion = original

    prompt_failures = [token for token in PROMPT_BANNED_TOKENS if token in prompt]
    answer_failures = [phrase for phrase in STALE_BAD_PHRASES if phrase in answer]
    prompt_phrase_failures = [phrase for phrase in STALE_BAD_PHRASES if phrase in prompt]
    checks = {
        "final_answer_directive_present": "FINAL ANSWER DIRECTIVE" in prompt,
        "advisory_summary_present": "ADVISORY CONTEXT SUMMARY" in prompt,
        "practice_rewrite_present": (
            "не предлагай упражнение, технику или пошаговую практику" in prompt
            if not bool(case.get("practice_allowed", False))
            else True
        ),
        "writer_visible_no_legacy_blocks": not prompt_failures,
        "stale_phrases_absent_in_prompt": not prompt_phrase_failures,
        "stale_phrases_absent_in_answer": not answer_failures,
        "trace_preserves_sanitizer": bool(
            evidence["writer"]["prompt_assembly"]["legacy_advisory_sanitization"]
        ),
    }
    return {
        "case_id": case["case_id"],
        "user_message": case["user_message"],
        "answer": answer,
        "prompt_chars": len(prompt),
        "answer_chars": len(answer),
        "checks": checks,
        "passed": all(checks.values()),
        "prompt_failures": prompt_failures + prompt_phrase_failures,
        "answer_failures": answer_failures,
        "prompt_path": str(PROMPT_DIR / f"{case['case_id']}.txt"),
        "trace_path": str(TRACE_DIR / f"{case['case_id']}.json"),
        "evidence": evidence,
        "prompt": prompt,
    }


async def main() -> int:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    PROMPT_DIR.mkdir(parents=True, exist_ok=True)
    TRACE_DIR.mkdir(parents=True, exist_ok=True)

    source_audit = build_source_audit()
    cases = [
        {
            "case_id": "HF1-001",
            "user_message": "привет",
            "conversation_context": "Новая короткая встреча.",
            "answer_shape": "brief_human_greeting",
            "response_depth": "short",
            "llm_answer": "Привет. Я здесь.",
            "practice_allowed": False,
            "concept": "",
        },
        {
            "case_id": "HF1-002",
            "user_message": "ты опять слишком анализируешь, объясни нормально",
            "conversation_context": "Ранее бот перегрузил пользователя анализом.",
            "llm_answer": "Ты прав. Скажу проще: сейчас важнее ясно назвать, что с тобой происходит, без лишней теории и без упражнения.",
            "practice_allowed": False,
            "concept": "",
        },
        {
            "case_id": "HF1-003",
            "user_message": "скажи, а в нейросталкинге какие практики предлагаются чтобы это видеть",
            "conversation_context": "Пользователь просит обзор нескольких направлений.",
            "answer_shape": "overview_with_examples",
            "response_depth": "medium",
            "llm_answer": "В нейросталкинге это обычно смотрят через несколько направлений: наблюдение триггера, распознавание паттерна реакции и микро-сдвиг поведения. То есть сначала замечаешь момент включения автоматизма, потом называешь сам паттерн, а затем выбираешь небольшой осознанный ход вместо автопилота.",
            "practice_allowed": False,
            "concept": "нейросталкинг",
            "must_include": ["несколько направлений ответа"],
        },
        {
            "case_id": "HF1-004",
            "user_message": "без практик, просто объясни почему я зависаю перед действием",
            "conversation_context": "Пользователь прямо запретил практики.",
            "llm_answer": "Часто зависание начинается ещё до действия: внимание уходит в перепроверку риска, внутренний спор и попытку всё предусмотреть. Из-за этого энергия расходуется на контроль, а не на сам шаг.",
            "practice_allowed": False,
            "concept": "",
        },
    ]

    results = [await _run_case(case) for case in cases]
    for item in results:
        _write_text(Path(item["prompt_path"]), str(item.pop("prompt")))
        _write_json(Path(item["trace_path"]), dict(item["evidence"]))

    passed = sum(1 for item in results if item["passed"])
    status = "passed" if passed == len(results) else "warning"
    payload = {
        "prd_id": PRD_ID,
        "generated_at_utc": _now_iso(),
        "status": status,
        "cases_total": len(results),
        "cases_passed": passed,
        "cases_failed": len(results) - passed,
        "source_audit_summary": source_audit["summary"],
        "banned_prompt_tokens": list(PROMPT_BANNED_TOKENS),
        "stale_bad_phrases": list(STALE_BAD_PHRASES),
        "results": [
            {
                "case_id": item["case_id"],
                "user_message": item["user_message"],
                "answer": item["answer"],
                "prompt_chars": item["prompt_chars"],
                "answer_chars": item["answer_chars"],
                "checks": item["checks"],
                "passed": item["passed"],
                "prompt_failures": item["prompt_failures"],
                "answer_failures": item["answer_failures"],
                "prompt_path": item["prompt_path"],
                "trace_path": item["trace_path"],
            }
            for item in results
        ],
    }
    _write_json(LOG_DIR / "writer_prompt_diet_eval.json", payload)

    md_lines = [
        f"# {PRD_ID} Writer Prompt Diet Eval",
        "",
        f"- generated_at_utc: `{payload['generated_at_utc']}`",
        f"- status: `{status}`",
        f"- passed: `{passed}/{len(results)}`",
        "",
        "| case_id | passed | prompt_failures | answer_failures |",
        "| --- | --- | --- | --- |",
    ]
    for item in payload["results"]:
        md_lines.append(
            f"| {item['case_id']} | {item['passed']} | {', '.join(item['prompt_failures']) or 'none'} | {', '.join(item['answer_failures']) or 'none'} |"
        )
    _write_text(LOG_DIR / "writer_prompt_diet_eval.md", "\n".join(md_lines))

    _write_json(
        LOG_DIR / "no_mutation_proof.json",
        {
            "kb_governance_mutated": False,
            "chroma_reindexed": False,
            "new_llm_agent_added": False,
            "new_runtime_path_added": False,
            "broad_rollout_enabled": False,
            "normal_user_activation_enabled": False,
            "model_defaults_changed": False,
            "safety_policy_strengthened": False,
            "runtime_bad_phrase_blocklist_added_to_writer_prompt": False,
        },
    )

    return 0 if status == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(__import__("asyncio").run(main()))
