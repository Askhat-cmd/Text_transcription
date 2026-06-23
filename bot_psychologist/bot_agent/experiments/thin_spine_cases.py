"""Case contracts and loader for PRD-047.28 thin-spine experiments."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class KnowledgePackageItem:
    title: str
    content: str
    source: str = "fixture"

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "KnowledgePackageItem":
        return cls(
            title=str(payload.get("title", "") or "").strip(),
            content=str(payload.get("content", "") or "").strip(),
            source=str(payload.get("source", "fixture") or "fixture").strip(),
        )


@dataclass(frozen=True)
class ExpectedBehavior:
    must_answer_directly: bool = True
    kb_allowed: bool = True
    practice_allowed: str = "only_if_requested_or_gently_optional"
    must_not: tuple[str, ...] = ()
    preferred_mode: str = "direct_human_answer"

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ExpectedBehavior":
        return cls(
            must_answer_directly=bool(payload.get("must_answer_directly", True)),
            kb_allowed=bool(payload.get("kb_allowed", True)),
            practice_allowed=str(
                payload.get("practice_allowed", "only_if_requested_or_gently_optional")
                or "only_if_requested_or_gently_optional"
            ),
            must_not=tuple(str(item) for item in list(payload.get("must_not", []) or []) if str(item).strip()),
            preferred_mode=str(payload.get("preferred_mode", "direct_human_answer") or "direct_human_answer"),
        )


@dataclass(frozen=True)
class ExperimentCase:
    case_id: str
    group: str
    title: str
    messages: tuple[dict[str, str], ...]
    expected_behavior: ExpectedBehavior
    quality_focus: tuple[str, ...] = ()
    case_summary: str = ""
    explicit_constraints: tuple[str, ...] = ()
    knowledge_package: tuple[KnowledgePackageItem, ...] = ()

    @property
    def current_user_message(self) -> str:
        for message in reversed(self.messages):
            if str(message.get("role", "") or "").strip() == "user":
                return str(message.get("content", "") or "")
        return ""

    @property
    def recent_messages(self) -> list[dict[str, str]]:
        if not self.messages:
            return []
        return [dict(item) for item in self.messages[:-1]]

    @property
    def is_multi_turn(self) -> bool:
        return len(self.messages) > 1

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ExperimentCase":
        messages = [
            {
                "role": str(item.get("role", "") or "").strip(),
                "content": str(item.get("content", "") or "").strip(),
            }
            for item in list(payload.get("messages", []) or [])
            if isinstance(item, dict)
        ]
        if not messages:
            raise ValueError("case.messages is required")
        if messages[-1]["role"] != "user":
            raise ValueError("last message must be a user turn")
        return cls(
            case_id=str(payload.get("case_id", "") or "").strip(),
            group=str(payload.get("group", "") or "").strip(),
            title=str(payload.get("title", "") or "").strip(),
            messages=tuple(messages),
            expected_behavior=ExpectedBehavior.from_dict(
                dict(payload.get("expected_behavior", {}) or {})
            ),
            quality_focus=tuple(
                str(item) for item in list(payload.get("quality_focus", []) or []) if str(item).strip()
            ),
            case_summary=str(payload.get("case_summary", "") or "").strip(),
            explicit_constraints=tuple(
                str(item) for item in list(payload.get("explicit_constraints", []) or []) if str(item).strip()
            ),
            knowledge_package=tuple(
                KnowledgePackageItem.from_dict(item)
                for item in list(payload.get("knowledge_package", []) or [])
                if isinstance(item, dict)
            ),
        )


def load_cases_jsonl(path: str | Path) -> list[ExperimentCase]:
    fixture_path = _resolve_cases_path(path)
    cases: list[ExperimentCase] = []
    for raw_line in fixture_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        payload = json.loads(line)
        cases.append(ExperimentCase.from_dict(payload))
    _validate_cases(cases)
    return cases


def _validate_cases(cases: list[ExperimentCase]) -> None:
    if not cases:
        raise ValueError("at least one experiment case is required")
    ids = [case.case_id for case in cases]
    duplicates = {item for item in ids if ids.count(item) > 1}
    if duplicates:
        raise ValueError(f"duplicate case ids: {sorted(duplicates)}")
    multi_turn_count = sum(1 for case in cases if case.is_multi_turn)
    if multi_turn_count < 5:
        raise ValueError("at least 5 multi-turn cases are required")
    required_groups = {
        "greeting_personal_question",
        "resistance",
        "anger_at_boss",
        "simplify_after_complexity",
        "practice_pushback",
        "long_term_perspective",
        "no_kb_request",
        "alternatives_to_breathing",
        "direct_kb_question",
        "safety_boundary",
    }
    present_groups = {case.group for case in cases}
    missing = sorted(required_groups - present_groups)
    if missing:
        raise ValueError(f"missing required case groups: {missing}")


def _resolve_cases_path(path: str | Path) -> Path:
    candidate = Path(path)
    if candidate.exists():
        return candidate
    repo_root = Path(__file__).resolve().parents[3]
    repo_relative = repo_root / candidate
    if repo_relative.exists():
        return repo_relative
    raise FileNotFoundError(candidate)
