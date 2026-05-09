from __future__ import annotations

import pytest
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from bot_agent.config import config
from bot_agent.multiagent.turn_summary_service import (
    build_pending_turn_summary_record,
    compute_turn_source_hash,
    generate_turn_llm_summary_v1,
)


def test_turn_source_hash_is_stable_for_whitespace_variants() -> None:
    left = compute_turn_source_hash("  привет   мир ", " ответ  ")
    right = compute_turn_source_hash("привет мир", "ответ")
    assert left == right


def test_build_pending_record_has_required_fields() -> None:
    record = build_pending_turn_summary_record(
        user_input="u",
        assistant_response="a",
        provider="mock",
        model="gpt-4o-mini",
    )
    payload = record.to_dict()
    assert payload["status"] == "pending"
    assert payload["summary_version"] == "turn_llm_summary_v1"
    assert payload["summary_method"] == "llm_abstractive_v1"
    assert payload["source_hash"]
    assert payload["created_at"]


@pytest.mark.asyncio
async def test_generate_turn_llm_summary_mock_provider_ready(monkeypatch) -> None:
    monkeypatch.setattr(config, "TURN_LLM_SUMMARY_MAX_SUMMARY_CHARS", 700)
    result = await generate_turn_llm_summary_v1(
        user_input="Мне тревожно и сложно начать разговор.",
        assistant_response="Давай выберем один самый маленький шаг.",
        provider="mock",
        model="gpt-4o-mini",
    )
    assert result.status == "ready"
    assert result.summary
    assert result.summary_version == "turn_llm_summary_v1"


@pytest.mark.asyncio
async def test_generate_turn_llm_summary_disabled_provider_returns_disabled() -> None:
    result = await generate_turn_llm_summary_v1(
        user_input="u",
        assistant_response="a",
        provider="disabled",
        model="gpt-4o-mini",
    )
    assert result.status == "disabled"


@pytest.mark.asyncio
async def test_generate_turn_llm_summary_unknown_provider_fails() -> None:
    result = await generate_turn_llm_summary_v1(
        user_input="u",
        assistant_response="a",
        provider="strange",
        model="gpt-4o-mini",
    )
    assert result.status == "failed"
    assert "unsupported_provider" in str(result.error or "")
