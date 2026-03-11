from models.universal_block import UniversalBlock
from processors.block_normalizer import BlockNormalizer


def test_sets_total_chunks():
    blocks = [UniversalBlock(text=f"Текст {i}", author="A") for i in range(5)]
    normalizer = BlockNormalizer()
    result = normalizer.normalize(blocks)
    assert all(b.total_chunks == 5 for b in result)


def test_auto_title():
    block = UniversalBlock(
        text="Осознанность это важный навык для современного человека",
        title="",
        author="A",
    )
    normalizer = BlockNormalizer()
    result = normalizer.normalize([block])
    assert result[0].title != ""


def test_invalid_sd_level():
    block = UniversalBlock(text="test", sd_level="INVALID", author="A")
    normalizer = BlockNormalizer()
    errors = normalizer.validate_block(block)
    assert len(errors) > 0
