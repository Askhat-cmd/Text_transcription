from __future__ import annotations

from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from api.main import app
from tools.legacy_sd_usage_audit import run_legacy_sd_usage_audit

client = TestClient(app)


class _DummyRunner:
    def __init__(self):
        self.chroma_manager = SimpleNamespace(_embed_texts=lambda texts: [[0.1, 0.2, 0.3] for _ in texts])
        self.registry = SimpleNamespace(get_source=lambda source_id: None)


@contextmanager
def _patched_query_runtime(mock_collection):
    with patch("api.routes.query._get_collection", return_value=mock_collection), patch(
        "api.routes.query._get_runner", return_value=_DummyRunner()
    ):
        yield


def _mock_results():
    return {
        "documents": [["текст 1", "текст 2"]],
        "metadatas": [[
            {
                "sd_level": "GREEN",
                "author_id": "a1",
                "author": "Author",
                "source_type": "book",
                "title": "Блок 1",
                "keywords": ["k1"],
            },
            {
                "sd_level": "BLUE",
                "author_id": "a2",
                "author": "Author2",
                "source_type": "book",
                "title": "Блок 2",
                "keywords": ["k2"],
            },
        ]],
        "distances": [[0.1, 0.2]],
        "ids": [["chunk1", "chunk2"]],
    }


def test_query_sd_level_is_deprecated_noop(monkeypatch) -> None:
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    mock_collection = MagicMock()
    mock_collection.query.return_value = _mock_results()

    with _patched_query_runtime(mock_collection):
        response = client.post(
            "/api/query/",
            json={"query": "практики", "sd_level": 7, "author_id": "a1", "use_rerank": False},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["sd_filter_applied"] is False
    assert payload["debug"]["legacy_sd_deprecated"] is True
    assert payload["debug"]["sd_level_ignored"] is True
    where_arg = mock_collection.query.call_args.kwargs.get("where")
    assert where_arg == {"author_id": {"$eq": "a1"}}


def test_legacy_sd_usage_report_marks_active_filter_disabled(tmp_path) -> None:
    output_json = tmp_path / "legacy_sd_usage_report.json"
    output_md = tmp_path / "legacy_sd_report.md"
    payload = run_legacy_sd_usage_audit(
        source_prd="PRD-046.0.7-HF1",
        output_json=output_json,
        output_md=output_md,
    )
    assert output_json.exists()
    assert output_md.exists()
    assert payload["legacy_sd_filter_still_active"] is False
