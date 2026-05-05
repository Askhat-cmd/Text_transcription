from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
README_PATH = REPO_ROOT / "bot_psychologist/README.md"
MIGRATION_PATH = REPO_ROOT / "bot_psychologist/docs/migration_legacy_to_multiagent.md"
TESTING_MATRIX_PATH = REPO_ROOT / "bot_psychologist/docs/testing_matrix.md"


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def test_readme_declares_multiagent_only_runtime() -> None:
    text = _read_text(README_PATH).lower()
    assert "multiagent-only" in text or "active runtime = multiagent-only" in text


def test_readme_does_not_recommend_multiagent_disabled_state() -> None:
    text = _read_text(README_PATH)
    assert "MULTIAGENT_ENABLED=false" not in text


def test_migration_doc_marks_legacy_as_prd_041_purge_only() -> None:
    text = _read_text(MIGRATION_PATH)
    assert "PRD-041" in text
    assert "retained only for PRD-041 purge" in text


def test_testing_matrix_mentions_active_runtime_multiagent_check() -> None:
    text = _read_text(TESTING_MATRIX_PATH)
    assert "active_runtime=multiagent" in text
