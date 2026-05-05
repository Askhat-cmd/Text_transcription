from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
ADAPTIVE_RUNTIME_DIR = REPO_ROOT / "bot_psychologist/bot_agent/adaptive_runtime"
ANSWER_ADAPTIVE_PATH = REPO_ROOT / "bot_psychologist/bot_agent/answer_adaptive.py"
FIXTURE_PATH = REPO_ROOT / "bot_psychologist/tests/fixtures/multiagent_runtime_invariants_v1.json"


def _read_answer_adaptive() -> str:
    return ANSWER_ADAPTIVE_PATH.read_text(encoding="utf-8", errors="ignore")


def test_adaptive_runtime_directory_removed() -> None:
    assert not ADAPTIVE_RUNTIME_DIR.exists()


def test_answer_adaptive_no_legacy_cascade_body() -> None:
    text = _read_answer_adaptive()
    assert "_answer_question_adaptive_legacy_cascade" not in text


def test_answer_adaptive_has_no_legacy_imports() -> None:
    text = _read_answer_adaptive()
    forbidden_tokens = [
        "adaptive_runtime",
        "state_classifier",
        "route_resolver",
        "from .decision",
        "from .response",
    ]
    for token in forbidden_tokens:
        assert token not in text, f"Forbidden legacy token found: {token}"


def test_answer_adaptive_still_routes_to_multiagent_adapter() -> None:
    text = _read_answer_adaptive()
    assert "run_multiagent_adaptive_sync" in text
    assert "def answer_question_adaptive" in text


def test_multiagent_invariants_fixture_contains_physical_purge_section() -> None:
    import json

    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8-sig"))
    purge = payload.get("physical_purge", {})
    assert purge.get("adaptive_runtime_exists") is False
    assert purge.get("answer_adaptive_contains_legacy_body") is False
    assert purge.get("legacy_fallback_available") is False
