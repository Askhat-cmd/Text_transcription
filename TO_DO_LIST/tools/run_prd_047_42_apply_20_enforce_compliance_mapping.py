from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
BOT_ROOT = REPO_ROOT / "bot_psychologist"
if str(BOT_ROOT) not in sys.path:
    sys.path.insert(0, str(BOT_ROOT))

from bot_agent.multiagent.agents.writer_agent import WriterAgent
from bot_agent.multiagent.contracts.memory_bundle import MemoryBundle, SemanticHit, UserProfile
from bot_agent.multiagent.contracts.thread_state import ThreadState
from bot_agent.multiagent.contracts.writer_contract import WriterContract


PRD_ID = "PRD-047.42-APPLY-20"
NORMALIZED_TIMESTAMP = "normalized_for_prd_047_42_apply_20"
OUT_DIR = REPO_ROOT / "TO_DO_LIST" / "logs" / PRD_ID
WRITER_AGENT_PATH = (
    REPO_ROOT / "bot_psychologist" / "bot_agent" / "multiagent" / "agents" / "writer_agent.py"
)
HISTORICAL_HEAD = "7f344967"
HISTORICAL_WRITER_AGENT_HASH = "2fd82678c0e971951355e84a1254e0982e32b8f9"
HISTORICAL_SLICE12_HASH = "8a9544b784f16bb3b3968d2c787964b684e85838"
PROTECTED_FILES = [
    "bot_psychologist/bot_agent/multiagent/agents/writer_agent_constants.py",
    "bot_psychologist/bot_agent/multiagent/agents/writer_agent_fallback_helpers.py",
    "bot_psychologist/bot_agent/multiagent/agents/writer_agent_fallback_state_mixin.py",
    "bot_psychologist/bot_agent/multiagent/agents/writer_agent_lifecycle_mixin.py",
    "bot_psychologist/bot_agent/multiagent/agents/writer_agent_call_llm_slice1.py",
    "bot_psychologist/bot_agent/multiagent/agents/writer_agent_call_llm_slice2.py",
    "bot_psychologist/bot_agent/multiagent/agents/writer_agent_call_llm_slice3.py",
    "bot_psychologist/bot_agent/multiagent/agents/writer_agent_call_llm_slice4.py",
    "bot_psychologist/bot_agent/multiagent/agents/writer_agent_call_llm_slice5.py",
    "bot_psychologist/bot_agent/multiagent/agents/writer_agent_call_llm_slice6.py",
    "bot_psychologist/bot_agent/multiagent/agents/writer_agent_call_llm_slice7.py",
    "bot_psychologist/bot_agent/multiagent/agents/writer_agent_call_llm_slice8.py",
    "bot_psychologist/bot_agent/multiagent/agents/writer_agent_call_llm_slice9.py",
    "bot_psychologist/bot_agent/multiagent/agents/writer_agent_call_llm_slice10.py",
    "bot_psychologist/bot_agent/multiagent/agents/writer_agent_call_llm_slice11.py",
    "bot_psychologist/bot_agent/multiagent/agents/writer_agent_prompts.py",
    "bot_psychologist/bot_agent/multiagent/contracts/writer_contract.py",
    "bot_psychologist/bot_agent/multiagent/agents/writer_agent_call_llm_slice12.py",
    "bot_psychologist/bot_agent/multiagent/agents/writer_agent.py",
]


@dataclass(frozen=True)
class RuleInfo:
    rule_id: int
    start: int
    end: int
    condition: str
    action: str
    early_return: bool
    locals_read: tuple[str, ...]
    body_lines: tuple[int, ...]


@dataclass(frozen=True)
class ClusterProposal:
    name: str
    start: int
    end: int
    rule_range: str
    rationale: str


@dataclass(frozen=True)
class ExternalDependency:
    name: str
    module_source: str
    kind: str


EXTERNAL_DEPENDENCIES = [
    ExternalDependency("normalize_dialogue_profile", "dialogue_policy", "function"),
    ExternalDependency("detect_expansion_request", "dialogue_policy", "function"),
    ExternalDependency("detect_repair_and_expand_request", "dialogue_policy", "function"),
    ExternalDependency("detect_explicit_answer_need", "dialogue_policy", "function"),
    ExternalDependency("detect_direct_concrete_request", "dialogue_policy", "function"),
    ExternalDependency("detect_summary_request", "dialogue_policy", "function"),
    ExternalDependency("detect_sarcasm_or_negative_feedback", "dialogue_policy", "function"),
    ExternalDependency("detect_application_request", "dialogue_policy", "function"),
    ExternalDependency("evaluate_concrete_answer_fit", "concrete_answer_fit", "function"),
    ExternalDependency("_contains_any", "writer_agent_constants", "function"),
    ExternalDependency("_extract_literal_markdown_echo_request", "writer_agent_constants", "function"),
    ExternalDependency("starts_with_mechanical_revoicing", "active_line", "function"),
    ExternalDependency("DIALOGUE_PROFILE_MVP_FREE", "dialogue_policy", "constant"),
    ExternalDependency("_PRACTICE_MARKERS", "writer_agent", "constant"),
    ExternalDependency("_KNOWN_CONCEPT_CLARIFICATION_MARKERS", "writer_agent", "constant"),
    ExternalDependency("_EXTERNAL_SURVEILLANCE_MARKERS", "writer_agent", "constant"),
    ExternalDependency("_LOW_RESOURCE_NO_PRACTICE_MARKERS", "writer_agent", "constant"),
    ExternalDependency("re", "stdlib", "module"),
]

