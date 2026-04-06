"""Shared user-level types.

Neo runtime keeps this module separate from legacy level-adapter logic
so active code paths can depend on enum types without importing adapter code.
"""

from __future__ import annotations

from enum import Enum


class UserLevel(Enum):
    """User preparation level (legacy compatibility enum)."""

    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"

