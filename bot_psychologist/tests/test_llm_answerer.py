from bot_agent.config import config
from bot_agent.llm_answerer import LLMAnswerer


def _restore_runtime_values(snapshot):
    for key, value in snapshot.items():
        setattr(config, key, value)


def _snapshot_runtime_values():
    return {
        "FREE_CONVERSATION_MODE": getattr(config, "FREE_CONVERSATION_MODE", False),
        "MAX_TOKENS": getattr(config, "MAX_TOKENS", None),
        "MAX_TOKENS_SOFT_CAP": getattr(config, "MAX_TOKENS_SOFT_CAP", 8192),
        "LLM_TEMPERATURE": getattr(config, "LLM_TEMPERATURE", 0.7),
        "LLM_MODEL": getattr(config, "LLM_MODEL", "gpt-5-mini"),
        "ENABLE_STREAMING": getattr(config, "ENABLE_STREAMING", True),
    }


def _build_answerer():
    # _build_api_params не требует инициализированный OpenAI клиент.
    return LLMAnswerer()


def test_free_mode_uses_soft_cap():
    snapshot = _snapshot_runtime_values()
    try:
        config.FREE_CONVERSATION_MODE = True
        config.MAX_TOKENS = None
        config.MAX_TOKENS_SOFT_CAP = 8192
        params = _build_answerer()._build_api_params([], model="gpt-4o")
        assert params.get("max_tokens") == 8192
    finally:
        _restore_runtime_values(snapshot)


def test_free_mode_ignores_explicit_max_tokens():
    snapshot = _snapshot_runtime_values()
    try:
        config.FREE_CONVERSATION_MODE = True
        config.MAX_TOKENS = 2000
        config.MAX_TOKENS_SOFT_CAP = 4096
        params = _build_answerer()._build_api_params([], model="gpt-4o", max_tokens=2000)
        assert params.get("max_tokens") == 4096
        assert params.get("max_tokens") != 2000
    finally:
        _restore_runtime_values(snapshot)


def test_normal_mode_null_tokens_no_param():
    snapshot = _snapshot_runtime_values()
    try:
        config.FREE_CONVERSATION_MODE = False
        config.MAX_TOKENS = None
        params = _build_answerer()._build_api_params([], model="gpt-4o")
        assert "max_tokens" not in params
    finally:
        _restore_runtime_values(snapshot)


def test_normal_mode_explicit_tokens_applied():
    snapshot = _snapshot_runtime_values()
    try:
        config.FREE_CONVERSATION_MODE = False
        config.MAX_TOKENS = None
        params = _build_answerer()._build_api_params([], model="gpt-4o", max_tokens=2000)
        assert params.get("max_tokens") == 2000
    finally:
        _restore_runtime_values(snapshot)


def test_soft_cap_configurable():
    snapshot = _snapshot_runtime_values()
    try:
        config.FREE_CONVERSATION_MODE = True
        config.MAX_TOKENS_SOFT_CAP = 4096
        params = _build_answerer()._build_api_params([], model="gpt-4o")
        assert params.get("max_tokens") == 4096
    finally:
        _restore_runtime_values(snapshot)


def test_temperature_skipped_for_reasoning_model():
    snapshot = _snapshot_runtime_values()
    try:
        config.FREE_CONVERSATION_MODE = False
        params = _build_answerer()._build_api_params([], model="gpt-5-mini")
        assert "temperature" not in params
    finally:
        _restore_runtime_values(snapshot)


def test_temperature_present_for_standard_model():
    snapshot = _snapshot_runtime_values()
    try:
        config.FREE_CONVERSATION_MODE = False
        config.LLM_TEMPERATURE = 0.8
        params = _build_answerer()._build_api_params([], model="gpt-4o")
        assert params.get("temperature") == 0.8
    finally:
        _restore_runtime_values(snapshot)


def test_streaming_flag_adds_stream_param():
    snapshot = _snapshot_runtime_values()
    try:
        params = _build_answerer()._build_api_params([], model="gpt-4o", stream=True)
        assert params.get("stream") is True
    finally:
        _restore_runtime_values(snapshot)
