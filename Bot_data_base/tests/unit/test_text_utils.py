from utils.text_utils import count_tokens, clean_text, detect_language


def test_count_tokens():
    n = count_tokens("Привет мир")
    assert isinstance(n, int)
    assert n > 0


def test_clean_text():
    dirty = "Привет   \n\n\n  мир  "
    clean = clean_text(dirty)
    assert "\n\n\n" not in clean
    assert clean.strip() == clean


def test_detect_language_ru():
    assert detect_language("Осознанность это важно") == "ru"


def test_detect_language_en():
    assert detect_language("Consciousness is important") == "en"
