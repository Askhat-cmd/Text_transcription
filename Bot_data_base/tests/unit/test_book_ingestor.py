from ingestors.book_ingestor import BookIngestor


def test_validate_supported_format(tmp_path):
    f = tmp_path / "book.txt"
    f.write_text("Текст книги", encoding="utf-8")
    ing = BookIngestor()
    valid, err = ing.validate_file(str(f))
    assert valid


def test_validate_unsupported_format(tmp_path):
    f = tmp_path / "book.pdf"
    f.write_bytes(b"%PDF")
    ing = BookIngestor()
    valid, err = ing.validate_file(str(f))
    assert not valid
    assert "pdf" in err.lower()


def test_load_utf8(tmp_path):
    f = tmp_path / "book.txt"
    f.write_text("Осознанность — это навык", encoding="utf-8")
    ing = BookIngestor()
    text = ing.load_text(str(f))
    assert "Осознанность" in text


def test_load_cp1251(tmp_path):
    f = tmp_path / "book.txt"
    f.write_bytes("Осознанность".encode("cp1251"))
    ing = BookIngestor()
    text = ing.load_text(str(f))
    assert "Осознанность" in text
