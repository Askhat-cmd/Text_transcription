from __future__ import annotations

from pathlib import Path
import subprocess


REPO_ROOT = Path(__file__).resolve().parents[3]
BOT_ROOT = REPO_ROOT / "bot_psychologist"
THREADS_DIR = BOT_ROOT / "data/threads"
DOCS_ARCHIVE_DIR = BOT_ROOT / "docs/archive/legacy_migration"
DOCS_INDEX = BOT_ROOT / "docs/README.md"

EXCLUDED_ROOTS = {
    ".venv",
    ".venv_migrated_backup_2026-04-24",
    "web_ui/node_modules",
}


def _iter_paths_under_bot() -> list[Path]:
    results: list[Path] = []
    for path in BOT_ROOT.rglob("*"):
        rel = path.relative_to(BOT_ROOT).as_posix()
        if any(rel == root or rel.startswith(f"{root}/") for root in EXCLUDED_ROOTS):
            continue
        results.append(path)
    return results


def _tracked_paths() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def test_no_pycache_in_tracked_repo_files() -> None:
    offenders = [path for path in _tracked_paths() if "__pycache__/" in path]
    assert offenders == []


def test_no_pytest_cache_in_tracked_repo_files() -> None:
    offenders = [path for path in _tracked_paths() if "/.pytest_cache/" in path]
    assert offenders == []


def test_no_tmp_pytest_directories_under_bot_tree() -> None:
    offenders = [
        p.relative_to(BOT_ROOT).as_posix()
        for p in _iter_paths_under_bot()
        if p.is_dir() and p.name.startswith(".tmp_pytest")
    ]
    assert offenders == []


def test_no_tmp_uvicorn_logs() -> None:
    offenders = [
        p.relative_to(BOT_ROOT).as_posix()
        for p in _iter_paths_under_bot()
        if p.is_file() and p.name.startswith(".tmp_uvicorn_") and p.name.endswith(".log")
    ]
    assert offenders == []


def test_no_legacy_snapshot_files() -> None:
    filenames = {
        "tests_before.txt",
        "tests_after.txt",
        "tests_diff.txt",
    }
    offenders = [
        p.relative_to(BOT_ROOT).as_posix()
        for p in _iter_paths_under_bot()
        if p.is_file() and p.name in filenames
    ]
    assert offenders == []


def test_no_live_test_report_files() -> None:
    offenders = [
        p.relative_to(BOT_ROOT).as_posix()
        for p in _iter_paths_under_bot()
        if p.is_file() and p.name.startswith("live_test_report.")
    ]
    assert offenders == []


def test_threads_directory_contains_only_gitkeep() -> None:
    assert THREADS_DIR.exists()
    files = sorted(p.name for p in THREADS_DIR.iterdir() if p.is_file())
    assert files == [".gitkeep"]


def test_legacy_migration_archive_directory_exists() -> None:
    assert DOCS_ARCHIVE_DIR.exists()


def test_docs_index_exists() -> None:
    assert DOCS_INDEX.exists()
