"""Validation result contract for deterministic Validator Agent."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ValidationResult:
    """Result of validating Writer draft answer."""

    is_blocked: bool
    block_reason: Optional[str] = None
    block_category: Optional[str] = None
    safe_replacement: Optional[str] = None
    quality_flags: list[str] = field(default_factory=list)

    @property
    def is_clean(self) -> bool:
        return (not self.is_blocked) and (not self.quality_flags)

