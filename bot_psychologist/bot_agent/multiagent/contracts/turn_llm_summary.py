"""Contract and validation for async per-turn LLM summaries."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


TURN_LLM_SUMMARY_VERSION = "turn_llm_summary_v1"
TURN_LLM_SUMMARY_METHOD = "llm_abstractive_v1"
TURN_LLM_SUMMARY_STATUSES = {"pending", "ready", "failed", "disabled"}
TURN_LLM_SUMMARY_MAX_QUOTE_CHARS = 160
TURN_LLM_SUMMARY_MAX_SUMMARY_CHARS_DEFAULT = 700

_DIAGNOSIS_MARKERS = (
    "\u0434\u0435\u043f\u0440\u0435\u0441\u0441",
    "\u043f\u0442\u0441\u0440",
    "\u0442\u0440\u0430\u0432\u043c",
    "\u0440\u0430\u0441\u0441\u0442\u0440\u043e\u0439\u0441\u0442\u0432",
    "\u043a\u043b\u0438\u043d\u0438\u0447\u0435\u0441\u043a",
    "\u0434\u0438\u0430\u0433\u043d\u043e\u0437",
    "рґрµрїсђрµсѓсѓ",
    "рїс‚сѓсђ",
    "с‚сђр°рірј",
    "сђр°сѓсѓс‚сђрѕр№сѓс‚рір",
    "рєр»рёрѕрёр§рµсѓрє",
    "рґрёр°рірѕр·",
)
_DIRECT_ADVICE_MARKERS = (
    "\u0442\u0435\u0431\u0435 \u043d\u0443\u0436\u043d\u043e",
    "\u0442\u0435\u0431\u0435 \u043d\u0430\u0434\u043e",
    "\u0442\u044b \u0434\u043e\u043b\u0436\u0435\u043d",
    "\u0442\u044b \u0434\u043e\u043b\u0436\u043d\u0430",
    "\u043e\u0431\u044f\u0437\u0430\u0442\u0435\u043b\u044c\u043d\u043e \u0441\u0434\u0435\u043b\u0430\u0439",
    "\u043d\u0430\u0434\u043e \u0441\u0440\u043e\u0447\u043d\u043e",
    "you must",
    "you should",
    "с‚рµр±рµ рѕсѓр¶рѕрѕ",
    "с‚рµр±рµ рѕр°рґрѕ",
    "с‚с‹ сѓрѕр»р¶рµрѕ",
    "с‚с‹ сѓрѕр»р¶рѕр°",
    "рѕр±сџр·р°с‚рµр»сњрѕрѕ сѓрґрµр»р°р№",
    "рѕр°рґрѕ сѓсђрѕс‡рѕрѕ",
)
_TRANSCRIPT_MARKERS = (
    "user:",
    "assistant:",
    "\u043f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u0435\u043b\u044c:",
    "\u0431\u043e\u0442:",
    "рїрѕр»сњр·рѕрір°с‚рµр»сњ:",
    "р±рѕс‚:",
)


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


def _normalize_text(text: str) -> str:
    return " ".join((text or "").strip().split())


def _contains_any_marker(text: str, patterns: tuple[str, ...]) -> bool:
    lowered = (text or "").lower()
    return any(marker in lowered for marker in patterns)


def _looks_like_transcript_dump(summary_text: str) -> bool:
    normalized = _normalize_text(summary_text).lower()
    markers_found = sum(1 for marker in _TRANSCRIPT_MARKERS if marker in normalized)
    if markers_found >= 2:
        return True
    if normalized.count("user:") + normalized.count("assistant:") >= 2:
        return True
    if normalized.count("\u043f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u0435\u043b\u044c:") + normalized.count("\u0431\u043e\u0442:") >= 2:
        return True
    return False


def validate_turn_llm_summary(
    summary: TurnLLMSummary | dict[str, Any] | None,
    source_hash: str,
    *,
    max_summary_chars: int = TURN_LLM_SUMMARY_MAX_SUMMARY_CHARS_DEFAULT,
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

    summary_text = _normalize_text(obj.summary or "")
    if not summary_text:
        return False, "empty_summary"
    if not obj.created_at.strip():
        return False, "missing_created_at"
    if len(summary_text) > int(max_summary_chars):
        return False, "summary_too_long"
    if obj.important_quote and len(_normalize_text(obj.important_quote)) > TURN_LLM_SUMMARY_MAX_QUOTE_CHARS:
        return False, "quote_too_long"
    if _contains_any_marker(summary_text, _DIAGNOSIS_MARKERS):
        return False, "diagnosis_language"
    if _contains_any_marker(summary_text, _DIRECT_ADVICE_MARKERS):
        return False, "direct_advice_voice"
    if _looks_like_transcript_dump(summary_text):
        return False, "transcript_style_dump"
    return True, "ok"
