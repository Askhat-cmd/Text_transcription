from __future__ import annotations

from review.post_apply_quality_gate import build_writer_kb_policy_smoke


def _block(block_id: str, *, chunk_type: str, allowed_use: list[str], safety_flags: list[str], llm_summary: str, practice_low_resource_safe: bool | None = None) -> dict:
    governance = {
        "chunk_type": chunk_type,
        "allowed_use": allowed_use,
        "safety_flags": safety_flags,
    }
    if practice_low_resource_safe is not None:
        governance["practice_metadata"] = {"low_resource_safe": practice_low_resource_safe}
    return {
        "id": block_id,
        "source": "book:123__кузница_духа",
        "metadata": {
            "source_id": "123__кузница_духа",
            "governance": governance,
            "llm_enrichment": {"summary": llm_summary},
        },
    }


def test_writer_policy_smoke_passes_on_safe_payload() -> None:
    blocks_payload = {
        "blocks": [
            _block(
                "p1",
                chunk_type="practice",
                allowed_use=["writer_context", "practice_suggestion"],
                safety_flags=["not_for_direct_quote"],
                llm_summary="Бережная практика с мягким фокусом и паузами.",
                practice_low_resource_safe=False,
            ),
            _block(
                "l1",
                chunk_type="lens",
                allowed_use=["writer_context"],
                safety_flags=["not_for_direct_quote"],
                llm_summary="Внутренняя линза для самонаблюдения без директивности.",
            ),
        ]
    }
    smoke = build_writer_kb_policy_smoke(blocks_payload=blocks_payload)
    assert smoke["status"] == "ok"
    assert smoke["writer_kb_policy_passed"] is True
    assert smoke["snippet_midword_cut_count"] == 0


def test_writer_policy_smoke_flags_authority_reference() -> None:
    blocks_payload = {
        "blocks": [
            _block(
                "x1",
                chunk_type="lens",
                allowed_use=["writer_context"],
                safety_flags=["not_for_direct_quote"],
                llm_summary="Кузница доказывает, что только так правильно.",
            )
        ]
    }
    smoke = build_writer_kb_policy_smoke(blocks_payload=blocks_payload)
    assert smoke["status"] == "ok"
    assert smoke["writer_kb_policy_passed"] is False
    assert smoke["authority_reference_count"] >= 1
