from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
API_ROUTES = REPO_ROOT / "bot_psychologist/api/routes.py"


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def test_streaming_entrypoint_exists() -> None:
    text = _read_text(API_ROUTES)
    assert "ask_adaptive_question_stream" in text
    assert "/questions/adaptive-stream" in text


def test_streaming_phase0_divergence_markers_exist() -> None:
    text = _read_text(API_ROUTES)
    # Phase 0 baseline: stream path still contains legacy-aligned markers.
    patterns = [
        "_classify_parallel(",
        "sd_classifier",
        "user_level_adapter",
        "\"sd_classification\"",
        "\"sd_detail\"",
    ]
    for pattern in patterns:
        assert pattern in text, f"Expected baseline streaming marker missing: {pattern}"
