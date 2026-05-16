from __future__ import annotations

from review.architect_auto_decision_policy import evaluate_item_policy, generate_auto_decisions


def _item(
    *,
    chunk_type: str = "lens",
    review_priority: str = "P2",
    summary: str = "Нейтральная внутренняя линза для мягкой саморефлексии без директив.",
    safe_preview: str = "Короткий безопасный превью-текст.",
    safety_flags: list[str] | None = None,
    review_item_id: str = "post_reprocess::x1",
    block_id: str = "x1",
) -> dict:
    return {
        "review_item_id": review_item_id,
        "block_id": block_id,
        "source_id": "123__кузница_духа",
        "heading_path": ["H1"],
        "chunk_type": chunk_type,
        "allowed_use": ["writer_context"],
        "safety_flags": safety_flags or [],
        "lens_family": ["self_reflection"],
        "review_priority": review_priority,
        "review_reasons": ["needs_human_review"],
        "recommended_action": "defer",
        "safe_preview": safe_preview,
        "llm_enrichment": {
            "summary": summary,
            "tags": ["tag1"],
            "lens_family_candidates": ["self_reflection"],
            "use_when": [],
            "avoid_when": [],
            "self_contained_score": 0.7,
            "self_contained_reason": "ok",
            "confidence": 0.6,
        },
    }


def test_practice_item_gets_conservative_edit_route() -> None:
    decision = evaluate_item_policy(
        _item(chunk_type="practice", safety_flags=["practice_requires_low_resource_check"]),
        source_prd="PRD-046.0.9.3",
    )
    assert decision.payload["decision"] == "needs_edit"
    assert decision.payload["edited_fields"]
    assert "summary" in decision.payload["edited_fields"]


def test_quote_item_defaults_to_defer() -> None:
    decision = evaluate_item_policy(
        _item(chunk_type="quote", summary="Нейтральный пересказ без цитирования."),
        source_prd="PRD-046.0.9.3",
    )
    assert decision.payload["decision"] == "defer"


def test_sensitive_terms_trigger_conservative_routing() -> None:
    decision = evaluate_item_policy(
        _item(chunk_type="lens", summary="Тема касается паники и риска потери контроля."),
        source_prd="PRD-046.0.9.3",
    )
    assert decision.payload["decision"] == "defer"


def test_generic_summary_triggers_defer() -> None:
    decision = evaluate_item_policy(
        _item(chunk_type="theory", summary="Может быть использовано для обогащения консультирования."),
        source_prd="PRD-046.0.9.3",
    )
    assert decision.payload["decision"] == "defer"


def test_generate_auto_decisions_has_no_authority_mutation_fields() -> None:
    queue_payload = {
        "schema_version": "post_reprocess_review_queue_after_real_enrichment_v1",
        "source_prd": "PRD-046.0.9-RUN1",
        "items": [
            {
                "review_item_id": "post_reprocess::b1",
                "block_id": "b1",
                "source_id": "123__кузница_духа",
                "source_title": "Кузница Духа",
                "chunk_type": "practice",
                "review_priority": "P2",
                "review_reasons": ["needs_human_review"],
                "recommended_action": "defer",
                "safe_preview": "preview one",
                "advisory_summary_preview": "summary one",
            },
            {
                "review_item_id": "post_reprocess::b2",
                "block_id": "b2",
                "source_id": "123__кузница_духа",
                "source_title": "Кузница Духа",
                "chunk_type": "quote",
                "review_priority": "P2",
                "review_reasons": ["needs_human_review"],
                "recommended_action": "defer",
                "safe_preview": "preview two",
                "advisory_summary_preview": "summary two",
            },
        ],
    }

    blocks_payload = {
        "schema_version": "bot_data_base_v1.0",
        "blocks": [
            {
                "id": "b1",
                "metadata": {
                    "source_id": "123__кузница_духа",
                    "heading_path": ["A"],
                    "governance": {
                        "chunk_type": "practice",
                        "allowed_use": ["writer_context", "practice_suggestion"],
                        "safety_flags": ["practice_requires_low_resource_check"],
                        "lens_family": ["somatic"],
                    },
                    "llm_enrichment": {"summary": "Директивная практика, сделай сразу."},
                },
            },
            {
                "id": "b2",
                "metadata": {
                    "source_id": "123__кузница_духа",
                    "heading_path": ["B"],
                    "governance": {
                        "chunk_type": "quote",
                        "allowed_use": ["writer_context"],
                        "safety_flags": ["not_for_direct_quote"],
                        "lens_family": ["self_reflection"],
                    },
                    "llm_enrichment": {"summary": "Нейтральный пересказ."},
                },
            },
        ],
    }

    decisions, stats = generate_auto_decisions(
        queue_payload=queue_payload,
        blocks_payload=blocks_payload,
        source_prd="PRD-046.0.9.3",
    )

    assert len(decisions) == 2
    forbidden = {
        "chunk_type",
        "allowed_use",
        "safety_flags",
        "source_id",
        "block_id",
        "text",
        "content",
        "raw_text",
        "embedding",
        "vector",
    }
    for decision in decisions:
        for key in (decision.get("edited_fields") or {}).keys():
            assert key not in forbidden
    assert stats["items_total"] == 2
