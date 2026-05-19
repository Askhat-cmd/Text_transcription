from __future__ import annotations

import json
from pathlib import Path

from tools import run_botdb_live_recovery_hf2 as runner


def test_chroma_consistency_gate_pass(monkeypatch, tmp_path: Path):
    repo_root = tmp_path
    botdb = repo_root / "Bot_data_base"
    (botdb / "data" / "processed").mkdir(parents=True, exist_ok=True)
    (botdb / "data" / "registry.json").write_text(
        json.dumps([{"source_id": "123__кузница_духа", "blocks_count": 247}], ensure_ascii=False),
        encoding="utf-8",
    )
    blocks = {"blocks": [{"source": "book:123__кузница_духа"} for _ in range(247)]}
    (botdb / "data" / "processed" / "all_blocks_merged.json").write_text(
        json.dumps(blocks, ensure_ascii=False),
        encoding="utf-8",
    )
    (botdb / "config.yaml").write_text("storage:\n  chroma_db_path: data/chroma_db\n", encoding="utf-8")

    def fake_http(base: str, method: str, endpoint: str, body=None, timeout: float = 20.0):
        if endpoint == "/api/registry/":
            return {"status_code": 200, "body": {"sources": [{"source_id": "123__кузница_духа", "blocks_count": 247}]}}
        if endpoint == "/api/dashboard":
            return {"status_code": 200, "body": {"chroma": {"count": 247}}}
        if endpoint == "/api/registry/stats":
            return {"status_code": 200, "body": {"chroma_total": 247}}
        return {"status_code": 200, "body": {}}

    monkeypatch.setattr(runner, "_http_json", fake_http)
    monkeypatch.setattr(
        runner,
        "get_chroma_runtime_health",
        lambda config_path: {"count": 247, "source_ids": ["123__кузница_духа"]},
    )
    payload = runner._chroma_consistency_gate(
        repo_root=repo_root,
        base_url="http://127.0.0.1:8003",
        expected_source_id="123__кузница_духа",
        expected_blocks=247,
        output_dir=tmp_path,
    )
    assert payload["chroma_consistency_passed"] is True
