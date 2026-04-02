from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from api.main import app


def test_app_boot_has_expected_metadata() -> None:
    assert app.title == "Bot Psychologist API"
    assert isinstance(app.version, str) and app.version


def test_app_boot_registers_core_routes() -> None:
    route_paths = {route.path for route in app.routes}
    assert "/" in route_paths
    assert "/api/v1/health" in route_paths
    assert "/api/v1/questions/adaptive" in route_paths
    assert "/api/v1/questions/adaptive-stream" in route_paths
