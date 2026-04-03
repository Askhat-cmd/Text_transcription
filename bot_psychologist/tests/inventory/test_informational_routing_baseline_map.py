from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_PATH = REPO_ROOT / "bot_psychologist/tests/fixtures/response_richness_baseline_v103.json"


def _load_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8-sig"))


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def test_informational_routing_baseline_map_shape() -> None:
    payload = _load_fixture()
    touchpoints = payload.get("routing_touchpoints")
    assert isinstance(touchpoints, list) and touchpoints


def test_informational_routing_touchpoints_exist() -> None:
    payload = _load_fixture()
    for point in payload.get("routing_touchpoints", []):
        file_path = REPO_ROOT / str(point.get("file", ""))
        assert file_path.exists(), f"Missing routing touchpoint file: {point}"
        source = _read_text(file_path)
        for symbol in point.get("symbols", []):
            assert symbol in source, f"Missing symbol '{symbol}' in {point['file']}"
