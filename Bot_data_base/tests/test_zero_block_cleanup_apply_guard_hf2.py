from __future__ import annotations

import json
from pathlib import Path

from tools import run_registry_zero_block_cleanup_hf2 as cleanup_tool


def test_cleanup_apply_guard_blocks_when_gates_failed(tmp_path: Path):
    registry_path = tmp_path / "registry.json"
    registry_payload = [{"source_id": "test123", "status": "archived", "blocks_count": 0}]
    registry_path.write_text(json.dumps(registry_payload, ensure_ascii=False), encoding="utf-8")
    result = cleanup_tool.apply_zero_block_cleanup(
        registry_path=registry_path,
        registry_payload=registry_payload,
        registry_format="list",
        safe_delete_source_ids=["test123"],
        expected_source_id="123__кузница_духа",
        backup_root=tmp_path / "backups",
        chroma_manifest={"status": "ok"},
        gates=cleanup_tool.GateStatus(
            live_preflight_passed=True,
            query_recovery_passed=False,
            bot_runtime_retrieval_passed=True,
            chroma_consistency_passed=True,
        ),
        perform_cleanup=True,
    )
    assert result["cleanup_performed"] is False
    assert result["cleanup_reason"] == "blocked_by_safety_gates"
