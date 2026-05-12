import logging
import os
import time
from typing import List, Optional

from fastapi import APIRouter, HTTPException

from api.schemas import QueryRequest, QueryResponse, ChunkResult
from api.retrieval_policy import apply_retrieval_governance_policy
from pipeline_runner import PipelineRunner
from utils.reranker import VoyageReranker

logger = logging.getLogger(__name__)

router = APIRouter()

_runner: PipelineRunner | None = None
chroma_collection = None

SD_LEVEL_TO_INT = {
    "BEIGE": 1,
    "PURPLE": 2,
    "RED": 3,
    "BLUE": 4,
    "ORANGE": 5,
    "GREEN": 6,
    "YELLOW": 7,
    "TURQUOISE": 8,
}


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


def _sd_name_to_int(value: object) -> int:
    if isinstance(value, int):
        return value
    if not isinstance(value, str):
        return 0
    normalized = value.strip().upper()
    return int(SD_LEVEL_TO_INT.get(normalized, 0))


def _build_where_filter(request: QueryRequest) -> tuple[dict, bool]:
    where_filter: dict = {}
    sd_level_ignored = request.sd_level > 0
    if request.author_id:
        where_filter["author_id"] = {"$eq": request.author_id}
    return where_filter, sd_level_ignored


def _split_csv(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    raw = str(value).strip()
    if not raw:
        return []
    return [part.strip() for part in raw.split(",") if part.strip()]


def _parse_bool(value: object) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return None


def _parse_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None


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
    governance_schema = str(meta.get("governance_schema_version") or "").strip()
    enrichment_schema = str(meta.get("llm_enrichment_schema_version") or "").strip()
    governance = {}
    if governance_schema:
        allowed_use = _split_csv(meta.get("governance_allowed_use"))
        governance = {
            "schema_version": governance_schema,
            "chunk_type": str(meta.get("governance_chunk_type") or "").strip(),
            "allowed_use": allowed_use,
            "safety_flags": _split_csv(meta.get("governance_safety_flags")),
            "lens_family": _split_csv(meta.get("governance_lens_family")),
            "low_resource_safe": _parse_bool(meta.get("governance_low_resource_safe")),
            "not_for_direct_quote": _parse_bool(meta.get("governance_not_for_direct_quote")),
            "source_style_not_user_facing": _parse_bool(
                meta.get("governance_source_style_not_user_facing")
            ),
            "internal_use_only": "internal_only" in {item.lower() for item in allowed_use},
            "chunking_quality": {
                "section_role_hint": str(meta.get("section_role_hint") or "").strip(),
                "heading_path_present": bool(str(meta.get("heading_path_text") or "").strip()),
                "mixed_intent_risk": _parse_bool(meta.get("mixed_intent_risk")),
                "mixed_intent_severity": str(meta.get("mixed_intent_severity") or "").strip(),
                "primary_role": str(meta.get("mixed_intent_primary_role") or "").strip(),
                "secondary_role_markers": _split_csv(meta.get("mixed_intent_secondary_roles")),
                "mixed_intent_reason": str(meta.get("mixed_intent_reason") or "").strip(),
                "quality_notes": _split_csv(meta.get("chunking_quality_notes")),
                "split_reason": str(meta.get("split_reason") or "").strip(),
            },
        }
        if enrichment_schema:
            enrichment_payload = {
                "schema_version": enrichment_schema,
                "applied_from_prd": str(meta.get("llm_enrichment_applied_from_prd") or "").strip(),
                "source_overlay": str(meta.get("llm_enrichment_source_overlay") or "").strip(),
                "status": str(meta.get("llm_enrichment_status") or "").strip(),
                "review_status": str(meta.get("llm_enrichment_review_status") or "").strip(),
                "summary": str(meta.get("llm_enrichment_summary") or "").strip(),
                "lens_family_candidates": _split_csv(
                    meta.get("llm_enrichment_lens_family_candidates")
                ),
                "tags": _split_csv(meta.get("llm_enrichment_tags")),
                "use_when": _split_csv(meta.get("llm_enrichment_use_when")),
                "avoid_when": _split_csv(meta.get("llm_enrichment_avoid_when")),
                "self_contained_score": _parse_float(meta.get("llm_enrichment_self_contained_score")),
                "self_contained_reason": str(
                    meta.get("llm_enrichment_self_contained_reason") or ""
                ).strip(),
                "confidence": _parse_float(meta.get("llm_enrichment_confidence")),
                "needs_human_review": _parse_bool(meta.get("llm_enrichment_needs_human_review")),
                "review_reasons": _split_csv(meta.get("llm_enrichment_review_reasons")),
                "llm_metadata": {
                    "provider": str(meta.get("llm_enrichment_provider") or "").strip(),
                    "model": str(meta.get("llm_enrichment_model") or "").strip(),
                    "prompt_version": str(meta.get("llm_enrichment_prompt_version") or "").strip(),
                    "mock": _parse_bool(meta.get("llm_enrichment_mock")),
                },
            }
            governance["llm_enrichment"] = enrichment_payload
            governance["llm_enrichment_summary"] = enrichment_payload["summary"]
            governance["llm_enrichment_tags"] = list(enrichment_payload["tags"])
            governance["llm_enrichment_use_when"] = list(enrichment_payload["use_when"])
            governance["llm_enrichment_avoid_when"] = list(enrichment_payload["avoid_when"])
            governance["llm_enrichment_confidence"] = enrichment_payload["confidence"]
            governance["llm_enrichment_review_status"] = enrichment_payload["review_status"]
            governance["llm_enrichment_needs_human_review"] = enrichment_payload[
                "needs_human_review"
            ]

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
        governance=governance,
    )


@router.post("/", response_model=QueryResponse)
async def semantic_query(request: QueryRequest) -> QueryResponse:
    """
    Семантический поиск по ChromaDB с SD-фильтром и Voyage Rerank.
    Основной эндпоинт для bot_psychologist.
    """
    start_ts = time.time()
    where_filter, sd_level_ignored = _build_where_filter(request)
    sd_filter_applied = False

    raw_fetch_k = max(int(request.pre_filter_k), int(request.top_k) * 3, int(request.top_k) + 10)

    try:
        collection = _get_collection()
        query_embedding = _get_runner().chroma_manager._embed_texts([request.query])
    except Exception as exc:
        logger.error("[QUERY] ChromaDB unavailable: %s", exc)
        raise HTTPException(status_code=503, detail="ChromaDB unavailable")

    def _query_collection(active_filter: Optional[dict]):
        return collection.query(
            query_embeddings=query_embedding,
            n_results=raw_fetch_k,
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
    if request.sd_level > 0:
        logger.info(
            "[QUERY] legacy sd_level=%s ignored (SD decommission, no active filter)",
            request.sd_level,
        )

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

    # Top-K + retrieval governance policy.
    candidates = sorted(candidates, key=lambda c: float(c.get("score") or 0.0), reverse=True)
    top_candidates, policy_trace = apply_retrieval_governance_policy(
        request.query,
        candidates,
        top_k=int(request.top_k),
    )

    chunks = [_build_chunk_result(c) for c in top_candidates]
    total_found = len(top_candidates)
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
            "raw_fetch_k": raw_fetch_k,
            "legacy_sd_deprecated": True,
            "sd_filter_applied": False,
            "sd_level_ignored": sd_level_ignored,
            "retrieval_policy_trace": policy_trace,
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
