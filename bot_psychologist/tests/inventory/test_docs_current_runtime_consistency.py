from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
README_PATH = REPO_ROOT / "bot_psychologist/README.md"
DOCS_INDEX_PATH = REPO_ROOT / "bot_psychologist/docs/README.md"
MIGRATION_DOC_PATH = REPO_ROOT / "bot_psychologist/docs/migration_legacy_to_multiagent.md"
MIGRATION_ARCHIVE_PATH = (
    REPO_ROOT
    / "bot_psychologist/docs/archive/legacy_migration/migration_legacy_to_multiagent.md"
)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def test_readme_mentions_active_runtime_and_multiagent_adapter() -> None:
    text = _read_text(README_PATH)
    lowered = text.lower()
    assert "active runtime" in lowered
    assert "multiagent_adapter" in text


def test_readme_mentions_legacy_cascade_physically_removed() -> None:
    text = _read_text(README_PATH).lower()
    assert "legacy cascade" in text
    assert "physically removed" in text


def test_readme_has_no_prd042_planned_phrases() -> None:
    text = _read_text(README_PATH).lower()
    assert "prd-042 planned" not in text
    assert "провести prd-042" not in text


def test_readme_does_not_recommend_multiagent_disabled() -> None:
    text = _read_text(README_PATH)
    assert "MULTIAGENT_ENABLED=false" not in text


def test_docs_index_contains_current_architecture_links() -> None:
    text = _read_text(DOCS_INDEX_PATH).lower()
    required_links = [
        "overview.md",
        "architecture.md",
        "multiagent_architecture.md",
        "multiagent_contracts.md",
        "thread_lifecycle.md",
        "trace_runtime.md",
    ]
    for link in required_links:
        assert link in text


def test_migration_doc_is_archived_or_stubbed_with_archive_pointer() -> None:
    archive_exists = MIGRATION_ARCHIVE_PATH.exists()
    active_exists = MIGRATION_DOC_PATH.exists()
    assert archive_exists
    assert active_exists

    active_text = _read_text(MIGRATION_DOC_PATH).lower()
    assert "archive/legacy_migration/migration_legacy_to_multiagent.md" in active_text
    assert "migration completed" in active_text
