from __future__ import annotations

import inspect
import json
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from api.main import app
from bot_agent.config import config
from bot_agent.runtime_config import RuntimeConfig


REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_PATH = REPO_ROOT / "bot_psychologist/tests/fixtures/multiagent_runtime_invariants_v1.json"
ADMIN_HEADERS = {"X-API-Key": "dev-key-001"}


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def _load_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8-sig"))


@pytest.fixture()
def admin_client(tmp_path, monkeypatch):
    override_path = tmp_path / "admin_overrides.json"
    monkeypatch.setattr(RuntimeConfig, "OVERRIDES_PATH", override_path, raising=False)
    monkeypatch.setattr(RuntimeConfig, "_cache_mtime", 0.0, raising=False)
    monkeypatch.setattr(RuntimeConfig, "_cache", {}, raising=False)
    monkeypatch.setattr(config, "OVERRIDES_PATH", override_path, raising=False)
    monkeypatch.setattr(config, "WARMUP_ON_START", False, raising=False)
    with TestClient(app, base_url="http://localhost") as client:
        yield client


def test_multiagent_runtime_invariants_fixture_shape() -> None:
    payload = _load_fixture()
    assert payload.get("schema_version") == "multiagent-runtime-invariants-v1"
    assert payload.get("status") == "active"

    runtime_contract = payload.get("runtime_contract", {})
    assert runtime_contract.get("active_runtime") == "multiagent"
    assert runtime_contract.get("runtime_entrypoint") == "multiagent_adapter"
    assert runtime_contract.get("legacy_fallback_enabled") is False
    assert runtime_contract.get("legacy_fallback_used") is False

    assert isinstance(payload.get("active_entrypoints"), list) and payload["active_entrypoints"]
    assert isinstance(payload.get("admin_contract"), dict)


def test_multiagent_entrypoints_follow_required_and_forbidden_symbols() -> None:
    payload = _load_fixture()

    for entrypoint in payload["active_entrypoints"]:
        file_path = REPO_ROOT / entrypoint["file"]
        assert file_path.exists(), f"Missing file for entrypoint: {entrypoint['name']}"

        text = _read_text(file_path)
        required = entrypoint.get("required_symbols", [])
        forbidden = entrypoint.get("forbidden_symbols", [])

        assert isinstance(required, list) and required, (
            f"required_symbols must be non-empty for {entrypoint['name']}"
        )
        for symbol in required:
            assert symbol in text, f"Missing required symbol '{symbol}' in {entrypoint['file']}"

        assert isinstance(forbidden, list), f"forbidden_symbols must be list for {entrypoint['name']}"
        for symbol in forbidden:
            assert symbol not in text, (
                f"Forbidden symbol '{symbol}' present in active entrypoint {entrypoint['file']}"
            )


def test_answer_adaptive_public_shim_has_no_legacy_fallback_tokens() -> None:
    payload = _load_fixture()
    shim_spec = next(
        item for item in payload["active_entrypoints"] if item["name"] == "answer_adaptive_public_shim"
    )

    from bot_agent.answer_adaptive import answer_question_adaptive

    source = inspect.getsource(answer_question_adaptive)
    for token in shim_spec.get("forbidden_in_public_function", []):
        assert token not in source, f"Forbidden token '{token}' present in answer_question_adaptive"


def test_admin_runtime_effective_matches_multiagent_contract(admin_client) -> None:
    payload = _load_fixture()
    admin_contract = payload["admin_contract"]

    response = admin_client.get(admin_contract["endpoint"], headers=ADMIN_HEADERS)
    assert response.status_code == 200
    runtime_payload = response.json()

    assert runtime_payload["active_runtime"] == admin_contract["active_runtime"]
    assert runtime_payload["legacy"]["fallback_enabled"] is admin_contract["legacy_fallback_enabled"]
    assert runtime_payload["legacy"]["fallback_used"] is admin_contract["legacy_fallback_used"]

    assert runtime_payload["pipeline_mode"] not in set(admin_contract["forbidden_active_modes"])
    compatibility_mode = runtime_payload.get("compatibility", {}).get("pipeline_mode")
    if compatibility_mode is not None:
        assert compatibility_mode not in set(admin_contract["forbidden_active_modes"])
