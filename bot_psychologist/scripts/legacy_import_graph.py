from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import argparse


DEFAULT_SYMBOLS = [
    "answer_adaptive",
    "adaptive_runtime",
    "state_classifier",
    "route_resolver",
    "from .decision",
    "from bot_agent.decision",
    "bot_agent/decision/",
    "from .response",
    "from bot_agent.response",
    "bot_agent/response/",
    "fast_detector",
    "user_level_types",
    "memory_v12",
    "legacy cascade",
    "_runtime_prepare_adaptive_run_context",
    "_answer_question_adaptive_legacy_cascade",
]

ALLOWED_SUFFIXES = {".py", ".md", ".tsx", ".ts", ".json"}
SKIP_PARTS = {
    ".git",
    ".venv",
    ".venv_migrated_backup_2026-04-24",
    ".tmp_pytest_full",
    "node_modules",
    "dist",
    "build",
    "__pycache__",
    ".pytest_cache",
}


@dataclass(frozen=True)
class Hit:
    path: Path
    line_no: int
    line: str


def _should_skip(path: Path) -> bool:
    return any(part in SKIP_PARTS for part in path.parts)


def _iter_files(root: Path):
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if _should_skip(path):
            continue
        if path.suffix.lower() not in ALLOWED_SUFFIXES:
            continue
        yield path


def _scan_symbol(root: Path, symbol: str) -> list[Hit]:
    hits: list[Hit] = []
    symbol_lower = symbol.lower()
    for path in _iter_files(root):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for idx, line in enumerate(text.splitlines(), start=1):
            if symbol_lower in line.lower():
                hits.append(Hit(path=path, line_no=idx, line=line.strip()))
    return hits


def main() -> int:
    parser = argparse.ArgumentParser(description="Legacy import graph scanner for PRD-041")
    parser.add_argument("--root", default=".", help="Repository root")
    parser.add_argument("--symbol", action="append", dest="symbols", help="Custom symbol (repeatable)")
    parser.add_argument("--max-per-symbol", type=int, default=200)
    args = parser.parse_args()

    root = Path(args.root).resolve()
    symbols = args.symbols if args.symbols else DEFAULT_SYMBOLS

    print(f"[legacy-import-graph] root={root}")
    encoding = "cp1251"

    def _safe_print(text: str) -> None:
        try:
            print(text)
        except UnicodeEncodeError:
            print(text.encode(encoding, errors="replace").decode(encoding, errors="replace"))

    for symbol in symbols:
        hits = _scan_symbol(root, symbol)
        _safe_print(f"\n=== {symbol} ===")
        _safe_print(f"count={len(hits)}")
        for hit in hits[: args.max_per_symbol]:
            rel = hit.path.relative_to(root)
            _safe_print(f"{rel}:{hit.line_no}: {hit.line}")
        if len(hits) > args.max_per_symbol:
            _safe_print(f"... truncated {len(hits) - args.max_per_symbol} more")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
