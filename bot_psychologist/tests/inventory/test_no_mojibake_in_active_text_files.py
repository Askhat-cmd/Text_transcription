from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
BOT_ROOT = REPO_ROOT / "bot_psychologist"

# PRD-043.1 forbidden mojibake markers:
# "Р’", "Рџ", "Рћ", "Р›", "Рґ", "Рµ", "РЅ", "вЂ", "вљ", "в”", "СЃ", "С‚"
FORBIDDEN_MARKERS = [
    "\u0420\u2019",  # Р’
    "\u0420\u045f",  # Рџ
    "\u0420\u045b",  # Рћ
    "\u0420\u203a",  # Р›
    "\u0420\u0491",  # Рґ
    "\u0420\u00b5",  # Рµ
    "\u0420\u00bd",  # РЅ
    "\u0432\u20ac",  # вЂ
    "\u0432\u0459",  # вљ
    "\u0432\u201d",  # в”
    "\u0421\u0403",  # СЃ
    "\u0421\u201a",  # С‚
]


def _active_text_files() -> list[Path]:
    files: list[Path] = []

    # Explicit top-level files.
    for rel in [
        ".gitignore",
        "README.md",
        "bot_psychologist/.gitignore",
        "bot_psychologist/README.md",
    ]:
        path = REPO_ROOT / rel
        if path.exists() and path.is_file():
            files.append(path)

    # Active docs only; archive is intentionally excluded.
    docs_dir = BOT_ROOT / "docs"
    files.extend(p for p in docs_dir.glob("*.md") if p.is_file())

    # Backend API surface.
    api_dir = BOT_ROOT / "api"
    files.extend(p for p in api_dir.glob("*.py") if p.is_file())
    files.extend(p for p in (api_dir / "routes").glob("*.py") if p.is_file())

    # Active web UI source files.
    web_src = BOT_ROOT / "web_ui" / "src"
    files.extend(
        p
        for p in web_src.rglob("*")
        if p.is_file() and p.suffix in {".ts", ".tsx"}
    )

    return sorted(set(files))


def test_no_mojibake_markers_in_active_text_files() -> None:
    offenders: list[str] = []

    for path in _active_text_files():
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(REPO_ROOT).as_posix()
        for marker in FORBIDDEN_MARKERS:
            if marker not in text:
                continue
            for line_no, line in enumerate(text.splitlines(), 1):
                if marker in line:
                    offenders.append(f"{rel}:{line_no} contains mojibake marker")

    assert offenders == []
