from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
COMMON_PATH = REPO_ROOT / "bot_psychologist/api/routes/common.py"
FIXTURE_PATH = REPO_ROOT / "bot_psychologist/tests/fixtures/multiagent_runtime_invariants_v1.json"


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def test_active_paths_use_multiagent_builders_not_legacy_strip_functions() -> None:
    text = _read_text(COMMON_PATH)

    assert "_build_multiagent_metadata(" in text
    assert "_build_multiagent_trace_storage_payload(" in text

    assert "metadata = _build_multiagent_metadata(" in text
    assert "enriched = _build_multiagent_trace_storage_payload(trace_payload)" in text


def test_compat_only_keys_constant_replaces_legacy_runtime_metadata_keys() -> None:
    text = _read_text(COMMON_PATH)

    assert "_COMPAT_ONLY_METADATA_KEYS" in text
    assert "_LEGACY_RUNTIME_METADATA_KEYS" not in text


def test_multiagent_runtime_invariants_fixture_has_no_forbidden_legacy_metadata_keys() -> None:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8-sig"))
    runtime_contract = payload.get("runtime_contract", {})

    forbidden = {
        "user_level",
        "user_level_adapter_applied",
        "sd_level",
        "sd_secondary",
        "sd_confidence",
        "sd_method",
        "sd_allowed_blocks",
        "decision_rule_id",
        "mode_reason",
        "confidence_level",
    }
    assert forbidden.isdisjoint(set(runtime_contract.keys()))
