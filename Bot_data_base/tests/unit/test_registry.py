from storage.registry import SourceRegistry, SourceRecord


def test_add_and_get(tmp_path):
    reg = SourceRegistry(str(tmp_path / "registry.json"))
    rec = SourceRecord(
        source_id="abc123",
        source_type="youtube",
        title="Test video",
        author="Author",
        author_id="avtor",
        language="ru",
        status="done",
        added_at="2026-01-01",
        processed_at=None,
        blocks_count=10,
        sd_distribution={"GREEN": 8, "BLUE": 2},
        file_paths={},
        error_message=None,
        pipeline_version="v1.0",
    )
    reg.add_source(rec)
    found = reg.get_source("abc123")
    assert found.title == "Test video"


def test_is_processed(tmp_path):
    reg = SourceRegistry(str(tmp_path / "registry.json"))
    assert reg.is_processed("nonexistent") is False


def test_update_status(tmp_path):
    reg = SourceRegistry(str(tmp_path / "registry.json"))
    rec = SourceRecord(
        source_id="abc123",
        source_type="youtube",
        title="Test video",
        author="Author",
        author_id="avtor",
        language="ru",
        status="pending",
        added_at="2026-01-01",
        processed_at=None,
        blocks_count=0,
        sd_distribution={},
        file_paths={},
        error_message=None,
        pipeline_version="v1.0",
    )
    reg.add_source(rec)
    reg.update_status("abc123", "processing")
    assert reg.get_source("abc123").status == "processing"


def test_statistics(tmp_path):
    reg = SourceRegistry(str(tmp_path / "registry.json"))
    stats = reg.get_statistics()
    assert "total_sources" in stats
    assert "total_blocks" in stats
