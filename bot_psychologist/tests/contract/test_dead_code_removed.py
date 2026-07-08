from __future__ import annotations

from pathlib import Path


BOT_ROOT = Path(__file__).resolve().parents[2]
WORKSPACE_ROOT = BOT_ROOT.parent

DEAD_TEST_PATHS = (
    "tests/test_phase1.py",
    "tests/test_phase2.py",
    "tests/test_phase3.py",
    "tests/test_fast_detector.py",
    "tests/test_full_dialogue_pipeline.py",
)

DEAD_IMPORT_MARKERS = (
    "from bot_agent.answer_basic import",
    "import bot_agent.answer_basic",
    "answer_question_basic(",
    "from bot_agent import answer_question_sag_aware",
    "answer_question_sag_aware(",
    "from bot_agent import answer_question_graph_powered",
    "answer_question_graph_powered(",
    "from bot_agent.sd_classifier import",
    "SDClassifier(",
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def test_dead_pipeline_tests_are_physically_absent() -> None:
    for rel_path in DEAD_TEST_PATHS:
        assert not (BOT_ROOT / rel_path).exists(), f"dead test still present: {rel_path}"


def test_dead_pipeline_import_markers_are_gone_from_executable_python_paths() -> None:
    excluded_paths = {
        "tests/contract/test_dead_code_removed.py",
    }
    for path in sorted(BOT_ROOT.rglob("*.py")):
        rel_path = path.relative_to(BOT_ROOT).as_posix()
        if rel_path in excluded_paths:
            continue
        if ".venv/" in rel_path or "/__pycache__/" in rel_path or rel_path.startswith(".venv/"):
            continue
        text = _read(path)
        for marker in DEAD_IMPORT_MARKERS:
            assert marker not in text, f"dead pipeline marker '{marker}' found in {rel_path}"


def test_user_level_adapter_verdict_is_recorded_as_active() -> None:
    report_path = WORKSPACE_ROOT / "TO_DO_LIST" / "logs" / "PRD-047.40" / "user_level_adapter_trace.md"
    assert report_path.exists(), "user_level_adapter trace report is missing"
    text = _read(report_path)
    assert "- verdict: `active`" in text
