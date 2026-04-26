"""Feature flags for PRD modernization phases."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict

from dotenv import load_dotenv

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(_PROJECT_ROOT / ".env")


_DEFAULTS: Dict[str, bool] = {
    # PRD 11.0 Wave 1 (Soft Freeze): Neo runtime is default.
    "NEO_MINDBOT_ENABLED": True,
    "LEGACY_PIPELINE_ENABLED": False,
    # Compatibility runtime switch.
    "DISABLE_USER_LEVEL_ADAPTER": True,
    # Explicit migration flag.
    "USER_LEVEL_ADAPTER_ENABLED": False,
    "PRE_ROUTING_ENABLED": False,
    # Neo runtime feature flags.
    "USE_NEW_DIAGNOSTICS_V1": True,
    "USE_DETERMINISTIC_ROUTE_RESOLVER": True,
    "USE_PROMPT_STACK_V2": True,
    "USE_OUTPUT_VALIDATION": True,
    "INFORMATIONAL_BRANCH_ENABLED": True,
    # Phase 1
    "ENABLE_EMBEDDING_PROVIDER": True,
    # Phase 2
    "ENABLE_CONDITIONAL_RERANKER": True,
    # Phase 3
    "ENABLE_FAST_STATE_DETECTOR": True,
    # Multiagent (PRD-017)
    "MULTIAGENT_ENABLED": False,
}

_STRING_DEFAULTS: Dict[str, str] = {
    "THREAD_MANAGER_MODEL": "gpt-5-nano",
    "STATE_ANALYZER_MODEL": "gpt-4o-mini",
    "WRITER_MODEL": "gpt-5-mini",
    "MULTIAGENT_LLM_TIMEOUT": "30",
    "MULTIAGENT_MAX_TOKENS": "600",
    "MULTIAGENT_TEMPERATURE": "0.7",
    "WRITER_MAX_TOKENS": "400",
    "WRITER_TEMPERATURE": "0.7",
    "MEMORY_RAG_N_RESULTS": "4",
    "MEMORY_RAG_MIN_SCORE": "0.45",
    "MEMORY_CONV_TURNS_DEFAULT": "6",
    "THREAD_STORAGE_DIR": "bot_psychologist/data/threads",
}


def _as_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class FeatureFlags:
    """Env-backed feature flags (read on each access)."""

    @staticmethod
    def enabled(name: str) -> bool:
        if name not in _DEFAULTS:
            return False
        return _as_bool(os.getenv(name), _DEFAULTS[name])

    @staticmethod
    def is_enabled(name: str) -> bool:
        return FeatureFlags.enabled(name)

    @staticmethod
    def snapshot() -> Dict[str, bool]:
        return {name: FeatureFlags.enabled(name) for name in _DEFAULTS}

    @staticmethod
    def value(name: str, default: str = "") -> str:
        if name in _STRING_DEFAULTS:
            return os.getenv(name, _STRING_DEFAULTS[name])
        return os.getenv(name, default)


feature_flags = FeatureFlags()