CLUSTER_PROPOSALS = [
    ClusterProposal(
        "intake_and_obligation_prelude",
        583,
        785,
        "R01-R03",
        "All ctx extraction, detector booleans, answer-fit evaluation, and early greeting gate live here. This must stay ahead of every repair family because later rules read these normalized locals.",
    ),
    ClusterProposal(
        "obligation_specific_repairs_before_profile_split",
        786,
        872,
        "R04-R16",
        "Continuous sequence of obligation-bound repairs (`bounded_practice`, literal markdown, answer_last_offer, direct knowledge answers) that all run before dialogue-profile dispatch.",
    ),
    ClusterProposal(
        "mvp_free_branch_handoff",
        874,
        911,
        "R17",
        "Single early-return handoff into `_enforce_mvp_free_dialogue_compliance`. Keep isolated until the parent method is smaller; it is a branch boundary, not a simple helper.",
    ),
    ClusterProposal(
        "non_mvp_contact_support_and_clarify_rules",
        913,
        970,
        "R18-R32",
        "Compact contact/safety/clarification rules with many literal returns. These are mostly order-sensitive but continuous and can become a later `text -> text` family.",
    ),
    ClusterProposal(
        "known_concept_and_question_policy_cascade",
        972,
        1067,
        "R33-R54",
        "Repairs for known concepts, question-policy stripping, and misalignment recovery. This is the first large semantic cluster after the MVP split.",
    ),
    ClusterProposal(
        "practice_step_and_active_line_tail",
        1068,
        1190,
        "R55-R75",
        "Late tail: template leakage, direct-step fallback, active-line suppression, mechanical revoicing, and known-concept tail repairs. Good candidate for several continuous sub-slices later.",
    ),
]


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        safe = [str(value).replace("|", "\\|").replace("\n", "<br>") for value in row]
        lines.append("| " + " | ".join(safe) + " |")
    return "\n".join(lines)


def _read_writer_source() -> str:
    return WRITER_AGENT_PATH.read_text(encoding="utf-8-sig")


def _read_writer_lines() -> list[str]:
    return _read_writer_source().splitlines()


def _extract_method_node() -> ast.FunctionDef:
    tree = ast.parse(_read_writer_source())
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "WriterAgent":
            for child in node.body:
                if isinstance(child, ast.FunctionDef) and child.name == "_enforce_answer_compliance":
                    return child
    raise RuntimeError("WriterAgent._enforce_answer_compliance not found")


def _walk_if_nodes_in_order(node: ast.AST) -> list[ast.If]:
    items: list[ast.If] = []

    def visit(current: ast.AST) -> None:
        body: Iterable[ast.stmt] = []
        if isinstance(current, ast.FunctionDef):
            body = current.body
        elif isinstance(current, ast.If):
            body = [*current.body, *current.orelse]
        else:
            return
        for stmt in body:
            if isinstance(stmt, ast.If):
                items.append(stmt)
                visit(stmt)
            else:
                for child in ast.iter_child_nodes(stmt):
                    if isinstance(child, ast.If):
                        items.append(child)
                        visit(child)

    visit(node)
    return sorted(items, key=lambda item: (item.lineno, getattr(item, "end_lineno", item.lineno)))


def _collect_assigned_names(target: ast.AST) -> list[str]:
    if isinstance(target, ast.Name):
        return [target.id]
    if isinstance(target, (ast.Tuple, ast.List)):
        result: list[str] = []
        for elt in target.elts:
            result.extend(_collect_assigned_names(elt))
        return result
    return []


def _collect_local_names(fn: ast.FunctionDef) -> set[str]:
    local_names = {arg.arg for arg in fn.args.args}
    for stmt in ast.walk(fn):
        if isinstance(stmt, ast.Assign):
            for target in stmt.targets:
                local_names.update(_collect_assigned_names(target))
        elif isinstance(stmt, ast.AnnAssign):
            local_names.update(_collect_assigned_names(stmt.target))
    return local_names


def _load_names(node: ast.AST) -> list[str]:
    seen: list[str] = []
    for child in ast.walk(node):
        if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load):
            if child.id not in seen:
                seen.append(child.id)
    return seen


def _body_lines(node: ast.If) -> tuple[int, ...]:
    if not node.body:
        return ()
    start = min(getattr(stmt, "lineno", node.lineno) for stmt in node.body)
    end = getattr(node, "end_lineno", node.lineno)
    return tuple(range(start, end + 1))


def _truncate(text: str, limit: int = 160) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 3] + "..."


def _action_summary(node: ast.If) -> str:
    for child in ast.walk(node):
        if isinstance(child, ast.Return):
            try:
                rendered = ast.unparse(child.value) if child.value is not None else "None"
            except Exception:
                rendered = "return"
            return _truncate(f"return {rendered}")
    body_text = "\n".join(ast.get_source_segment(_read_writer_source(), stmt) or "" for stmt in node.body)
    if "self.last_debug" in body_text:
        return "mutates `self.last_debug` and continues"
    if "re.sub(" in body_text:
        return "rewrites question markers inside `text`"
    if "parts[1].strip()" in body_text:
        return "drops mechanical revoicing prefix and returns tail"
    if "_resolve_one_step_or_no_practice_fallback" in body_text:
        return "delegates to one-step / no-practice fallback helper"
    if "_defer_no_stub_repair" in body_text:
        return "returns no-stub retry signal via defer helper"
    return "conditional branch without direct return summary"


