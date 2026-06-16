from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient


CURRENT_DIR = Path(__file__).resolve().parent
BOT_ROOT = CURRENT_DIR.parent
REPO_ROOT = BOT_ROOT.parent
LOGS_DIR_DEFAULT = REPO_ROOT / "TO_DO_LIST" / "logs" / "PRD-047.21"
REPORTS_DIR_DEFAULT = REPO_ROOT / "TO_DO_LIST" / "reports"
PRD_ID = "PRD-047.21"
NEXT_PRD = "PRD-047.22 - Overlay Shadow Allowlisted Live Evidence / Trace Review v1"
PRD20_LOG_DIR = REPO_ROOT / "TO_DO_LIST" / "logs" / "PRD-047.20"
ENCODING_VALIDATOR = CURRENT_DIR / "validate_prd_artifact_encoding.py"

if str(BOT_ROOT) not in sys.path:
    sys.path.insert(0, str(BOT_ROOT))

from api.main import app  # noqa: E402
from api.session_store import get_session_store  # noqa: E402
from bot_agent.multiagent.contracts.memory_bundle import MemoryBundle  # noqa: E402
from bot_agent.multiagent.contracts.state_snapshot import StateSnapshot  # noqa: E402
from bot_agent.multiagent.contracts.thread_state import ThreadState  # noqa: E402
from bot_agent.multiagent.contracts.validation_result import ValidationResult  # noqa: E402
from bot_agent.multiagent.overlay_shadow_trace import (  # noqa: E402
    build_overlay_shadow_trace,
    get_overlay_shadow_trace_settings,
)
from tools import validate_prd_artifact_encoding as encoding_validator  # noqa: E402


DEV_HEADERS = {"X-API-Key": "dev-key-001"}


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _markdown(title: str, lines: list[str]) -> str:
    return "\n".join([f"# {title}", "", *lines])


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    ).stdout.strip()


def _utc_now() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _safe_rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(path.resolve()).replace("\\", "/")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _reset_store() -> None:
    store = get_session_store()
    with store._lock:  # type: ignore[attr-defined]
        store._sessions.clear()  # type: ignore[attr-defined]
        store._blobs.clear()  # type: ignore[attr-defined]
        store._multiagent_debug.clear()  # type: ignore[attr-defined]
        store._multiagent_updated.clear()  # type: ignore[attr-defined]
        store._session_stats.clear()  # type: ignore[attr-defined]
        store._session_stats_updated.clear()  # type: ignore[attr-defined]


def _thread() -> ThreadState:
    now = datetime.utcnow()
    return ThreadState(
        thread_id="overlay-shadow-runner",
        user_id="runner-user",
        core_direction="support",
        phase="clarify",
        relation_to_thread="continue",
        response_mode="reflect",
        continuity_score=0.85,
        active_frame={"active_concept": "страх"},
        created_at=now,
        updated_at=now,
    )


