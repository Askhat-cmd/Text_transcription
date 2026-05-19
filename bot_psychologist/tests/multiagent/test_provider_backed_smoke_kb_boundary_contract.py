from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_provider_backed_smoke_readiness as readiness


def test_provider_backed_smoke_kb_boundary_contract_forbids_quotes() -> None:
    payload = readiness.build_kb_boundary_contract()
    assert payload["kuznitsa_duha_role"] == "internal_lens_library"
    assert payload["raw_kb_quote_allowed"] is False
    assert payload["kuznitsa_authority_citation_allowed"] is False