def build_rule_inventory() -> list[RuleInfo]:
    fn = _extract_method_node()
    local_names = _collect_local_names(fn)
    rules: list[RuleInfo] = []
    for index, if_node in enumerate(_walk_if_nodes_in_order(fn), start=1):
        condition = _truncate(ast.unparse(if_node.test), limit=220)
        locals_read = tuple(
            name
            for name in _load_names(if_node.test)
            if name in local_names and name not in {"self", "contract", "response_text"}
        )
        rules.append(
            RuleInfo(
                rule_id=index,
                start=if_node.lineno,
                end=getattr(if_node, "end_lineno", if_node.lineno),
                condition=condition,
                action=_action_summary(if_node),
                early_return=any(isinstance(child, ast.Return) for child in ast.walk(if_node)),
                locals_read=locals_read,
                body_lines=_body_lines(if_node),
            )
        )
    return rules


def _classify_source(expr: ast.AST) -> str:
    rendered = ast.unparse(expr)
    if "contract.to_prompt_context" in rendered:
        return "contract.to_prompt_context()"
    if "ctx.get" in rendered:
        return "ctx.get(...)"
    if "detect_" in rendered:
        return "detector/helper call"
    if "_contains_any" in rendered:
        return "_contains_any(...)"
    if "evaluate_concrete_answer_fit" in rendered:
        return "evaluate_concrete_answer_fit(...)"
    if rendered.startswith("dict("):
        return "dict-normalization"
    if rendered.startswith("bool("):
        return "bool-derived flag"
    if rendered.startswith("str("):
        return "str-normalized value"
    if rendered.startswith("any("):
        return "any(...) detector"
    if "re." in rendered:
        return "regex-derived value"
    return _truncate(rendered, limit=60)


def build_prelude_inventory(rules: list[RuleInfo]) -> list[dict[str, Any]]:
    fn = _extract_method_node()
    prelude: list[dict[str, Any]] = []
    prelude_rule_reads = {rule.rule_id: set(rule.locals_read) for rule in rules}
    for stmt in fn.body:
        lineno = getattr(stmt, "lineno", 0)
        if lineno >= 786:
            break
        if isinstance(stmt, ast.Assign):
            targets: list[str] = []
            for target in stmt.targets:
                targets.extend(_collect_assigned_names(target))
            for name in targets:
                if name == "self":
                    continue
                read_by = [rule_id for rule_id, names in prelude_rule_reads.items() if name in names]
                prelude.append(
                    {
                        "name": name,
                        "lines": f"{stmt.lineno}-{getattr(stmt, 'end_lineno', stmt.lineno)}",
                        "source": _classify_source(stmt.value),
                        "read_by_rules": read_by,
                    }
                )
        elif isinstance(stmt, ast.AnnAssign):
            for name in _collect_assigned_names(stmt.target):
                read_by = [rule_id for rule_id, names in prelude_rule_reads.items() if name in names]
                prelude.append(
                    {
                        "name": name,
                        "lines": f"{stmt.lineno}-{getattr(stmt, 'end_lineno', stmt.lineno)}",
                        "source": _classify_source(stmt.value),
                        "read_by_rules": read_by,
                    }
                )
    return prelude


def build_external_dependency_rows(rules: list[RuleInfo]) -> list[list[Any]]:
    rule_name_sets: dict[int, set[str]] = {}
    fn = _extract_method_node()
    rule_nodes = _walk_if_nodes_in_order(fn)
    for rule, node in zip(rules, rule_nodes):
        rule_name_sets[rule.rule_id] = set(_load_names(node))
    rows: list[list[Any]] = []
    for dep in EXTERNAL_DEPENDENCIES:
        used_by = [
            rule.rule_id
            for rule in rules
            if dep.name in rule_name_sets.get(rule.rule_id, set())
        ]
        rows.append([dep.name, dep.module_source, dep.kind, ", ".join(f"R{idx:02d}" for idx in used_by) or "none"])
    return rows


def build_boundary_map_report() -> str:
    rules = build_rule_inventory()
    prelude = build_prelude_inventory(rules)
    prelude_rows = [
        [
            item["name"],
            item["lines"],
            item["source"],
            ", ".join(f"R{rule_id:02d}" for rule_id in item["read_by_rules"]) or "none",
        ]
        for item in prelude
    ]
    rule_rows = [
        [
            f"R{rule.rule_id:02d}",
            f"{rule.start}-{rule.end}",
            rule.condition,
            rule.action,
            "yes" if rule.early_return else "no",
            ", ".join(rule.locals_read) or "none",
        ]
        for rule in rules
    ]
    cluster_rows = [
        [item.name, f"{item.start}-{item.end}", item.rule_range, item.rationale]
        for item in CLUSTER_PROPOSALS
    ]
    dependency_rows = build_external_dependency_rows(rules)
    lines = [
        "# _enforce_answer_compliance Boundary Map",
        "",
        f"- PRD: `{PRD_ID}`",
        "- target: `WriterAgent._enforce_answer_compliance(self, response_text: str, contract: WriterContract) -> str`",
        "- method lines: `582-1191` (`610` LOC)",
        f"- rule_count: `{len(rules)}`",
        "",
        "## Section A. Prelude locals / detector intake",
        "",
        _markdown_table(
            ["local", "lines", "source", "read by rules"],
            prelude_rows,
        ),
        "",
        "## Section B. Numbered rule cascade",
        "",
        _markdown_table(
            ["rule", "lines", "condition", "action on text / branch result", "early return", "locals read"],
            rule_rows,
        ),
        "",
        "## Section C. Proposed continuous cluster families",
        "",
        _markdown_table(
            ["cluster family", "lines", "rule range", "why this is a coherent future slice"],
            cluster_rows,
        ),
        "",
        "## Section D. External dependencies",
        "",
        _markdown_table(
            ["dependency", "module source", "kind", "used by rules"],
            dependency_rows,
        ),
    ]
    return "\n".join(lines)


