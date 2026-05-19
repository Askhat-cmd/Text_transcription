from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_provider_backed_limited_smoke_execution as execution


def test_provider_backed_limited_smoke_hard_stop() -> None:
    hard_stop = execution.build_hard_stop_evaluation(
        provider_budget={"provider_calls_performed": 6, "provider_calls_for_normal_users": 0, "provider_error_leak_to_user_output": False},
        normal_controls={"normal_user_apply_count": 0},
        quality_review={"quality_status": "passed"},
        safety_review={
            "raw_kb_quote_exposure_count": 0,
            "kuznitsa_authority_citation_count": 0,
            "content_full_exposure_count": 0,
            "high_stakes_directive_advice_count": 0,
            "safety_regression_count": 0,
            "kb_boundary_violation_count": 0,
        },
        trace_review={"trace_sanitization_status": "passed"},
        rollback_postcheck={"rollback_failure_count": 0, "stale_apply_after_force_disabled_count": 0},
        live_preflight={"query_http_200": True, "semantic_fallback_used": False, "dashboard_chroma_count": 247, "registry_sources_count": 1},
        provider_output_review={"raw_provider_payload_committed": False},
        production_mutation_detected=False,
    )
    assert hard_stop["hard_stop_triggered"] is True