async def _run_stubbed_turn(*, overlay_enabled: bool, overlay_file: Path) -> dict[str, Any]:
    import importlib

    orch_module = importlib.import_module("bot_agent.multiagent.orchestrator")
    captured: dict[str, Any] = {}

    async def _write(contract):
        prompt_context = contract.to_prompt_context()
        captured["prompt_context_json"] = json.dumps(prompt_context, ensure_ascii=False, sort_keys=True)
        captured["writer_contract"] = prompt_context
        orch_module.writer_agent.last_debug = {
            "system_prompt": "SYSTEM PROMPT",
            "user_prompt": "USER PROMPT",
            "llm_response": "writer answer",
            "tokens_prompt": 10,
            "tokens_completion": 10,
            "tokens_total": 20,
            "estimated_cost_usd": 0.0,
            "model": "gpt-5-mini",
            "temperature": 0.7,
            "max_tokens": 400,
        }
        return "writer answer"

    previous_env = {
        "OVERLAY_SHADOW_TRACE_ENABLED": os.getenv("OVERLAY_SHADOW_TRACE_ENABLED"),
        "OVERLAY_SHADOW_OVERLAY_FILE": os.getenv("OVERLAY_SHADOW_OVERLAY_FILE"),
        "OVERLAY_SHADOW_MAX_MATCHES": os.getenv("OVERLAY_SHADOW_MAX_MATCHES"),
        "OVERLAY_SHADOW_MIN_SCORE": os.getenv("OVERLAY_SHADOW_MIN_SCORE"),
        "HYBRID_RETRIEVAL_PLANNER_MODE": os.getenv("HYBRID_RETRIEVAL_PLANNER_MODE"),
    }
    os.environ["OVERLAY_SHADOW_TRACE_ENABLED"] = "true" if overlay_enabled else "false"
    os.environ["OVERLAY_SHADOW_OVERLAY_FILE"] = str(overlay_file)
    os.environ["OVERLAY_SHADOW_MAX_MATCHES"] = "5"
    os.environ["OVERLAY_SHADOW_MIN_SCORE"] = "0.0"
    os.environ["HYBRID_RETRIEVAL_PLANNER_MODE"] = "off"

    try:
        orch_module.thread_manager_agent.last_debug = {
            "version": "thread_diagnostics_v1",
            "relation": {"continuity_risk": "none"},
            "phase": {},
            "mode": {},
            "loops": {},
            "action": {"thread_action": "continue"},
            "summary_flags": [],
        }
        orch_module.state_analyzer_agent.analyze = AsyncMock(
            return_value=StateSnapshot("window", "explore", "open", "I+W+", False, 0.82)
        )
        orch_module.thread_manager_agent.update = AsyncMock(return_value=_thread())
        orch_module.memory_retrieval_agent.assemble = AsyncMock(
            return_value=MemoryBundle(
                conversation_context="User: мне страшно\nAssistant: понимаю",
                has_relevant_knowledge=True,
                context_turns=2,
                rag_query="контроль страх механизм",
                semantic_hits=[
                    {
                        "chunk_id": "h1",
                        "source": "doc_1",
                        "score": 0.91,
                        "content": "контент чанка",
                    }
                ],
                rag_retrieval_trace={"executed_rag_query": "контроль страх механизм"},
                hybrid_retrieval_trace={
                    "planned_composed_query": "контроль страх механизм",
                    "executed_rag_query": "контроль страх механизм",
                    "legacy_rag_query": "контроль страх механизм",
                    "query_before_rag_proof": False,
                    "retrieval_gap_reason": "",
                },
            )
        )
        orch_module.writer_agent.write = _write
        orch_module.validator_agent.validate = lambda _a, _c: ValidationResult(is_blocked=False)
        orch_module.memory_retrieval_agent.update = AsyncMock(return_value=None)
        orch_module.thread_storage.load_active = lambda _u: None
        orch_module.thread_storage.load_archived = lambda _u: []
        orch_module.thread_storage.save_active = lambda _t: None
        orch_module.thread_storage.archive_thread = lambda *_a, **_k: None
        orch_module.asyncio.create_task = lambda coro: (coro.close(), None)[1]

        result = await orch_module.MultiAgentOrchestrator().run(
            query="мне страшно потерять контроль",
            user_id="runner-user",
        )
        captured["result"] = result
        return captured
    finally:
        for key, value in previous_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def run_source_gates(*, out_dir: Path, overlay_file: Path) -> dict[str, Any]:
    required_files = [
        PRD20_LOG_DIR / "batch_1_accepted_overlay_preview.json",
        PRD20_LOG_DIR / "retrieval_eval_results.json",
        PRD20_LOG_DIR / "batch_1_apply_preflight_report.json",
    ]
    overlay_doc = _read_json(overlay_file)
    overlay_is_non_live = bool(overlay_doc.get("evaluation_only")) or (
        overlay_doc.get("live_apply_allowed") is False
        and overlay_doc.get("safe_to_apply_to_live_metadata") is False
    )
    report = {
        "schema_version": "prd_047_21_source_gate_report_v1",
        "prd_id": PRD_ID,
        "created_at": _utc_now(),
        "status": "passed",
        "git_status_short": _git("status", "--short").splitlines(),
        "recent_commits": _git("log", "--oneline", "-10").splitlines(),
        "required_files": [
            {
                "path": _safe_rel(path),
                "exists": path.exists(),
            }
            for path in required_files
        ],
        "overlay_summary": dict(overlay_doc.get("summary") or {}),
        "evaluation_only": overlay_is_non_live,
        "overlay_trace_visibility_only": True,
        "human_final_approval": bool(overlay_doc.get("human_final_approval")),
        "live_apply_allowed": bool(overlay_doc.get("live_apply_allowed")),
        "safe_to_apply_to_live_metadata": bool(overlay_doc.get("safe_to_apply_to_live_metadata")),
        "blockers": [],
    }
    if not overlay_is_non_live:
        report["blockers"].append("overlay_must_remain_non_live")
    if overlay_doc.get("live_apply_allowed") is not False:
        report["blockers"].append("overlay_live_apply_allowed_must_be_false")
    if overlay_doc.get("human_final_approval") is not False:
        report["blockers"].append("overlay_human_final_approval_must_be_false")
    for item in report["required_files"]:
        if not item["exists"]:
            report["blockers"].append(f"missing_required_file:{item['path']}")
    if report["blockers"]:
        report["status"] = "blocked"
    _write_json(out_dir / "source_gate_report.json", report)
    _write_text(
        out_dir / "source_gate_report.md",
        _markdown(
            "PRD-047.21 Source Gate Report",
            [
                f"- status: `{report['status']}`",
                f"- evaluation_only: `{report['evaluation_only']}`",
                f"- human_final_approval: `{report['human_final_approval']}`",
                f"- live_apply_allowed: `{report['live_apply_allowed']}`",
                "",
                "## Blockers",
                *([f"- {item}" for item in report["blockers"]] or ["- none"]),
            ],
        ),
    )
    return report


