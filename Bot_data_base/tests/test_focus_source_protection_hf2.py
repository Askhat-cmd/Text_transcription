from __future__ import annotations

from tools import run_live_chroma_runtime_binding_hf2 as runner


def test_focus_source_protection_gate(monkeypatch):
    monkeypatch.setattr(
        runner,
        "_http_json",
        lambda base, method, endpoint, body=None: {
            "ok": True,
            "status_code": 200,
            "body": {
                "sources": [
                    {
                        "source_id": "123__кузница_духа",
                        "blocks_count": 247,
                        "status": "done",
                        "delete_policy": {"state": "protected"},
                        "delete_allowed": False,
                    }
                ]
            },
            "error": None,
        },
    )

    payload = runner._focus_source_protection("http://127.0.0.1:8003", "123__кузница_духа")
    assert payload["focus_source_protected"] is True
    assert payload["focus_source_blocks"] == 247
