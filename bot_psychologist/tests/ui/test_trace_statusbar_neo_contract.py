from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
STATUS_BAR_PATH = REPO_ROOT / "bot_psychologist/web_ui/src/components/debug/StatusBar.tsx"
TRACE_HISTORY_PATH = REPO_ROOT / "bot_psychologist/web_ui/src/components/debug/TraceHistory.tsx"


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def test_statusbar_uses_fixed_neo_chips() -> None:
    text = _read_text(STATUS_BAR_PATH)

    for marker in ("MODE:", "STATE:", "RULE:", "CHUNKS:", "HITS:", "TOKENS:", "LLM:", "WARN:"):
        assert marker in text

    assert "SD:" not in text
    assert "sd_level" not in text
    assert "sd_classification" not in text


def test_trace_history_uses_mode_and_state() -> None:
    text = _read_text(TRACE_HISTORY_PATH)
    assert "#${turn} · ${mode} · ${state}" in text
    assert "sd_classification" not in text
    assert "sd_level" not in text

