from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

import pytest


def _load_runner_module():
    project_root = Path(__file__).resolve().parents[2]
    module_path = project_root / "scripts" / "run_quality_baseline.py"
    spec = importlib.util.spec_from_file_location("run_quality_baseline", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class _FakeOrchestrator:
    async def run(self, *, query: str, user_id: str):  # noqa: ANN003
        return {
            "status": "ok",
            "answer": f"echo:{query}",
            "response_mode": "validate",
            "thread_id": f"th_{user_id}",
            "debug": {
                "pipeline_version": "multiagent_v1",
                "nervous_state": "window",
                "intent": "contact",
                "openness": "mixed",
                "ok_position": "I+W+",
                "confidence": 0.81,
                "phase": "clarify",
                "relation_to_thread": "continue",
                "response_mode": "validate",
                "state_analyzer_model": "deterministic",
                "state_analyzer_api_mode": "heuristic",
                "model_used": "gpt-5-mini",
                "model_temperature": 0.7,
                "model_max_tokens": 600,
                "quality_trace_version": "quality_trace_v1",
                "quality_trace": {"summary_flags": ["generic_phrase_risk"]},
                "total_latency_ms": 120,
            },
        }


@pytest.mark.asyncio
async def test_run_case_direct_async_uses_orchestrator_and_keeps_debug(monkeypatch) -> None:
    runner = _load_runner_module()

    fake_module = types.ModuleType("bot_agent.multiagent.orchestrator")
    fake_module.orchestrator = _FakeOrchestrator()
    monkeypatch.setitem(sys.modules, "bot_agent.multiagent.orchestrator", fake_module)

    case = {
        "id": "QB-TEST-001",
        "title": "Direct smoke test case",
        "category": "contact",
        "user_turns": ["hello", "still here"],
        "expected": {"should": [], "should_not": []},
    }
    result, errors = await runner._run_case_direct_async(case)
    assert errors == []
    assert result["case_id"] == "QB-TEST-001"
    assert result["turns"] == 2
    assert result["final_debug_summary"]["state"]["intent"] == "contact"
    assert result["final_debug_summary"]["thread"]["response_mode"] == "validate"
    assert result["final_debug_summary"]["quality_trace_summary"] == ["generic_phrase_risk"]


def test_select_cases_supports_case_ids_list() -> None:
    runner = _load_runner_module()
    cases = [
        {"id": "QB-001"},
        {"id": "QB-002"},
        {"id": "QB-003"},
    ]
    selected = runner._select_cases(cases, limit=None, case_id=None, case_ids="QB-003,QB-001")
    assert [item["id"] for item in selected] == ["QB-003", "QB-001"]
