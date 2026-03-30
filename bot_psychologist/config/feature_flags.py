"""Compatibility wrapper for feature flags.

Canonical implementation lives in ``bot_agent.feature_flags``.
This module exists to keep PRD path ``config/feature_flags.py``.
"""

from bot_agent.feature_flags import FeatureFlags, feature_flags

__all__ = ["FeatureFlags", "feature_flags"]

