from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from bot_agent.feature_flags import _DEFAULTS, _STRING_DEFAULTS


FORBIDDEN_FLAGS = {
    "OWNER_WEB_CHAT_SEMANTIC_CARDS_ENABLED",
    "SEMANTIC_CARDS_WEB_TRACE_FORCE_ENABLE",
    "SEMANTIC_CARDS_ADMIN_OVERRIDE",
    "SEMANTIC_CARDS_RUNTIME_PARITY_MODE",
}


def test_no_forbidden_runtime_flags_were_added() -> None:
    known_flags = set(_DEFAULTS) | set(_STRING_DEFAULTS)
    assert FORBIDDEN_FLAGS.isdisjoint(known_flags)


def test_changed_startup_and_runtime_files_do_not_reference_forbidden_flags() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    targets = [
        repo_root / "запуск проека.txt",
        repo_root / "bot_psychologist" / "tools" / "start_pilot_web_chat_backend.ps1",
        repo_root / "bot_psychologist" / "bot_agent" / "feature_flags.py",
        repo_root / "bot_psychologist" / "bot_agent" / "multiagent" / "dialogue_act_resolver.py",
        repo_root / "bot_psychologist" / "bot_agent" / "multiagent" / "final_answer_directive.py",
    ]
    combined_text = "\n".join(path.read_text(encoding="utf-8") for path in targets)
    for flag in FORBIDDEN_FLAGS:
        assert flag not in combined_text
