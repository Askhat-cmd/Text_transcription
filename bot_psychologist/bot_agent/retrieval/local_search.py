"""Local retrieval adapter over existing TF-IDF retriever."""

from __future__ import annotations

from typing import List, Optional, Tuple

from ..retriever import get_retriever


class LocalSearch:
    """Thin adapter to keep retrieval layer API stable."""

    def __init__(self, top_k_default: int = 7) -> None:
        self.top_k_default = top_k_default

    def search(self, query: str, top_k: Optional[int] = None) -> List[Tuple[object, float]]:
        retriever = get_retriever()
        return retriever.retrieve(query, top_k=top_k or self.top_k_default)
