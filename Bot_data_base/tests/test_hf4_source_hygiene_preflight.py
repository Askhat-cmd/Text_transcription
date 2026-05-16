from __future__ import annotations

from tools import run_chroma_recovery_hf4 as hf4


def test_source_hygiene_focus_only_pass(monkeypatch) -> None:
    payload = {
        "sources": [
            {
                "source_id": "123__кузница_духа",
                "status": "done",
                "blocks_count": 247,
                "author": "Саламат Сарсекенов",
                "title": "Кузница Духа",
                "delete_policy": {"state": "protected"},
            }
        ]
    }

    def _fake_http(url: str, timeout: float = 12.0) -> dict:  # noqa: ARG001
        return {"ok": True, "status_code": 200, "body": payload, "error": None}

    monkeypatch.setattr(hf4, "_http_json", _fake_http)
    report = hf4.build_source_hygiene_live_preflight(
        source_prd="PRD-046.0.7.2-HF4",
        admin_base_url="http://127.0.0.1:8003",
        expected_source_id="123__кузница_духа",
        expected_blocks=247,
    )
    assert report["source_hygiene_focus_only"] is True
    assert report["issues"] == []


def test_source_hygiene_blocks_on_non_focus_with_blocks(monkeypatch) -> None:
    payload = {
        "sources": [
            {"source_id": "123__кузница_духа", "status": "done", "blocks_count": 247},
            {"source_id": "other", "status": "done", "blocks_count": 12},
        ]
    }

    def _fake_http(url: str, timeout: float = 12.0) -> dict:  # noqa: ARG001
        return {"ok": True, "status_code": 200, "body": payload, "error": None}

    monkeypatch.setattr(hf4, "_http_json", _fake_http)
    report = hf4.build_source_hygiene_live_preflight(
        source_prd="PRD-046.0.7.2-HF4",
        admin_base_url="http://127.0.0.1:8003",
        expected_source_id="123__кузница_духа",
        expected_blocks=247,
    )
    assert "non_focus_sources_with_blocks_present" in report["issues"]
