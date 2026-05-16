from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

from review.post_apply_quality_gate import build_no_mutation_proof


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def test_no_mutation_proof_reports_clean_hashes(tmp_path: Path) -> None:
    blocks = tmp_path / "blocks.json"
    registry = tmp_path / "registry.json"
    _write_json(blocks, {"blocks": [{"id": "b1"}]})
    _write_json(registry, [{"source_id": "123__кузница_духа"}])
    blocks_before = _sha(blocks)
    registry_before = _sha(registry)

    proof = build_no_mutation_proof(
        source_prd="PRD-046.0.7.2",
        blocks_hash_before=blocks_before,
        blocks_hash_after=blocks_before,
        registry_hash_before=registry_before,
        registry_hash_after=registry_before,
    )
    assert proof["all_blocks_merged_mutated"] is False
    assert proof["registry_mutated"] is False
    assert proof["provider_called"] is False
    assert proof["chroma_reindex_performed"] is False


def test_no_mutation_proof_detects_changed_hashes() -> None:
    proof = build_no_mutation_proof(
        source_prd="PRD-046.0.7.2",
        blocks_hash_before="a",
        blocks_hash_after="b",
        registry_hash_before="c",
        registry_hash_after="d",
    )
    assert proof["all_blocks_merged_mutated"] is True
    assert proof["registry_mutated"] is True
