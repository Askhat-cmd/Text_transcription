from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools import prd_047_23_chunk_boundary_audit as audit


def _load_real_cases() -> list[dict[str, object]]:
    trace_path = audit.find_local_trace_fixture()
    assert trace_path is not None
    return audit.extract_trace_cases(trace_path.read_text(encoding="utf-8"))


def _load_real_blocks() -> tuple[list[dict[str, object]], dict[str, dict[str, object]]]:
    return audit.load_merged_blocks()


def test_case_matrix_includes_required_case_ids() -> None:
    cases = _load_real_cases()
    assert [case["case_id"] for case in cases] == ["C23-001", "C23-002", "C23-003"]


def test_detect_mid_word_boundary_signal_on_case_c23_001() -> None:
    cases = _load_real_cases()
    case = cases[0]
    excerpt = str(case["payload_chunks"][0]["content_excerpt"])
    assert audit.looks_mid_word_cut(excerpt) is True


def test_classify_case_c23_001_as_non_none_cut() -> None:
    cases = _load_real_cases()
    _, block_index = _load_real_blocks()
    source_info = audit.load_primary_source_text()
    case = cases[0]
    chunk = case["payload_chunks"][0]
    block = block_index[str(chunk["chunk_id"])]
    cut_class = audit.classify_cut_case(
        excerpt=str(chunk["content_excerpt"]),
        stored_text=str(block["text"]),
        source_text=str(source_info["text"]),
        total_sent_char_count=int(case["total_sent_char_count"]),
        content_truncated=bool(chunk["content_truncated"]),
        truncation_strategy=str(chunk["truncation_strategy"]),
    )
    assert cut_class in {"stored_preview_used_as_full_content", "unknown_needs_manual_review", "source_chunk_boundary_cut"}
    assert cut_class != "none"


def test_runtime_sentence_boundary_truncation_is_classified_as_allowed() -> None:
    cases = _load_real_cases()
    _, block_index = _load_real_blocks()
    source_info = audit.load_primary_source_text()
    case = cases[1]
    chunk = case["payload_chunks"][0]
    block = block_index[str(chunk["chunk_id"])]
    cut_class = audit.classify_cut_case(
        excerpt=str(chunk["content_excerpt"]),
        stored_text=str(block["text"]),
        source_text=str(source_info["text"]),
        total_sent_char_count=int(case["total_sent_char_count"]),
        content_truncated=bool(chunk["content_truncated"]),
        truncation_strategy=str(chunk["truncation_strategy"]),
    )
    assert cut_class == "runtime_payload_sentence_truncation"


def test_classify_ui_preview_only_when_sent_chars_exceed_excerpt() -> None:
    cut_class = audit.classify_cut_case(
        excerpt="Короткий preview без точки",
        stored_text="Короткий preview без точки и потом идёт длинное продолжение полного текста.",
        source_text="Короткий preview без точки и потом идёт длинное продолжение полного текста.",
        total_sent_char_count=200,
        content_truncated=False,
        truncation_strategy="none",
    )
    assert cut_class == "ui_preview_only"


def test_query_duplicate_fragments_detected_for_case_c23_003() -> None:
    cases = _load_real_cases()
    case = cases[2]
    executed_query = str(case["observed_rag_query"])
    assert audit.detect_query_duplicate_fragment_count(executed_query) >= 1
    assert audit.query_truncated_mid_word(executed_query) is True


def test_previous_topic_pollution_detected_for_case_c23_002() -> None:
    cases = _load_real_cases()
    case = cases[1]
    assert audit.query_contains_previous_question(
        str(case["observed_rag_query"]),
        str(case["previous_canonical_query"]),
    ) is True


def test_writer_payload_mismatch_detected_for_zero_rag_nonzero_payload_cases() -> None:
    cases = _load_real_cases()
    results, _ = audit.audit_writer_payload_consistency(cases)
    by_case = {item["case_id"]: item for item in results}
    assert by_case["C23-002"]["rag_for_writer_vs_payload_mismatch"] is True
    assert by_case["C23-003"]["rag_for_writer_vs_payload_mismatch"] is True
    assert by_case["C23-003"]["ui_chunks_vs_prompt_payload_mismatch"] is True


def test_relevance_audit_marks_case_c23_003_as_missing_expected_source() -> None:
    cases = _load_real_cases()
    blocks, block_index = _load_real_blocks()
    results, _ = audit.audit_retrieval_relevance(cases, blocks, block_index)
    by_case = {item["case_id"]: item for item in results}
    assert by_case["C23-003"]["overall_label"] == "missing_expected_source"


def test_run_audit_writes_required_json_and_md_artifacts(tmp_path: Path, monkeypatch) -> None:
    trace_path = audit.find_local_trace_fixture()
    assert trace_path is not None
    reports_dir = tmp_path / "reports"
    monkeypatch.setattr(audit, "REPORTS_DIR_DEFAULT", reports_dir)

    def fake_encoding(out_dir: Path) -> dict[str, object]:
        payload = {"final_status": "passed"}
        audit._write_json(out_dir / "encoding_hygiene_report.json", payload)
        return payload

    monkeypatch.setattr(audit, "run_encoding_hygiene", fake_encoding)
    summary = audit.run_audit(
        mode="trace-fixtures",
        out_dir=tmp_path / "logs",
        trace_path=trace_path,
    )
    assert summary["status"] == "passed"
    required = [
        "source_gate_report.json",
        "source_gate_report.md",
        "trace_case_matrix.json",
        "trace_case_matrix.md",
        "chunking_code_map.json",
        "chunking_code_map.md",
        "chunk_boundary_audit.json",
        "chunk_boundary_audit.md",
        "retrieval_query_assembly_audit.json",
        "writer_payload_consistency_audit.json",
        "retrieval_relevance_audit.json",
        "suspect_chunk_inventory.json",
        "no_mutation_proof.json",
        "encoding_hygiene_report.json",
        "implementation_summary.json",
        "live_sample_report.json",
    ]
    for name in required:
        assert (tmp_path / "logs" / name).exists(), name
    assert (reports_dir / f"{audit.PRD_ID}_IMPLEMENTATION_REPORT.md").exists()
    assert (reports_dir / f"{audit.PRD_ID}_NEXT_PRD_RECOMMENDATION.md").exists()


def test_sanitized_live_payload_excludes_raw_writer_llm() -> None:
    debug_payload = {
        "session_id": "s1",
        "turn_index": 2,
        "retrieval_action": "query_kb",
        "writer_llm": {"user_prompt": "sensitive"},
        "memory_context": {"semantic_hits": [{"x": 1}], "recent_turns": [1, 2]},
        "writer_kb_payload_trace": {"primary_path": "writer_kb_payload_v1"},
    }
    sanitized = audit._sanitize_live_debug_payload(debug_payload, "ok")
    assert "writer_llm" not in sanitized
    assert sanitized["memory_context_summary"]["semantic_hits_count"] == 1
    assert sanitized["internal_payload_leak_in_answer"] is False
    json.dumps(sanitized, ensure_ascii=False)
