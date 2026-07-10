from __future__ import annotations

import argparse
import ast
import asyncio
import hashlib
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
BOT_ROOT = REPO_ROOT / "bot_psychologist"
if str(BOT_ROOT) not in sys.path:
    sys.path.insert(0, str(BOT_ROOT))

from bot_agent.multiagent.agents.agent_llm_client import AgentLLMResult
from bot_agent.multiagent.agents.writer_agent import WriterAgent
from bot_agent.multiagent.contracts.memory_bundle import MemoryBundle, SemanticHit, UserProfile
from bot_agent.multiagent.contracts.thread_state import ThreadState
from bot_agent.multiagent.contracts.writer_contract import WriterContract


PRD_ID = "PRD-047.42-APPLY-6"
OUT_DIR = REPO_ROOT / "TO_DO_LIST" / "logs" / PRD_ID
WRITER_AGENT_PATH = (
    REPO_ROOT / "bot_psychologist" / "bot_agent" / "multiagent" / "agents" / "writer_agent.py"
)
WRITER_AGENT_MODULE = "bot_agent.multiagent.agents.writer_agent"
PROTECTED_FILES = [
    "bot_psychologist/bot_agent/multiagent/agents/writer_agent.py",
    "bot_psychologist/bot_agent/multiagent/agents/writer_agent_constants.py",
    "bot_psychologist/bot_agent/multiagent/agents/writer_agent_fallback_helpers.py",
    "bot_psychologist/bot_agent/multiagent/agents/writer_agent_fallback_state_mixin.py",
    "bot_psychologist/bot_agent/multiagent/agents/writer_agent_lifecycle_mixin.py",
    "bot_psychologist/bot_agent/multiagent/contracts/writer_contract.py",
    "bot_psychologist/api/admin_routes.py",
    "bot_psychologist/api/admin_runtime_compat.py",
    "bot_psychologist/api/admin_runtime_effective_payload.py",
    "bot_psychologist/api/admin_diagnostics_payload.py",
    "bot_psychologist/api/admin_config_schema.py",
    "bot_psychologist/api/admin_config_routes.py",
    "bot_psychologist/api/admin_prompt_routes.py",
    "bot_psychologist/api/admin_agent_ops_routes.py",
    "bot_psychologist/api/admin_misc_routes.py",
    "bot_psychologist/api/admin_surface_bootstrap.py",
    "bot_psychologist/api/admin_surface_helpers.py",
]


@dataclass(frozen=True)
class BoundarySection:
    name: str
    start: int
    end: int
    responsibility: str
    extraction_candidate: str
    mutates_last_debug: bool = False

    @property
    def loc(self) -> int:
        return self.end - self.start + 1


