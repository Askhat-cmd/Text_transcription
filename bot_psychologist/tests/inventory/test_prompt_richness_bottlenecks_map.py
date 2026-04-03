from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_PATH = REPO_ROOT / "bot_psychologist/tests/fixtures/response_richness_baseline_v103.json"


def _load_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8-sig"))


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def test_prompt_richness_bottlenecks_map_shape() -> None:
    payload = _load_fixture()
    bottlenecks = payload.get("prompt_bottlenecks")
    assert isinstance(bottlenecks, list) and bottlenecks


def test_prompt_richness_bottlenecks_symbols_exist() -> None:
    payload = _load_fixture()
    for item in payload.get("prompt_bottlenecks", []):
        file_path = REPO_ROOT / str(item.get("file", ""))
        assert file_path.exists(), f"Missing prompt bottleneck file: {item}"
        source = _read_text(file_path)
        symbol = str(item.get("symbol", ""))
        assert symbol and symbol in source, f"Missing symbol '{symbol}' in {item['file']}"
