from __future__ import annotations

import ast
import importlib
import json
import os
import subprocess
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PRD_ID = "PRD-047.42"
REPO_ROOT = Path(__file__).resolve().parents[2]
BOT_ROOT = REPO_ROOT / "bot_psychologist"
if str(BOT_ROOT) not in os.sys.path:
    os.sys.path.insert(0, str(BOT_ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from api.main import app  # noqa: E402
from api.session_store import get_session_store  # noqa: E402
from bot_agent.config import config  # noqa: E402
from bot_agent.runtime_config import RuntimeConfig  # noqa: E402
from bot_agent.multiagent.agents.writer_agent import WriterAgent  # noqa: E402
from bot_agent.multiagent.contracts.memory_bundle import (  # noqa: E402
    MemoryBundle,
    SemanticHit,
    UserProfile,
)
from bot_agent.multiagent.contracts.thread_state import ThreadState  # noqa: E402
from bot_agent.multiagent.contracts.writer_contract import WriterContract  # noqa: E402


OUT_DIR = REPO_ROOT / "TO_DO_LIST" / "logs" / PRD_ID
ADMIN_HEADERS = {"X-API-Key": "dev-key-001"}
TARGET_FILES = {
    "writer_agent": REPO_ROOT / "bot_psychologist" / "bot_agent" / "multiagent" / "agents" / "writer_agent.py",
    "admin_routes": REPO_ROOT / "bot_psychologist" / "api" / "admin_routes.py",
    "writer_contract": REPO_ROOT / "bot_psychologist" / "bot_agent" / "multiagent" / "contracts" / "writer_contract.py",
}
TARGET_MODULES = {
    "writer_agent": "bot_agent.multiagent.agents.writer_agent",
    "admin_routes": "api.admin_routes",
    "writer_contract": "bot_agent.multiagent.contracts.writer_contract",
}


@dataclass(frozen=True)
class BoundarySection:
    name: str
    start: int
    end: int
    responsibility: str
    proposed_module: str
    legacy_compat: bool = False

    @property
    def loc(self) -> int:
        return self.end - self.start + 1


BOUNDARY_MAPS: dict[str, list[BoundarySection]] = {
    "writer_agent": [
        BoundarySection(
            "module_constants_and_detectors",
            45,
            169,
            "Static runtime defaults, lexical detectors, and tiny coercion helpers used by later Writer paths.",
            "writer_agent_constants.py",
        ),
        BoundarySection(
            "runtime_settings_and_write_lifecycle",
            172,
            297,
            "Agent identity, runtime setting resolution, and top-level write/fallback lifecycle orchestration.",
            "writer_agent_runtime.py",
        ),
        BoundarySection(
            "prompt_context_default_injection",
            299,
            418,
            "Mass default injection into prompt context before template rendering; protects prompt assembly from missing fields.",
            "writer_prompt_defaults.py",
        ),
        BoundarySection(
            "prompt_policy_overrides_and_context_budgeting",
            419,
            617,
            "Transforms policy flags, dialogue profile, knowledge/practice gates, and context budget rules into Writer-visible prompt inputs and debug metadata.",
            "writer_prompt_policy.py",
            legacy_compat=True,
        ),
        BoundarySection(
            "prompt_render_and_llm_io",
            618,
            1102,
            "Renders the actual Writer user prompt, dispatches to the model client, and records token/cost/debug metadata.",
            "writer_llm_dispatch.py",
        ),
        BoundarySection(
            "compliance_intake_and_obligation_resolution",
            1104,
            1307,
            "Normalizes post-LLM answer, reconstructs per-turn constraints, and prepares compliance/evaluator state.",
            "writer_answer_compliance_core.py",
        ),
        BoundarySection(
            "bounded_practice_and_direct_answer_repairs",
            1308,
            1433,
            "Repairs bounded-practice, literal-markdown, direct-answer, and answer-obligation-specific misalignment before profile-specific branches.",
            "writer_answer_compliance_repairs.py",
        ),
        BoundarySection(
            "safe_guided_compliance_branch",
            1435,
            1712,
            "Non-MVP compliance branch for greeting, support, safety, no-question, known-concept, and practice-suppression sanitization.",
            "writer_answer_compliance_safe_guided.py",
            legacy_compat=True,
        ),
        BoundarySection(
            "mvp_free_dialogue_branch",
            1714,
            1936,
            "MVP-free-dialogue-specific compliance and retry-defer logic for contextual follow-ups, summary, sarcasm, expansion, and practice suppression.",
            "writer_answer_compliance_mvp.py",
        ),
        BoundarySection(
            "fallbacks_debug_client_and_name_continuity",
            1938,
            2183,
            "Static fallback builders, retry signaling, client acquisition, language detection, and name continuity helpers.",
            "writer_agent_fallbacks.py",
            legacy_compat=True,
        ),
    ],
    "admin_routes": [
        BoundarySection(
            "runtime_compat_helpers",
            91,
            173,
            "Admin runtime compatibility and deprecated-surface helpers for multiagent-only truth exposure.",
            "admin_runtime_compat.py",
            legacy_compat=True,
        ),
        BoundarySection(
            "router_bootstrap_and_admin_constants",
            178,
            233,
            "Auth dependency, router registration, schema versions, and admin surface constants.",
            "admin_surface_bootstrap.py",
        ),
        BoundarySection(
            "status_prompt_thread_and_prd_status_helpers",
            235,
            665,
            "Status snapshots, prompt-stack builders, thread listings, agent-prompt reflection, and historical PRD artifact status loaders.",
            "admin_surface_helpers.py",
        ),
        BoundarySection(
            "runtime_effective_payload_builder",
            668,
            956,
            "Assembles the canonical runtime/effective admin payload across flags, dialogue policy, planner, trace, semantic cards, and compat metadata.",
            "admin_runtime_effective_payload.py",
            legacy_compat=True,
        ),
        BoundarySection(
            "diagnostics_effective_payload_builder",
            959,
            982,
            "Builds compact diagnostics payload for dedicated admin diagnostics surface.",
            "admin_diagnostics_payload.py",
        ),
        BoundarySection(
            "schema_and_import_validation",
            985,
            1132,
            "Builds admin config schema v10.4 and validates import/export payload normalization.",
            "admin_config_schema.py",
        ),
        BoundarySection(
            "config_status_runtime_and_trace_routes",
            1148,
            1432,
            "Config CRUD, runtime status/effective endpoints, diagnostics endpoints, and deprecated admin trace routes.",
            "admin_config_routes.py",
            legacy_compat=True,
        ),
        BoundarySection(
            "prompt_history_import_export_routes",
            1447,
            1705,
            "Prompt CRUD, prompt-stack v2 editing, history, and import/export endpoints.",
            "admin_prompt_routes.py",
        ),
        BoundarySection(
            "agent_orchestrator_and_overview_routes",
            1716,
            1905,
            "Agent status/toggles/metrics, orchestrator config, traces, and overview endpoints.",
            "admin_agent_ops_routes.py",
            legacy_compat=True,
        ),
        BoundarySection(
            "thread_agent_llm_reset_and_identity_routes",
            1916,
            2144,
            "Thread cleanup, per-agent prompt/LLM config endpoints, full reset, and user identity admin route.",
            "admin_misc_routes.py",
        ),
    ],
    "writer_contract": [
        BoundarySection(
            "dataclass_and_dict_serialization",
            21,
            87,
            "Stable contract dataclass definition plus shallow serialization for tracing and transport.",
            "writer_contract_model.py",
        ),
        BoundarySection(
            "prompt_context_source_collection",
            89,
            240,
            "Collects fresh-chat policy, writer context package, conversation/rag sources, and base governance dictionaries.",
            "writer_prompt_context_sources.py",
        ),
        BoundarySection(
            "grounding_visibility_and_payload_budgeting",
            241,
            378,
            "Resolves semantic-hit budgets, writer grounding visibility, payload/trace toggles, and dialogue profile/directive inputs.",
            "writer_prompt_context_grounding.py",
        ),
        BoundarySection(
            "legacy_advisory_sanitization_bridge",
            379,
            468,
            "Builds legacy-source signal bundle and sanitizes it into Writer-visible advisory guidance.",
            "writer_prompt_context_legacy_bridge.py",
            legacy_compat=True,
        ),
        BoundarySection(
            "prompt_context_payload_export",
            469,
            979,
            "Exports the full prompt-context payload consumed by Writer, including governance traces, planner, directive, and retrieval metadata.",
            "writer_prompt_context_payload.py",
            legacy_compat=True,
        ),
    ],
}


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


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig", errors="replace")


def _ast_summary(path: Path) -> list[dict[str, Any]]:
    tree = ast.parse(_read_text(path))
    items: list[dict[str, Any]] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            entry: dict[str, Any] = {
                "type": type(node).__name__,
                "name": node.name,
                "start": node.lineno,
                "end": getattr(node, "end_lineno", node.lineno),
            }
            if isinstance(node, ast.ClassDef):
                entry["methods"] = [
                    {
                        "name": child.name,
                        "start": child.lineno,
                        "end": getattr(child, "end_lineno", child.lineno),
                    }
                    for child in node.body
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
                ]
            items.append(entry)
    return items


def _importers_for(module_name: str) -> list[str]:
    module_tail = module_name.rsplit(".", 1)[-1]
    patterns = [module_name, f"from {module_name} import", f"import {module_tail}", f'"{module_tail}"']
    results: set[str] = set()
    for pattern in patterns:
        command = ["rg", "-l", "--fixed-strings", "--glob", "*.py", pattern, "bot_psychologist", "docs", "TO_DO_LIST"]
        proc = subprocess.run(
            command,
            cwd=REPO_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if proc.returncode not in (0, 1):
            continue
        for line in proc.stdout.splitlines():
            normalized = line.replace("\\", "/").strip()
            if normalized:
                results.add(normalized)
    target_rel = {
        path.relative_to(REPO_ROOT).as_posix()
        for path in TARGET_FILES.values()
    }
    return sorted(item for item in results if item not in target_rel)


def _imported_modules(path: Path) -> list[str]:
    tree = ast.parse(_read_text(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                modules.add(node.module)
    return sorted(modules)


def _git_diff_lines(paths: list[Path]) -> list[str]:
    rel_paths = [str(path.relative_to(REPO_ROOT)) for path in paths]
    result = subprocess.run(
        ["git", "diff", "--"] + rel_paths,
        cwd=REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return result.stdout.splitlines()


def _git_status_target_lines(paths: list[Path]) -> list[str]:
    rel_paths = [str(path.relative_to(REPO_ROOT)) for path in paths]
    result = subprocess.run(
        ["git", "status", "--short", "--"] + rel_paths,
        cwd=REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return [line for line in result.stdout.splitlines() if line.strip()]


def _categorize_paths(paths: list[str]) -> dict[str, list[str]]:
    buckets = {"production": [], "tests": [], "tools": [], "docs": [], "other": []}
    for item in paths:
        if item.startswith("bot_psychologist/tests/"):
            buckets["tests"].append(item)
        elif item.startswith("bot_psychologist/tools/") or item.startswith("TO_DO_LIST/tools/"):
            buckets["tools"].append(item)
        elif "/docs/" in item or item.startswith("docs/") or item.startswith("bot_psychologist/docs/"):
            buckets["docs"].append(item)
        elif item.startswith("bot_psychologist/"):
            buckets["production"].append(item)
        else:
            buckets["other"].append(item)
    return buckets


def _report_boundary_map(key: str, title: str) -> None:
    path = TARGET_FILES[key]
    sections = BOUNDARY_MAPS[key]
    ast_items = _ast_summary(path)
    total_loc = len(_read_text(path).splitlines())
    section_loc = sum(item.loc for item in sections)
    rows = [
        [
            item.name,
            f"{item.start}-{item.end}",
            item.loc,
            "yes" if item.legacy_compat else "no",
            item.proposed_module,
            item.responsibility,
        ]
        for item in sections
    ]
    ast_rows: list[list[Any]] = []
    for item in ast_items:
        if item["type"] == "ClassDef":
            ast_rows.append([item["type"], item["name"], f'{item["start"]}-{item["end"]}', ""])
            for method in item.get("methods", []):
                ast_rows.append(["method", method["name"], f'{method["start"]}-{method["end"]}', item["name"]])
        else:
            ast_rows.append([item["type"], item["name"], f'{item["start"]}-{item["end"]}', ""])
    body = [
        f"# {PRD_ID} {title}",
        "",
        f"- file: `{path.relative_to(REPO_ROOT).as_posix()}`",
        f"- total_loc: `{total_loc}`",
        f"- mapped_loc: `{section_loc}`",
        f"- exact_cover: `{section_loc == total_loc - (sections[0].start - 1)}`",
        "",
        "## Responsibility Sections",
        _markdown_table(
            ["Section", "Lines", "LOC", "legacy_compat", "Proposed future module", "Responsibility"],
            rows,
        ),
        "",
        "## AST Anchors",
        _markdown_table(["Node type", "Name", "Lines", "Owner class"], ast_rows),
    ]
    _write_text(OUT_DIR / f"{key}_boundary_map.md", "\n".join(body))


def _report_external_dependency_graph() -> None:
    body = [f"# {PRD_ID} External Dependency Graph", ""]
    for key, module_name in TARGET_MODULES.items():
        importers = _importers_for(module_name)
        categories = _categorize_paths(importers)
        imported_modules = _imported_modules(TARGET_FILES[key])
        summary_rows = [
            [bucket, len(items), "<br>".join(items[:25]) or "none"]
            for bucket, items in categories.items()
        ]
        body.extend(
            [
                f"## {key}",
                "",
                f"- module: `{module_name}`",
                f"- imported_module_count: `{len(imported_modules)}`",
                f"- importer_count: `{len(importers)}`",
                "",
                "### Imported Modules",
                _markdown_table(
                    ["Index", "Imported module"],
                    [[index + 1, name] for index, name in enumerate(imported_modules)],
                ),
                "",
                "### Importers by Category",
                _markdown_table(["Category", "Count", "Examples"], summary_rows),
                "",
            ]
        )
    _write_text(OUT_DIR / "external_dependency_graph.md", "\n".join(body))


def _report_proposed_module_structure() -> None:
    rows: list[list[Any]] = []
    for key, sections in BOUNDARY_MAPS.items():
        for section in sections:
            rows.append(
                [
                    key,
                    section.proposed_module,
                    f"{section.start}-{section.end}",
                    section.loc,
                    "yes" if section.legacy_compat else "no",
                    section.responsibility,
                ]
            )
    body = [
        f"# {PRD_ID} Proposed Module Structure",
        "",
        "- stage: mapping only, no code moved in this PRD.",
        "- purpose: produce a future-safe split plan before any decomposition PRD mutates source files.",
        "",
        _markdown_table(
            ["Current file", "Proposed module", "Lines", "Approx LOC", "legacy_compat", "Moved responsibility"],
            rows,
        ),
    ]
    _write_text(OUT_DIR / "proposed_module_structure.md", "\n".join(body))


def _thread_state() -> ThreadState:
    return ThreadState(
        thread_id="th_boundary",
        user_id="u_boundary",
        core_direction="контроль и перегруз",
        phase="clarify",
        response_mode="reflect",
        response_goal="direct_answer",
        nervous_state="window",
        openness="open",
        ok_position="I+W+",
        pattern_core="control_then_freeze",
        active_frame={"current_need": "простое объяснение", "next_recommended_direction": "answer_directly"},
        must_avoid=["диагноз"],
        open_loops=["что со мной происходит"],
        safety_active=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def _writer_contract() -> WriterContract:
    bundle = MemoryBundle(
        conversation_context="USER: Мне тяжело. ASSISTANT: Я рядом.",
        user_profile=UserProfile(patterns=["control"], values=["clarity"]),
        semantic_hits=[
            SemanticHit(chunk_id="c1", content="Нейросталкинг — наблюдение автоматических реакций.", source="kb", score=0.92),
            SemanticHit(chunk_id="c2", content="Контроль может сжимать внимание до действия.", source="kb", score=0.87),
        ],
        has_relevant_knowledge=True,
        context_turns=2,
        recent_turns=[
            {"role": "user", "content": "что такое нейросталкинг?"},
            {"role": "assistant", "content": "это наблюдение реакции"},
        ],
    )
    return WriterContract(
        user_message="объясни по-человечески, что такое нейросталкинг, без практик",
        thread_state=_thread_state(),
        memory_bundle=bundle,
        knowledge_answer_guard={
            "knowledge_answer": {"should_answer_directly": True, "concept": "нейросталкинг"},
            "practice_gate": {"practice_allowed": False, "is_greeting": False},
        },
        philosophy_kernel={
            "kernel_version": "philosophy_kernel_v1",
            "quote_policy": "internal_lens_not_citation",
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
        dialogue_policy={
            "profile": "safe_guided",
            "profile_preset": "safe_guided",
            "context_budget_chars": 2800,
            "explicit_answer_need": True,
            "dialogue_pragmatics": {"version": "dialogue_pragmatics_v1", "should_answer_directly": True},
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


def _writer_contract_snapshot() -> dict[str, Any]:
    ctx = _writer_contract().to_prompt_context()
    return {
        "keys_present": [
            "fresh_chat_context_policy_version",
            "writer_context_package_version",
            "writer_grounding_visibility_v1",
            "response_planner_next_move",
            "answer_obligation",
            "final_answer_writer_contact_mode",
            "retrieval_action",
        ],
        "response_planner_next_move": ctx["response_planner_next_move"],
        "answer_obligation": ctx["answer_obligation"],
        "semantic_hits_count": len(ctx["semantic_hits"]),
        "semantic_hits_preview": ctx["semantic_hits"],
        "fresh_chat_active_context_source": ctx["fresh_chat_active_context_source"],
        "writer_contact_mode": ctx["final_answer_writer_contact_mode"],
        "retrieval_action": ctx["retrieval_action"],
        "writer_grounding_authority_note": ctx["writer_grounding_authority_note"],
    }


def _writer_agent_runtime_settings_snapshot() -> dict[str, Any]:
    writer_agent_module = importlib.import_module("bot_agent.multiagent.agents.writer_agent")

    original_value = writer_agent_module.feature_flags.value
    original_temp = writer_agent_module.get_temperature_for_agent
    try:
        def fake_value(key: str, default: str | None = None) -> str | None:
            mapping = {
                "MULTIAGENT_MAX_TOKENS": "700",
                "WRITER_MAX_TOKENS": "700",
                "MULTIAGENT_LLM_TIMEOUT": "11.5",
            }
            return mapping.get(key, default)

        writer_agent_module.feature_flags.value = fake_value
        writer_agent_module.get_temperature_for_agent = lambda _agent: 0.42
        guided = WriterAgent(model="gpt-4o-mini")._resolve_runtime_settings("safe_guided")
        free = WriterAgent(model="gpt-4o-mini")._resolve_runtime_settings("mvp_free_dialogue")
        return {"safe_guided": guided, "mvp_free_dialogue": free}
    finally:
        writer_agent_module.feature_flags.value = original_value
        writer_agent_module.get_temperature_for_agent = original_temp


def _writer_agent_compliance_snapshots() -> dict[str, Any]:
    agent = WriterAgent(model="gpt-5-mini")

    markdown_contract = _writer_contract()
    markdown_contract.user_message = (
        "Верни без объяснений и без изменений следующий markdown-блок: "
        "**Заголовок**\n\n- пункт один\n- пункт два"
    )
    literal = agent._enforce_answer_compliance("Я слышу тебя.", markdown_contract)

    no_practice_contract = _writer_contract()
    no_practice_contract.user_message = "Мне тяжело, без практик, просто скажи по-человечески."
    no_practice_contract.dialogue_policy = {
        "profile": "mvp_free_dialogue",
        "answer_obligation_resolution": {"answer_obligation": "answer_latest_turn"},
    }
    no_practice_contract.response_planner = {
        "enabled": True,
        "next_move": "give_direct_step",
        "answer_shape": "one_step",
        "question_policy": "none",
        "practice_policy": "forbidden",
    }
    no_practice = agent._enforce_answer_compliance(
        "Понял. Тебе тяжело. Если захочешь дальше, можем придумать один шаг.",
        no_practice_contract,
    )
    return {
        "literal_markdown_echo": literal,
        "literal_markdown_shape": agent.last_debug.get("final_answer_shape"),
        "no_practice_contact": no_practice,
        "no_practice_shape": agent.last_debug.get("final_answer_shape"),
    }


@contextmanager
def _admin_client() -> Any:
    store = get_session_store()
    with tempfile.TemporaryDirectory() as tmp_dir:
        override_path = Path(tmp_dir) / "admin_overrides.json"
        original_runtime_path = getattr(RuntimeConfig, "OVERRIDES_PATH", None)
        original_runtime_mtime = getattr(RuntimeConfig, "_cache_mtime", 0.0)
        original_runtime_cache = getattr(RuntimeConfig, "_cache", {}).copy()
        original_config_path = getattr(config, "OVERRIDES_PATH", None)
        original_warmup = getattr(config, "WARMUP_ON_START", True)
        original_sessions = getattr(store, "_sessions", {}).copy()
        original_blobs = getattr(store, "_blobs", {}).copy()
        RuntimeConfig.OVERRIDES_PATH = override_path
        RuntimeConfig._cache_mtime = 0.0
        RuntimeConfig._cache = {}
        config.OVERRIDES_PATH = override_path
        config.WARMUP_ON_START = False
        store._sessions = {}
        store._blobs = {}
        try:
            with TestClient(app, base_url="http://localhost") as client:
                yield client
        finally:
            RuntimeConfig.OVERRIDES_PATH = original_runtime_path
            RuntimeConfig._cache_mtime = original_runtime_mtime
            RuntimeConfig._cache = original_runtime_cache
            config.OVERRIDES_PATH = original_config_path
            config.WARMUP_ON_START = original_warmup
            store._sessions = original_sessions
            store._blobs = original_blobs


def _admin_route_snapshots() -> dict[str, Any]:
    with _admin_client() as client:
        runtime = client.get("/api/admin/runtime/effective", headers=ADMIN_HEADERS).json()
        orchestrator = client.get("/api/admin/orchestrator/config", headers=ADMIN_HEADERS).json()
        deprecated = client.get("/api/admin/prompts/stack-v2/usage", headers=ADMIN_HEADERS)
    return {
        "runtime_effective": {
            "schema_version": runtime["schema_version"],
            "active_runtime": runtime["active_runtime"],
            "pipeline_mode": runtime["pipeline_mode"],
            "effective_config_flag_count": runtime["effective_config"]["flag_count"],
            "dialogue_policy_version": runtime["dialogue_policy"]["version"],
        },
        "orchestrator_config": {
            "pipeline_mode": orchestrator["pipeline_mode"],
            "runtime_entrypoint": orchestrator["runtime_entrypoint"],
            "legacy_cascade_status": orchestrator["legacy"]["cascade_status"],
        },
        "deprecated_prompt_stack_usage": {
            "status_code": deprecated.status_code,
            "detail": deprecated.json().get("detail"),
        },
    }


def _report_behavior_snapshots() -> None:
    payload = {
        "writer_contract": _writer_contract_snapshot(),
        "writer_agent_runtime_settings": _writer_agent_runtime_settings_snapshot(),
        "writer_agent_compliance": _writer_agent_compliance_snapshots(),
        "admin_routes": _admin_route_snapshots(),
    }
    body = [
        f"# {PRD_ID} Behavior Snapshot Contracts",
        "",
        "- note: these are representative read-only contract snapshots, not exhaustive answer-quality coverage.",
        "",
        "```json",
        json.dumps(payload, ensure_ascii=False, indent=2),
        "```",
    ]
    _write_text(OUT_DIR / "behavior_snapshot_contracts.md", "\n".join(body))


def _report_no_mutation() -> None:
    target_paths = list(TARGET_FILES.values())
    status_lines = _git_status_target_lines(target_paths)
    diff_lines = _git_diff_lines(target_paths)
    rows = []
    for key, path in TARGET_FILES.items():
        text = _read_text(path)
        rows.append(
            [
                key,
                path.relative_to(REPO_ROOT).as_posix(),
                len(text.splitlines()),
                subprocess.run(
                    ["git", "hash-object", str(path.relative_to(REPO_ROOT))],
                    cwd=REPO_ROOT,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    check=False,
                ).stdout.strip(),
            ]
        )
    body = [
        f"# {PRD_ID} No Mutation Proof",
        "",
        f"- target_status_lines_present: `{bool(status_lines)}`",
        f"- target_diff_lines_present: `{bool(diff_lines)}`",
        "",
        "## Target Files",
        _markdown_table(["Key", "Path", "LOC", "git hash-object"], rows),
        "",
        "## git status --short -- target files",
        "```text",
        *(status_lines or ["<clean>"]),
        "```",
        "",
        "## git diff -- target files",
        "```diff",
        *(diff_lines[:300] or ["<no diff>"]),
        "```",
    ]
    _write_text(OUT_DIR / "no_mutation_proof.md", "\n".join(body))


def _report_implementation_and_next() -> None:
    implementation = [
        f"# {PRD_ID} Implementation Report",
        "",
        "- status: pending_test_execution",
        "- scope_result: mapping-only reports, dependency inventory, representative behavior snapshots, and no-mutation proof created without touching the three target source files.",
        "- files_kept_unchanged: `writer_agent.py`, `admin_routes.py`, `writer_contract.py`.",
        "- deferred_scope: physical decomposition of these files and all `diagnostic_center_*` production modules.",
    ]
    next_report = [
        f"# {PRD_ID} Next Recommendation",
        "",
        "- If PRD-047.42 is accepted, open a follow-up decomposition PRD that moves one boundary block at a time with unchanged signatures and pre-recorded snapshot contracts.",
        "- Keep `admin_routes.py` split separate from `writer_agent.py`; they have different blast radii and different caller graphs.",
        "- Keep `writer_contract.to_prompt_context` decomposition especially conservative because it is the highest fan-out contract surface in the three-file set.",
    ]
    _write_text(OUT_DIR / "implementation_report.md", "\n".join(implementation))
    _write_text(OUT_DIR / "next_recommendation.md", "\n".join(next_report))


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    _report_boundary_map("writer_agent", "writer_agent Boundary Map")
    _report_boundary_map("admin_routes", "admin_routes Boundary Map")
    _report_boundary_map("writer_contract", "writer_contract Boundary Map")
    _report_proposed_module_structure()
    _report_external_dependency_graph()
    _report_behavior_snapshots()
    _report_no_mutation()
    _report_implementation_and_next()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
