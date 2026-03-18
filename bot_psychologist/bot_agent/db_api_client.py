"""
HTTP-клиент для обращения к Bot_data_base /api/query/.
Единственная точка взаимодействия bot_agent с базой данных.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List, Optional

import httpx

BOT_DB_URL = os.getenv("BOT_DB_URL", "http://localhost:8001")
QUERY_TIMEOUT = float(os.getenv("BOT_DB_TIMEOUT", "10.0"))


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
    pass


class DBApiClient:
    """
    Синхронный и асинхронный клиент к Bot_data_base API.
    При недоступности сервиса бросает DBApiUnavailableError.
    """

    def __init__(self, base_url: str = BOT_DB_URL, timeout: float = QUERY_TIMEOUT):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def query(
        self,
        query: str,
        sd_level: int = 0,
        top_k: int = 5,
        author_id: Optional[str] = None,
        use_rerank: bool = True,
        search_mode: str = "hybrid",
    ) -> List[RetrievedChunk]:
        payload = {
            "query": query,
            "sd_level": sd_level,
            "top_k": top_k,
            "author_id": author_id,
            "use_rerank": use_rerank,
            "search_mode": search_mode,
        }
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(f"{self.base_url}/api/query/", json=payload)
                response.raise_for_status()
                data = response.json()
                return [RetrievedChunk(**c) for c in data.get("chunks", [])]
        except httpx.ConnectError:
            raise DBApiUnavailableError(f"Bot_data_base недоступен: {self.base_url}")
        except httpx.TimeoutException:
            raise DBApiUnavailableError(f"Таймаут запроса к Bot_data_base ({self.timeout}s)")
        except httpx.HTTPError as exc:
            raise DBApiUnavailableError(f"Ошибка HTTP Bot_data_base: {exc}")

    async def aquery(self, **kwargs) -> List[RetrievedChunk]:
        payload = {
            "query": kwargs.get("query"),
            "sd_level": kwargs.get("sd_level", 0),
            "top_k": kwargs.get("top_k", 5),
            "author_id": kwargs.get("author_id"),
            "use_rerank": kwargs.get("use_rerank", True),
            "search_mode": kwargs.get("search_mode", "hybrid"),
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(f"{self.base_url}/api/query/", json=payload)
                response.raise_for_status()
                data = response.json()
                return [RetrievedChunk(**c) for c in data.get("chunks", [])]
        except httpx.ConnectError:
            raise DBApiUnavailableError(f"Bot_data_base недоступен: {self.base_url}")
        except httpx.TimeoutException:
            raise DBApiUnavailableError(f"Таймаут запроса к Bot_data_base ({self.timeout}s)")
        except httpx.HTTPError as exc:
            raise DBApiUnavailableError(f"Ошибка HTTP Bot_data_base: {exc}")