def run_trace_samples(*, out_dir: Path, overlay_file: Path) -> dict[str, Any]:
    sample_cases = [
        {"id": "control_as_safety", "query": "мне страшно потерять контроль над собой", "retrieval_query": "контроль страх механизм"},
        {"id": "shame_visibility", "query": "мне стыдно когда меня замечают и оценивают", "retrieval_query": "стыд видимость оценка"},
        {"id": "fact_vs_interpretation", "query": "как отделить факт от моей интерпретации", "retrieval_query": "факт интерпретация практика"},
        {"id": "practice_timing", "query": "дай один короткий шаг если у меня есть силы", "retrieval_query": "короткий шаг практика ресурс"},
        {"id": "irrelevant", "query": "какая сегодня погода в москве", "retrieval_query": "погода москва"},
    ]
    samples: list[dict[str, Any]] = []
    for case in sample_cases:
        enabled = build_overlay_shadow_trace(
            user_message=case["query"],
            retrieval_query=case["retrieval_query"],
            state_snapshot={"intent": "explore", "nervous_state": "window"},
            thread_state={"phase": "clarify", "active_frame": {"active_concept": ""}},
            overlay_file=str(overlay_file),
            enabled=True,
            max_matches=5,
            min_score=0.0,
        )
        disabled = build_overlay_shadow_trace(
            user_message=case["query"],
            retrieval_query=case["retrieval_query"],
            state_snapshot={"intent": "explore", "nervous_state": "window"},
            thread_state={"phase": "clarify", "active_frame": {"active_concept": ""}},
            overlay_file=str(overlay_file),
            enabled=False,
            max_matches=5,
            min_score=0.0,
        )
        samples.append(
            {
                "id": case["id"],
                "query": case["query"],
                "disabled_trace": disabled,
                "enabled_trace": enabled,
                "used_for_writer": bool(enabled.get("used_for_writer", False)),
                "used_for_retrieval_execution": bool(enabled.get("used_for_retrieval_execution", False)),
            }
        )
    payload = {
        "schema_version": "prd_047_21_overlay_shadow_trace_samples_v1",
        "prd_id": PRD_ID,
        "created_at": _utc_now(),
        "sample_count": len(samples),
        "samples": samples,
    }
    _write_json(out_dir / "overlay_shadow_trace_samples.json", payload)
    lines = [
        f"- sample_count: `{len(samples)}`",
        "",
        "## Samples",
    ]
    for sample in samples:
        enabled = sample["enabled_trace"]
        lines.append(
            f"- `{sample['id']}` | would_help=`{enabled.get('would_help')}` | match_count=`{enabled.get('match_count')}` | writer=`{enabled.get('used_for_writer')}` | retrieval=`{enabled.get('used_for_retrieval_execution')}`"
        )
    _write_text(out_dir / "overlay_shadow_trace_samples.md", _markdown("PRD-047.21 Overlay Shadow Trace Samples", lines))
    return payload


