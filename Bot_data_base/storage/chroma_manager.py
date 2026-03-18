from __future__ import annotations

import logging
import os
from typing import Dict, List

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

from models.universal_block import UniversalBlock

logger = logging.getLogger(__name__)


class ChromaManager:
    def __init__(self, db_path: str, collection_name: str) -> None:
        self.db_path = db_path
        self.collection_name = collection_name

        settings = Settings(anonymized_telemetry=False, allow_reset=True)
        if db_path == ":memory:":
            self.client = chromadb.EphemeralClient(settings=settings)
        else:
            self.client = chromadb.PersistentClient(path=self.db_path, settings=settings)

        self._collection = self.client.get_or_create_collection(name=self.collection_name)
        self._model = self._init_embedding_model()

    def add_blocks(self, blocks: List[UniversalBlock]) -> int:
        if not blocks:
            return 0
        texts = [b.text for b in blocks]
        embeddings = self._embed_texts(texts)
        ids = [b.block_id for b in blocks]
        metadatas = [self._to_metadata(b) for b in blocks]

        self._collection.add(ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas)
        return len(blocks)

    def delete_source(self, source_id: str) -> int:
        if not source_id:
            return 0
        existing = self._collection.get(where={"source_id": source_id})
        ids = existing.get("ids", []) if existing else []
        if not ids:
            return 0
        self._collection.delete(ids=ids)
        return len(ids)

    def get_stats(self) -> dict:
        data = self._collection.get()
        total = len(data.get("ids", [])) if data else 0
        by_sd_level: Dict[str, int] = {}
        by_source_type: Dict[str, int] = {}
        for meta in data.get("metadatas", []) if data else []:
            sd = meta.get("sd_level") if meta else None
            st = meta.get("source_type") if meta else None
            if sd:
                by_sd_level[sd] = by_sd_level.get(sd, 0) + 1
            if st:
                by_source_type[st] = by_source_type.get(st, 0) + 1
        return {"total": total, "by_sd_level": by_sd_level, "by_source_type": by_source_type}

    def source_exists(self, source_id: str) -> bool:
        if not source_id:
            return False
        res = self._collection.get(where={"source_id": source_id})
        return bool(res and res.get("ids"))

    def _to_metadata(self, block: UniversalBlock) -> dict:
        return {
            "sd_level": block.sd_level,
            "author_id": block.author_id,
            "author": block.author,
            "source_type": block.source_type,
            "language": block.language,
            "complexity": block.complexity,
            "source_id": block.source_id,
            "title": block.title,
            "source_title": block.source_title,
            "chapter_title": block.chapter_title,
            "chunk_index": block.chunk_index,
        }

    def _init_embedding_model(self) -> SentenceTransformer:
        if os.getenv("BOT_DB_DISABLE_EMBEDDINGS") == "1":
            class _DummyModel:
                def encode(self, texts, convert_to_numpy=True):
                    import numpy as np
                    return np.zeros((len(texts), 3), dtype=float)

            return _DummyModel()
        model_name = os.getenv(
            "SENTENCE_TRANSFORMERS_MODEL",
            "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        )
        try:
            return SentenceTransformer(model_name)
        except Exception as exc:
            logger.error(f"[ChromaManager] failed to load embedding model: {exc}")
            raise

    def _embed_texts(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        embeddings = self._model.encode(texts, convert_to_numpy=True)
        if hasattr(embeddings, "tolist"):
            return embeddings.tolist()
        return embeddings
