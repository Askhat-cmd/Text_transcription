from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from bot_agent.multiagent.writer_kb_payload import (
    WRITER_KB_PAYLOAD_VERSION,
    WriterKbPayloadConfig,
    build_writer_kb_payload,
    build_writer_kb_payload_trace,
)


def _config(**overrides: object) -> WriterKbPayloadConfig:
    base = WriterKbPayloadConfig(
        enabled=True,
        max_chunks=2,
        max_total_chars=3600,
        excerpt_target_chars=1200,
        excerpt_max_chars=1600,
        sentence_boundary=True,
        use_overlay_metadata=False,
    )
    return WriterKbPayloadConfig(**{**base.__dict__, **overrides})


def test_builder_returns_contract_v1_and_metadata_fields() -> None:
    payload = build_writer_kb_payload(
        semantic_hits=[],
        rag_for_writer=[
            {
                "chunk_id": "c1",
                "source": "123__kuznica_duha",
                "content": "Нейросталкинг помогает замечать триггеры и привычные реакции.",
                "chunking_quality": {"chunk_type": "concept"},
            }
        ],
        overlay_items=None,
        config=_config(),
    )

    assert payload["schema_version"] == WRITER_KB_PAYLOAD_VERSION
    assert payload["enabled"] is True
    assert payload["chunk_count"] == 1
    chunk = payload["chunks"][0]
    assert chunk["chunk_id"] == "c1"
    assert chunk["source_id"] == "123__kuznica_duha"
    assert chunk["chunk_type"] == "concept"
    assert chunk["writer_instruction"]
    assert chunk["quote_policy"] == "paraphrase_only"


def test_short_content_is_not_truncated() -> None:
    content = "Короткий чанк. Он целиком должен дойти до Writer."
    payload = build_writer_kb_payload(
        semantic_hits=[],
        rag_for_writer=[{"chunk_id": "c1", "source": "doc", "content": content}],
        overlay_items=None,
        config=_config(excerpt_max_chars=300),
    )

    chunk = payload["chunks"][0]
    assert chunk["content_excerpt"] == content
    assert chunk["content_truncated"] is False
    assert chunk["truncation_strategy"] == "none"
    assert chunk["original_char_count"] == len(content)
    assert chunk["sent_char_count"] == len(content)


def test_long_content_truncates_at_boundary_without_mid_sentence_cut() -> None:
    content = (
        "Нейросталкинг — это наблюдение за паттернами, триггерами и автоматическими реакциями. "
        "Он нужен не для самокритики, а для возвращения себе выбора.\n\n"
        "Второй абзац поясняет, как видеть цепочку триггер -> тело -> мысль -> действие. "
        "Третий абзац уже выходит за бюджет и не должен обрываться на полуслове."
    )
    payload = build_writer_kb_payload(
        semantic_hits=[],
        rag_for_writer=[{"chunk_id": "c1", "source": "doc", "content": content}],
        overlay_items=None,
        config=_config(excerpt_target_chars=140, excerpt_max_chars=180),
    )

    chunk = payload["chunks"][0]
    assert chunk["content_truncated"] is True
    assert chunk["truncation_strategy"] in {
        "paragraph_then_sentence_boundary",
        "sentence_boundary",
    }
    assert chunk["truncated_mid_sentence"] is False
    assert chunk["content_excerpt"].endswith((".", "!", "?", "…"))


def test_neurostalking_regression_has_no_blind_mid_cut() -> None:
    content = (
        "**Нейросталкинг** — это работа с первым этажом наблюдения: "
        "триггеры, внутренние толчки, телесные реакции, автоматические мысли и повторяющиеся ходы.\n\n"
        "**НеоСталкинг** — это второй этаж, где человек уже видит конфигурацию своих механизмов "
        "и может выбирать более точный ответ вместо автопилота."
    )
    payload = build_writer_kb_payload(
        semantic_hits=[],
        rag_for_writer=[{"chunk_id": "c1", "source": "doc", "content": content}],
        overlay_items=None,
        config=_config(excerpt_target_chars=150, excerpt_max_chars=220),
    )

    chunk = payload["chunks"][0]
    assert "**НеоСталкинг** — это в" not in chunk["content_excerpt"]
    assert chunk["truncated_mid_sentence"] is False


def test_payload_respects_max_chunks_and_total_chars() -> None:
    content = "Первое полное предложение. Второе полное предложение. Третье полное предложение."
    payload = build_writer_kb_payload(
        semantic_hits=[],
        rag_for_writer=[
            {"chunk_id": "c1", "source": "doc", "content": content},
            {"chunk_id": "c2", "source": "doc", "content": content},
            {"chunk_id": "c3", "source": "doc", "content": content},
        ],
        overlay_items=None,
        config=_config(max_chunks=2, max_total_chars=120, excerpt_target_chars=80, excerpt_max_chars=90),
    )

    assert payload["chunk_count"] <= 2
    assert payload["total_sent_char_count"] <= 120


def test_overlay_metadata_is_not_used_by_default_and_only_enriches_when_enabled() -> None:
    hit = {"chunk_id": "c1", "source": "doc", "content": "Текст для Writer."}
    overlay = [{"chunk_id": "c1", "chunk_type": "mechanism", "mechanism_hints": ["control_as_safety"]}]

    disabled_payload = build_writer_kb_payload(
        semantic_hits=[],
        rag_for_writer=[hit],
        overlay_items=overlay,
        config=_config(use_overlay_metadata=False),
    )
    enabled_payload = build_writer_kb_payload(
        semantic_hits=[],
        rag_for_writer=[hit],
        overlay_items=overlay,
        config=_config(use_overlay_metadata=True),
    )

    assert disabled_payload["chunks"][0]["overlay_metadata_used"] is False
    assert disabled_payload["chunks"][0]["mechanism_hints"] == []
    assert enabled_payload["chunks"][0]["overlay_metadata_used"] is True
    assert enabled_payload["chunks"][0]["mechanism_hints"] == ["control_as_safety"]


def test_internal_only_quote_policy_suppresses_excerpt_like_dump() -> None:
    payload = build_writer_kb_payload(
        semantic_hits=[],
        rag_for_writer=[
            {
                "chunk_id": "c1",
                "source": "doc",
                "content": "Секретный длинный источник, который нельзя отдавать как цитату.",
                "governance": {"allowed_use": ["internal_only"], "quote_policy": "internal_only"},
            }
        ],
        overlay_items=None,
        config=_config(),
    )

    chunk = payload["chunks"][0]
    assert chunk["quote_policy"] == "internal_only"
    assert chunk["content_excerpt"] == ""
    trace = build_writer_kb_payload_trace(payload=payload, input_rag_for_writer_count=1)
    assert "internal_only_quote_policy_detected" in trace["warnings"]