def _deep_merge(base: dict[str, Any], override: dict[str, Any] | None) -> dict[str, Any]:
    result = copy.deepcopy(base)
    if not override:
        return result
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def _thread_state(*, safety_active: bool = False) -> ThreadState:
    now = datetime.now(timezone.utc)
    return ThreadState(
        thread_id="th_apply_20",
        user_id="u_apply_20",
        core_direction="контроль и перегруз",
        phase="clarify",
        response_mode="reflect",
        response_goal="answer",
        nervous_state="window",
        openness="open",
        ok_position="I+W+",
        pattern_core="control_then_freeze",
        active_frame={"current_need": "простое объяснение"},
        must_avoid=["диагноз"],
        open_loops=["что со мной происходит"],
        safety_active=safety_active,
        created_at=now,
        updated_at=now,
    )


def _memory_bundle() -> MemoryBundle:
    return MemoryBundle(
        conversation_context="USER: Мне тяжело. ASSISTANT: Я рядом.",
        user_profile=UserProfile(patterns=["control"], values=["clarity"]),
        semantic_hits=[
            SemanticHit(
                chunk_id="c1",
                content="Нейросталкинг — наблюдение автоматических реакций.",
                source="kb",
                score=0.92,
            ),
            SemanticHit(
                chunk_id="c2",
                content="Контроль может сжимать внимание до действия.",
                source="kb",
                score=0.87,
            ),
        ],
        has_relevant_knowledge=True,
        context_turns=2,
        recent_turns=[
            {"role": "user", "content": "что такое нейросталкинг?"},
            {"role": "assistant", "content": "это наблюдение реакции"},
        ],
    )


def _base_contract() -> WriterContract:
    return WriterContract(
        user_message="объясни по-человечески, что такое нейросталкинг, без практик",
        thread_state=_thread_state(),
        memory_bundle=_memory_bundle(),
        knowledge_answer_guard={
            "knowledge_answer": {"should_answer_directly": True, "concept": "нейросталкинг"},
            "practice_gate": {"practice_allowed": False, "is_greeting": False},
        },
        philosophy_kernel={
            "kernel_version": "philosophy_kernel_v1",
            "selection": {"selected_lenses": ["mechanism", "protection"]},
            "prompt_compactness": {"max_kernel_chars": 1800},
        },
        writer_freedom_contract={
            "version": "writer_freedom_contract_v1",
            "freedom_level": "guided",
            "mode_hint": "reflect",
            "question_limit": 1,
            "practice_requires_gate": True,
            "hard_boundaries": ["safety", "no_unsolicited_practice"],
        },
        active_line={
            "version": "active_line_v1",
            "user_intent": "known_concept_question",
            "repair_mode": "",
            "revoicing_allowed": True,
            "should_offer_practice": False,
            "practice_suppression_active": True,
        },
        response_planner={
            "version": "response_planner_v1",
            "enabled": True,
            "next_move": "answer_known_concept",
            "answer_shape": "compact_direct",
            "question_policy": "none",
            "practice_policy": "forbidden",
            "safety_priority": False,
        },
        dialogue_policy={
            "profile": "safe_guided",
            "profile_preset": "safe_guided",
            "context_budget_chars": 2800,
            "explicit_answer_need": True,
            "direct_concrete_request": False,
            "summary_request": False,
            "sarcasm_or_negative_feedback": False,
            "application_request": False,
            "answer_obligation_resolution": {
                "answer_obligation": "answer_knowledge_question",
                "answer_shape": "structured_explanation",
                "depth": "medium",
                "question_policy": "none",
                "source": ["latest_turn"],
            },
        },
        dialogue_pragmatics={"version": "dialogue_pragmatics_v1", "should_answer_directly": True},
        retrieval_decision={
            "retrieval_decision_version": "contextual_retrieval_gating_v1",
            "retrieval_action": "include_rag",
            "rag_candidates_count": 2,
            "rag_included_count": 2,
            "rag_included_reason": "direct_concept_followup",
            "writer_can_ignore_rag": True,
            "composer": {
                "version": "contextual_retrieval_query_composer_v1",
                "query_source": "current_turn",
                "composed_query": "что такое нейросталкинг",
                "retrieval_need": "direct_knowledge",
                "retrieval_action": "include_rag",
                "writer_can_ignore_rag": True,
            },
        },
        final_answer_directive={
            "version": "final_answer_directive_v1",
            "current_user_request": "объясни по-человечески, что такое нейросталкинг, без практик",
            "must_answer_source": "latest_turn",
            "answer_target": "latest_turn",
            "writer_contact_mode": "structured_answer",
            "no_practice_unless_requested": True,
            "latest_turn_constraints_v1": {"active_constraints": ["no_practice"]},
        },
    )


