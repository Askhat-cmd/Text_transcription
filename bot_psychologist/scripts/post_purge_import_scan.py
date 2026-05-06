from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


SKIP_PARTS = {
    ".git",
    ".venv",
    "node_modules",
    "dist",
    "build",
    "__pycache__",
    ".pytest_cache",
    ".tmp_pytest_full",
    "tests",
    "АРХИВ_отработано",
}

DELETED_SYMBOL_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("adaptive_runtime_import", re.compile(r"^\s*(from|import)\s+.*\badaptive_runtime\b")),
    ("legacy_cascade_function", re.compile(r"\b_answer_question_adaptive_legacy_cascade\b")),
    ("legacy_prepare_context", re.compile(r"\b_runtime_prepare_adaptive_run_context\b")),
    ("bootstrap_runtime_helpers", re.compile(r"\bbootstrap_runtime_helpers\b")),
    ("fast_path_stage_helpers", re.compile(r"\bfast_path_stage_helpers\b")),
    ("full_path_stage_helpers", re.compile(r"\bfull_path_stage_helpers\b")),
    ("retrieval_stage_helpers", re.compile(r"\bretrieval_stage_helpers\b")),
]

FORBIDDEN_ACTIVE_RUNTIME_IMPORTS: list[tuple[str, re.Pattern[str]]] = [
    ("state_classifier", re.compile(r"^\s*from\s+bot_agent\.state_classifier\s+import\b")),
    ("route_resolver", re.compile(r"^\s*from\s+bot_agent\.route_resolver\s+import\b")),
    ("decision", re.compile(r"^\s*from\s+bot_agent\.decision\s+import\b")),
    ("response", re.compile(r"^\s*from\s+bot_agent\.response\s+import\b")),
]

ACTIVE_RUNTIME_PATH_MARKERS = (
    "api/",
    "bot_agent/multiagent/",
    "bot_agent/llm_streaming.py",
    "bot_agent/answer_adaptive.py",
)
SCAN_SUBDIRS = ("api", "bot_agent", "telegram_adapter", "scripts")
RUNTIME_SCAN_SUBDIRS = ("api", "bot_agent", "telegram_adapter")


@dataclass(frozen=True)
class Violation:
    kind: str
    path: Path
    line_no: int
    line: str



def _should_skip(path: Path) -> bool:
    return any(part in SKIP_PARTS for part in path.parts)



def _iter_python_files(root: Path, *, subdirs: tuple[str, ...] = SCAN_SUBDIRS) -> Iterable[Path]:
    for subdir in subdirs:
        base = root / subdir
        if not base.exists():
            continue
        for path in base.rglob("*.py"):
            if path.is_file() and not _should_skip(path):
                yield path



def _is_active_runtime_path(path: Path, root: Path) -> bool:
    rel = path.relative_to(root).as_posix()
    return any(rel.startswith(marker) or rel == marker for marker in ACTIVE_RUNTIME_PATH_MARKERS)



def _scan_deleted_symbols(root: Path) -> list[Violation]:
    violations: list[Violation] = []
    for path in _iter_python_files(root, subdirs=RUNTIME_SCAN_SUBDIRS):
        text = path.read_text(encoding="utf-8", errors="ignore")
        for line_no, line in enumerate(text.splitlines(), start=1):
            for kind, pattern in DELETED_SYMBOL_PATTERNS:
                if pattern.search(line):
                    violations.append(Violation(kind=kind, path=path, line_no=line_no, line=line.strip()))
    return violations



def _scan_forbidden_active_imports(root: Path) -> list[Violation]:
    violations: list[Violation] = []
    for path in _iter_python_files(root, subdirs=RUNTIME_SCAN_SUBDIRS):
        if not _is_active_runtime_path(path, root):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for line_no, line in enumerate(text.splitlines(), start=1):
            for kind, pattern in FORBIDDEN_ACTIVE_RUNTIME_IMPORTS:
                if pattern.search(line):
                    violations.append(Violation(kind=kind, path=path, line_no=line_no, line=line.strip()))
    return violations



def _print_report(title: str, violations: list[Violation], root: Path, max_items: int) -> None:
    print(f"\n=== {title} ===")
    print(f"count={len(violations)}")
    for item in violations[:max_items]:
        rel = item.path.relative_to(root).as_posix()
        print(f"[{item.kind}] {rel}:{item.line_no}: {item.line}")
    if len(violations) > max_items:
        print(f"... truncated {len(violations) - max_items} more")



def main() -> int:
    parser = argparse.ArgumentParser(description="Post-purge import scan for PRD-042")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]), help="Project root")
    parser.add_argument("--max-items", type=int, default=200)
    args = parser.parse_args()

    root = Path(args.root).resolve()
    print(f"[post-purge-import-scan] root={root}")

    deleted_hits = _scan_deleted_symbols(root)
    active_import_hits = _scan_forbidden_active_imports(root)

    _print_report("Deleted legacy symbol references", deleted_hits, root, args.max_items)
    _print_report("Forbidden imports in active runtime paths", active_import_hits, root, args.max_items)

    total = len(deleted_hits) + len(active_import_hits)
    if total == 0:
        print("\nRESULT: PASS")
        return 0

    print(f"\nRESULT: FAIL ({total} findings)")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
