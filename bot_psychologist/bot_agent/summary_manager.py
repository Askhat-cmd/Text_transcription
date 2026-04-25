"""Summary manager helpers for runtime memory policy."""

from __future__ import annotations

from dataclasses import dataclass

from .memory_context import resolve_summary_staleness


@dataclass(frozen=True)
class SummaryPolicy:
    stale_after_turns: int = 8
    max_summary_chars: int = 1200


class SummaryManager:
    def __init__(self, policy: SummaryPolicy | None = None) -> None:
        self.policy = policy or SummaryPolicy()

    def normalize_summary(self, summary: str | None) -> str:
        text = (summary or "").strip()
        if not text:
            return ""
        if len(text) > self.policy.max_summary_chars:
            return text[: self.policy.max_summary_chars].rstrip()
        return text

    def staleness(self, summary: str | None, summary_updated_at: int | None, total_turns: int) -> str:
        return resolve_summary_staleness(
            summary=self.normalize_summary(summary),
            summary_updated_at=summary_updated_at,
            total_turns=total_turns,
            stale_after_turns=self.policy.stale_after_turns,
        )


summary_manager = SummaryManager()
