from pydantic import BaseModel, Field
from typing import Optional, List, Literal


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


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    sd_level: int = Field(default=0, ge=0, le=8)
    top_k: int = Field(default=5, ge=1, le=50)
    pre_filter_k: int = Field(default=20, ge=5, le=100)
    author_id: Optional[str] = None
    use_rerank: bool = True
    search_mode: Literal["semantic", "hybrid"] = "hybrid"


class ChunkResult(BaseModel):
    chunk_id: str
    content: str
    score: float
    sd_level: int
    author_id: str
    author_name: str
    source_type: Literal["youtube", "book"]
    youtube_url: Optional[str] = None
    start_time: Optional[int] = None
    end_time: Optional[int] = None
    block_title: Optional[str] = None
    keywords: List[str]


class QueryResponse(BaseModel):
    chunks: List[ChunkResult]
    total_found: int
    reranked: bool
    search_mode: str
    sd_filter_applied: bool
    query_time_ms: int
    debug: Optional[dict] = None
