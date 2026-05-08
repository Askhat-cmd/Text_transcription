from models.universal_block import UniversalBlock


def test_universal_block_defaults():
    block = UniversalBlock(text="Test", author="Author")
    assert block.block_id != ""
    assert block.sd_level == "GREEN"
    assert block.source_type == ""


def test_to_bot_format_has_required_fields():
    block = UniversalBlock(
        text="Consciousness is important",
        sd_level="GREEN",
        complexity=0.4,
        author="Author",
        source_type="youtube",
        heading_path=["Root", "Section"],
        section_role_hint="theory",
        boundary_confidence=0.6,
        split_reason="theory_budget_split",
        parent_section_id="src::section::0::abc",
    )
    bot_fmt = block.to_bot_format()
    assert "text" in bot_fmt
    assert "sd_level" in bot_fmt
    assert "complexity" in bot_fmt
    assert "source" in bot_fmt
    assert "metadata" in bot_fmt
    assert bot_fmt["sd_level"] == "GREEN"
    assert bot_fmt["metadata"]["heading_path"] == ["Root", "Section"]


def test_to_dict_serializable():
    import json

    block = UniversalBlock(text="test")
    d = block.to_dict()
    json.dumps(d)
