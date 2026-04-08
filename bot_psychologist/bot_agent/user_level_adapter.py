"""Legacy stub: user level adapter retired in Neo runtime (PRD 11.0).

Full legacy implementation archived at `bot_agent/legacy/python/user_level_adapter.py`.
"""

from __future__ import annotations

from .user_level_types import UserLevel


class UserLevelAdapter:
    def __init__(self, *_args, **_kwargs) -> None:
        raise RuntimeError(
            "UserLevelAdapter is archived and disabled in Neo runtime."
        )
