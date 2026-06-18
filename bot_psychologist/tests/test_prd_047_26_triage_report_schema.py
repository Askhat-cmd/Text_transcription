from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from bot_psychologist.eval.prd_047_26_schema import load_cases, default_cases_path
from bot_psychologist.tools.prd_047_26_triage_report import build_triage_report, classify_live_case


def _export(*, case_id: str, answer: str, case_type: str = "direct_kb_answer") -> dict:
    return {
        "case_id": case_id,
        "assistant_answer": answer,
        "active_runtime_path": "multiagent_adapter",
        "retrieval_query_build_trace_v1": {
            "primary_path": "current_turn_focus_v1",
            "previous_user_query_included": False,
            "query_truncated_mid_word": False,
            "duplicate_fragment_count": 0,
        },
        "writer_kb_payload_trace": {
            "primary_path": "writer_kb_payload_v1",
            "payload_chunk_count": 1,
            "fallback_is_primary": False,
        },
        "overlay_shadow_trace": {
            "enabled": True,
            "would_help": False,
            "used_for_writer": False,
            "used_for_retrieval_execution": False,
            "used_for_final_answer": False,
        },
        "final_answer_directive_v1": {"answer_obligation": "answer_knowledge_question"},
        "validator": {"is_blocked": False, "quality_flags": []},
        "evaluator": {"fit_status": "pass"},
        "live_turn_evidence": {
            "state_thread": {"response_mode": "reflect"},
            "dialogue": {
                "dialogue_act_resolution": {"dialogue_act": "knowledge_question"},
                "answer_obligation_resolution": {"answer_obligation": "answer_knowledge_question"},
            },
        },
        "triage": {},
        "case_type": case_type,
    }


def test_missing_trace_fields_become_trace_missing_evidence() -> None:
    case = {
        "case_id": "Q26-X",
        "case_type": "direct_kb_answer",
        "expected_answer_shape": {
            "should_answer_directly": True,
            "should_not_reask_definition": True,
            "should_not_open_new_topic": True,
            "should_not_dump_raw_kb": True,
            "should_preserve_living_tone": True,
        },
        "expected_trace_signals": {
            "writer_kb_payload_expected": True,
            "overlay_apply_must_be_false": True,
            "legacy_query_builder_must_be_false": True,
            "current_turn_focus_expected": True,
        },
        "expected_dialogue_acts": ["knowledge_question"],
        "expected_answer_obligations": ["answer_knowledge_question"],
        "allowed_response_modes": ["reflect"],
        "expected_keywords": ["несовершенное"],
        "forbidden_keywords": [],
        "failure_class_candidates": ["trace_missing_evidence"],
    }
    export = _export(case_id="Q26-X", answer="Это паттерн несовершенного Я.")
    export["live_turn_evidence"] = {}
    triage = classify_live_case(case, export)
    assert "trace_missing_evidence" in triage["failure_classes"]
    assert triage["missing_fields"]


def test_triage_report_has_required_counters(tmp_path: Path) -> None:
    cases = load_cases(default_cases_path())
    case = next(item for item in cases if item["case_id"] == "Q26-001")
    export = _export(case_id="Q26-001", answer="Это программа несовершенного Я, внутренний автоматический паттерн.")
    live_results = {
        "cases": [export],
    }
    report = build_triage_report(cases=[case], live_results=live_results, out_dir=tmp_path)
    assert "dialogue_act_error_count" in report
    assert "answer_obligation_error_count" in report
    assert "response_mode_error_count" in report
    assert "retrieval_query_error_count" in report
    assert "kb_payload_error_count" in report
    assert "writer_style_regression_count" in report
    assert "evaluator_false_pass_count" in report
    assert "trace_missing_evidence_count" in report
    assert (tmp_path / "live_quality_triage_report.json").exists()
