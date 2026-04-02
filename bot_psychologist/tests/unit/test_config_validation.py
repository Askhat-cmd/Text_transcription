from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.config_validation import assert_runtime_config, validate_runtime_config


def _cfg(**overrides):
    base = {
        "TOP_K_BLOCKS": 7,
        "MIN_RELEVANCE_SCORE": 0.1,
        "VOYAGE_TOP_K": 5,
        "MAX_CONTEXT_SIZE": 2200,
        "LLM_MODEL": "gpt-5-mini",
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_validate_runtime_config_ok() -> None:
    result = validate_runtime_config(_cfg())
    assert result.valid is True
    assert result.errors == []


def test_validate_runtime_config_collects_errors() -> None:
    result = validate_runtime_config(
        _cfg(
            TOP_K_BLOCKS=0,
            MIN_RELEVANCE_SCORE=1.2,
            VOYAGE_TOP_K=0,
            MAX_CONTEXT_SIZE=100,
            LLM_MODEL="",
        )
    )
    assert result.valid is False
    assert "TOP_K_BLOCKS:range_1_20" in result.errors
    assert "MIN_RELEVANCE_SCORE:range_0_1" in result.errors
    assert "VOYAGE_TOP_K:min_1" in result.errors
    assert "MAX_CONTEXT_SIZE:min_500" in result.errors
    assert "LLM_MODEL:required" in result.errors


def test_assert_runtime_config_raises_on_invalid() -> None:
    with pytest.raises(RuntimeError):
        assert_runtime_config(_cfg(TOP_K_BLOCKS=100))
