from __future__ import annotations

from review.post_apply_quality_gate import build_quality_gate_snapshot


def _base_payloads() -> dict:
    return {
        "data_consistency": {"data_consistency_passed": True},
        "apply_route": {"apply_route_consistency_passed": True},
        "retrieval": {"retrieval_quality_passed": True},
        "writer": {"writer_kb_policy_passed": True},
        "no_mutation": {"all_blocks_merged_mutated": False, "registry_mutated": False},
    }


def test_quality_gate_passed_only_with_admin_passed() -> None:
    payloads = _base_payloads()
    snapshot = build_quality_gate_snapshot(
        source_prd="PRD-046.0.7.2-HF1",
        data_consistency=payloads["data_consistency"],
        apply_route_consistency=payloads["apply_route"],
        retrieval_quality=payloads["retrieval"],
        writer_policy=payloads["writer"],
        admin_runtime={"admin_consistency_passed": True, "admin_runtime_status": "passed"},
        no_mutation_proof=payloads["no_mutation"],
    )
    assert snapshot["quality_gate_passed"] is True
    assert snapshot["diagnostic_center_ready"] is True
    assert snapshot["final_status"] == "passed"


def test_admin_api_blocker_status_mapping() -> None:
    payloads = _base_payloads()
    snapshot = build_quality_gate_snapshot(
        source_prd="PRD-046.0.7.2-HF1",
        data_consistency=payloads["data_consistency"],
        apply_route_consistency=payloads["apply_route"],
        retrieval_quality=payloads["retrieval"],
        writer_policy=payloads["writer"],
        admin_runtime={"admin_consistency_passed": False, "admin_runtime_status": "blocked_admin_api_unavailable"},
        no_mutation_proof=payloads["no_mutation"],
    )
    assert snapshot["quality_gate_passed"] is False
    assert snapshot["diagnostic_center_ready"] is False
    assert snapshot["final_status"] == "done_with_admin_api_blocker"


def test_admin_launch_blocker_status_mapping() -> None:
    payloads = _base_payloads()
    snapshot = build_quality_gate_snapshot(
        source_prd="PRD-046.0.7.2-HF1",
        data_consistency=payloads["data_consistency"],
        apply_route_consistency=payloads["apply_route"],
        retrieval_quality=payloads["retrieval"],
        writer_policy=payloads["writer"],
        admin_runtime={"admin_consistency_passed": False, "admin_runtime_status": "blocked_admin_launch_failed"},
        no_mutation_proof=payloads["no_mutation"],
    )
    assert snapshot["quality_gate_passed"] is False
    assert snapshot["diagnostic_center_ready"] is False
    assert snapshot["final_status"] == "done_with_admin_launch_blocker"


def test_admin_schema_blocker_status_mapping() -> None:
    payloads = _base_payloads()
    snapshot = build_quality_gate_snapshot(
        source_prd="PRD-046.0.7.2-HF1",
        data_consistency=payloads["data_consistency"],
        apply_route_consistency=payloads["apply_route"],
        retrieval_quality=payloads["retrieval"],
        writer_policy=payloads["writer"],
        admin_runtime={"admin_consistency_passed": False, "admin_runtime_status": "failed_schema_validation"},
        no_mutation_proof=payloads["no_mutation"],
    )
    assert snapshot["quality_gate_passed"] is False
    assert snapshot["diagnostic_center_ready"] is False
    assert snapshot["final_status"] == "done_with_admin_schema_blocker"


def test_chroma_count_blocker_status_mapping() -> None:
    payloads = _base_payloads()
    snapshot = build_quality_gate_snapshot(
        source_prd="PRD-046.0.7.2-HF3",
        data_consistency=payloads["data_consistency"],
        apply_route_consistency=payloads["apply_route"],
        retrieval_quality=payloads["retrieval"],
        writer_policy=payloads["writer"],
        admin_runtime={"admin_consistency_passed": False, "admin_runtime_status": "blocked_chroma_count_mismatch"},
        no_mutation_proof=payloads["no_mutation"],
    )
    assert snapshot["quality_gate_passed"] is False
    assert snapshot["diagnostic_center_ready"] is False
    assert snapshot["final_status"] == "done_with_chroma_count_blocker"