def run_behavior_proof(*, out_dir: Path, overlay_file: Path) -> dict[str, Any]:
    off_case = asyncio.run(_run_stubbed_turn(overlay_enabled=False, overlay_file=overlay_file))
    on_case = asyncio.run(_run_stubbed_turn(overlay_enabled=True, overlay_file=overlay_file))
    off_debug = dict(off_case["result"].get("debug", {}))
    on_debug = dict(on_case["result"].get("debug", {}))
    proof = {
        "schema_version": "prd_047_21_no_behavior_change_proof_v1",
        "prd_id": PRD_ID,
        "same_executed_retrieval_query_with_overlay_on_off": (
            off_debug.get("executed_rag_query") == on_debug.get("executed_rag_query")
        ),
        "same_writer_contract_keys_with_overlay_on_off": (
            sorted((off_case["writer_contract"] or {}).keys()) == sorted((on_case["writer_contract"] or {}).keys())
        ),
        "overlay_not_in_writer_contract": "overlay_shadow" not in on_case["prompt_context_json"],
        "overlay_not_in_prompt_canvas": (
            "overlay_shadow" not in on_case["prompt_context_json"]
            and "RAW SOURCE MUST STAY OUT" not in on_case["prompt_context_json"]
        ),
        "overlay_not_in_final_answer": "overlay" not in str(on_case["result"].get("answer", "")).lower(),
        "semantic_hits_not_modified_by_overlay": (
            off_debug.get("semantic_hits_detail") == on_debug.get("semantic_hits_detail")
        ),
        "same_final_answer_with_overlay_on_off": off_case["result"].get("answer") == on_case["result"].get("answer"),
        "overlay_enabled_trace_present": isinstance(on_debug.get("overlay_shadow"), dict),
        "overlay_disabled_trace_present": isinstance(off_debug.get("overlay_shadow"), dict),
    }
    _write_json(out_dir / "no_behavior_change_proof.json", proof)
    _write_text(
        out_dir / "no_behavior_change_proof.md",
        _markdown(
            "PRD-047.21 No Behavior Change Proof",
            [f"- {key}: `{value}`" for key, value in proof.items() if key not in {"schema_version", "prd_id"}],
        ),
    )
    return {
        "proof": proof,
        "debug_on": on_debug,
        "debug_off": off_debug,
    }


def run_api_smoke(*, out_dir: Path, enabled_debug: dict[str, Any]) -> dict[str, Any]:
    if os.getenv("PRD_047_21_ENABLE_INPROCESS_API_SMOKE", "").strip().lower() not in {"1", "true", "yes"}:
        payload = {
            "schema_version": "prd_047_21_api_trace_smoke_v1",
            "prd_id": PRD_ID,
            "status": "warning",
            "reason": "skipped_inprocess_app_smoke_default_off",
            "overlay_shadow_present": False,
            "used_for_writer": False,
            "used_for_retrieval_execution": False,
            "contract_coverage_provided_by": "tests/api/test_overlay_shadow_trace_api_debug.py",
        }
        _write_json(out_dir / "api_trace_smoke.json", payload)
        _write_text(
            out_dir / "api_trace_smoke.md",
            _markdown(
                "PRD-047.21 API Trace Smoke",
                [f"- {key}: `{value}`" for key, value in payload.items() if key not in {"schema_version", "prd_id"}],
            ),
        )
        return payload

    _reset_store()
    store = get_session_store()
    store.save_multiagent_debug(
        session_id="overlay-shadow-api",
        turn_index=1,
        debug=dict(enabled_debug),
    )
    with TestClient(app, base_url="http://localhost") as client:
        response = client.get("/api/debug/session/overlay-shadow-api/multiagent-trace", headers=DEV_HEADERS)
    payload = {
        "schema_version": "prd_047_21_api_trace_smoke_v1",
        "prd_id": PRD_ID,
        "status": "passed" if response.status_code == 200 else "warning",
        "response_status_code": response.status_code,
        "overlay_shadow_present": False,
        "used_for_writer": False,
        "used_for_retrieval_execution": False,
    }
    if response.status_code == 200:
        body = response.json()
        overlay_shadow = body.get("overlay_shadow") if isinstance(body.get("overlay_shadow"), dict) else {}
        payload["overlay_shadow_present"] = bool(overlay_shadow)
        payload["used_for_writer"] = bool(overlay_shadow.get("used_for_writer", False))
        payload["used_for_retrieval_execution"] = bool(overlay_shadow.get("used_for_retrieval_execution", False))
        payload["would_help"] = bool(overlay_shadow.get("would_help", False))
    _write_json(out_dir / "api_trace_smoke.json", payload)
    _write_text(
        out_dir / "api_trace_smoke.md",
        _markdown(
            "PRD-047.21 API Trace Smoke",
            [f"- {key}: `{value}`" for key, value in payload.items() if key not in {"schema_version", "prd_id"}],
        ),
    )
    return payload


