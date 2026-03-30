"""Feature flags for PRD modernization phases."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict

from dotenv import load_dotenv

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(_PROJECT_ROOT / ".env")


_DEFAULTS: Dict[str, bool] = {
    # Phase 1
    "ENABLE_EMBEDDING_PROVIDER": True,
    # Phase 2
    "ENABLE_CONDITIONAL_RERANKER": True,
    # Phase 3
    "ENABLE_FAST_STATE_DETECTOR": True,
    "ENABLE_FAST_SD_DETECTOR": True,
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
    def snapshot() -> Dict[str, bool]:
        return {name: FeatureFlags.enabled(name) for name in _DEFAULTS}


feature_flags = FeatureFlags()

