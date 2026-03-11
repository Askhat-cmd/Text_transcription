from chunkers.book_chunker import BookChunker
from utils.text_utils import count_tokens


SAMPLE_MD = """
# Глава 1. Введение в осознанность

Осознанность — это способность человека...
Первый абзац содержит важную информацию о природе ума.

Второй абзац раскрывает практические аспекты медитации.
Здесь описаны конкретные упражнения для начинающих.

# Глава 2. Практика

Регулярная практика позволяет развить навык присутствия.
"""


def test_detects_chapters():
    chunker = BookChunker(config={})
    blocks = chunker.chunk_file_from_text(SAMPLE_MD, "Автор", "Книга", "ru")
    chapter_titles = set(b.chapter_title for b in blocks)
    assert "Глава 1. Введение в осознанность" in chapter_titles
    assert "Глава 2. Практика" in chapter_titles


def test_chunks_not_empty():
    chunker = BookChunker(config={})
    blocks = chunker.chunk_file_from_text(SAMPLE_MD, "Автор", "Книга", "ru")
    for b in blocks:
        assert len(b.text.strip()) > 50


def test_chunk_tokens_within_limits():
    chunker = BookChunker(config={"target_tokens": 200, "min_tokens": 50, "max_tokens": 300, "overlap_tokens": 30})
    long_text = "Это предложение. " * 500
    blocks = chunker.chunk_file_from_text(f"# Глава\n\n{long_text}", "A", "B", "ru")
    for b in blocks:
        assert count_tokens(b.text) <= 330


def test_fallback_no_headers():
    chunker = BookChunker(config={})
    plain_text = "Это текст без заголовков. " * 200
    blocks = chunker.chunk_file_from_text(plain_text, "Автор", "Книга", "ru")
    assert len(blocks) > 0
    assert all(b.text for b in blocks)


def test_chunk_index_sequential():
    chunker = BookChunker(config={})
    blocks = chunker.chunk_file_from_text(SAMPLE_MD, "A", "B", "ru")
    indices = [b.chunk_index for b in blocks]
    assert indices == list(range(len(blocks)))


def test_author_metadata():
    chunker = BookChunker(config={})
    blocks = chunker.chunk_file_from_text(
        SAMPLE_MD,
        "Экхарт Толле",
        "Сила настоящего",
        "ru",
    )
    assert all(b.author == "Экхарт Толле" for b in blocks)
    assert all(b.source_title == "Сила настоящего" for b in blocks)
    assert all(b.source_type == "book" for b in blocks)