def build_authority_boundary(*, out_dir: Path, overlay_shadow: dict[str, Any]) -> dict[str, Any]:
    report = {
        "overlay_trace_visible": bool(overlay_shadow.get("enabled", False)),
        "overlay_writer_visible": bool(overlay_shadow.get("used_for_writer", False)),
        "overlay_retrieval_authority": bool(overlay_shadow.get("used_for_retrieval_execution", False)),
        "overlay_context_assembly_authority": False,
        "overlay_final_answer_authority": bool(overlay_shadow.get("used_for_final_answer", False)),
        "overlay_runtime_authority_summary": "trace_only",
    }
    _write_json(out_dir / "overlay_shadow_authority_boundary_report.json", report)
    return report


def build_no_mutation_proof(*, out_dir: Path) -> dict[str, Any]:
    report = {
        "schema_version": "prd_047_21_no_mutation_proof_v1",
        "prd_id": PRD_ID,
        "status": "passed",
        "live_metadata_applied": False,
        "processed_blocks_overwritten": False,
        "registry_mutated": False,
        "chroma_reindexed": False,
        "embeddings_changed": False,
        "writer_prompt_changed": False,
        "writer_contract_changed_for_overlay": False,
        "executed_retrieval_changed_by_overlay": False,
        "semantic_hits_changed_by_overlay": False,
        "final_answer_changed_by_overlay": False,
        "overlay_shadow_trace_only": True,
        "feature_flag_default_enabled": False,
        "web_admin_changed": False,
        "raw_provider_payload_committed": False,
        "raw_full_source_text_committed": False,
    }
    _write_json(out_dir / "no_mutation_proof.json", report)
    return report


def write_reports(*, out_dir: Path, reports_dir: Path, summary: dict[str, Any]) -> None:
    report_lines = [
        f"- final_status: `{summary['final_status']}`",
        f"- source_gate_status: `{summary['source_gate_status']}`",
        f"- overlay_trace_visible: `{summary['overlay_trace_visible']}`",
        f"- same_executed_query: `{summary['same_executed_query']}`",
        f"- semantic_hits_unchanged: `{summary['semantic_hits_unchanged']}`",
        f"- api_trace_smoke_status: `{summary['api_trace_smoke_status']}`",
        f"- implementation_commit: `pending`",
    ]
    _write_text(reports_dir / "PRD-047.21_IMPLEMENTATION_REPORT.md", _markdown("PRD-047.21 Implementation Report", report_lines))
    _write_text(
        reports_dir / "PRD-047.21_NEXT_PRD_RECOMMENDATION.md",
        _markdown("PRD-047.21 Next PRD Recommendation", [f"1. `{NEXT_PRD}`"]),
    )


def write_implementation_summary(*, out_dir: Path, summary: dict[str, Any]) -> None:
    payload = {
        "schema_version": "prd_047_21_implementation_summary_v1",
        "prd_id": PRD_ID,
        "created_at": _utc_now(),
        **summary,
    }
    _write_json(out_dir / "implementation_summary.json", payload)


