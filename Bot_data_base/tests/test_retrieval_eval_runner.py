from __future__ import annotations

from tools.run_retrieval_eval import detect_raw_leak, run_retrieval_eval


def _ok_query_chunk() -> dict:
    return {
        "chunk_id": "chunk_1",
        "content": "длинный внутренний текст, который в артефакты целиком попадать не должен",
        "score": 0.92,
        "block_title": "block",
        "governance": {
            "chunk_type": "lens",
            "allowed_use": ["writer_context", "diagnostic_lens"],
            "safety_flags": ["not_for_direct_quote"],
            "lens_family": ["self_criticism", "achievement"],
            "not_for_direct_quote": True,
            "source_style_not_user_facing": False,
            "llm_enrichment_summary": "summary",
            "llm_enrichment_tags": ["low_resource", "practice"],
            "llm_enrichment_use_when": ["when low resource"],
        },
    }


def test_run_retrieval_eval_scores_and_sanitizes() -> None:
    dataset = {
        "schema_version": "retrieval_eval_v1",
        "dataset_path": "Bot_data_base/eval/retrieval_eval_v1.json",
        "cases": [
            {
                "id": "KR-T1",
                "query": "я слишком требовательный к себе",
                "category": "self_criticism_achievement",
                "expected_any_lens_family": ["self_criticism"],
                "expected_any_chunk_type": ["lens"],
                "expected_any_allowed_use": ["writer_context"],
                "expected_safety_flags_any": ["not_for_direct_quote"],
                "must_not_allowed_use": ["internal_only"],
            }
        ],
    }

    def fake_http(method: str, url: str, payload=None, timeout=15.0):
        del timeout
        if method == "GET" and url.endswith("/api/status/"):
            return {"ok": True, "status_code": 200, "body": {"status": "ok"}, "error": None}
        if method == "GET" and url.endswith("/api/registry/"):
            return {"ok": True, "status_code": 200, "body": {"total": 1}, "error": None}
        if method == "POST" and url.endswith("/api/query/"):
            assert payload["top_k"] == 5
            return {
                "ok": True,
                "status_code": 200,
                "body": {"chunks": [_ok_query_chunk()]},
                "error": None,
            }
        raise AssertionError(f"Unexpected call: {method} {url}")

    result = run_retrieval_eval(
        dataset=dataset,
        api_base_url="http://127.0.0.1:8013",
        top_k=5,
        timeout_seconds=5.0,
        include_sanitized_previews=True,
        fail_on_api_error=True,
        http_client=fake_http,
    )

    scorecard = result["scorecard"]
    assert scorecard["cases_total"] == 1
    assert scorecard["queries_failed"] == 0
    assert scorecard["top1_semantic_match_rate"] == 1.0
    assert scorecard["top5_governance_present_rate"] == 1.0
    assert scorecard["weak_cases_count"] == 0
    top_hit = result["results"]["cases"][0]["top_hits"][0]
    assert "content" not in top_hit
    assert "content_preview" in top_hit
    assert scorecard["raw_full_text_leak_detected"] is False


def test_run_retrieval_eval_generates_weak_case_on_failure() -> None:
    dataset = {
        "schema_version": "retrieval_eval_v1",
        "dataset_path": "Bot_data_base/eval/retrieval_eval_v1.json",
        "cases": [
            {
                "id": "KR-T2",
                "query": "страх отвержения",
                "category": "fear_rejection",
                "expected_any_lens_family": ["fear_rejection"],
                "expected_any_chunk_type": ["lens"],
                "expected_any_allowed_use": ["writer_context"],
                "expected_safety_flags_any": ["not_for_direct_quote"],
                "must_not_allowed_use": ["internal_only"],
            }
        ],
    }

    def fake_http(method: str, url: str, payload=None, timeout=15.0):
        del payload, timeout
        if method == "GET":
            return {"ok": True, "status_code": 200, "body": {"status": "ok", "total": 1}, "error": None}
        return {"ok": True, "status_code": 200, "body": {"chunks": []}, "error": None}

    result = run_retrieval_eval(
        dataset=dataset,
        api_base_url="http://127.0.0.1:8013",
        top_k=5,
        timeout_seconds=5.0,
        include_sanitized_previews=False,
        fail_on_api_error=False,
        http_client=fake_http,
    )
    assert result["scorecard"]["weak_cases_count"] == 1
    assert result["weak_cases"][0]["id"] == "KR-T2"
    assert "missing_semantic_match_top5" in result["weak_cases"][0]["why_failed"]


def test_detect_raw_leak() -> None:
    safe_payload = {"cases": [{"top_hits": [{"content_preview": "ok"}]}]}
    unsafe_payload = {"cases": [{"top_hits": [{"content_full": "secret"}]}]}
    assert detect_raw_leak(safe_payload) is False
    assert detect_raw_leak(unsafe_payload) is True

