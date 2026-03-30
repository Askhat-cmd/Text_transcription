"""Embedding provider abstraction for pluggable embedding backends."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List


class EmbeddingProvider(ABC):
    """Unified embedding interface used by bot components."""

    @abstractmethod
    def embed_query(self, text: str) -> List[float]:
        """Return embedding vector for search query text."""

    @abstractmethod
    def embed_passages(self, texts: List[str]) -> List[List[float]]:
        """Return embedding vectors for passage/document texts."""

    @abstractmethod
    def model_name(self) -> str:
        """Return provider model name."""


class SentenceTransformerEmbeddingProvider(EmbeddingProvider):
    """Generic sentence-transformers provider without special prefixes."""

    def __init__(self, model_name: str, device: str = "auto", normalize: bool = True):
        from sentence_transformers import SentenceTransformer

        self._model_name = model_name
        self._device = self._resolve_device(device)
        self._model = SentenceTransformer(model_name, device=self._device)
        self._normalize = bool(normalize)

    @staticmethod
    def _resolve_device(device: str) -> str:
        if device and device != "auto":
            return device
        try:
            import torch

            if torch.cuda.is_available():
                return "cuda"
            if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                return "mps"
        except Exception:
            pass
        return "cpu"

    @staticmethod
    def _to_list(vectors):
        try:
            return vectors.tolist()
        except Exception:
            return vectors

    def embed_query(self, text: str) -> List[float]:
        vec = self._model.encode(
            text,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=self._normalize,
        )
        return self._to_list(vec)

    def embed_passages(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        vecs = self._model.encode(
            texts,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=self._normalize,
        )
        return self._to_list(vecs)

    def model_name(self) -> str:
        return self._model_name


class E5EmbeddingProvider(SentenceTransformerEmbeddingProvider):
    """
    E5 provider with required prefixes:
    - query: "query: <text>"
    - passages: "passage: <text>"
    """

    def __init__(self, model_name: str = "intfloat/multilingual-e5-base", device: str = "auto"):
        lowered = (model_name or "").lower()
        if "large" in lowered:
            # PRD constraint: warn/fail for e5-large without GPU by default.
            try:
                import torch

                has_gpu = torch.cuda.is_available()
            except Exception:
                has_gpu = False
            if not has_gpu and device != "cpu":
                raise RuntimeError(
                    f"{model_name} requires CUDA for practical use. "
                    "Set EMBEDDING_DEVICE=cpu explicitly if you really want CPU mode."
                )

        super().__init__(model_name=model_name, device=device, normalize=True)

    def embed_query(self, text: str) -> List[float]:
        return super().embed_query(f"query: {text}")

    def embed_passages(self, texts: List[str]) -> List[List[float]]:
        prefixed = [f"passage: {t}" for t in texts]
        return super().embed_passages(prefixed)


def create_embedding_provider(
    model_name: str,
    device: str = "auto",
) -> EmbeddingProvider:
    """Factory for embedding provider selection by model name."""
    lowered = (model_name or "").lower()
    if "e5" in lowered:
        return E5EmbeddingProvider(model_name=model_name, device=device)
    return SentenceTransformerEmbeddingProvider(model_name=model_name, device=device)

