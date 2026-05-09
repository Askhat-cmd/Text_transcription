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
        title="Практика заземления",
        text="Цель: снизить тревогу. Время: 5 минут. Шаг 1: медленный выдох. Шаг 2: опора в теле.",
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

