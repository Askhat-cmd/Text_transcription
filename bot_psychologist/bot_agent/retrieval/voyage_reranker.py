"""Voyage reranker wrapper with graceful local fallback."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Sequence, Tuple

from ..config import config

logger = logging.getLogger(__name__)


@dataclass
class RerankItem:
    """Document item for reranking."""

    text: str
    payload: object
    score: float = 0.0


class VoyageReranker:
    """Rerank candidate items using Voyage API when available."""

    _logged_disabled_reason: bool = False
    _logged_enabled: bool = False

    def __init__(self, model: str = "rerank-2", enabled: bool = True) -> None:
        self.model = model
        self.enabled = enabled
        self.api_key = getattr(config, "VOYAGE_API_KEY", None)

    def rerank(self, query: str, items: Sequence[RerankItem], top_k: int = 1) -> List[RerankItem]:
        if not items:
            return []
        if not self.enabled or not self.api_key:
            if not VoyageReranker._logged_disabled_reason:
                VoyageReranker._logged_disabled_reason = True
                logger.info(
                    "[VOYAGE] rerank disabled (enabled=%s, has_api_key=%s). Using local score sort fallback.",
                    bool(self.enabled),
                    bool(self.api_key),
                )
            # Preserve candidate diversity when Voyage rerank is unavailable.
            return sorted(items, key=lambda x: x.score, reverse=True)

        try:
            import voyageai  # type: ignore

            if not VoyageReranker._logged_enabled:
                VoyageReranker._logged_enabled = True
                logger.info("[VOYAGE] rerank enabled (model=%s). Calling Voyage API.", self.model)

            client = voyageai.Client(api_key=self.api_key)
            texts = [item.text for item in items]
            result = client.rerank(
                model=self.model,
                query=query,
                documents=texts,
                top_k=top_k,
            )
            reranked: List[RerankItem] = []
            for hit in result.results:
                item = items[hit.index]
                reranked.append(
                    RerankItem(
                        text=item.text,
                        payload=item.payload,
                        score=float(hit.relevance_score),
                    )
                )
            return reranked
        except Exception as exc:
            logger.warning("Voyage rerank fallback: %s: %s", type(exc).__name__, exc)
            # Preserve candidate diversity in local fallback.
            return sorted(items, key=lambda x: x.score, reverse=True)

    def rerank_pairs(
        self,
        query: str,
        candidates: Sequence[Tuple[object, float]],
        top_k: int = 1,
    ) -> List[Tuple[object, float]]:
        items = [
            RerankItem(
                text=getattr(block, "summary", "") or getattr(block, "title", ""),
                payload=block,
                score=float(score),
            )
            for block, score in candidates
        ]
        reranked = self.rerank(query, items, top_k=top_k)
        return [(item.payload, item.score) for item in reranked]
