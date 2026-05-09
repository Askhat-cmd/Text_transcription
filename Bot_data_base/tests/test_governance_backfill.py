from tools.source_reprocess import _backfill_block


def _mk_raw_block(*, block_id: str, text: str, title: str, role_hint: str = "") -> dict:
    return {
        "id": block_id,
        "text": text,
        "title": title,
        "summary": "",
        "sd_level": "GREEN",
        "sd_confidence": 0.5,
        "complexity": 0.5,
        "source": "book:123__кузница_духа",
        "metadata": {
            "author": "Author",
            "author_id": "123",
            "source_title": "Кузница Духа",
            "language": "ru",
            "source_type": "book",
            "chapter_title": "Глава 1",
            "chunk_index": 0,
            "section_role_hint": role_hint,
        },
    }


def test_backfill_adds_required_governance_fields_and_summary() -> None:
    raw = _mk_raw_block(
        block_id="p1",
        title="\u041f\u0440\u0430\u043a\u0442\u0438\u043a\u0430 \u0437\u0430\u0437\u0435\u043c\u043b\u0435\u043d\u0438\u044f",
        text="\u0426\u0435\u043b\u044c: \u0441\u043d\u0438\u0437\u0438\u0442\u044c \u0442\u0440\u0435\u0432\u043e\u0433\u0443. \u0412\u0440\u0435\u043c\u044f: 5 \u043c\u0438\u043d\u0443\u0442. \u0428\u0430\u0433 1: \u043c\u0435\u0434\u043b\u0435\u043d\u043d\u044b\u0439 \u0432\u044b\u0434\u043e\u0445. \u0428\u0430\u0433 2: \u043e\u043f\u043e\u0440\u0430 \u0432 \u0442\u0435\u043b\u0435.",
        role_hint="practice",
    )
    updated, _signal = _backfill_block(raw)
    md = updated["metadata"]
    gov = md["governance"]

    assert gov["schema_version"] == "governance_v1"
    assert gov["source_profile"] == "practice_manual"
    assert gov["chunk_type"] == "practice"
    assert "practice_suggestion" in gov["allowed_use"]
    assert "not_for_direct_quote" in gov["safety_flags"]
    assert isinstance(md["heading_path"], list) and md["heading_path"]
    assert md["boundary_confidence"] > 0
    assert md["split_reason"]
    assert md["parent_section_id"]
    assert updated["summary"]
    assert len(updated["summary"]) <= 240


def test_backfill_practice_suggestion_only_for_practice_chunks() -> None:
    raw = _mk_raw_block(
        block_id="t1",
        title="Теоретический фрагмент",
        text="Почему избегание усиливает стыд и прокрастинацию.",
        role_hint="theory",
    )
    updated, _signal = _backfill_block(raw)
    allowed = updated["metadata"]["governance"]["allowed_use"]
    assert "practice_suggestion" not in allowed
