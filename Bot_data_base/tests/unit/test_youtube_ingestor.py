from ingestors.youtube_ingestor import YouTubeIngestor


def test_extract_video_id_standard():
    ing = YouTubeIngestor()
    assert ing.extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"


def test_extract_video_id_short():
    ing = YouTubeIngestor()
    assert ing.extract_video_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"


def test_extract_video_id_invalid():
    ing = YouTubeIngestor()
    assert ing.extract_video_id("https://google.com") is None


def test_clean_subtitle_removes_timestamps():
    ing = YouTubeIngestor()
    raw = "00:00:01.000 --> 00:00:03.000\nПривет мир\n\n00:00:04.000 --> 00:00:06.000\nКак дела"
    clean = ing._clean_subtitle_text(raw)
    assert "00:00" not in clean
    assert "Привет мир" in clean
