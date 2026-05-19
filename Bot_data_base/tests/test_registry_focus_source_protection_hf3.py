from __future__ import annotations

from types import SimpleNamespace

from api.routes import registry


def test_focus_source_stays_protected():
    policy = registry._resolve_delete_policy(
        {
            "source_id": "123__кузница_духа",
            "source_type": "book",
            "title": "Кузница Духа",
            "status": "done",
            "blocks_count": 247,
        },
        production_source_ids={"123__кузница_духа"},
        runner=SimpleNamespace(),
    )
    assert policy["allowed"] is False
    assert policy["state"] == "protected"
