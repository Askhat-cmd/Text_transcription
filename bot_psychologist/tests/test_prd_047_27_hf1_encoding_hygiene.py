from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
TRACE_WIDGET = REPO_ROOT / "bot_psychologist" / "web_ui" / "src" / "components" / "chat" / "MultiAgentTraceWidget.tsx"
ADMIN_PANEL = REPO_ROOT / "bot_psychologist" / "web_ui" / "src" / "components" / "admin" / "AdminPanel.tsx"

FORBIDDEN_MOJIBAKE_MARKERS = (
    "Рњ",
    "Рџ",
    "Р°",
    "РЅ",
    "Рє",
    "СЊ",
    "в–",
    "вЂ",
    "�",
)


def test_core_trace_and_admin_ui_sources_have_no_forbidden_mojibake_markers() -> None:
    for path in (TRACE_WIDGET, ADMIN_PANEL):
        text = path.read_text(encoding="utf-8")
        for marker in FORBIDDEN_MOJIBAKE_MARKERS:
            assert marker not in text, f"marker '{marker}' found in {path.name}"


def test_trace_widget_contains_expected_unicode_labels_and_symbols() -> None:
    text = TRACE_WIDGET.read_text(encoding="utf-8")

    required = (
        "Мультиагентный пайплайн",
        "Нет релевантных чанков",
        "Semantic Cards Pilot",
        "—",
        "▾",
        "▸",
        "→",
    )
    for item in required:
        assert item in text, f"missing required unicode/UI label: {item}"
