"""Per-agent LLM model registry for multiagent runtime."""

from __future__ import annotations

import threading

from ...config import Config

ALLOWED_MODELS: tuple[str, ...] = Config.SUPPORTED_MODELS

_AGENT_MODEL_DEFAULTS: dict[str, str] = {
    "state_analyzer": "gpt-5-nano",
    "thread_manager": "gpt-5-nano",
    "writer": "gpt-5-mini",
}

_AGENT_MODEL_OVERRIDES: dict[str, str] = {}
_AGENT_TEMPERATURE_DEFAULTS: dict[str, float] = {
    "state_analyzer": 0.1,
    "thread_manager": 0.2,
    "writer": 0.7,
}
_AGENT_TEMPERATURE_OVERRIDES: dict[str, float] = {}
_lock = threading.Lock()


def get_model_for_agent(agent_id: str) -> str:
    """Return active model for agent: override -> default -> Config.LLM_MODEL."""
    with _lock:
        if agent_id in _AGENT_MODEL_OVERRIDES:
            return _AGENT_MODEL_OVERRIDES[agent_id]
    return _AGENT_MODEL_DEFAULTS.get(agent_id, Config.LLM_MODEL)


def get_temperature_for_agent(agent_id: str) -> float:
    """Return active temperature for agent: override -> default -> 0.7."""
    with _lock:
        if agent_id in _AGENT_TEMPERATURE_OVERRIDES:
            return _AGENT_TEMPERATURE_OVERRIDES[agent_id]
    return _AGENT_TEMPERATURE_DEFAULTS.get(agent_id, 0.7)


def set_model_for_agent(agent_id: str, model: str) -> None:
    """Set model override for known agent and allowed model."""
    if model not in ALLOWED_MODELS:
        raise ValueError(
            f"Model '{model}' is not allowed. Allowed: {list(ALLOWED_MODELS)}"
        )
    if agent_id not in _AGENT_MODEL_DEFAULTS:
        raise ValueError(
            f"Unknown agent_id '{agent_id}'. Valid agents: {sorted(_AGENT_MODEL_DEFAULTS)}"
        )
    with _lock:
        _AGENT_MODEL_OVERRIDES[agent_id] = model


def set_temperature_for_agent(agent_id: str, temperature: float) -> None:
    """Set temperature override for known agent."""
    if agent_id not in _AGENT_TEMPERATURE_DEFAULTS:
        raise ValueError(
            f"Unknown agent_id '{agent_id}'. Valid agents: {sorted(_AGENT_TEMPERATURE_DEFAULTS)}"
        )
    if not (0.0 <= float(temperature) <= 2.0):
        raise ValueError(f"temperature must be in [0.0, 2.0], got {temperature}")
    with _lock:
        _AGENT_TEMPERATURE_OVERRIDES[agent_id] = float(temperature)


def reset_model_for_agent(agent_id: str) -> None:
    """Reset override for agent to return to default."""
    if agent_id not in _AGENT_MODEL_DEFAULTS:
        raise ValueError(
            f"Unknown agent_id '{agent_id}'. Valid agents: {sorted(_AGENT_MODEL_DEFAULTS)}"
        )
    with _lock:
        _AGENT_MODEL_OVERRIDES.pop(agent_id, None)


def reset_temperature_for_agent(agent_id: str) -> None:
    """Reset temperature override for agent to return to default."""
    if agent_id not in _AGENT_TEMPERATURE_DEFAULTS:
        raise ValueError(
            f"Unknown agent_id '{agent_id}'. Valid agents: {sorted(_AGENT_TEMPERATURE_DEFAULTS)}"
        )
    with _lock:
        _AGENT_TEMPERATURE_OVERRIDES.pop(agent_id, None)


def get_all_agent_models() -> dict[str, dict[str, object]]:
    """Return complete snapshot for admin API."""
    with _lock:
        overrides = dict(_AGENT_MODEL_OVERRIDES)

    result: dict[str, dict[str, object]] = {}
    for agent_id, default_model in _AGENT_MODEL_DEFAULTS.items():
        active = overrides.get(agent_id, default_model)
        default_temperature = _AGENT_TEMPERATURE_DEFAULTS.get(agent_id, 0.7)
        active_temperature = _AGENT_TEMPERATURE_OVERRIDES.get(agent_id, default_temperature)
        result[agent_id] = {
            "model": active,
            "default_model": default_model,
            "is_overridden": agent_id in overrides,
            "temperature": active_temperature,
            "default_temperature": default_temperature,
            "is_temperature_overridden": agent_id in _AGENT_TEMPERATURE_OVERRIDES,
        }
    return result
