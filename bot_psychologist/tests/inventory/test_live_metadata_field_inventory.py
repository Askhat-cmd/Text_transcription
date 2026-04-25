from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_PATH = REPO_ROOT / "bot_psychologist/tests/fixtures/runtime_legacy_touchpoints_v102.json"
ANSWER_ADAPTIVE = REPO_ROOT / "bot_psychologist/bot_agent/answer_adaptive.py"
API_ROUTES_DIR = REPO_ROOT / "bot_psychologist/api/routes"
API_ROUTES_FILES = [
    API_ROUTES_DIR / "__init__.py",
    API_ROUTES_DIR / "chat.py",
    API_ROUTES_DIR / "common.py",
    API_ROUTES_DIR / "users.py",
    API_ROUTES_DIR / "feedback.py",
    API_ROUTES_DIR / "health.py",
]


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def test_legacy_metadata_field_inventory_is_defined() -> None:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    fields = payload.get("legacy_metadata_fields", [])
    assert isinstance(fields, list) and fields, "legacy_metadata_fields must be non-empty list"


def test_legacy_metadata_fields_exist_in_phase0_sources() -> None:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    fields = payload["legacy_metadata_fields"]
    answer_adaptive_text = _read_text(ANSWER_ADAPTIVE)
    api_routes_text = "\n".join(_read_text(path) for path in API_ROUTES_FILES)
    combined_text = f"{answer_adaptive_text}\n{api_routes_text}"

    missing = [field for field in fields if field not in combined_text]
    assert not missing, f"Phase 0 baseline lost expected legacy metadata fields: {missing}"
