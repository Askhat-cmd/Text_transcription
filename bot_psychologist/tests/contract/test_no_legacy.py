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
        "bot_agent/__init__.py": [
            "from .answer_basic",
            "from .answer_sag_aware",
            "from .answer_graph_powered",
        ],
        "api/routes.py": [
            "answer_question_basic(",
            "answer_question_sag_aware(",
            "answer_question_graph_powered(",
        ],
        "bot_agent/prompt_registry_v2.py": [
            "prompt_sd_",
            "prompt_system_level_beginner",
            "prompt_system_level_intermediate",
            "prompt_system_level_advanced",
        ],
        "bot_agent/runtime_config.py": [
            "prompt_sd_green",
            "prompt_sd_blue",
            "prompt_sd_red",
            "prompt_sd_orange",
            "prompt_sd_yellow",
            "prompt_sd_purple",
            "prompt_system_level_beginner",
            "prompt_system_level_intermediate",
            "prompt_system_level_advanced",
        ],
        "api/main.py": [
            "prompt_sd_green",
            "prompt_sd_blue",
            "prompt_sd_red",
            "prompt_sd_orange",
            "prompt_sd_yellow",
            "prompt_sd_purple",
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


def test_sd_and_level_prompt_files_fully_removed_from_runtime_tree() -> None:
    legacy_prompt_names = [
        "prompt_sd_green.md",
        "prompt_sd_blue.md",
        "prompt_sd_red.md",
        "prompt_sd_orange.md",
        "prompt_sd_yellow.md",
        "prompt_sd_purple.md",
        "prompt_system_level_beginner.md",
        "prompt_system_level_intermediate.md",
        "prompt_system_level_advanced.md",
    ]
    for filename in legacy_prompt_names:
        root_path = REPO_ROOT / "bot_agent" / filename
        legacy_path = REPO_ROOT / "bot_agent" / "legacy" / "prompts" / filename
        assert not root_path.exists(), f"legacy prompt still located in active root: {root_path}"
        assert not legacy_path.exists(), f"legacy prompt file should be removed: {legacy_path}"


def test_legacy_python_modules_fully_removed_from_runtime_tree() -> None:
    legacy_python_modules = [
        "answer_basic.py",
        "answer_sag_aware.py",
        "answer_graph_powered.py",
        "sd_classifier.py",
        "user_level_adapter.py",
    ]

    for filename in legacy_python_modules:
        active_path = REPO_ROOT / "bot_agent" / filename
        archived_path = REPO_ROOT / "bot_agent" / "legacy" / "python" / filename
        assert not archived_path.exists(), f"legacy module file should be removed: {archived_path}"
        assert not active_path.exists(), f"legacy module still exists in active path: {active_path}"
