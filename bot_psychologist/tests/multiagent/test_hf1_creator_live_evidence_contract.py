from __future__ import annotations

from pathlib import Path
import sys

CURRENT_FILE = Path(__file__).resolve()
BOT_PSYCHOLOGIST_ROOT = CURRENT_FILE.parents[2]
if str(BOT_PSYCHOLOGIST_ROOT) not in sys.path:
    sys.path.insert(0, str(BOT_PSYCHOLOGIST_ROOT))
from bot_agent.multiagent.contracts.creator_live_evidence_rag_repair_v1 import (
    CreatorLiveTurnProof,
    HF1Decision,
    HF1Scorecard,
    RagToWriterDeliveryProof,
)


def test_hf1_contract_defaults_are_stable() -> None:
    live = CreatorLiveTurnProof().to_dict()
    rag = RagToWriterDeliveryProof().to_dict()
    score = HF1Scorecard().to_dict()
    decision = HF1Decision().to_dict()

    assert live["schema_version"] == "creator_live_turn_proof_v1"
    assert rag["schema_version"] == "rag_to_writer_delivery_proof_v1"
    assert score["schema_version"] == "creator_live_evidence_rag_repair_scorecard_v1"
    assert decision["schema_version"] == "creator_live_evidence_rag_repair_decision_v1"

