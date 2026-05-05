from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def test_chat_route_no_longer_uses_legacy_adaptive_import_or_resolver() -> None:
    path = REPO_ROOT / "bot_psychologist/api/routes/chat.py"
    text = _read_text(path)
    assert "from bot_agent import answer_question_adaptive" not in text
    assert "_resolve_answer_question_adaptive" not in text


def test_common_route_no_longer_imports_legacy_answer_adaptive() -> None:
    path = REPO_ROOT / "bot_psychologist/api/routes/common.py"
    text = _read_text(path)
    assert "from bot_agent import answer_question_adaptive" not in text


def test_telegram_service_no_longer_imports_legacy_answer_adaptive() -> None:
    path = REPO_ROOT / "bot_psychologist/api/telegram_adapter/service.py"
    text = _read_text(path)
    assert "from bot_agent.answer_adaptive import answer_question_adaptive" not in text


def test_runtime_adapter_exists() -> None:
    path = REPO_ROOT / "bot_psychologist/bot_agent/multiagent/runtime_adapter.py"
    assert path.exists()
