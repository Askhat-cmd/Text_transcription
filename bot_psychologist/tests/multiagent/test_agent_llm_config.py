"""Unit tests for per-agent LLM model registry."""

import pytest

from bot_agent.multiagent.agents.agent_llm_config import (
    ALLOWED_MODELS,
    _AGENT_MODEL_OVERRIDES,
    get_all_agent_models,
    get_model_for_agent,
    reset_model_for_agent,
    set_model_for_agent,
)


@pytest.fixture(autouse=True)
def clear_overrides():
    _AGENT_MODEL_OVERRIDES.clear()
    yield
    _AGENT_MODEL_OVERRIDES.clear()


def test_default_state_analyzer_model():
    assert get_model_for_agent("state_analyzer") == "gpt-5-nano"


def test_default_thread_manager_model():
    assert get_model_for_agent("thread_manager") == "gpt-5-nano"


def test_default_writer_model():
    assert get_model_for_agent("writer") == "gpt-5-mini"


def test_set_override_model():
    set_model_for_agent("writer", "gpt-5")
    assert get_model_for_agent("writer") == "gpt-5"


def test_override_does_not_affect_other_agents():
    set_model_for_agent("writer", "gpt-5")
    assert get_model_for_agent("state_analyzer") == "gpt-5-nano"
    assert get_model_for_agent("thread_manager") == "gpt-5-nano"


def test_reset_override_restores_default():
    set_model_for_agent("writer", "gpt-5")
    reset_model_for_agent("writer")
    assert get_model_for_agent("writer") == "gpt-5-mini"


def test_reset_without_override_is_noop():
    reset_model_for_agent("writer")
    assert get_model_for_agent("writer") == "gpt-5-mini"


def test_invalid_model_raises_value_error():
    with pytest.raises(ValueError, match="not allowed"):
        set_model_for_agent("writer", "claude-3-opus")


def test_unknown_agent_set_raises_value_error():
    with pytest.raises(ValueError, match="Unknown agent_id"):
        set_model_for_agent("nonexistent_agent", "gpt-5-nano")


def test_unknown_agent_reset_raises_value_error():
    with pytest.raises(ValueError, match="Unknown agent_id"):
        reset_model_for_agent("nonexistent_agent")


def test_allowed_models_from_config():
    from bot_agent.config import Config

    assert set(ALLOWED_MODELS) == set(Config.SUPPORTED_MODELS)


def test_get_all_snapshot():
    set_model_for_agent("writer", "gpt-4.1")
    result = get_all_agent_models()
    assert set(result.keys()) == {"state_analyzer", "thread_manager", "writer"}
    assert result["writer"]["model"] == "gpt-4.1"
    assert result["writer"]["default_model"] == "gpt-5-mini"
    assert result["writer"]["is_overridden"] is True
    assert result["state_analyzer"]["is_overridden"] is False
