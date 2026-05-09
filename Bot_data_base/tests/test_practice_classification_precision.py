from tools.source_reprocess import _backfill_block


def _mk_block(*, block_id: str, title: str, text: str) -> dict:
    return {
        "id": block_id,
        "text": text,
        "title": title,
        "summary": "",
        "sd_level": "GREEN",
        "sd_confidence": 0.7,
        "complexity": 0.4,
        "source": "book:123__кузница_духа",
        "metadata": {
            "author": "Author",
            "author_id": "123",
            "source_title": "Кузница Духа",
            "language": "ru",
            "source_type": "book",
            "chapter_title": "Глава 1",
            "chunk_index": 0,
        },
    }


def test_true_practice_keeps_practice_with_suggestion() -> None:
    raw = _mk_block(
        block_id="p1",
        title="\u041f\u0440\u0430\u043a\u0442\u0438\u043a\u0430 \u0437\u0430\u0437\u0435\u043c\u043b\u0435\u043d\u0438\u044f",
        text=(
            "\u0426\u0435\u043b\u044c: \u0441\u043d\u0438\u0437\u0438\u0442\u044c \u0442\u0440\u0435\u0432\u043e\u0433\u0443.\n"
            "\u0412\u0440\u0435\u043c\u044f: 5 \u043c\u0438\u043d\u0443\u0442.\n"
            "\u0428\u0430\u0433 1: \u043d\u0430\u0437\u043e\u0432\u0438 5 \u043f\u0440\u0435\u0434\u043c\u0435\u0442\u043e\u0432.\n"
            "\u0428\u0430\u0433 2: \u043f\u043e\u0447\u0443\u0432\u0441\u0442\u0432\u0443\u0439 \u043e\u043f\u043e\u0440\u0443 \u0441\u0442\u043e\u043f.\n"
            "\u041f\u043e\u0441\u043b\u0435 \u0432\u044b\u043f\u043e\u043b\u043d\u0435\u043d\u0438\u044f \u043e\u0442\u043c\u0435\u0442\u044c, \u0447\u0442\u043e \u0438\u0437\u043c\u0435\u043d\u0438\u043b\u043e\u0441\u044c."
        ),
    )
    updated, signal = _backfill_block(raw, force_reclassify=True)
    gov = updated["metadata"]["governance"]
    assert gov["chunk_type"] == "practice"
    assert "practice_suggestion" in gov["allowed_use"]
    assert signal["decision_reason"] == "self_contained_practice"


def test_theory_with_numbered_list_is_not_practice() -> None:
    raw = _mk_block(
        block_id="t1",
        title="\u041f\u043e\u0447\u0435\u043c\u0443 \u043f\u0440\u043e\u0433\u0440\u0430\u043c\u043c\u0430 \u0434\u0435\u0440\u0436\u0438\u0442\u0441\u044f",
        text=(
            "\u0422\u0440\u0438 \u043f\u0440\u0438\u0447\u0438\u043d\u044b, \u043f\u043e \u043a\u043e\u0442\u043e\u0440\u044b\u043c \u043f\u0430\u0442\u0442\u0435\u0440\u043d \u0437\u0430\u043a\u0440\u0435\u043f\u043b\u044f\u0435\u0442\u0441\u044f:\n"
            "1. \u043d\u0435\u0439\u0440\u043e\u043f\u043b\u0430\u0441\u0442\u0438\u0447\u043d\u043e\u0441\u0442\u044c\n"
            "2. \u0441\u0442\u0440\u0430\u0445 \u043e\u0442\u0432\u0435\u0440\u0436\u0435\u043d\u0438\u044f\n"
            "3. \u0438\u0437\u0431\u0435\u0433\u0430\u043d\u0438\u0435"
        ),
    )
    updated, _signal = _backfill_block(raw, force_reclassify=True)
    assert updated["metadata"]["governance"]["chunk_type"] in {"lens", "theory"}
    assert "practice_suggestion" not in updated["metadata"]["governance"]["allowed_use"]


def test_qa_fragment_is_not_practice() -> None:
    raw = _mk_block(
        block_id="q1",
        title="Q&A",
        text="\u2014 \u042f \u0436\u0438\u0432\u0443 \u0432 \u0441\u0442\u0440\u0435\u0441\u0441\u0435. \u041a\u0430\u043a \u043f\u0435\u0440\u0435\u0439\u0442\u0438 \u0432 \u0440\u0435\u0441\u0443\u0440\u0441? \n\u2014 \u041d\u0435\u043b\u044c\u0437\u044f \u043d\u0430\u043f\u0440\u044f\u043c\u0438\u043a, \u0441\u043d\u0430\u0447\u0430\u043b\u0430 \u043f\u043e\u043d\u044f\u0442\u044c \u043c\u0435\u0445\u0430\u043d\u0438\u0437\u043c.",
    )
    updated, _signal = _backfill_block(raw, force_reclassify=True)
    assert updated["metadata"]["governance"]["chunk_type"] in {"lens", "case"}
    assert "practice_suggestion" not in updated["metadata"]["governance"]["allowed_use"]


