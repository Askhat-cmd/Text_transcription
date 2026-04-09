"""Hybrid query builder where user question remains the anchor."""

from __future__ import annotations

from typing import Dict, Iterable, Optional, Union

from ..working_state import WorkingState


class HybridQueryBuilder:
    """
    Build a retrieval query from multiple memory layers.

    Core rule: current user question must stay the anchor.
    """

    def __init__(
        self,
        max_chars: int = 2000,
        short_term_chars: int = 700,
        summary_chars: int = 500,
    ) -> None:
        self.max_chars = max_chars
        self.short_term_chars = short_term_chars
        self.summary_chars = summary_chars

    @staticmethod
    def _clean(text: str) -> str:
        return " ".join((text or "").strip().split())

    def _clip(self, text: str, limit: int) -> str:
        cleaned = self._clean(text)
        if len(cleaned) <= limit:
            return cleaned
        return cleaned[: max(0, limit - 3)] + "..."

    def _format_working_state(
        self,
        working_state: Optional[Union[WorkingState, Dict]],
    ) -> str:
        if working_state is None:
            return ""

        if isinstance(working_state, WorkingState):
            data = working_state.to_dict()
        else:
            data = dict(working_state)

        nss = self._clean(
            str(
                data.get("nss")
                or data.get("nervous_system_state")
                or data.get("nervous_state")
                or ""
            )
        )
        request_function = self._clean(
            str(data.get("request_function") or data.get("fn") or "")
        )
        confidence = data.get("confidence")
        if confidence is None:
            confidence = data.get("confidence_score")

        conf_text = ""
        if isinstance(confidence, (int, float)):
            conf_text = f"{float(confidence):.2f}"
        else:
            fallback_conf = data.get("confidence_level")
            if isinstance(fallback_conf, str) and fallback_conf.strip():
                conf_text = fallback_conf.strip()

        if not nss and not request_function and not conf_text:
            return ""

        if not nss:
            nss = "window"
        if not request_function:
            request_function = "understand"
        if not conf_text:
            conf_text = "0.00"

        return f"nss={nss} fn={request_function} conf={conf_text}"

    def _format_latest_user_turns(
        self,
        latest_user_turns: Optional[Iterable[str]],
        *,
        limit: int = 2,
    ) -> str:
        if not latest_user_turns:
            return ""
        cleaned: list[str] = []
        for item in latest_user_turns:
            value = self._clean(str(item or ""))
            if value:
                cleaned.append(value)
        if not cleaned:
            return ""
        tail = cleaned[-max(1, limit):]
        return " | ".join(f"u{i + 1}: {text}" for i, text in enumerate(tail))

    def build_query(
        self,
        current_question: str,
        conversation_summary: str = "",
        working_state: Optional[Union[WorkingState, Dict]] = None,
        short_term_context: str = "",
        latest_user_turns: Optional[Iterable[str]] = None,
    ) -> str:
        question = self._clean(current_question)
        if not question:
            raise ValueError("current_question must not be empty")

        summary = self._clip(conversation_summary, self.summary_chars)
        summary_excerpt = self._clip((conversation_summary or "")[:200], 200)
        short_term = self._clip(short_term_context, self.short_term_chars)
        working_state_text = self._format_working_state(working_state)
        latest_user_text = self._format_latest_user_turns(latest_user_turns, limit=2)

        parts = [f"QUESTION_ANCHOR: {question}"]

        if working_state_text:
            parts.append(f"WORKING_STATE: {working_state_text}")
        if summary_excerpt:
            parts.append(f"SUMMARY_EXCERPT_200: {summary_excerpt}")
        if summary:
            parts.append(f"DIALOG_SUMMARY: {summary}")
        if latest_user_text:
            parts.append(f"LATEST_USER_TURNS: {latest_user_text}")
        if short_term:
            parts.append(f"SHORT_TERM_CONTEXT: {short_term}")

        # Repeat the question at the end to preserve anchor dominance.
        parts.append(f"QUESTION_ANCHOR_REPEAT: {question}")

        query = "\n".join(parts)
        if len(query) <= self.max_chars:
            return query

        # Clip middle while preserving anchor lines at top and bottom.
        head = parts[0]
        tail = parts[-1]
        middle = "\n".join(parts[1:-1])

        reserve = len(head) + len(tail) + 2
        allowed_middle = max(0, self.max_chars - reserve)
        middle = self._clip(middle, allowed_middle)

        if middle:
            return "\n".join([head, middle, tail])
        return "\n".join([head, tail])