BOUNDARY_SECTIONS: list[BoundarySection] = [
    BoundarySection(
        "client_and_ctx_default_seeding",
        141,
        254,
        "Gets the client, builds `ctx = contract.to_prompt_context()`, and seeds a large default surface with `ctx.setdefault(...)` so prompt rendering never sees missing keys.",
        "Read-only in this PRD. Future cut candidate only after defaults are grouped into smaller helper families.",
    ),
    BoundarySection(
        "knowledge_practice_kernel_inputs",
        255,
        303,
        "Extracts knowledge/practice guards, philosophy kernel, freedom contract, and list-like helper payloads from `ctx` into local normalized structures.",
        "Good early helper candidates: pure dict/list normalization helpers with explicit parameters.",
    ),
    BoundarySection(
        "dialogue_policy_and_context_budget",
        304,
        332,
        "Builds `dialogue_policy_payload`, human-like/constraint payloads, normalizes profile, resolves context budget, and formats conversation context with metadata.",
        "Likely safe next-stage helper cluster if split away from later prompt rendering.",
    ),
    BoundarySection(
        "request_detectors_and_mvp_override_block",
        333,
        406,
        "Derives request-shape booleans from policy plus lexical detectors, computes `rich_user_request`, and constructs the MVP override text block.",
        "Mixed but still helper-friendly: detector booleans are pure, MVP override block is formatting-only.",
    ),
    BoundarySection(
        "writer_kb_payload_and_trace_capture",
        407,
        453,
        "Formats `writer_kb_payload_text`, normalizes fallback reason, and copies several payload/trace structures into `self.last_debug` before prompt assembly.",
        "Not pure as-is because it mutates `self.last_debug`; could move behind a stateful helper or return a debug patch dict.",
        mutates_last_debug=True,
    ),
    BoundarySection(
        "writer_user_template_render_core",
        454,
        611,
        "First half of `WRITER_USER_TEMPLATE.format(...)`: core thread state, governance, context budget, KB payload, philosophy kernel, freedom contract, and final-answer directive wiring.",
        "Too large for one cut; split by template responsibility groups before moving.",
    ),
    BoundarySection(
        "writer_user_template_render_runtime_tail",
        612,
        842,
        "Second half of `WRITER_USER_TEMPLATE.format(...)`: fresh-chat policy, writer-context package, active line, planner, pragmatics, retrieval, human-like policy, shape profile, and constraint-resolution fields.",
        "Likely later extraction target after core render arguments are grouped into named builder helpers.",
    ),
    BoundarySection(
        "prompt_constraint_append_and_debug_bookkeeping",
        843,
        891,
        "Builds the optional prompt-constraint section, appends it to `user_prompt`, and records prompt/context/policy diagnostics in `self.last_debug`.",
        "State-coupled cluster; candidate for a helper returning `(user_prompt, debug_patch)`.",
        mutates_last_debug=True,
    ),
    BoundarySection(
        "runtime_settings_and_system_prompt_selection",
        892,
        901,
        "Starts timing, re-normalizes dialogue profile, resolves runtime settings, chooses the system prompt, and stores the final prompt mode in debug.",
        "Small, isolated, and a strong early candidate for APPLY-7 after mapping review.",
        mutates_last_debug=True,
    ),
    BoundarySection(
        "provider_dispatch",
        902,
        912,
        "Single provider call through `create_agent_completion(...)` using the assembled prompts and runtime settings.",
        "Keep separate. Explicitly deferred by this PRD and the previous recommendation.",
    ),
    BoundarySection(
        "response_unpack_cost_and_return",
        913,
        938,
        "Unpacks `AgentLLMResult`, estimates cost, computes duration, patches `self.last_debug`, and returns `llm_response`.",
        "Provider-response parsing should be a later dedicated slice, not merged with prompt preparation.",
        mutates_last_debug=True,
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
        cells = [str(value).replace("|", "\\|").replace("\n", "<br>") for value in row]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def _read_writer_lines() -> list[str]:
    return WRITER_AGENT_PATH.read_text(encoding="utf-8-sig").splitlines()


def _extract_call_llm_node(source_text: str | None = None) -> ast.AsyncFunctionDef:
    text = source_text.lstrip("\ufeff") if source_text is not None else WRITER_AGENT_PATH.read_text(encoding="utf-8-sig")
    tree = ast.parse(text)
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "WriterAgent":
            for child in node.body:
                if isinstance(child, ast.AsyncFunctionDef) and child.name == "_call_llm":
                    return child
    raise RuntimeError("WriterAgent._call_llm not found")


def _cluster_for_line(line_no: int) -> str:
    for section in BOUNDARY_SECTIONS:
        if section.start <= line_no <= section.end:
            return section.name
    return "outside_call_llm"


def _collect_assigned_names(target: ast.AST) -> list[str]:
    if isinstance(target, ast.Name):
        return [target.id]
    if isinstance(target, (ast.Tuple, ast.List)):
        result: list[str] = []
        for element in target.elts:
            result.extend(_collect_assigned_names(element))
        return result
    return []


def _load_names(node: ast.AST) -> list[str]:
    seen: list[str] = []
    for child in ast.walk(node):
        if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load):
            seen.append(child.id)
    ordered: list[str] = []
    for name in seen:
        if name not in ordered:
            ordered.append(name)
    return ordered


def _usage_sites(fn: ast.AsyncFunctionDef) -> dict[str, list[int]]:
    usage: dict[str, list[int]] = {}
    for node in ast.walk(fn):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            usage.setdefault(node.id, []).append(node.lineno)
    return usage


def build_variable_inventory(source_text: str | None = None) -> list[dict[str, Any]]:
    fn = _extract_call_llm_node(source_text=source_text)
    usage = _usage_sites(fn)
    entries: list[dict[str, Any]] = []
    for stmt in fn.body:
        if isinstance(stmt, ast.Assign):
            targets = []
            for target in stmt.targets:
                targets.extend(_collect_assigned_names(target))
        elif isinstance(stmt, ast.AnnAssign):
            targets = _collect_assigned_names(stmt.target)
        else:
            continue
        if not targets:
            continue
        depends_on = [name for name in _load_names(stmt.value) if name not in targets]
        for name in targets:
            later_uses = [line for line in usage.get(name, []) if line > getattr(stmt, "end_lineno", stmt.lineno)]
            feeds_user_prompt = any(454 <= line <= 860 for line in later_uses)
            feeds_provider_call = any(902 <= line <= 912 for line in later_uses)
            feeds_response_parse = any(913 <= line <= 938 for line in later_uses)
            scope = "local_only"
            if feeds_provider_call:
                scope = "provider_dispatch_input"
            elif feeds_user_prompt:
                scope = "writer_prompt_input"
            elif feeds_response_parse:
                scope = "response_parse_input"
            entries.append(
                {
                    "name": name,
                    "line": stmt.lineno,
                    "end_line": getattr(stmt, "end_lineno", stmt.lineno),
                    "cluster": _cluster_for_line(stmt.lineno),
                    "depends_on": depends_on,
                    "scope": scope,
                    "later_uses": later_uses,
                }
            )
    return sorted(entries, key=lambda item: (item["line"], item["name"]))


def build_boundary_map_report() -> str:
    rows = [
        [
            section.name,
            f"{section.start}-{section.end}",
            section.loc,
            "yes" if section.mutates_last_debug else "no",
            section.responsibility,
            section.extraction_candidate,
        ]
        for section in BOUNDARY_SECTIONS
    ]
    lines = [
        "# _call_llm Boundary Map",
        "",
        f"- PRD: `{PRD_ID}`",
        "- Target: `bot_psychologist/bot_agent/multiagent/agents/writer_agent.py::WriterAgent._call_llm`",
        "- Method line span: `135-938` (804 LOC)",
        "- Real provider call: line `902` via `create_agent_completion(...)`",
        "- Rule of this PRD: mapping only, no production-code movement",
        "",
        _markdown_table(
            ["cluster", "lines", "loc", "writes last_debug", "responsibility", "future extraction note"],
            rows,
        ),
        "",
        "## Immediate Apply-7 Reading",
        "",
        "- Safest early extraction edge is not the provider call itself; it is the small pre-dispatch runtime block at `892-901` plus selected pure detector/default-formatting helpers earlier in the method.",
        "- The largest single concentration of responsibility remains `WRITER_USER_TEMPLATE.format(...)` at `454-842`; this block should be decomposed by argument-family builders, not by one giant move.",
        "- The first clearly state-coupled preparation cluster begins at `407-453`, where prompt preparation starts writing directly into `self.last_debug`.",
    ]
    return "\n".join(lines)


def build_variable_dependency_report() -> str:
    inventory = build_variable_inventory()
    summary_rows = []
    for section in BOUNDARY_SECTIONS:
        members = [item for item in inventory if item["cluster"] == section.name]
        summary_rows.append(
            [
                section.name,
                f"{section.start}-{section.end}",
                len(members),
                ", ".join(sorted({item['scope'] for item in members})) or "none",
                ", ".join(sorted({dep for item in members for dep in item["depends_on"] if dep})) or "none",
            ]
        )

    inventory_rows = []
    for item in inventory:
        inventory_rows.append(
            [
                item["name"],
                f"{item['line']}-{item['end_line']}",
                item["cluster"],
                ", ".join(item["depends_on"]) or "literal_or_direct_ctx_only",
                item["scope"],
                ", ".join(str(line) for line in item["later_uses"][:8]) or "none",
            ]
        )

    lines = [
        "# _call_llm Variable Dependency Graph",
        "",
        "## Cluster Summary",
        "",
        _markdown_table(
            ["cluster", "lines", "assigned vars", "downstream scope", "dominant dependencies"],
            summary_rows,
        ),
        "",
        "## Full Local Variable Inventory",
        "",
        _markdown_table(
            ["name", "assignment lines", "cluster", "depends_on", "downstream scope", "sample later uses"],
            inventory_rows,
        ),
        "",
        "## Notes",
        "",
        "- `writer_prompt_input` means the variable feeds `WRITER_USER_TEMPLATE.format(...)` directly or indirectly.",
        "- `provider_dispatch_input` means the variable survives until the `create_agent_completion(...)` call at lines `902-912`.",
        "- Variables inside `407-453`, `843-891`, and `913-938` are the most obviously coupled to `self.last_debug` and therefore poor pure-function candidates without returning explicit debug patches.",
    ]
    return "\n".join(lines)


def _thread_state(*, safety_active: bool = False) -> ThreadState:
    now = datetime.now(timezone.utc)
    return ThreadState(
        thread_id="th_047_42_apply_6",
        user_id="u_047_42_apply_6",
        core_direction="контроль и перегруз",
        phase="clarify",
        response_mode="reflect",
        response_goal="direct_answer",
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


def _contract(
    *,
    user_message: str,
    profile: str,
    extra_dialogue_policy: dict[str, Any] | None = None,
    extra_final_answer_directive: dict[str, Any] | None = None,
) -> WriterContract:
    dialogue_policy = {
        "profile": profile,
        "profile_preset": profile,
        "context_budget_chars": 2800,
        "explicit_answer_need": True,
        "answer_obligation_resolution": {
            "answer_obligation": "answer_knowledge_question",
            "answer_shape": "structured_explanation",
            "depth": "medium",
            "question_policy": "none",
            "source": ["latest_turn"],
        },
    }
    if extra_dialogue_policy:
        dialogue_policy.update(extra_dialogue_policy)
    final_answer_directive = {
        "version": "final_answer_directive_v1",
        "current_user_request": user_message,
        "must_answer_source": "latest_turn",
        "answer_target": "latest_turn",
        "writer_contact_mode": "structured_answer",
        "no_practice_unless_requested": True,
        "latest_turn_constraints_v1": {"active_constraints": ["no_practice"]},
    }
    if extra_final_answer_directive:
        final_answer_directive.update(extra_final_answer_directive)
    return WriterContract(
        user_message=user_message,
        thread_state=_thread_state(safety_active=False),
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
        },
        dialogue_policy=dialogue_policy,
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
        final_answer_directive=final_answer_directive,
    )


class _PerfCounter:
    def __init__(self, values: list[float]) -> None:
        self._values = list(values)

    def __call__(self) -> float:
        if self._values:
            return self._values.pop(0)
        return 100.123


def _sanitize_for_json(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize_for_json(val) for key, val in value.items()}
    if isinstance(value, (list, tuple)):
        return [_sanitize_for_json(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


async def build_snapshot_baseline() -> dict[str, Any]:
    writer_agent_module = __import__(WRITER_AGENT_MODULE, fromlist=["WriterAgent"])
    original_create = writer_agent_module.create_agent_completion
    original_perf_counter = writer_agent_module.time.perf_counter

    async def _fake_completion(**kwargs: Any) -> AgentLLMResult:
        return AgentLLMResult(
            text=f"FAKE::{kwargs['model']}::{kwargs['messages'][1]['content'][:24]}",
            model=str(kwargs["model"]),
            api_mode="snapshot_fake",
            tokens_prompt=111,
            tokens_completion=37,
            tokens_total=148,
            raw_response=None,
        )

    scenarios = [
        (
            "safe_guided_direct",
            _contract(
                user_message="объясни по-человечески, без практик, что такое нейросталкинг",
                profile="safe_guided",
            ),
        ),
        (
            "mvp_free_overview",
            _contract(
                user_message="объясни подробнее и дай примеры, без практик",
                profile="mvp_free_dialogue",
                extra_dialogue_policy={"examples_requested": True, "expansion_requested": True},
            ),
        ),
        (
            "mvp_free_rich_request",
            _contract(
                user_message="сделай структурированный ответ с примерами и списком, без практик",
                profile="mvp_free_dialogue",
                extra_dialogue_policy={
                    "examples_requested": True,
                    "numbered_list_requested": True,
                    "direct_concrete_request": True,
                },
            ),
        ),
    ]

    try:
        writer_agent_module.create_agent_completion = _fake_completion
        writer_agent_module.time.perf_counter = _PerfCounter([100.0, 100.123])
        cases: list[dict[str, Any]] = []
        for case_name, contract in scenarios:
            writer_agent_module.time.perf_counter = _PerfCounter([100.0, 100.123])
            agent = WriterAgent(client=object(), model="snapshot-model")
            llm_response = await agent._call_llm(contract)
            debug = _sanitize_for_json(dict(agent.last_debug))
            cases.append(
                {
                    "case": case_name,
                    "dialogue_profile": contract.dialogue_policy["profile"],
                    "llm_response": llm_response,
                    "last_debug": debug,
                    "user_prompt_sha1": hashlib.sha1(
                        str(debug.get("user_prompt", "")).encode("utf-8")
                    ).hexdigest(),
                }
            )
    finally:
        writer_agent_module.create_agent_completion = original_create
        writer_agent_module.time.perf_counter = original_perf_counter

    return {
        "schema_version": "prd_047_42_apply_6_call_llm_snapshot_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "cases": cases,
    }


def build_no_mutation_proof() -> str:
    rel_paths = [str(path) for path in PROTECTED_FILES]
    diff_proc = subprocess.run(
        ["git", "diff", "--name-only", "--", *rel_paths],
        cwd=REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    changed = [line.strip() for line in diff_proc.stdout.splitlines() if line.strip()]
    hash_lines = []
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
        hash_lines.append(f"- `{rel_path}` -> `{proc.stdout.strip()}`")

    body = [
        "# No Mutation Proof",
        "",
        f"- PRD: `{PRD_ID}`",
        "- Scope rule: mapping-only PRD; no production code moved or edited.",
        f"- Protected files checked: `{len(PROTECTED_FILES)}`",
        f"- Protected diff result: `{len(changed)} changed paths`",
        "",
    ]
    if changed:
        body.append("## Unexpected Protected Diffs")
        body.extend(f"- `{path}`" for path in changed)
        body.append("")
    else:
        body.extend(
            [
                "## Protected Diff Result",
                "",
                "- `git diff --name-only -- <protected files>` returned empty output.",
                "",
            ]
        )
    body.extend(["## Protected Blob Hashes", "", *hash_lines])
    return "\n".join(body)


def build_implementation_report() -> str:
    body = [
        "# PRD-047.42-APPLY-6 Implementation Report",
        "",
        f"- PRD: `{PRD_ID}`",
        "- Status: `accepted_pending_delivery_metadata`",
        "- Delivery: `main_commit_pending`",
        "",
        "## Scope Delivered",
        "",
        "- Added a read-only runner `TO_DO_LIST/tools/run_prd_047_42_apply_6_call_llm_boundary_mapping.py`.",
        "- Built an exact line-range boundary map for `WriterAgent._call_llm`.",
        "- Built a local-variable dependency inventory over `_call_llm` assignments.",
        "- Captured a 3-scenario `_call_llm` snapshot baseline with mocked `create_agent_completion` and full `self.last_debug` export.",
        "- Produced no-mutation proof over the protected production files.",
        "",
        "## Honest Boundary",
        "",
        "- No production code was moved out of `_call_llm` in this PRD.",
        "- Provider dispatch at lines `902-912` stayed untouched and is intentionally deferred.",
        "- `_enforce_answer_compliance`, `_enforce_mvp_free_dialogue_compliance`, `writer_contract.py`, `admin_routes.py`, and the `10` admin decomposition modules stayed out of scope.",
    ]
    return "\n".join(body)


def build_next_recommendation() -> str:
    body = [
        "# PRD-047.42-APPLY-6 Next Recommendation",
        "",
        "- recommended_next_prd: `PRD-047.42-APPLY-7 - writer_agent.py _call_llm decomposition slice 1`",
        "- rationale:",
        "  - start with the smallest pre-provider extraction edge identified in this map, not with provider dispatch;",
        "  - the best first cut candidate is the isolated runtime/system-prompt block at `892-901`, optionally together with one or two pure detector/default-formatting helpers earlier in the method;",
        "  - keep `create_agent_completion(...)` plus result parsing for later dedicated PRDs once the preparation block is no longer a single giant mixed method.",
    ]
    return "\n".join(body)


def write_reports(output_dir: Path = OUT_DIR) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    reports = {
        "boundary_map": output_dir / "call_llm_boundary_map.md",
        "dependency_graph": output_dir / "call_llm_variable_dependency_graph.md",
        "snapshot": output_dir / "call_llm_snapshot_baseline.json",
        "no_mutation": output_dir / "no_mutation_proof.md",
        "implementation": output_dir / "implementation_report.md",
        "next": output_dir / "next_recommendation.md",
    }
    _write_text(reports["boundary_map"], build_boundary_map_report())
    _write_text(reports["dependency_graph"], build_variable_dependency_report())
    reports["snapshot"].write_text(
        json.dumps(asyncio.run(build_snapshot_baseline()), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    _write_text(reports["no_mutation"], build_no_mutation_proof())
    _write_text(reports["implementation"], build_implementation_report())
    _write_text(reports["next"], build_next_recommendation())
    return reports


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default=str(OUT_DIR))
    args = parser.parse_args()
    reports = write_reports(Path(args.output_dir))
    for path in reports.values():
        print(path.relative_to(REPO_ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