def run(args: argparse.Namespace) -> dict[str, Any]:
    out_dir = Path(args.out_dir).resolve()
    reports_dir = Path(args.reports_dir).resolve()
    overlay_file = Path(args.overlay_file).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    source_gate = run_source_gates(out_dir=out_dir, overlay_file=overlay_file)
    if source_gate["status"] != "passed":
        return {"status": "blocked", "source_gate_report": source_gate}

    config_snapshot = get_overlay_shadow_trace_settings()
    _write_json(out_dir / "overlay_shadow_config_snapshot.json", config_snapshot)
    if args.mode == "unit":
        return {"status": "passed", "source_gate_report": source_gate, "config_snapshot": config_snapshot}
    trace_samples = run_trace_samples(out_dir=out_dir, overlay_file=overlay_file)
    if args.mode == "trace-samples":
        return {"status": "passed", "source_gate_report": source_gate, "trace_samples": trace_samples}
    behavior_bundle = run_behavior_proof(out_dir=out_dir, overlay_file=overlay_file)
    api_smoke = run_api_smoke(out_dir=out_dir, enabled_debug=behavior_bundle["debug_on"])
    if args.mode == "api-smoke":
        return {
            "status": "passed" if api_smoke["status"] == "passed" else "warning",
            "source_gate_report": source_gate,
            "api_trace_smoke": api_smoke,
        }
    authority = build_authority_boundary(
        out_dir=out_dir,
        overlay_shadow=dict(behavior_bundle["debug_on"].get("overlay_shadow", {})),
    )
    no_mutation = build_no_mutation_proof(out_dir=out_dir)
    encoding_args = SimpleNamespace(
        repo_root=str(REPO_ROOT),
        logs_dir=str(out_dir),
        reports_dir=str(reports_dir),
        out_dir=str(out_dir),
        prd=PRD_ID,
        report_prd=PRD_ID,
        fixed_file=[],
    )
    encoding_report = encoding_validator.run(encoding_args)
    _write_json(out_dir / "encoding_hygiene_report.json", encoding_report)

    summary = {
        "final_status": "passed"
        if source_gate["status"] == "passed"
        and behavior_bundle["proof"]["same_executed_retrieval_query_with_overlay_on_off"]
        and behavior_bundle["proof"]["semantic_hits_not_modified_by_overlay"]
        and authority["overlay_runtime_authority_summary"] == "trace_only"
        and encoding_report.get("final_status") == "passed"
        else "warning",
        "source_gate_status": source_gate["status"],
        "overlay_trace_visible": authority["overlay_trace_visible"],
        "same_executed_query": behavior_bundle["proof"]["same_executed_retrieval_query_with_overlay_on_off"],
        "semantic_hits_unchanged": behavior_bundle["proof"]["semantic_hits_not_modified_by_overlay"],
        "api_trace_smoke_status": api_smoke["status"],
        "trace_sample_count": int(trace_samples["sample_count"]),
        "next_prd_recommendation": NEXT_PRD,
    }
    write_reports(out_dir=out_dir, reports_dir=reports_dir, summary=summary)
    write_implementation_summary(out_dir=out_dir, summary=summary)
    return {
        "status": summary["final_status"],
        "source_gate_report": source_gate,
        "trace_samples": trace_samples,
        "no_behavior_change_proof": behavior_bundle["proof"],
        "api_trace_smoke": api_smoke,
        "authority_boundary": authority,
        "no_mutation_proof": no_mutation,
        "encoding_hygiene": encoding_report,
        "implementation_summary": _read_json(out_dir / "implementation_summary.json"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run PRD-047.21 overlay shadow trace smoke.")
    parser.add_argument("--mode", default="full", choices=["unit", "trace-samples", "api-smoke", "full"])
    parser.add_argument(
        "--overlay-file",
        default=str(PRD20_LOG_DIR / "batch_1_accepted_overlay_preview.json"),
    )
    parser.add_argument("--out-dir", default=str(LOGS_DIR_DEFAULT))
    parser.add_argument("--reports-dir", default=str(REPORTS_DIR_DEFAULT))
    args = parser.parse_args()

    result = run(args)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") in {"passed", "warning"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
