"""
HTTP-клиент для обращения к Bot_data_base /api/query/.
Единственная точка взаимодействия bot_agent с базой данных.
"""

from __future__ import annotations

import os
import time
import asyncio
import logging
from dataclasses import dataclass
from typing import List, Optional

import httpx

BOT_DB_URL = os.getenv("BOT_DB_URL", "http://localhost:8003")
QUERY_TIMEOUT = float(os.getenv("BOT_DB_TIMEOUT", "10.0"))
logger = logging.getLogger(__name__)


@dataclass
class RetrievedChunk:
    chunk_id: str
    content: str
    score: float
    sd_level: int
    author_id: str
    author_name: str
    source_type: str
    youtube_url: Optional[str]
    start_time: Optional[int]
    end_time: Optional[int]
    block_title: Optional[str]
    keywords: List[str]


class DBApiUnavailableError(RuntimeError):
    def __init__(self, message: str, kind: str = "unknown", status_code: int | None = None):
        super().__init__(message)
        self.kind = kind
        self.status_code = status_code


class DBApiClient:
    """
    Синхронный и асинхронный клиент к Bot_data_base API.
    При недоступности сервиса бросает DBApiUnavailableError.
    """

    def __init__(self, base_url: str = BOT_DB_URL, timeout: float = QUERY_TIMEOUT, retries: int = 2):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.retries = max(1, int(retries))

    def query(
        self,
        query: str,
        top_k: int = 5,
        author_id: Optional[str] = None,
        use_rerank: bool = True,
        search_mode: str = "hybrid",
        **legacy_kwargs,
    ) -> List[RetrievedChunk]:
        sd_level = legacy_kwargs.pop("sd_level", None)
        if sd_level not in (None, 0):
            logger.info("[DB_API] sd_level=%s ignored by retrieval contract v11.0", sd_level)
        if legacy_kwargs:
            logger.debug("[DB_API] ignored legacy kwargs in query(): %s", sorted(legacy_kwargs.keys()))
        payload = {
            "query": query,
            "top_k": top_k,
            "author_id": author_id,
            "use_rerank": use_rerank,
            "search_mode": search_mode,
        }
        last_error: Exception | None = None
        for attempt in range(1, self.retries + 1):
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.post(f"{self.base_url}/api/query/", json=payload)
                    response.raise_for_status()
                    data = response.json()
                    return [RetrievedChunk(**c) for c in data.get("chunks", [])]
            except httpx.ConnectError as exc:
                last_error = exc
            except httpx.TimeoutException as exc:
                last_error = exc
            except httpx.HTTPStatusError as exc:
                last_error = exc
                # retry transient server errors
                if exc.response.status_code not in (500, 502, 503, 504):
                    break
            except httpx.HTTPError as exc:
                last_error = exc
                break

            if attempt < self.retries:
                time.sleep(0.25 * attempt)

        self._raise_unavailable(last_error)

    async def aquery(
        self,
        *,
        query: str,
        top_k: int = 5,
        author_id: Optional[str] = None,
        use_rerank: bool = True,
        search_mode: str = "hybrid",
        **legacy_kwargs,
    ) -> List[RetrievedChunk]:
        sd_level = legacy_kwargs.pop("sd_level", None)
        if sd_level not in (None, 0):
            logger.info("[DB_API] sd_level=%s ignored by async retrieval contract v11.0", sd_level)
        if legacy_kwargs:
            logger.debug("[DB_API] ignored legacy kwargs in aquery(): %s", sorted(legacy_kwargs.keys()))
        payload = {
            "query": query,
            "top_k": top_k,
            "author_id": author_id,
            "use_rerank": use_rerank,
            "search_mode": search_mode,
        }
        last_error: Exception | None = None
        for attempt in range(1, self.retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(f"{self.base_url}/api/query/", json=payload)
                    response.raise_for_status()
                    data = response.json()
                    return [RetrievedChunk(**c) for c in data.get("chunks", [])]
            except httpx.ConnectError as exc:
                last_error = exc
            except httpx.TimeoutException as exc:
                last_error = exc
            except httpx.HTTPStatusError as exc:
                last_error = exc
                if exc.response.status_code not in (500, 502, 503, 504):
                    break
            except httpx.HTTPError as exc:
                last_error = exc
                break

            if attempt < self.retries:
                await asyncio.sleep(0.25 * attempt)

        self._raise_unavailable(last_error)

    def _raise_unavailable(self, last_error: Exception | None) -> None:
        if isinstance(last_error, httpx.ConnectError):
            raise DBApiUnavailableError(
                f"Bot_data_base недоступен: {self.base_url}",
                kind="connect",
            )
        if isinstance(last_error, httpx.TimeoutException):
            raise DBApiUnavailableError(
                f"Таймаут запроса к Bot_data_base ({self.timeout}s)",
                kind="timeout",
            )
        if isinstance(last_error, httpx.HTTPStatusError):
            status = int(last_error.response.status_code)
            body = (last_error.response.text or "").strip()
            if len(body) > 200:
                body = body[:200] + "..."
            msg = f"HTTP {status} from Bot_data_base"
            if body:
                msg = f"{msg}: {body}"
            raise DBApiUnavailableError(msg, kind="http_status", status_code=status)
        if isinstance(last_error, httpx.HTTPError):
            raise DBApiUnavailableError(
                f"HTTP client error: {last_error}",
                kind="http_error",
            )
        raise DBApiUnavailableError("Bot_data_base unavailable", kind="unknown")
