import logging
import os
import time
from typing import List, Optional

from fastapi import APIRouter, HTTPException

from api.schemas import QueryRequest, QueryResponse, ChunkResult
from pipeline_runner import PipelineRunner
from utils.reranker import VoyageReranker

logger = logging.getLogger(__name__)

router = APIRouter()

_runner: PipelineRunner | None = None
chroma_collection = None

SD_LEVELS_ORDER = [
    "BEIGE",
    "PURPLE",
    "RED",
    "BLUE",
    "ORANGE",
    "GREEN",
    "YELLOW",
    "TURQUOISE",
]


def _get_runner() -> PipelineRunner:
    global _runner
    if _runner is None:
        _runner = PipelineRunner(config_path="config.yaml")
    return _runner


def _get_collection():
    global chroma_collection
    if chroma_collection is None:
        chroma_collection = _get_runner().chroma_manager._collection
    return chroma_collection


def _sd_int_to_names(sd_level: int) -> List[str]:
    if sd_level <= 0:
        return []
    allowed = [sd_level - 1, sd_level, sd_level + 1]
    allowed = [l for l in allowed if 1 <= l <= 8]
    return [SD_LEVELS_ORDER[l - 1] for l in allowed]


def _sd_name_to_int(value: object) -> int:
    if isinstance(value, int):
        return value
    if not isinstance(value, str):
        return 0
    normalized = value.strip().upper()
    if normalized in SD_LEVELS_ORDER:
        return SD_LEVELS_ORDER.index(normalized) + 1
    return 0


def _build_where_filter(request: QueryRequest) -> dict:
    where_filter: dict = {}
    if request.sd_level > 0:
        allowed_names = _sd_int_to_names(request.sd_level)
        if allowed_names:
            where_filter["sd_level"] = {"$in": allowed_names}
    if request.author_id:
        where_filter["author_id"] = {"$eq": request.author_id}
    return where_filter


def _extract_candidates(results: dict) -> List[dict]:
    documents = (results.get("documents") or [[]])[0]
    metadatas = (results.get("metadatas") or [[]])[0]
    distances = (results.get("distances") or [[]])[0]
    ids = (results.get("ids") or [[]])[0]

    candidates = []
    for idx, content in enumerate(documents):
        meta = metadatas[idx] if idx < len(metadatas) else {}
        distance = distances[idx] if idx < len(distances) else None
        block_id = ids[idx] if idx < len(ids) else meta.get("block_id") or ""
        candidates.append(
            {
                "chunk_id": block_id,
                "content": content or "",
                "metadata": meta or {},
                "distance": distance,
            }
        )
    return candidates


def _apply_hybrid_scores(query: str, candidates: List[dict]) -> None:
    if not candidates:
        return
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
    except Exception as exc:
        logger.warning("[QUERY] TF-IDF unavailable, fallback to semantic only: %s", exc)
        for c in candidates:
            distance = c.get("distance")
            c["score"] = float(1.0 - distance) if distance is not None else 0.0
        return

    texts = [c["content"] for c in candidates]
    vectorizer = TfidfVectorizer(
        analyzer="char_wb",
        ngram_range=(2, 4),
        max_features=8000,
        lowercase=True,
        strip_accents="unicode",
    )
    tfidf_matrix = vectorizer.fit_transform(texts)
    query_vec = vectorizer.transform([query])
    tfidf_scores = cosine_similarity(query_vec, tfidf_matrix).flatten()

    for i, c in enumerate(candidates):
        distance = c.get("distance")
        semantic_score = float(1.0 - distance) if distance is not None else 0.0
        tfidf_score = float(tfidf_scores[i]) if i < len(tfidf_scores) else 0.0
        c["score"] = 0.7 * semantic_score + 0.3 * tfidf_score


def _apply_semantic_scores(candidates: List[dict]) -> None:
    for c in candidates:
        distance = c.get("distance")
        c["score"] = float(1.0 - distance) if distance is not None else 0.0