def _contract(
    *,
    user_message: str | None = None,
    safety_active: bool | None = None,
    knowledge_answer_guard: dict[str, Any] | None = None,
    active_line: dict[str, Any] | None = None,
    response_planner: dict[str, Any] | None = None,
    dialogue_policy: dict[str, Any] | None = None,
    dialogue_pragmatics: dict[str, Any] | None = None,
    final_answer_directive: dict[str, Any] | None = None,
) -> WriterContract:
    contract = _base_contract()
    if user_message is not None:
        contract.user_message = user_message
    if safety_active is not None:
        contract.thread_state = _thread_state(safety_active=safety_active)
    if knowledge_answer_guard is not None:
        contract.knowledge_answer_guard = _deep_merge(contract.knowledge_answer_guard, knowledge_answer_guard)
    if active_line is not None:
        contract.active_line = _deep_merge(contract.active_line, active_line)
    if response_planner is not None:
        contract.response_planner = _deep_merge(contract.response_planner, response_planner)
    if dialogue_policy is not None:
        contract.dialogue_policy = _deep_merge(contract.dialogue_policy, dialogue_policy)
    if dialogue_pragmatics is not None:
        contract.dialogue_pragmatics = _deep_merge(contract.dialogue_pragmatics, dialogue_pragmatics)
    if final_answer_directive is not None:
        contract.final_answer_directive = _deep_merge(contract.final_answer_directive, final_answer_directive)
    return contract


