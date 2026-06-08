from __future__ import annotations

import ast
from pathlib import Path


WRITER_PATH = (
    Path(__file__).resolve().parents[1]
    / "bot_agent"
    / "multiagent"
    / "agents"
    / "writer_agent.py"
)
TARGET_FUNCTIONS = {"_enforce_answer_compliance", "_enforce_mvp_free_dialogue_compliance"}
HIGH_CONFIDENCE_MARKERS = (
    "нейросталкинг",
    "самореализац",
    "механизм",
    "паттерн",
    "триггер",
    "автопилот",
    "ты прав",
    "отвечаю прямо",
    "показываю сразу",
    "если отвечать прямо",
    "ключевой механизм",
)
ALLOWED_BOUNDARY_MARKERS = (
    "я рядом",
    "стабилиз",
    "перегруз",
    "пожалуйста",
    "рад",
    "соберу итог",
)


def _literal_string(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        return "".join(
            value.value
            for value in node.values
            if isinstance(value, ast.Constant) and isinstance(value.value, str)
        )
    return None


def test_writer_compliance_has_no_high_confidence_static_semantic_returns() -> None:
    tree = ast.parse(WRITER_PATH.read_text(encoding="utf-8-sig"))
    offenders: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name not in TARGET_FUNCTIONS:
            continue
        for child in ast.walk(node):
            if not isinstance(child, ast.Return):
                continue
            literal = _literal_string(child.value)
            if not literal:
                continue
            lowered = literal.lower()
            if any(marker in lowered for marker in ALLOWED_BOUNDARY_MARKERS):
                continue
            if any(marker in lowered for marker in HIGH_CONFIDENCE_MARKERS):
                offenders.append(f"{node.name}:{child.lineno}:{literal[:90]}")

    assert offenders == []