def _build_chunk_result(candidate: dict) -> ChunkResult:
    meta = candidate.get("metadata") or {}
    sd_value = _sd_name_to_int(meta.get("sd_level"))
    author_name = meta.get("author") or meta.get("author_name") or ""
    if not author_name and meta.get("source_id"):
        try:
            source = _get_runner().registry.get_source(meta.get("source_id"))
            if source:
                author_name = source.author
        except Exception:
            author_name = author_name or ""
    return ChunkResult(
        chunk_id=candidate.get("chunk_id") or "",
        content=candidate.get("content") or "",
        score=float(candidate.get("score") or 0.0),
        sd_level=sd_value,
        author_id=meta.get("author_id") or "",
        author_name=author_name,
        source_type=meta.get("source_type") or "book",
        youtube_url=meta.get("youtube_url"),
        start_time=meta.get("start_time"),
        end_time=meta.get("end_time"),
        block_title=meta.get("title") or meta.get("chapter_title") or meta.get("source_title"),
        keywords=meta.get("keywords") or [],
    )


@router.post("/", response_model=QueryResponse)
async def semantic_query(request: QueryRequest) -> QueryResponse:
    """
    Семантический поиск по ChromaDB с SD-фильтром и Voyage Rerank.
    Основной эндпоинт для bot_psychologist.
    """
    start_ts = time.time()
    where_filter = _build_where_filter(request)
    sd_filter_applied = request.sd_level > 0 and bool(where_filter.get("sd_level"))

    try:
        collection = _get_collection()
        query_embedding = _get_runner().chroma_manager._embed_texts([request.query])
    except Exception as exc:
        logger.error("[QUERY] ChromaDB unavailable: %s", exc)
        raise HTTPException(status_code=503, detail="ChromaDB unavailable")

    def _query_collection(active_filter: Optional[dict]):
        return collection.query(
            query_embeddings=query_embedding,
            n_results=request.pre_filter_k,
            where=active_filter if active_filter else None,
            include=["documents", "metadatas", "distances"],
        )

    try:
        results = _query_collection(where_filter)
        candidates = _extract_candidates(results)
    except Exception as exc:
        logger.error("[QUERY] Chroma query failed: %s", exc)
        raise HTTPException(status_code=503, detail="ChromaDB unavailable")

    # Fallback: если SD-фильтр дал слишком мало результатов
    if request.sd_level > 0 and len(candidates) < 2:
        logger.warning(
            "[QUERY] SD-filter fallback: sd_level=%s results=%s -> retry without filter",
            request.sd_level,
            len(candidates),
        )
        sd_filter_applied = False
        try:
            results = _query_collection(
                {"author_id": where_filter["author_id"]}
                if where_filter.get("author_id")
                else None
            )
            candidates = _extract_candidates(results)
        except Exception as exc:
            logger.error("[QUERY] Chroma query failed on fallback: %s", exc)
            raise HTTPException(status_code=503, detail="ChromaDB unavailable")

    # Scoring
    if request.search_mode == "hybrid":
        _apply_hybrid_scores(request.query, candidates)
    else:
        _apply_semantic_scores(candidates)

    # Rerank
    reranked = False
    if request.use_rerank and candidates:
        reranker = VoyageReranker()
        try:
            indices = reranker.rerank(
                request.query,
                [c["content"] for c in candidates],
                top_k=min(request.top_k, len(candidates)),
            )
            if getattr(reranker, "_client", None) is not None:
                reranked = True
            if indices:
                candidates = [candidates[i] for i in indices if i < len(candidates)]
        except Exception as exc:
            logger.warning("[QUERY] Voyage rerank failed: %s", exc)
            reranked = False

    # Top-K
    candidates = sorted(candidates, key=lambda c: float(c.get("score") or 0.0), reverse=True)
    top_candidates = candidates[: request.top_k]

    chunks = [_build_chunk_result(c) for c in top_candidates]
    total_found = len(candidates)
    query_time_ms = int((time.time() - start_ts) * 1000)

    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logger.info(
        "[QUERY] time_ms=%s total=%s reranked=%s sd_level=%s search_mode=%s",
        query_time_ms,
        total_found,
        reranked,
        request.sd_level,
        request.search_mode,
    )

    debug_payload = None
    if log_level == "DEBUG":
        debug_payload = {
            "where_filter": where_filter,
            "candidates": len(candidates),
            "pre_filter_k": request.pre_filter_k,
        }

    return QueryResponse(
        chunks=chunks,
        total_found=total_found,
        reranked=reranked,
        search_mode=request.search_mode,
        sd_filter_applied=sd_filter_applied,
        query_time_ms=query_time_ms,
        debug=debug_payload,
    )
