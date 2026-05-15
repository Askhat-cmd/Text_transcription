from __future__ import annotations

from tools.real_provider_enrichment_run import _pick_pilot_inventory


def test_pick_pilot_inventory_prefers_target_types() -> None:
    items = [
        {"block_id": "1", "chunk_type": "practice"},
        {"block_id": "2", "chunk_type": "lens"},
        {"block_id": "3", "chunk_type": "quote"},
        {"block_id": "4", "chunk_type": "case"},
        {"block_id": "5", "chunk_type": "theory"},
        {"block_id": "6", "chunk_type": "style"},
    ]
    inv = {"items": items}
    out = _pick_pilot_inventory(inv, limit=5)
    picked = {x["chunk_type"] for x in out["items"]}
    assert {"practice", "lens", "quote", "case", "theory"}.issubset(picked)

