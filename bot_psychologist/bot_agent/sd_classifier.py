"""Legacy stub: SD classifier retired in Neo runtime (PRD 11.0).

Full legacy implementation archived at `bot_agent/legacy/python/sd_classifier.py`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


def get_sd_settings() -> Dict[str, object]:
    return {
        "heuristic_confidence_threshold": 0.65,
        "update_profile_every_n_messages": 5,
        "enabled": False,
    }


@dataclass(frozen=True)
class SDClassificationResult:
    primary: str
    secondary: Optional[str] = None
    confidence: float = 0.0
    indicator: str = "disabled_by_design"
    method: str = "disabled"
    allowed_blocks: list[str] = field(default_factory=list)


class SDCompatibilityResolver:
    def get_allowed_levels(self, *_args, **_kwargs) -> list[str]:
        return ["NONE"]


class SDClassifier:
    async def classify_user(self, *_args, **_kwargs) -> SDClassificationResult:
        return SDClassificationResult(primary="NONE")

    def classify_user_sync(self, *_args, **_kwargs) -> SDClassificationResult:
        return SDClassificationResult(primary="NONE")


sd_classifier = None
sd_compatibility_resolver = SDCompatibilityResolver()
