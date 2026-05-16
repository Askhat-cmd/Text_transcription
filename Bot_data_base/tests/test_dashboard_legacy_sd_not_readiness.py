from __future__ import annotations

from api.routes.dashboard import _governance_summary


def test_legacy_sd_presence_does_not_block_readiness() -> None:
    blocks = [
        {
            "metadata": {
                "governance": {
                    "allowed_use": ["writer_context"],
                    "safety_flags": ["not_for_direct_quote"],
                    "sd_distribution": {"GREEN": 1},
                }
            }
        }
    ]

    summary = _governance_summary(blocks)
    assert summary["legacy_sd_active"] is True
    assert summary["readiness"] == "ready"