def build_cases() -> list[dict[str, Any]]:
    requested_markdown = "**Жирный заголовок**\n\nПервый абзац.\n\n- Пункт один\n- Пункт два"
    return [
        {
            "name": "empty_text_passthrough",
            "response_text": "",
            "contract": _contract(),
            "note": "Covers the initial empty-text return.",
        },
        {
            "name": "greeting_gate_feedback_repair",
            "response_text": "Главный механизм в том, что автоматический контроль заранее забирает ресурс.",
            "contract": _contract(
                user_message="Привет! Как перестать наступать на одни и те же грабли?",
                response_planner={
                    "next_move": "deepen_mechanism",
                    "answer_shape": "mechanism_explanation",
                    "question_policy": "optional_none",
                },
                dialogue_policy={
                    "answer_obligation_resolution": {"answer_obligation": "continue_thread"},
                },
                final_answer_directive={
                    "acceptance_gate_feedback": {
                        "failed_checks": ["greeting_answered_with_mechanism_explanation"]
                    }
                },
            ),
            "note": "Early greeting repair branch before the main cascade.",
        },
        {
            "name": "close_gently_obligation",
            "response_text": "Пожалуйста. Если хочешь, в следующий раз можем продолжить и разобрать это глубже?",
            "contract": _contract(
                user_message="Спасибо, мне пока хватит.",
                dialogue_policy={"answer_obligation_resolution": {"answer_obligation": "close_gently"}},
                response_planner={
                    "next_move": "continue_active_line",
                    "answer_shape": "expanded_explanation",
                    "question_policy": "optional_none",
                },
            ),
            "note": "Obligation-specific gentle close repair.",
        },
        {
            "name": "bounded_practice_be_strong",
            "response_text": "Сначала сделай три шага и потом задай себе вопрос, как ты держишься?",
            "contract": _contract(
                user_message="Когда включается драйвер «будь сильным», дай одну короткую практику.",
                dialogue_policy={
                    "answer_obligation_resolution": {"answer_obligation": "provide_one_bounded_practice"}
                },
                response_planner={
                    "next_move": "give_direct_step",
                    "answer_shape": "one_step",
                    "question_policy": "none",
                    "practice_policy": "required",
                },
            ),
            "note": "Exercises the bounded-practice repair path and the nested 'будь сильным' branch.",
        },
        {
            "name": "literal_markdown_echo",
            "response_text": "Я слышу тебя. Расскажи больше, если хочешь.",
            "contract": _contract(
                user_message=f"Верни без объяснений и без изменений следующий markdown-блок: {requested_markdown}",
            ),
            "note": "Literal markdown echo repair.",
        },
        {
            "name": "repair_last_question_neurostalking",
            "response_text": "Ладно, тогда уточню иначе.",
            "contract": _contract(
                user_message="ты не ответил мне на вопрос",
                dialogue_policy={
                    "answer_obligation_resolution": {"answer_obligation": "repair_and_answer_last_question"},
                    "unanswered_question_state": {"last_direct_user_question": "что такое нейросталкинг?"},
                },
                dialogue_pragmatics={"repair_user_dissatisfaction": True},
            ),
            "note": "Repair-and-answer-last-question obligation.",
        },
        {
            "name": "mvp_free_branch_handoff",
            "response_text": "Понял — тебе тяжело, и это нормально. Не нужно сейчас ничего исправлять или заставлять себя.\n\nЕсли захочешь дальше — можем вместе придумать один маленький шаг, когда тебе станет легче.",
            "contract": _contract(
                user_message="Всё, не хочу сейчас практику. Мне тяжело, просто скажи по-человечески.",
                dialogue_policy={
                    "profile": "mvp_free_dialogue",
                    "profile_preset": "mvp_free_dialogue",
                    "answer_obligation_resolution": {"answer_obligation": "answer_latest_turn"},
                },
                response_planner={
                    "next_move": "give_direct_step",
                    "answer_shape": "one_step",
                    "question_policy": "none",
                    "practice_policy": "forbidden",
                },
            ),
            "note": "Covers the profile handoff into `_enforce_mvp_free_dialogue_compliance`.",
        },
        {
            "name": "low_resource_short_contact",
            "response_text": "Давай разберем это подробно? Сначала можно сделать шаг.",
            "contract": _contract(
                user_message="Я устал, без анализа, просто поддержи.",
            ),
            "note": "Low-resource no-practice compression.",
        },
        {
            "name": "thanks_close_no_more_steps",
            "response_text": "Пожалуйста. Давай сделаем еще один шаг.",
            "contract": _contract(
                user_message="Спасибо, этого пока хватит.",
                active_line={"user_intent": "thanks_close"},
            ),
            "note": "Active-line thanks-close short-circuit.",
        },
        {
            "name": "safety_priority_question_strip",
            "response_text": "Я рядом. Что сейчас помогает тебе держаться?",
            "contract": _contract(
                safety_active=True,
                response_planner={"safety_priority": True},
            ),
            "note": "Planner safety-priority branch for non-MVP profile.",
        },
        {
            "name": "clarify_one_point_insert_question",
            "response_text": "Похоже, это сильно сжимает тебя.",
            "contract": _contract(
                user_message="Не понимаю, что со мной в этот момент.",
                response_planner={
                    "next_move": "clarify_one_point",
                    "answer_shape": "clarify_one_point",
                    "question_policy": "optional_none",
                },
            ),
            "note": "Clarify-one-point rule with zero questions in text.",
        },
        {
            "name": "user_repair_signal_retry",
            "response_text": "Хорошо, тогда пойдем дальше.",
            "contract": _contract(
                user_message="Ты ушел не туда, вернись к сути и не предлагай практику.",
            ),
            "note": "User repair signal should defer to no-stub retry.",
        },
        {
            "name": "known_concept_neurostalking_repair",
            "response_text": "Это внешнее слежение и биофидбек. О каком варианте ты говоришь?",
            "contract": _contract(
                user_message="что такое нейросталкинг?",
                knowledge_answer_guard={"knowledge_answer": {"concept": "нейросталкинг", "should_answer_directly": True}},
            ),
            "note": "Known-concept repair path before question-policy cascade.",
        },
        {
            "name": "question_policy_none_known_concept",
            "response_text": "Нейросталкинг — это внутреннее наблюдение за автоматическими реакциями?",
            "contract": _contract(
                user_message="что такое нейросталкинг?",
                response_planner={
                    "next_move": "answer_known_concept",
                    "answer_shape": "compact_direct",
                    "question_policy": "none",
                    "practice_policy": "forbidden",
                },
            ),
            "note": "Question-policy none path with known-concept repair tail.",
        },
        {
            "name": "template_leakage_practice_forbidden",
            "response_text": "Попробуй сделать вдох и потом задай себе вопрос, как ты сейчас.",
            "contract": _contract(
                user_message="объясни по-человечески без практик",
                response_planner={
                    "next_move": "continue_active_line",
                    "answer_shape": "compact_direct",
                    "question_policy": "optional_none",
                    "practice_policy": "forbidden",
                },
            ),
            "note": "Planner practice-forbidden with unsolicited practice in answer text.",
        },
        {
            "name": "active_line_revoicing_trim",
            "response_text": "Тебе сейчас тяжело. Попробуй заметить, что именно сжимает тебя в теле.",
            "contract": _contract(
                user_message="Скажи прямо, без перефразирования.",
                active_line={
                    "revoicing_allowed": False,
                    "user_intent": "continue_thread",
                    "repair_mode": "",
                },
                response_planner={
                    "next_move": "continue_active_line",
                    "answer_shape": "compact_direct",
                    "question_policy": "optional_none",
                    "practice_policy": "optional",
                },
                knowledge_answer_guard={"practice_gate": {"practice_allowed": True}},
            ),
            "note": "Mechanical revoicing tail branch.",
        },
        {
            "name": "tail_known_concept_self_realization",
            "response_text": "Самореализация — это когда ты раскрываешь свои задатки и двигаешься к своему пути.",
            "contract": _contract(
                user_message="что такое самореализация?",
                response_planner={
                    "next_move": "answer_known_concept",
                    "answer_shape": "compact_direct",
                    "question_policy": "optional_none",
                    "practice_policy": "forbidden",
                },
                knowledge_answer_guard={"knowledge_answer": {"concept": "самореализация", "should_answer_directly": True}},
            ),
            "note": "Tail known-concept branch for self-realization.",
        },
    ]


def _trace_executed_lines(agent: WriterAgent, response_text: str, contract: WriterContract) -> tuple[str, set[int]]:
    executed: set[int] = set()
    previous = sys.gettrace()

    def local_tracer(frame, event, arg):
        if event == "line":
            executed.add(frame.f_lineno)
        return local_tracer

    def tracer(frame, event, arg):
        if (
            event == "call"
            and frame.f_code.co_name == "_enforce_answer_compliance"
            and Path(frame.f_code.co_filename).resolve() == WRITER_AGENT_PATH.resolve()
        ):
            return local_tracer
        return tracer

    sys.settrace(tracer)
    try:
        result = agent._enforce_answer_compliance(response_text, contract)
    finally:
        sys.settrace(previous)
    return result, executed


def _triggered_rules(executed_lines: set[int], rules: list[RuleInfo]) -> list[int]:
    triggered: list[int] = []
    for rule in rules:
        if set(rule.body_lines) & executed_lines:
            triggered.append(rule.rule_id)
    return triggered


