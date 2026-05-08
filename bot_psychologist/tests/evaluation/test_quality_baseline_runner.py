from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from unittest.mock import patch


def _load_runner_module():
    project_root = Path(__file__).resolve().parents[2]
    module_path = project_root / "scripts" / "run_quality_baseline.py"
    spec = importlib.util.spec_from_file_location("run_quality_baseline", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_extract_debug_summary_keeps_quality_trace() -> None:
    runner = _load_runner_module()
    response = {
        "trace": {
            "pipeline_version": "multiagent_v1",
            "quality_trace_version": "quality_trace_v1",
            "quality_trace": {
                "version": "quality_trace_v1",
                "summary_flags": ["generic_phrase_risk"],
            },
            "quality_trace_error": None,
        },
        "processing_time_seconds": 0.123,
    }

    summary, latency_ms = runner._extract_debug_summary(response, session_id="s-1")

    assert summary["quality_trace_version"] == "quality_trace_v1"
    assert summary["quality_trace"]["summary_flags"] == ["generic_phrase_risk"]
    assert summary["quality_trace_error"] is None
    assert latency_ms == 123.0


def test_extract_debug_summary_has_nested_state_thread_writer_blocks() -> None:
    runner = _load_runner_module()
    response = {
        "debug": {
            "nervous_state": "window",
            "intent": "contact",
            "phase": "clarify",
            "relation_to_thread": "continue",
            "response_mode": "validate",
            "pattern_core": "stable continuity core",
            "active_frame": {
                "current_need": "short support without pressure",
                "next_recommended_direction": "keep answer short and low pressure",
            },
            "state_analyzer_model": "deterministic",
            "state_analyzer_api_mode": "heuristic",
            "model_used": "gpt-5-mini",
            "model_temperature": 0.7,
            "model_max_tokens": 600,
            "quality_trace": {
                "summary_flags": ["generic_phrase_risk"],
                "state": {"openness": "mixed", "ok_position": "I+W+"},
                "thread": {"continuity_score": 0.12},
                "writer_move_compliance": {
                    "version": "writer_move_compliance_trace_v1",
                    "move": "reflect_pattern_once",
                    "max_sentences": 6,
                    "max_questions": 1,
                    "sentence_count": 3,
                    "question_count": 0,
                    "violations": [],
                    "risk_flags": [],
                },
            },
            "thread_diagnostics_version": "thread_diagnostics_v1",
            "thread_diagnostics": {
                "relation": {"relation_reason": "continuity_continue"},
                "phase": {"phase_reason": "keep_current_phase"},
                "mode": {"mode_reason": "phase_clarify_reflect"},
                "action": {"thread_action": "continue_thread"},
                "semantic_frame": {
                    "pattern_core_present": True,
                    "active_frame_present": True,
                    "active_frame_keys": ["current_need", "next_recommended_direction"],
                    "current_need": "short support without pressure",
                    "next_recommended_direction": "keep answer short and low pressure",
                },
            },
            "context_assembly_trace_version": "context_assembly_trace_v1",
            "context_assembly_trace": {
                "version": "context_assembly_trace_v1",
                "recent_full_count": 3,
                "summarized_count": 1,
                "dropped_count": 0,
                "semantic_hits_count": 1,
                "knowledge_hits_count": 1,
                "duplicates_removed": 1,
                "budget_used_chars": 3200,
                "budget_limit_chars": 8000,
                "reasons": [],
            },
            "context_package_summary": {
                "has_current_user_message": True,
                "pattern_core_present": True,
                "active_frame_present": True,
                "recent_full_count": 3,
                "recent_summarized_count": 1,
                "personal_history_count": 1,
                "semantic_hits_count": 1,
                "knowledge_hits_count": 1,
            },
            "diagnostic_card_version": "diagnostic_card_v1",
            "diagnostic_card_summary": {
                "present": True,
                "situation_label": "semantic_continuation",
                "suggested_writer_move": "reflect_pattern_once",
                "confidence": 0.88,
                "risk_flags": [],
            },
            "total_latency_ms": 321,
        }
    }
    summary, latency_ms = runner._extract_debug_summary(response, session_id="s-2")
    assert isinstance(summary["state"], dict)
    assert isinstance(summary["thread"], dict)
    assert isinstance(summary["writer"], dict)
    assert summary["state"]["intent"] == "contact"
    assert summary["thread"]["response_mode"] == "validate"
    assert summary["writer"]["model_used"] == "gpt-5-mini"
    assert summary["quality_trace_summary"] == ["generic_phrase_risk"]
    assert summary["thread_diagnostics_version"] == "thread_diagnostics_v1"
    assert summary["thread"]["relation_reason"] == "continuity_continue"
    assert summary["thread"]["phase_reason"] == "keep_current_phase"
    assert summary["thread"]["mode_reason"] == "phase_clarify_reflect"
    assert summary["thread"]["thread_action"] == "continue_thread"
    assert summary["thread"]["pattern_core"] == "stable continuity core"
    assert summary["thread"]["pattern_core_present"] is True
    assert summary["thread"]["active_frame"]["current_need"] == "short support without pressure"
    assert summary["semantic_frame_summary"]["pattern_core_present"] is True
    assert summary["context_assembly_trace_version"] == "context_assembly_trace_v1"
    assert summary["context_assembly_trace"]["recent_full_count"] == 3
    assert summary["context_package_summary"]["recent_summarized_count"] == 1
    assert summary["diagnostic_card_version"] == "diagnostic_card_v1"
    assert summary["diagnostic_card_summary"]["situation_label"] == "semantic_continuation"
    assert summary["writer_move_compliance"]["version"] == "writer_move_compliance_trace_v1"
    assert summary["writer_move_compliance"]["move"] == "reflect_pattern_once"
    assert latency_ms == 321.0


def test_runtime_metadata_contains_fingerprint_keys() -> None:
    runner = _load_runner_module()
    meta = runner._runtime_metadata(runner_mode="direct")
    assert isinstance(meta, dict)
    assert "git_sha" in meta
    assert "git_dirty" in meta
    assert "runtime_fingerprint" in meta
    fp = meta["runtime_fingerprint"]
    assert isinstance(fp, dict)
    assert "state_analyzer_file_sha256" in fp
    assert "thread_manager_file_sha256" in fp
    assert "writer_prompt_file_sha256" in fp
    assert "orchestrator_file_sha256" in fp


def test_git_dirty_returns_none_when_git_unavailable() -> None:
    runner = _load_runner_module()
    with patch.object(runner.subprocess, "run", side_effect=FileNotFoundError("git missing")):
        value = runner._git_dirty()
    assert value is None
