"""Deterministic output validation layer for Neo MindBot Phase 6."""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import List


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

    def validate(
        self,
        text: str,
        *,
        route: str,
        mode: str,
        safety_override: bool = False,
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
    def build_regeneration_hint(errors: List[str], *, route: str, mode: str) -> str:
        joined = ", ".join(errors) if errors else "format_issues"
        return (
            "Служебная правка ответа: исправь ошибки вывода и верни новый ответ.\n"
            f"- route={route or 'reflect'}\n"
            f"- mode={mode or 'PRESENCE'}\n"
            f"- errors={joined}\n"
            "- Никаких markdown-блоков кода, HTML-тегов и директивного давления."
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