def _summarize_case(contract: WriterContract) -> dict[str, Any]:
    return {
        "user_message": contract.user_message,
        "dialogue_profile": str(contract.dialogue_policy.get("profile", "")),
        "answer_obligation": str(
            dict(contract.dialogue_policy.get("answer_obligation_resolution", {})).get("answer_obligation", "")
        ),
        "planner_next_move": str(contract.response_planner.get("next_move", "")),
        "planner_answer_shape": str(contract.response_planner.get("answer_shape", "")),
        "planner_question_policy": str(contract.response_planner.get("question_policy", "")),
        "planner_practice_policy": str(contract.response_planner.get("practice_policy", "")),
        "active_line_intent": str(contract.active_line.get("user_intent", "")),
        "practice_allowed": bool(
            dict(contract.knowledge_answer_guard.get("practice_gate", {})).get("practice_allowed", True)
        ),
    }


def _coverage_reason(rule: RuleInfo) -> str:
    condition = rule.condition.lower()
    if "самореализац" in condition:
        return "needs dedicated self-realization concept fixture"
    if "answer_last_offer" in condition or "offer" in condition:
        return "needs last-offer memory state plus exact repeated-offer wording"
    if "repair_and_answer_last_question" in condition:
        return "needs dissatisfaction repair context and stored last direct question"
    if "bounded_practice" in condition:
        return "needs bounded-practice obligation plus malformed candidate answer"
    if "stabilize_safety" in condition:
        return "needs safety-priority planner profile with exact long/question shape"
    if "clarify_one_point" in condition:
        return "needs planner clarify branch plus specific question-count shape"
    if "one_step" in condition or "give_direct_step" in condition:
        return "needs exact one-step planner state and text shape to reach this nested branch"
    if "revoicing" in condition:
        return "needs mechanical revoicing output plus active-line settings"
    if "practice" in condition:
        return "needs practice markers plus matching policy state"
    if "нейросталкинг" in condition or "concept" in condition:
        return "needs exact concept-oriented user message and matching planner obligation"
    return "requires a more specific compound contract/text state than the current deterministic case set"


def build_normalized_snapshot(*, generated_at_utc: str = NORMALIZED_TIMESTAMP) -> dict[str, Any]:
    rules = build_rule_inventory()
    cases_payload: list[dict[str, Any]] = []
    coverage: dict[int, list[str]] = {rule.rule_id: [] for rule in rules}
    for case in build_cases():
        agent = WriterAgent(client=object(), model="snapshot-model")
        result, executed_lines = _trace_executed_lines(agent, case["response_text"], case["contract"])
        triggered = _triggered_rules(executed_lines, rules)
        for rule_id in triggered:
            coverage[rule_id].append(case["name"])
        cases_payload.append(
            {
                "case": case["name"],
                "note": case["note"],
                "input": {
                    "response_text": case["response_text"],
                    "contract_summary": _summarize_case(case["contract"]),
                },
                "output_text": result,
                "output_sha1": hashlib.sha1(result.encode("utf-8")).hexdigest(),
                "final_answer_shape": agent.last_debug.get("final_answer_shape"),
                "retry_signal_reason": (agent.last_debug.get("no_stub_repair_signal") or {}).get("reason"),
                "triggered_rules": [f"R{rule_id:02d}" for rule_id in triggered],
            }
        )
    uncovered = [
        {
            "rule": f"R{rule.rule_id:02d}",
            "lines": f"{rule.start}-{rule.end}",
            "condition": rule.condition,
            "reason": _coverage_reason(rule),
        }
        for rule in rules
        if not coverage[rule.rule_id]
    ]
    return {
        "schema_version": "prd_047_42_apply_20_enforce_compliance_snapshot_v1",
        "generated_at_utc": generated_at_utc,
        "metadata": {
            "rule_count": len(rules),
            "case_count": len(cases_payload),
            "covered_rule_count": len([rule_id for rule_id, items in coverage.items() if items]),
            "uncovered_rule_count": len(uncovered),
            "target_method": "WriterAgent._enforce_answer_compliance",
        },
        "cases": cases_payload,
        "coverage": {
            f"R{rule.rule_id:02d}": coverage[rule.rule_id]
            for rule in rules
        },
        "uncovered_rules": uncovered,
    }


def build_rule_coverage_report(snapshot: dict[str, Any] | None = None) -> str:
    rules = build_rule_inventory()
    payload = snapshot or build_normalized_snapshot()
    coverage = payload["coverage"]
    uncovered_lookup = {item["rule"]: item["reason"] for item in payload["uncovered_rules"]}
    rows = [
        [
            f"R{rule.rule_id:02d}",
            f"{rule.start}-{rule.end}",
            rule.condition,
            ", ".join(coverage.get(f"R{rule.rule_id:02d}", [])) or "none",
        ]
        for rule in rules
    ]
    lines = [
        "# Rule Coverage Log",
        "",
        f"- PRD: `{PRD_ID}`",
        f"- case_count: `{payload['metadata']['case_count']}`",
        f"- covered_rule_count: `{payload['metadata']['covered_rule_count']}`",
        f"- uncovered_rule_count: `{payload['metadata']['uncovered_rule_count']}`",
        "",
        _markdown_table(["rule", "lines", "condition", "cases where condition fired"], rows),
        "",
        "## НЕПОКРЫТЫЕ ПРАВИЛА",
        "",
    ]
    if not uncovered_lookup:
        lines.append("- none")
    else:
        for rule in rules:
            rule_name = f"R{rule.rule_id:02d}"
            if rule_name in uncovered_lookup:
                lines.append(
                    f"- `{rule_name}` `{rule.start}-{rule.end}`: {uncovered_lookup[rule_name]}"
                )
    return "\n".join(lines)


