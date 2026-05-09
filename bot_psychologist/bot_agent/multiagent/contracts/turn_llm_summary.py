"""Contract and validation for async per-turn LLM summaries."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


TURN_LLM_SUMMARY_VERSION = "turn_llm_summary_v1"
TURN_LLM_SUMMARY_METHOD = "llm_abstractive_v1"
TURN_LLM_SUMMARY_STATUSES = {"pending", "ready", "failed", "disabled"}


@dataclass
class TurnLLMSummary:
    """Stored async LLM summary for one completed user+assistant exchange."""

    status: str
    summary: str
    important_quote: str | None
    open_loop: str | None
    user_need: str | None
    assistant_move: str | None
    emotional_tone: str | None
    summary_version: str
    summary_method: str
    model: str | None
    provider: str | None
    source_hash: str
    created_at: str
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "summary": self.summary,
            "important_quote": self.important_quote,
            "open_loop": self.open_loop,
            "user_need": self.user_need,
            "assistant_move": self.assistant_move,
            "emotional_tone": self.emotional_tone,
            "summary_version": self.summary_version,
            "summary_method": self.summary_method,
            "model": self.model,
            "provider": self.provider,
            "source_hash": self.source_hash,
            "created_at": self.created_at,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "TurnLLMSummary":
        def _opt_text(key: str) -> str | None:
            value = payload.get(key)
            if not isinstance(value, str):
                return None
            stripped = value.strip()
            return stripped if stripped else None

        return cls(
            status=str(payload.get("status", "pending") or "pending"),
            summary=str(payload.get("summary", "") or ""),
            important_quote=_opt_text("important_quote"),
            open_loop=_opt_text("open_loop"),
            user_need=_opt_text("user_need"),
            assistant_move=_opt_text("assistant_move"),
            emotional_tone=_opt_text("emotional_tone"),
            summary_version=str(payload.get("summary_version", TURN_LLM_SUMMARY_VERSION) or TURN_LLM_SUMMARY_VERSION),
            summary_method=str(payload.get("summary_method", TURN_LLM_SUMMARY_METHOD) or TURN_LLM_SUMMARY_METHOD),
            model=_opt_text("model"),
            provider=_opt_text("provider"),
            source_hash=str(payload.get("source_hash", "") or ""),
            created_at=str(payload.get("created_at", "") or ""),
            error=_opt_text("error"),
        )


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def validate_turn_llm_summary(
    summary: TurnLLMSummary | dict[str, Any] | None,
    source_hash: str,
) -> tuple[bool, str]:
    """Conservative validator: only fully valid ready summaries can be used."""
    if summary is None:
        return False, "missing"
    obj = summary if isinstance(summary, TurnLLMSummary) else TurnLLMSummary.from_dict(summary)

    if obj.status not in TURN_LLM_SUMMARY_STATUSES:
        return False, "invalid_status"
    if obj.status != "ready":
        return False, obj.status
    if obj.summary_version != TURN_LLM_SUMMARY_VERSION:
        return False, "version_mismatch"
    if obj.source_hash != source_hash:
        return False, "source_hash_mismatch"
    if not obj.summary.strip():
        return False, "empty_summary"
    if not obj.created_at.strip():
        return False, "missing_created_at"
    return True, "ok"

