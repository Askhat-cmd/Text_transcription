from chunkers.semantic_chunker import SemanticChunker
from utils.text_utils import count_tokens


def test_basic_chunking():
    chunker = SemanticChunker(config={})
    text = "Первое предложение. " * 50 + "\n\n" + "Второе предложение. " * 50
    blocks = chunker.chunk(text, author="Автор", source_title="Видео", source_id="abc")
    assert len(blocks) >= 1
    assert all(b.source_type == "youtube" for b in blocks)


def test_tokens_within_range():
    chunker = SemanticChunker(config={"min_tokens": 100, "max_tokens": 400})
    text = "Слово " * 1000
    blocks = chunker.chunk(text, "A", "B", "vid1")
    for b in blocks[:-1]:
        assert count_tokens(b.text) <= 450
