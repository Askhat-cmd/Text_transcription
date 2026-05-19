from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_provider_backed_limited_smoke_execution as execution


def test_provider_backed_limited_smoke_kb_boundary() -> None:
    passed = execution.build_safety_kb_boundary_review(
        aggregate={
            "raw_kb_quote_exposure_count": 0,
            "kuznitsa_authority_citation_count": 0,
            "high_stakes_directive_advice_count": 0,
        }
    )
    assert passed["safety_kb_boundary_status"] == "passed"
    failed = execution.build_safety_kb_boundary_review(
        aggregate={
            "raw_kb_quote_exposure_count": 1,
            "kuznitsa_authority_citation_count": 0,
            "high_stakes_directive_advice_count": 0,
        }
    )
    assert failed["safety_kb_boundary_status"] == "failed"
