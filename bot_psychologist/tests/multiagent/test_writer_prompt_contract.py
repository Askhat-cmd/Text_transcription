from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent.agents.writer_agent_prompts import WRITER_SYSTEM, WRITER_USER_TEMPLATE


def test_writer_prompt_v2_contains_quality_guardrails() -> None:
    assert "Один ответ = один точный следующий ход" in WRITER_SYSTEM
    assert "АНТИ-ОБЩИЕ ОТВЕТЫ" in WRITER_SYSTEM
    assert "Не задавай больше одного вопроса" in WRITER_SYSTEM
    assert "validate —" in WRITER_SYSTEM
    assert "reflect —" in WRITER_SYSTEM
    assert "practice —" in WRITER_SYSTEM
    assert "safe_override —" in WRITER_SYSTEM
    assert "must_avoid" in WRITER_SYSTEM
    assert "open_loops" in WRITER_SYSTEM
    assert "Никаких нумерованных списков" in WRITER_SYSTEM


def test_writer_user_template_contains_internal_focus_instructions() -> None:
    assert "ПЕРЕД ОТВЕТОМ ВНУТРИ СЕБЯ ВЫБЕРИ" in WRITER_USER_TEMPLATE
    assert "главный фокус пользователя" in WRITER_USER_TEMPLATE
    assert "нужную глубину" in WRITER_USER_TEMPLATE
    assert "один следующий ход" in WRITER_USER_TEMPLATE
    assert "В ответе не показывай этот анализ" in WRITER_USER_TEMPLATE

