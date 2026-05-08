import numpy as np

from models.universal_block import UniversalBlock
from storage.chroma_manager import ChromaManager


class DummyModel:
    def encode(self, texts, convert_to_numpy=True):
        return np.zeros((len(texts), 3), dtype=float)


def test_chroma_metadata_contains_flat_governance_fields(monkeypatch) -> None:
    monkeypatch.setattr(ChromaManager, "_init_embedding_model", lambda self: DummyModel())
    manager = ChromaManager(":memory:", "gov_test")

    block = UniversalBlock(
        text="Практика дыхания",
        title="Практика",
        source_type="book",
        source_id="src",
        author="Author",
        sd_level="GREEN",
        heading_path=["Manual", "Практика"],
        section_role_hint="practice",
        boundary_confidence=0.92,
        split_reason="practice_preserved",
        parent_section_id="src::section::0::abc",
        governance={
            "schema_version": "governance_v1",
            "chunk_type": "practice",
            "allowed_use": ["diagnostic_lens", "practice_suggestion", "writer_context"],
            "safety_flags": ["requires_grounding", "not_for_direct_quote"],
            "lens_family": ["somatic", "avoidance"],
            "practice_metadata": {"low_resource_safe": True},
        },
        chunking_quality={
            "quality_notes": ["ok"],
            "mixed_intent_risk": False,
        },
    )

    meta = manager._to_metadata(block)
    assert meta["governance_schema_version"] == "governance_v1"
    assert meta["governance_chunk_type"] == "practice"
    assert meta["governance_allowed_use"] == "diagnostic_lens,practice_suggestion,writer_context"
    assert meta["governance_safety_flags"] == "requires_grounding,not_for_direct_quote"
    assert meta["governance_lens_family"] == "somatic,avoidance"
    assert meta["governance_low_resource_safe"] == "true"
    assert meta["governance_not_for_direct_quote"] == "true"
    assert meta["heading_path_text"] == "Manual > Практика"
    assert meta["section_role_hint"] == "practice"
    assert meta["split_reason"] == "practice_preserved"
    assert meta["mixed_intent_risk"] == "false"
