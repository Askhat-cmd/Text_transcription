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
    def __init__(
        self,
        db_path: str,
        collection_name: str,
        embedding_model_name: str | None = None,
    ) -> None:
        self.db_path = db_path
        self.collection_name = collection_name
        self.embedding_model_name = (
            str(embedding_model_name).strip()
            if embedding_model_name is not None and str(embedding_model_name).strip()
            else os.getenv(
                "SENTENCE_TRANSFORMERS_MODEL",
                "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
            )
        )

        settings = Settings(anonymized_telemetry=False, allow_reset=True)
        if db_path == ":memory:":
            self.client = chromadb.EphemeralClient(settings=settings)
        else:
            self.client = chromadb.PersistentClient(path=self.db_path, settings=settings)

        self._collection = self.client.get_or_create_collection(name=self.collection_name)
        self._model = self._init_embedding_model()

    def probe_collection_health(self) -> dict:
        collection_exists = False
        collection_count = None
        collection_count_error = None
        collection_dimension_detected = None
        collection_dimension_detection_reason = "not_available"

        try:
            names = []
            try:
                collections = self.client.list_collections()
            except Exception:
                collections = []
            for collection in collections:
                if hasattr(collection, "name"):
                    names.append(str(collection.name))
                elif isinstance(collection, str):
                    names.append(collection)
            collection_exists = self.collection_name in names
        except Exception:
            collection_exists = False

        try:
            collection_count = int(self._collection.count())
        except Exception as exc:
            collection_count_error = str(exc)

        metadata = getattr(self._collection, "metadata", None)
        if isinstance(metadata, dict):
            dim = metadata.get("dimension") or metadata.get("embedding_dimension")
            if dim is not None:
                try:
                    collection_dimension_detected = int(dim)
                    collection_dimension_detection_reason = "collection_metadata"
                except Exception:
                    collection_dimension_detected = None

        if collection_dimension_detected is None:
            try:
                sample = self._collection.get(limit=1, include=["embeddings"])
                embeddings = sample.get("embeddings") if isinstance(sample, dict) else None
                if embeddings and isinstance(embeddings, list) and embeddings[0]:
                    collection_dimension_detected = int(len(embeddings[0]))
                    collection_dimension_detection_reason = "sample_embedding"
            except Exception as exc:
                if not collection_count_error:
                    collection_count_error = str(exc)

        embedding_probe_dimension = None
        embedding_probe_error = None
        try:
            probe = self._embed_texts(["probe"])
            if probe and probe[0]:
                embedding_probe_dimension = int(len(probe[0]))
        except Exception as exc:
            embedding_probe_error = str(exc)

        return {
            "db_path": self.db_path,
            "collection_name": self.collection_name,
            "embedding_model_name": self.embedding_model_name,
            "collection_exists": collection_exists,
            "collection_count": collection_count,
            "collection_count_error": collection_count_error,
            "embedding_probe_dimension": embedding_probe_dimension,
            "embedding_probe_error": embedding_probe_error,
            "collection_dimension_detected": collection_dimension_detected,
            "collection_dimension_detection_reason": collection_dimension_detection_reason,
            "dimension_mismatch": (
                embedding_probe_dimension is not None
                and collection_dimension_detected is not None
                and embedding_probe_dimension != collection_dimension_detected
            ),
        }

    def reset_collection(self) -> None:
        try:
            self.client.delete_collection(name=self.collection_name)
        except Exception:
            pass
        self._collection = self.client.get_or_create_collection(name=self.collection_name)

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
        governance = block.governance or {}
        chunking_quality = block.chunking_quality or {}
        allowed_use = governance.get("allowed_use") or []
        safety_flags = governance.get("safety_flags") or []
        lens_family = governance.get("lens_family") or []
        practice_metadata = governance.get("practice_metadata") or {}

        def _csv(items: list) -> str:
            return ",".join([str(item).strip() for item in items if str(item).strip()])

        def _bool_to_str(value: object) -> str:
            return "true" if bool(value) else "false"

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
            "governance_schema_version": str(governance.get("schema_version") or ""),
            "governance_chunk_type": str(governance.get("chunk_type") or ""),
            "governance_allowed_use": _csv(allowed_use),
            "governance_safety_flags": _csv(safety_flags),
            "governance_lens_family": _csv(lens_family),
            "governance_low_resource_safe": _bool_to_str(
                practice_metadata.get("low_resource_safe")
            ),
            "governance_not_for_direct_quote": _bool_to_str(
                "not_for_direct_quote" in safety_flags
            ),
            "governance_source_style_not_user_facing": _bool_to_str(
                "source_style_not_user_facing" in safety_flags
            ),
            "heading_path_text": " > ".join([str(p).strip() for p in (block.heading_path or []) if str(p).strip()]),
            "section_role_hint": str(block.section_role_hint or ""),
            "boundary_confidence": float(block.boundary_confidence or 0.0),
            "split_reason": str(block.split_reason or ""),
            "parent_section_id": str(block.parent_section_id or ""),
            "chunking_quality_notes": _csv(chunking_quality.get("quality_notes") or []),
            "mixed_intent_risk": _bool_to_str(chunking_quality.get("mixed_intent_risk")),
            "mixed_intent_severity": str(chunking_quality.get("mixed_intent_severity") or ""),
            "mixed_intent_primary_role": str(chunking_quality.get("primary_role") or ""),
            "mixed_intent_secondary_roles": _csv(chunking_quality.get("secondary_role_markers") or []),
            "mixed_intent_reason": str(chunking_quality.get("mixed_intent_reason") or ""),
        }

    def _init_embedding_model(self) -> SentenceTransformer:
        if os.getenv("BOT_DB_DISABLE_EMBEDDINGS") == "1":
            class _DummyModel:
                def encode(self, texts, convert_to_numpy=True):
                    import numpy as np
                    return np.zeros((len(texts), 3), dtype=float)

            return _DummyModel()
        try:
            return SentenceTransformer(self.embedding_model_name)
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
