from __future__ import annotations

import inspect
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api.routes import ask_adaptive_question_stream


def test_stream_endpoint_has_no_graph_client_dependency() -> None:
    sig = inspect.signature(ask_adaptive_question_stream)
    param_names = list(sig.parameters.keys())
    assert "_graph_client" not in param_names


def test_stream_endpoint_has_required_dependencies() -> None:
    sig = inspect.signature(ask_adaptive_question_stream)
    param_names = list(sig.parameters.keys())
    assert "request" in param_names
    assert "api_key" in param_names
    assert "store" in param_names
