from __future__ import annotations

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]

TARGET_FILES = [
    REPO_ROOT / "bot_agent" / "state_classifier.py",
    REPO_ROOT / "bot_agent" / "answer_adaptive.py",
    REPO_ROOT / "bot_agent" / "diagnostics_classifier.py",
]

BANNED_PATTERNS = [
    (r"SD runtime disabled in Neo v11 pipeline", "legacy SD runtime log marker"),
    (r"DIAG state legacy term", "legacy diagnostics mapper warning"),
    (r"Уровень развития \(СД\)", "SD level line in runtime prompt context"),
    (r"SD-оверлей", "SD overlay directive in runtime prompt context"),
    (r"LEGACY_STATE_MAP\s*=", "legacy state map in diagnostics classifier"),
]


def test_sd_cleanup_banned_markers_absent_in_target_files() -> None:
    violations: list[str] = []
    for file_path in TARGET_FILES:
        text = file_path.read_text(encoding="utf-8", errors="ignore")
        for pattern, description in BANNED_PATTERNS:
            if re.search(pattern, text):
                violations.append(f"{file_path.name}: {description}")
    assert not violations, "Found banned SD legacy markers:\n" + "\n".join(violations)
