import os
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from api.main import app


def _set_env():
    os.environ["BOT_DB_DISABLE_EMBEDDINGS"] = "1"


@pytest.fixture(autouse=True)
def _bot_db_workdir(monkeypatch):
    # Endpoints construct PipelineRunner(config_path="config.yaml"), so tests must
    # run with Bot_data_base as cwd to resolve config deterministically.
    monkeypatch.chdir(Path(__file__).resolve().parents[2])


def _make_client() -> AsyncClient:
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_ingest_youtube_returns_job_id():
    _set_env()
    async with _make_client() as client:
        resp = await client.post(
            "/api/ingest/youtube",
            json={"url": "https://youtube.com/watch?v=test123", "author": "Автор", "author_id": "avtor"},
        )
    assert resp.status_code == 200
    assert "job_id" in resp.json()


@pytest.mark.asyncio
async def test_invalid_youtube_url():
    _set_env()
    async with _make_client() as client:
        resp = await client.post(
            "/api/ingest/youtube",
            json={"url": "https://google.com", "author": "Автор", "author_id": "avtor"},
        )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_list_registry():
    _set_env()
    async with _make_client() as client:
        resp = await client.get("/api/registry/")
    assert resp.status_code == 200
    assert "sources" in resp.json()


@pytest.mark.asyncio
async def test_upload_book(tmp_path):
    _set_env()
    book_content = "# Глава 1\n\nТексь".encode("utf-8")
    async with _make_client() as client:
        resp = await client.post(
            "/api/ingest/book",
            data={"author": "Автор", "author_id": "avtor", "book_title": "Книга", "language": "ru"},
            files={"file": ("book.md", book_content, "text/markdown")},
        )
    assert resp.status_code == 200
    assert "job_id" in resp.json()
