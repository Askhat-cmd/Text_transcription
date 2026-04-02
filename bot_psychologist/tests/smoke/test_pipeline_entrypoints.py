from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from api.routes import (
    ask_adaptive_question,
    ask_adaptive_question_stream,
    router,
)
from bot_agent import answer_question_adaptive


def test_pipeline_entrypoints_are_callable() -> None:
    assert callable(answer_question_adaptive)
    assert callable(ask_adaptive_question)
    assert callable(ask_adaptive_question_stream)


def test_pipeline_entrypoints_registered_in_router() -> None:
    route_paths = {route.path for route in router.routes}
    assert "/api/v1/questions/adaptive" in route_paths
    assert "/api/v1/questions/adaptive-stream" in route_paths
