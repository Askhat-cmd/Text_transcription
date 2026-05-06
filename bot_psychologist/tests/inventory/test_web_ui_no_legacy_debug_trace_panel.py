from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
WEB_UI_SRC = REPO_ROOT / "bot_psychologist" / "web_ui" / "src"

ACTIVE_DIRS = [
    WEB_UI_SRC / "components" / "chat",
    WEB_UI_SRC / "components" / "debug",
    WEB_UI_SRC / "pages",
]

EXCLUDED_DIR = WEB_UI_SRC / "components" / "debug" / "compat"

FORBIDDEN_LEGACY_MARKERS = [
    "Problems only",
    "Роутинг и классификация",
    "BLOCK CAP",
]


def _active_web_ui_files() -> list[Path]:
    files: list[Path] = []
    for base_dir in ACTIVE_DIRS:
        if not base_dir.exists():
            continue
        for path in base_dir.rglob("*"):
            if not path.is_file() or path.suffix not in {".ts", ".tsx"}:
                continue
            if EXCLUDED_DIR in path.parents:
                continue
            files.append(path)
    return sorted(set(files))


def test_active_web_ui_has_no_legacy_trace_markers() -> None:
    offenders: list[str] = []
    for path in _active_web_ui_files():
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(REPO_ROOT).as_posix()
        for marker in FORBIDDEN_LEGACY_MARKERS:
            if marker not in text:
                continue
            for line_no, line in enumerate(text.splitlines(), 1):
                if marker in line:
                    offenders.append(f"{rel}:{line_no} contains '{marker}'")
    assert offenders == []


def test_active_chat_does_not_use_legacy_inline_trace_panel() -> None:
    offenders: list[str] = []
    for path in _active_web_ui_files():
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(REPO_ROOT).as_posix()
        for line_no, line in enumerate(text.splitlines(), 1):
            if "InlineDebugTrace" in line:
                offenders.append(f"{rel}:{line_no} contains legacy InlineDebugTrace usage")
    assert offenders == []


def test_multiagent_trace_renderer_markers_exist() -> None:
    message_file = WEB_UI_SRC / "components" / "chat" / "Message.tsx"
    widget_file = WEB_UI_SRC / "components" / "chat" / "MultiAgentTraceWidget.tsx"

    message_text = message_file.read_text(encoding="utf-8")
    widget_text = widget_file.read_text(encoding="utf-8")

    assert "multiagent_v1" in message_text
    assert "Pipeline NEO" in widget_text