def test_session_case_is_not_practice() -> None:
    raw = _mk_block(
        block_id="c1",
        title="\u0418\u0437 \u0441\u0435\u0441\u0441\u0438\u0438",
        text="\u0418\u0437 \u0441\u0435\u0441\u0441\u0438\u0438: \u043a\u043b\u0438\u0435\u043d\u0442, 44 \u0433\u043e\u0434\u0430, \u043e\u043f\u0438\u0441\u044b\u0432\u0430\u0435\u0442 \u0446\u0438\u043a\u043b \u0438\u0437\u0431\u0435\u0433\u0430\u043d\u0438\u044f \u0438 \u0441\u0442\u044b\u0434\u0430.",
    )
    updated, _signal = _backfill_block(raw, force_reclassify=True)
    assert updated["metadata"]["governance"]["chunk_type"] == "case"
    assert "practice_suggestion" not in updated["metadata"]["governance"]["allowed_use"]


def test_noise_chunk_not_practice_and_internal_only() -> None:
    raw = _mk_block(block_id="n1", title="***", text="***")
    updated, _signal = _backfill_block(raw, force_reclassify=True)
    gov = updated["metadata"]["governance"]
    assert gov["chunk_type"] == "style"
    assert "internal_only" in gov["allowed_use"]
    assert "do_not_use" in gov["safety_flags"]
    assert "practice_suggestion" not in gov["allowed_use"]


def test_long_complete_practice_marks_low_resource_not_p0_trigger_only() -> None:
    raw = _mk_block(
        block_id="lp1",
        title="\u041f\u0440\u0430\u043a\u0442\u0438\u043a\u0430 \u0433\u043b\u0443\u0431\u043e\u043a\u043e\u0433\u043e \u043a\u043e\u043d\u0442\u0430\u043a\u0442\u0430",
        text=(
            "\u0426\u0435\u043b\u044c: \u0440\u0430\u0441\u0448\u0438\u0440\u0438\u0442\u044c \u043a\u043e\u043d\u0442\u0430\u043a\u0442 \u0441 \u0447\u0443\u0432\u0441\u0442\u0432\u0430\u043c\u0438.\n"
            "\u0412\u0440\u0435\u043c\u044f: 30 \u043c\u0438\u043d\u0443\u0442.\n"
            "\u0428\u0430\u0433 1: \u0441\u044f\u0434\u044c \u0438 \u0437\u0430\u043a\u0440\u043e\u0439 \u0433\u043b\u0430\u0437\u0430.\n"
            "\u0428\u0430\u0433 2: \u043d\u0430\u0437\u043e\u0432\u0438 \u0447\u0443\u0432\u0441\u0442\u0432\u0430.\n"
            "\u0428\u0430\u0433 3: \u0437\u0430\u043f\u0438\u0448\u0438 \u0432\u044b\u0432\u043e\u0434.\n"
            "\u041f\u043e\u0441\u043b\u0435 \u0432\u044b\u043f\u043e\u043b\u043d\u0435\u043d\u0438\u044f \u043e\u0442\u043c\u0435\u0442\u044c \u0438\u0437\u043c\u0435\u043d\u0435\u043d\u0438\u044f."
        ),
    )
    updated, signal = _backfill_block(raw, force_reclassify=True)
    gov = updated["metadata"]["governance"]
    assert gov["chunk_type"] == "practice"
    assert gov["practice_metadata"]["low_resource_safe"] is False
    assert "practice_requires_low_resource_check" in gov["safety_flags"]
    assert "long_practice_requires_review" in signal["needs_manual_review_reasons"]


def test_classification_trace_added() -> None:
    raw = _mk_block(
        block_id="tr1",
        title="\u041f\u0440\u0430\u043a\u0442\u0438\u043a\u0430",
        text="\u0426\u0435\u043b\u044c: \u0442\u0435\u0441\u0442. \u0412\u0440\u0435\u043c\u044f: 5 \u043c\u0438\u043d\u0443\u0442. \u0428\u0430\u0433 1: \u0441\u0434\u0435\u043b\u0430\u0439 \u043f\u0430\u0443\u0437\u0443.",
    )
    updated, _signal = _backfill_block(raw, force_reclassify=True)
    trace = (updated.get("metadata") or {}).get("chunking_quality", {}).get("classification_trace_v1")
    assert isinstance(trace, dict)
    assert trace.get("version") == "chunk_classification_trace_v1"
