from __future__ import annotations

from tools import runtime_smoke_utf8


def test_utf8_check_passes_on_clean_russian_payload() -> None:
    payload = {
        "focus_source_identity": {
            "source_id": "123__кузница_духа",
            "title": "Кузница Духа",
            "author": "Саламат Сарсекенов",
        }
    }
    check = runtime_smoke_utf8.build_utf8_check_payload(runtime_payload=payload, source_prd="PRD-046.0.10-HF1")
    assert check["passed"] is True
    assert check["mojibake_markers_found"] == []


def test_utf8_check_detects_mojibake_markers() -> None:
    payload = {"value": "Гђ broken text"}
    check = runtime_smoke_utf8.build_utf8_check_payload(runtime_payload=payload, source_prd="PRD-046.0.10-HF1")
    assert check["passed"] is False
    assert len(check["mojibake_markers_found"]) >= 1


def test_runtime_smoke_payload_contains_focus_russian_identity(monkeypatch) -> None:
    def _fake_fetch(url: str, timeout_sec: int = 15):
        if url.endswith("/api/dashboard"):
            return (
                {
                    "sources": {"total": 1},
                    "blocks": {"production_total": 247},
                    "chroma": {"count": 247},
                    "governance": {"legacy_sd_active": False},
                },
                {"ok": True, "status_code": 200, "error": None},
            )
        if url.endswith("/api/registry/"):
            return (
                {
                    "total": 1,
                    "sources": [
                        {
                            "source_id": "123__кузница_духа",
                            "title": "Кузница Духа",
                            "author": "Саламат Сарсекенов",
                        }
                    ],
                },
                {"ok": True, "status_code": 200, "error": None},
            )
        return ({}, {"ok": True, "status_code": 200, "error": None})

    monkeypatch.setattr(runtime_smoke_utf8, "_fetch_json", _fake_fetch)
    payload = runtime_smoke_utf8.build_runtime_smoke_utf8_payload(
        base_url="http://127.0.0.1:8003",
        source_prd="PRD-046.0.10-HF1",
    )

    assert payload["summary"]["sources_total"] == 1
    assert payload["summary"]["blocks"] == 247
    assert payload["summary"]["chroma"] == 247
    assert payload["summary"]["legacy_sd_active"] is False
    assert payload["focus_source_identity"]["source_id"] == "123__кузница_духа"
    assert payload["focus_source_identity"]["title"] == "Кузница Духа"
