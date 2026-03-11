from pydantic import BaseModel
from typing import Optional


class YouTubeIngestRequest(BaseModel):
    url: str
    author: str
    author_id: str


class BookIngestRequest(BaseModel):
    author: str
    author_id: str
    book_title: str
    language: str = "ru"


class JobResponse(BaseModel):
    job_id: str
    status: str
    progress: int
    current_stage: str
    created_at: str
    finished_at: Optional[str]
    error: Optional[str]
    result: Optional[dict]


class RegistryListResponse(BaseModel):
    total: int
    sources: list


class StatsResponse(BaseModel):
    total_sources: int
    total_blocks: int
    chroma_total: int
    sd_distribution: dict
    sources_by_type: dict
