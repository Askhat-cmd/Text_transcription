from bot_agent.config import config
from bot_agent.fast_detector import detect_user_state


def _snapshot():
    keys = [
        "FREE_CONVERSATION_MODE",
        "FAST_DETECTOR_ENABLED",
        "FAST_DETECTOR_CONFIDENCE_THRESHOLD",
        "STATE_CLASSIFIER_ENABLED",
        "STATE_CLASSIFIER_CONFIDENCE_THRESHOLD",
        "SD_CLASSIFIER_ENABLED",
        "SD_CLASSIFIER_CONFIDENCE_THRESHOLD",
        "PROMPT_SD_OVERRIDES_BASE",
        "PROMPT_MODE_OVERRIDES_SD",
        "MAX_TOKENS_SOFT_CAP",
    ]
    return {k: getattr(config, k) for k in keys}


def _restore(snapshot):
    for key, value in snapshot.items():
        setattr(config, key, value)


def test_fast_detector_disabled_returns_none():
    snapshot = _snapshot()
    try:
        config.FAST_DETECTOR_ENABLED = False
        result = detect_user_state("Мне страшно умереть, не могу дышать")
        assert result is None
    finally:
        _restore(snapshot)


def test_fast_detector_low_confidence_returns_none():
    snapshot = _snapshot()
    try:
        config.FAST_DETECTOR_ENABLED = True
        config.FAST_DETECTOR_CONFIDENCE_THRESHOLD = 0.99
        result = detect_user_state("Мне страшно умереть, не могу дышать")
        assert result is None
    finally:
        _restore(snapshot)


def test_free_mode_toggle_immediate():
    snapshot = _snapshot()
    try:
        config.FREE_CONVERSATION_MODE = False
        assert config.FREE_CONVERSATION_MODE is False
        config.FREE_CONVERSATION_MODE = True
        assert config.FREE_CONVERSATION_MODE is True
    finally:
        _restore(snapshot)


def test_all_routing_params_have_defaults():
    assert isinstance(config.FAST_DETECTOR_ENABLED, bool)
    assert isinstance(config.FAST_DETECTOR_CONFIDENCE_THRESHOLD, float)
    assert isinstance(config.STATE_CLASSIFIER_ENABLED, bool)
    assert isinstance(config.STATE_CLASSIFIER_CONFIDENCE_THRESHOLD, float)
    assert isinstance(config.SD_CLASSIFIER_ENABLED, bool)
    assert isinstance(config.SD_CLASSIFIER_CONFIDENCE_THRESHOLD, float)
    assert isinstance(config.PROMPT_SD_OVERRIDES_BASE, bool)
    assert isinstance(config.PROMPT_MODE_OVERRIDES_SD, bool)
    assert isinstance(config.FREE_CONVERSATION_MODE, bool)
    assert isinstance(config.MAX_TOKENS_SOFT_CAP, int)
