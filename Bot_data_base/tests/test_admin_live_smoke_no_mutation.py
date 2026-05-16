from __future__ import annotations

import json
from pathlib import Path

from review.admin_live_smoke import run_admin_live_smoke
from review.post_apply_quality_gate import build_no_mutation_proof, sha256_file


def _online_contract_fetch(url: str) -> dict:
    if url.endswith("/api/status"):
        return {"ok": True, "status_code": 200, "body": {"ok": True}, "error": None}
    if url.endswith("/api/registry") or url.endswith("/api/registry/"):
        return {
            "ok": True,
            "status_code": 200,
            "body": {"sources": [{"source_id": "123__кузница_духа", "status": "done", "blocks_count": 247}]},
            "error": None,
        }
    if url.endswith("/api/dashboard") or url.endswith("/api/dashboard/"):
        return {
            "ok": True,
            "status_code": 200,
            "body": {"blocks": {"production_total": 247}, "chroma": {"count": 247}},
            "error": None,
        }
    return {"ok": False, "status_code": None, "body": None, "error": "unknown"}


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def test_live_smoke_does_not_mutate_production_hashes(tmp_path: Path) -> None:
    blocks_path = tmp_path / "all_blocks_merged.json"
    registry_path = tmp_path / "registry.json"
    _write_json(blocks_path, {"blocks": [{"id": "1"}]})
    _write_json(registry_path, [{"source_id": "123__кузница_духа", "status": "done", "blocks_count": 247}])

    before_blocks = sha256_file(blocks_path)
    before_registry = sha256_file(registry_path)

    run_admin_live_smoke(
        admin_base_url="http://127.0.0.1:8000",
        try_start_server=False,
        repo_root=tmp_path,
        http_get=_online_contract_fetch,
    )

    after_blocks = sha256_file(blocks_path)
    after_registry = sha256_file(registry_path)

    proof = build_no_mutation_proof(
        source_prd="PRD-046.0.7.2-HF1",
        blocks_hash_before=before_blocks,
        blocks_hash_after=after_blocks,
        registry_hash_before=before_registry,
        registry_hash_after=after_registry,
    )
    assert proof["all_blocks_merged_mutated"] is False
    assert proof["registry_mutated"] is False
    assert proof["provider_called"] is False
    assert proof["chroma_reindex_performed"] is False
    assert proof["production_apply_performed"] is False
