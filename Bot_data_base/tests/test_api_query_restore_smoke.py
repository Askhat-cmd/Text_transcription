from tools.api_query_restore_smoke import _normalize_query_row


def test_normalize_query_row_redacts_full_content() -> None:
    response = {
        "ok": True,
        "status_code": 200,
        "body": {
            "chunks": [
                {
                    "chunk_id": "c1",
                    "content": "SECRET VERY LONG CONTENT " * 20,
                    "score": 0.91,
                    "block_title": "title",
                    "governance": {
                        "chunk_type": "lens",
                        "allowed_use": ["writer_context"],
                        "safety_flags": ["not_for_direct_quote"],
                        "lens_family": ["shame"],
                        "not_for_direct_quote": True,
                        "source_style_not_user_facing": False,
                        "chunking_quality": {"mixed_intent_severity": "low"},
                    },
                }
            ]
        },
        "error": None,
    }
    row = _normalize_query_row("q", response)
    assert row["status"] == "ok"
    assert row["hits_count"] == 1
    assert len(row["top_hits"]) == 1
    top = row["top_hits"][0]
    assert "content" not in top
    assert "content_full" not in top
    assert isinstance(top["content_preview"], str)
    assert len(top["content_preview"]) <= 160
