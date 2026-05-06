from __future__ import annotations

import importlib
import re
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

SOURCE_ROOT = PROJECT_ROOT
TARGET_DIRS = [
    SOURCE_ROOT / "api",
    SOURCE_ROOT / "bot_agent",
    SOURCE_ROOT / "telegram_adapter",
]
SKIP_PARTS = {"__pycache__", ".pytest_cache", ".tmp_pytest_full", ".venv"}

ADAPTIVE_RUNTIME_IMPORT_RE = re.compile(r"^\s*(from|import)\s+.*\badaptive_runtime\b")


LEGACY_TOKENS = [
    "_answer_question_adaptive_legacy_cascade",
    "_runtime_prepare_adaptive_run_context",
]

OLD_RUNTIME_HELPER_TOKENS = [
    "bootstrap_runtime_helpers",
    "fast_path_stage_helpers",
    "full_path_stage_helpers",
    "retrieval_stage_helpers",
]

ACTIVE_RUNTIME_FILES = [
    SOURCE_ROOT / "api" / "routes" / "chat.py",
    SOURCE_ROOT / "api" / "routes" / "common.py",
    SOURCE_ROOT / "api" / "debug_routes.py",
    SOURCE_ROOT / "bot_agent" / "llm_streaming.py",
    SOURCE_ROOT / "bot_agent" / "answer_adaptive.py",
]


def _iter_py_files():
    for target in TARGET_DIRS:
        if not target.exists():
            continue
        for path in target.rglob("*.py"):
            if any(part in SKIP_PARTS for part in path.parts):
                continue
            yield path


def test_runtime_sources_have_no_adaptive_runtime_imports() -> None:
    offenders: list[str] = []
    for path in _iter_py_files():
        text = path.read_text(encoding="utf-8", errors="ignore")
        for line_no, line in enumerate(text.splitlines(), start=1):
            if ADAPTIVE_RUNTIME_IMPORT_RE.search(line):
                rel = path.relative_to(SOURCE_ROOT).as_posix()
                offenders.append(f"{rel}:{line_no}: {line.strip()}")
    assert not offenders, "\n".join(offenders)


def test_runtime_sources_have_no_legacy_cascade_tokens() -> None:
    offenders: list[str] = []
    for path in _iter_py_files():
        text = path.read_text(encoding="utf-8", errors="ignore")
        for token in LEGACY_TOKENS:
            if token in text:
                rel = path.relative_to(SOURCE_ROOT).as_posix()
                offenders.append(f"{rel}: contains {token}")
    assert not offenders, "\n".join(offenders)


def test_active_runtime_files_have_no_old_stage_helper_references() -> None:
    offenders: list[str] = []
    for path in ACTIVE_RUNTIME_FILES:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for token in OLD_RUNTIME_HELPER_TOKENS:
            if token in text:
                rel = path.relative_to(SOURCE_ROOT).as_posix()
                offenders.append(f"{rel}: contains {token}")
    assert not offenders, "\n".join(offenders)


def test_targeted_import_smoke_after_physical_purge() -> None:
    modules = [
        "api.main",
        "bot_agent",
        "bot_agent.answer_adaptive",
        "bot_agent.multiagent.runtime_adapter",
    ]
    for module in modules:
        importlib.import_module(module)
