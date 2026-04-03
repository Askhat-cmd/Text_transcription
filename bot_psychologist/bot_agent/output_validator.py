"""Deterministic output validation layer for Neo MindBot Phase 6."""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import List, Tuple


_BROKEN_HTML_RE = re.compile(r"<[^>]*$")
_MARKDOWN_LEAK_RE = re.compile(r"(```|^#{1,6}\s+)", flags=re.MULTILINE)
_FORBIDDEN_DIRECTIVE_RE = re.compile(
    r"\b(обязательно сделай|ты должен|срочно сделай|немедленно сделай|прекрати принимать)\b",
    flags=re.IGNORECASE,
)
_CERTAINTY_RE = re.compile(
    r"\b(гарантированно|однозначно|точно (?:причина|диагноз)|это единственный путь|100%)\b",
    flags=re.IGNORECASE,
)
_EXPLICIT_SHORT_RE = re.compile(
    r"\b(кратко|коротко|в двух словах|briefly|short answer)\b",
    flags=re.IGNORECASE,
)
_COMPARISON_QUERY_RE = re.compile(
    r"(чем отличается|разниц|difference|vs\\.?|в чем отличие)",
    flags=re.IGNORECASE,
)
_COMPARISON_ANSWER_RE = re.compile(
    r"(отлича|разниц|в отличие|тогда как|с одной стороны|с другой стороны)",
    flags=re.IGNORECASE,
)
_EXAMPLE_RE = re.compile(
    r"(например|к примеру|пример:|допустим)",
    flags=re.IGNORECASE,
)
_BRIDGE_ONLY_RE = re.compile(
    r"(что из этого тебе ближе|хочешь разобрать твой случай|хочешь разобрать это глубже|что из этого откликается)",
    flags=re.IGNORECASE,
)


@dataclass(frozen=True)
class OutputValidationResult:
    valid: bool
    text: str
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    repair_applied: bool = False
    needs_regeneration: bool = False

    def as_dict(self) -> dict:
        return {
            "valid": self.valid,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "repair_applied": self.repair_applied,
            "needs_regeneration": self.needs_regeneration,
        }


class OutputValidator:
    """Validation rules for generation output."""

    @staticmethod
    def _normalize(text: str) -> str:
        return (text or "").replace("\r\n", "\n").strip()

    @staticmethod
    def _strip_markdown(text: str) -> str:
        cleaned = re.sub(r"```[\s\S]*?```", "", text or "")
        cleaned = re.sub(r"^#{1,6}\s+", "", cleaned, flags=re.MULTILINE)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        return cleaned.strip()

    @staticmethod
    def _soften_certainty(text: str) -> str:
        softened = text or ""
        softened = _CERTAINTY_RE.sub("вероятно", softened)
        return softened

    @staticmethod
    def _split_sentences(text: str) -> List[str]:
        return [part.strip() for part in re.split(r"[.!?]+\s*", text or "") if part.strip()]

    def _detect_underfilled_inform(
        self,
        text: str,
        *,
        query: str,
    ) -> Tuple[bool, List[str]]:
        query_text = (query or "").strip().lower()
        if not query_text:
            return False, []
        if _EXPLICIT_SHORT_RE.search(query_text):
            return False, []

        body = (text or "").strip()
        lowered = body.lower()
        sentences = self._split_sentences(body)
        reasons: List[str] = []

        if len(sentences) <= 2 and len(body) < 260:
            reasons.append("thin_body")

        asks_difference = bool(_COMPARISON_QUERY_RE.search(query_text))
        if asks_difference and not _COMPARISON_ANSWER_RE.search(lowered):
            reasons.append("missing_comparison")

        has_bridge = bool(_BRIDGE_ONLY_RE.search(lowered))
        has_examples = bool(_EXAMPLE_RE.search(lowered))
        if has_bridge and len(body) < 420 and not has_examples:
            reasons.append("bridge_without_depth")

        return bool(reasons), reasons

    def validate(
        self,
        text: str,
        *,
        route: str,
        mode: str,
        safety_override: bool = False,
        query: str = "",
    ) -> OutputValidationResult:
        errors: List[str] = []
        warnings: List[str] = []
        repaired = self._normalize(text)
        repair_applied = False

        if not repaired:
            errors.append("empty_output")
            return OutputValidationResult(
                valid=False,
                text="",
                errors=errors,
                warnings=warnings,
                repair_applied=False,
                needs_regeneration=True,
            )

        if _MARKDOWN_LEAK_RE.search(repaired):
            warnings.append("markdown_leakage")
            repaired = self._strip_markdown(repaired)
            repair_applied = True

        if _BROKEN_HTML_RE.search(repaired):
            errors.append("broken_html_tail")

        if _CERTAINTY_RE.search(repaired):
            warnings.append("certainty_softened")
            repaired = self._soften_certainty(repaired)
            repair_applied = True

        normalized_route = (route or "").strip().lower()
        normalized_mode = (mode or "").strip().upper()

        if safety_override or normalized_route == "safe_override":
            if _FORBIDDEN_DIRECTIVE_RE.search(repaired):
                errors.append("forbidden_directive_advice")

        if normalized_route == "inform" and "?" not in repaired and len(repaired) < 120:
            warnings.append("inform_too_short")

        if normalized_route == "inform" or normalized_mode == "CLARIFICATION":
            underfilled, sparse_reasons = self._detect_underfilled_inform(
                repaired,
                query=query,
            )
            if underfilled:
                errors.append("underfilled_inform_answer")
                warnings.extend([f"sparse_{reason}" for reason in sparse_reasons])

        if normalized_mode == "CLARIFICATION" and "?" not in repaired:
            warnings.append("clarification_without_question")

        needs_regeneration = bool(errors)
        valid = not errors
        return OutputValidationResult(
            valid=valid,
            text=repaired,
            errors=errors,
            warnings=warnings,
            repair_applied=repair_applied,
            needs_regeneration=needs_regeneration,
        )

    @staticmethod
    def build_regeneration_hint(
        errors: List[str],
        *,
        route: str,
        mode: str,
        query: str = "",
    ) -> str:
        joined = ", ".join(errors) if errors else "format_issues"
        extra_lines: List[str] = []
        if "underfilled_inform_answer" in (errors or []):
            extra_lines.extend(
                [
                    "- Углуби объяснение: раскрой суть и практический смысл без воды.",
                    "- Если вопрос про различия, сравни по 2-3 критериям.",
                    "- Добавь 2-4 коротких примера там, где это усиливает понимание.",
                ]
            )
        if query:
            extra_lines.append(f"- Фокусируйся на исходном запросе: {query.strip()[:240]}")
        return (
            "Служебная правка ответа: исправь ошибки вывода и верни новый ответ.\n"
            f"- route={route or 'reflect'}\n"
            f"- mode={mode or 'PRESENCE'}\n"
            f"- errors={joined}\n"
            + ("\n".join(extra_lines) + "\n" if extra_lines else "")
            + "- Никаких markdown-блоков кода, HTML-тегов и директивного давления."
        )

    @staticmethod
    def safe_fallback(*, route: str) -> str:
        normalized_route = (route or "").strip().lower()
        if normalized_route == "safe_override":
            return (
                "Сейчас важно снизить нагрузку и вернуть опору. "
                "Если есть риск для безопасности, лучше обратиться к живой поддержке рядом."
            )
        return (
            "Могу ошибаться, попробую короче и точнее. "
            "Если хочешь, уточни один главный фокус — и разберём его по шагам."
        )


output_validator = OutputValidator()
