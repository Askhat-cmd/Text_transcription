from __future__ import annotations

from pathlib import Path
import sys

CURRENT_FILE = Path(__file__).resolve()
BOT_PSYCHOLOGIST_ROOT = CURRENT_FILE.parents[2]
if str(BOT_PSYCHOLOGIST_ROOT) not in sys.path:
    sys.path.insert(0, str(BOT_PSYCHOLOGIST_ROOT))
from bot_agent.multiagent import creator_live_evidence_rag_repair as hf1


def test_hf1_botdb_probe_contract(monkeypatch) -> None:
    def _fake_http_json(**kwargs):
        return (
            200,
            {
                "chunks": [{"chunk_id": "c1", "score": 0.77}],
                "debug": {"botdb_query_route_fallback_used": True},
            },
            None,
        )

    monkeypatch.setattr(hf1, "_http_json", _fake_http_json)
    payload = hf1.probe_botdb_query(query="что такое нейросталкинг", botdb_base_url="http://localhost:8003")

    assert payload["botdb_query_attempted"] is True
    assert payload["botdb_http_status"] == 200
    assert payload["botdb_chunks_returned"] == 1
    assert payload["botdb_query_route_fallback_used"] is True
    assert payload["botdb_query_gate"] == "passed"