def build_no_mutation_proof() -> str:
    diff_proc = subprocess.run(
        ["git", "diff", "--name-only", "--", *PROTECTED_FILES],
        cwd=REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    changed = [line.strip() for line in diff_proc.stdout.splitlines() if line.strip()]
    hash_lines: list[str] = []
    for rel_path in PROTECTED_FILES:
        proc = subprocess.run(
            ["git", "hash-object", rel_path],
            cwd=REPO_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=True,
        )
        current_hash = proc.stdout.strip()
        note = ""
        if rel_path.endswith("writer_agent.py"):
            note = f" (expected @ {HISTORICAL_HEAD}: `{HISTORICAL_WRITER_AGENT_HASH}`, match={str(current_hash == HISTORICAL_WRITER_AGENT_HASH).lower()})"
        elif rel_path.endswith("writer_agent_call_llm_slice12.py"):
            note = f" (expected @ {HISTORICAL_HEAD}: `{HISTORICAL_SLICE12_HASH}`, match={str(current_hash == HISTORICAL_SLICE12_HASH).lower()})"
        hash_lines.append(f"- `{rel_path}` -> `{current_hash}`{note}")

    lines = [
        "# No Mutation Proof",
        "",
        f"- PRD: `{PRD_ID}`",
        "- Scope rule: mapping-only PRD, so the whole production surface must remain untouched.",
        f"- Protected files checked: `{len(PROTECTED_FILES)}`",
        f"- Historical anchor commit: `{HISTORICAL_HEAD}`",
        f"- Protected diff result: `{len(changed)} changed paths`",
        "",
    ]
    if changed:
        lines.extend(["## Unexpected Protected Diffs", ""])
        lines.extend(f"- `{path}`" for path in changed)
        lines.append("")
    else:
        lines.extend(
            [
                "## Protected Diff Result",
                "",
                "- `git diff --name-only -- <protected files>` returned empty output.",
                "",
            ]
        )
    lines.extend(["## Protected Blob Hashes", "", *hash_lines])
    return "\n".join(lines)


def build_implementation_report(snapshot: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# PRD-047.42-APPLY-20 Implementation Report",
            "",
            f"- PRD: `{PRD_ID}`",
            "- Status: `accepted_pending_delivery_metadata`",
            "- Delivery: `main_commit_pending`",
            "",
            "## Scope Delivered",
            "",
            "- Added a read-only runner `TO_DO_LIST/tools/run_prd_047_42_apply_20_enforce_compliance_mapping.py`.",
            "- Built a full numbered rule inventory for `_enforce_answer_compliance` with exact line spans and early-return markers.",
            "- Built deterministic `(response_text, contract) -> output_text` snapshots over named cases without touching production files.",
            "- Built an in-memory line-tracing coverage log that maps rules to cases and preserves an explicit uncovered-rules section.",
            "- Produced no-mutation proof over the canonical `17` protected files plus `writer_agent_call_llm_slice12.py` and whole `writer_agent.py`.",
            "",
            "## Honest Boundary",
            "",
            "- No production code was moved or edited in this PRD.",
            f"- Snapshot coverage is intentionally partial: `{snapshot['metadata']['uncovered_rule_count']}` rules remain uncovered and are listed explicitly for architect follow-up.",
            "- `_enforce_mvp_free_dialogue_compliance` stayed out of scope; only the handoff line inside `_enforce_answer_compliance` is mapped here.",
        ]
    )


def build_next_recommendation() -> str:
    return "\n".join(
        [
            "# PRD-047.42-APPLY-20 Next Recommendation",
            "",
            "- recommended_next_prd: `PRD-047.42-APPLY-21 - _enforce_answer_compliance decomposition slice 1`",
            "- rationale:",
            "  - start with one continuous non-MVP rule family, not with the MVP handoff and not with mixed late-tail logic;",
            "  - the cleanest first candidate from this map is the compact obligation-specific repair band around bounded practice / literal markdown / answer-last-offer rules before the profile split;",
            "  - keep the question-policy cascade and active-line tail for later because they mix many overlapping planner states and have more uncovered rules in the current harness.",
        ]
    )


def write_reports(output_dir: Path = OUT_DIR, *, generated_at_utc: str = NORMALIZED_TIMESTAMP) -> dict[str, Path]:
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    snapshot = build_normalized_snapshot(generated_at_utc=generated_at_utc)
    reports = {
        "boundary_map": output_dir / "enforce_compliance_boundary_map.md",
        "snapshot": output_dir / "enforce_compliance_snapshot.json",
        "coverage": output_dir / "rule_coverage_log.md",
        "no_mutation": output_dir / "no_mutation_proof.md",
        "implementation": output_dir / "implementation_report.md",
        "next": output_dir / "next_recommendation.md",
    }
    _write_text(reports["boundary_map"], build_boundary_map_report())
    reports["snapshot"].write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _write_text(reports["coverage"], build_rule_coverage_report(snapshot))
    _write_text(reports["no_mutation"], build_no_mutation_proof())
    _write_text(reports["implementation"], build_implementation_report(snapshot))
    _write_text(reports["next"], build_next_recommendation())
    return reports


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default=str(OUT_DIR))
    args = parser.parse_args()
    reports = write_reports(Path(args.output_dir), generated_at_utc=NORMALIZED_TIMESTAMP)
    for path in reports.values():
        print(path.relative_to(REPO_ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
