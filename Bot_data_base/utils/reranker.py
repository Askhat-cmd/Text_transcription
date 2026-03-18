import logging
import os
from typing import List

logger = logging.getLogger(__name__)

try:
    import voyageai  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    from types import SimpleNamespace
    voyageai = SimpleNamespace(Client=None)


class VoyageReranker:
    """
    Обёртка над Voyage AI rerank API.
    При недоступности API возвращает исходный порядок (graceful degradation).
    """

    MODEL = "rerank-2"

    def __init__(self, model: str | None = None) -> None:
        self.model = model or self.MODEL
        api_key = os.getenv("VOYAGE_API_KEY")
        if not api_key:
            logger.warning("VOYAGE_API_KEY не задан, rerank отключён")
            self._client = None
            return
        if not getattr(voyageai, "Client", None):
            logger.warning("voyageai не установлен, rerank отключён")
            self._client = None
            return
        self._client = voyageai.Client(api_key=api_key)

    def rerank(self, query: str, documents: List[str], top_k: int = 5) -> List[int]:
        if not documents:
            return []
        top_k = max(1, min(int(top_k), len(documents)))
        if self._client is None:
            return list(range(top_k))
        try:
            result = self._client.rerank(
                model=self.model,
                query=query,
                documents=documents,
                top_k=top_k,
            )
            return [hit.index for hit in result.results]
        except Exception as exc:
            logger.warning("[VoyageReranker] API error: %s", exc)
            return list(range(top_k))
