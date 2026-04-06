from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def _read(rel_path: str) -> str:
    return (REPO_ROOT / rel_path).read_text(encoding="utf-8", errors="ignore")


def test_no_legacy_runtime_markers_in_active_neo_paths() -> None:
    checks = {
        "bot_agent/retriever.py": [
            "sd_filter=",
        ],
        "bot_agent/prompt_registry_v2.py": [
            "prompt_sd_",
            "prompt_system_level_beginner",
            "prompt_system_level_intermediate",
            "prompt_system_level_advanced",
        ],
        "bot_agent/response/response_generator.py": [
            "_load_sd_prompt",
            "sd_overlay",
        ],
        "bot_agent/answer_adaptive.py": [
            "pre_rerank_result",
            "filter_blocks_by_level",
            "request_function in {\"solution\", \"directive\"}",
            "_load_sd_prompt",
            "sd_overlay=",
        ],
        "bot_agent/route_resolver.py": [
            "request_function in {\"solution\", \"directive\"}",
        ],
    }

    for rel_path, forbidden_markers in checks.items():
        text = _read(rel_path)
        for marker in forbidden_markers:
            assert marker not in text, f"legacy marker '{marker}' found in {rel_path}"
