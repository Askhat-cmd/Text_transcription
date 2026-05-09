from __future__ import annotations

import json
from pathlib import Path

import pytest

from knowledge_governance.enrichment_contracts import EnrichmentCandidate, LLMMetadata
from knowledge_governance.enrichment_validators import validate_candidate
from tools import kb_llm_enrichment
from tools.kb_llm_enrichment import _MockLLMClient, run_enrichment


def _mk_block(block_id: str, chunk_type: str, mixed_intent: str = "none") -> dict:
    return {
        "id": block_id,
        "text": (
            f"Длинный исходный фрагмент {block_id} с выраженным паттерном, который нельзя копировать дословно в summary. "
            "Текст описывает устойчивую эмоциональную реакцию, внутренний конфликт, телесные маркеры и возможный следующий шаг."
        ),
        "title": f"Раздел {block_id}",
        "summary": "",
        "source": "book:123__кузница_духа",
        "metadata": {
            "source_title": "Кузница Духа",
            "chapter_title": "Глава 1",
            "governance": {
                "chunk_type": chunk_type,
                "allowed_use": ["writer_context", "practice_suggestion"],
                "safety_flags": ["not_for_direct_quote", "practice_requires_low_resource_check"],
                "lens_family": ["self_criticism"],
            },
            "chunking_quality": {"mixed_intent_severity": mixed_intent},
        },
    }


def test_copy_like_summary_fails_direct_quote_guard() -> None:
    source_text = (
        "Это исходный фрагмент, который содержит длинную последовательность фразы для проверки риска прямого цитирования."
    )
    candidate = EnrichmentCandidate(
        block_id="b1",
        source_title="Кузница Духа",
        chunk_type_original="theory",
        allowed_use_original=["writer_context"],
        safety_flags_original=["not_for_direct_quote"],
        summary_candidate=source_text + " дополнительный хвост",
        lens_family_candidates=["meaning"],
        tags=["theory"],
        use_when=["когда нужно пояснение механизма"],
        avoid_when=["когда нужен кризисный протокол"],
        llm_metadata=LLMMetadata(),
    )
    result = validate_candidate(candidate=candidate, source_text=source_text)
    assert "summary_direct_quote_risk" in result.reasons


def test_paraphrased_summary_passes_direct_quote_guard() -> None:
    source_text = (
        "Исходный материал подробно описывает, как тревожная реакция закрепляется через автоматизм и повторяющуюся оценку себя."
    )
    candidate = EnrichmentCandidate(
        block_id="b2",
        source_title="Кузница Духа",
        chunk_type_original="theory",
        allowed_use_original=["writer_context"],
        safety_flags_original=["not_for_direct_quote"],
        summary_candidate=(
            "Фрагмент полезен для контекстной сборки: он помогает связать тревожный автоматизм с циклом самооценки и выбрать "
            "формат мягкого отражения паттерна в диалоге без дословного переноса исходной формулировки."
        ),
        lens_family_candidates=["meaning", "self_criticism"],
        tags=["theory", "meaning"],
        use_when=["когда нужен контекст механизма переживания"],
        avoid_when=["когда состояние остро нестабильно"],
        llm_metadata=LLMMetadata(),
    )
    result = validate_candidate(candidate=candidate, source_text=source_text)
    assert "summary_direct_quote_risk" not in result.reasons


def test_mock_summary_not_starting_with_source_text() -> None:
    source = (
        "Три причины, почему внутренний сценарий удерживается, связаны с ранним опытом, значимостью переживания и автоматичностью реакции."
    )
    context = {
        "chunk_type_original": "lens",
        "title": "Внутренний сценарий",
        "chapter_title": "Глава 2",
        "lens_family_current": ["self_criticism"],
        "mixed_intent_severity": "medium",
        "safety_flags_original": ["not_for_direct_quote"],
        "content_excerpt": source,
    }
    payload = _MockLLMClient().enrich(context)
    summary = str(payload.get("summary_candidate") or "")
    assert len(summary) >= 120
    assert summary[:80] not in source


def test_mock_calibration_batch_is_mostly_valid(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    blocks_path = tmp_path / "all_blocks_merged.json"
    blocks = []
    for chunk_type in ("case", "lens", "practice", "safety", "style", "theory"):
        for i in range(5):
            mixed = "medium" if i == 0 else "none"
            blocks.append(_mk_block(f"{chunk_type}-{i}", chunk_type, mixed))
    blocks_path.write_text(json.dumps({"blocks": blocks}, ensure_ascii=False), encoding="utf-8")

    monkeypatch.setattr(
        kb_llm_enrichment,
        "_evaluate_preflight",
        lambda: {"preflight_passed": True, "reasons": [], "observed": {}},
    )

    prompt_path = Path("Bot_data_base/knowledge_governance/prompts/kb_enrichment_v1_1.md")
    result = run_enrichment(
        run_tag="PRD-046.0.5-RUN1-HF2",
        source_hint="123__",
        blocks_path=blocks_path,
        output_dir=tmp_path / "logs",
        reports_dir=tmp_path / "reports",
        prompt_path=prompt_path,
        limit=30,
        offset=0,
        chunk_type_filter="",
        dry_run=True,
        write_overlay=False,
        apply_changes=False,
        confirm=False,
        mock_llm=True,
        require_real_llm=False,
        allow_promotion_candidate=False,
        overlay_path=None,
        max_concurrency=1,
        max_retries=2,
        timeout_seconds=10.0,
    )
    assert result["status"] == "done"
    assert result["validation_failed"] <= 6
