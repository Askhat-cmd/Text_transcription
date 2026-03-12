from __future__ import annotations

import os
import copy
from datetime import datetime
from typing import Dict, List, Optional

import yaml
from dotenv import load_dotenv

from chunkers.book_chunker import BookChunker
from chunkers.semantic_chunker import SemanticChunker
from ingestors.book_ingestor import BookIngestor
from ingestors.youtube_ingestor import YouTubeIngestor
from jobs.job_manager import JobManager
from models.universal_block import UniversalBlock
from processors.block_normalizer import BlockNormalizer
from processors.sd_labeler import SDLabeler
from storage.chroma_manager import ChromaManager
from storage.json_export import JSONExporter
from storage.registry import SourceRecord, SourceRegistry


class PipelineRunner:
    """
    Главный оркестратор. Собирает все модули вместе.
    Используется напрямую из API (через jobs) и через CLI.
    """

    def __init__(self, config_path: str = "config.yaml", job_manager: Optional[JobManager] = None):
        self.config_path = config_path
        self.base_dir = (
            os.path.abspath(os.path.dirname(config_path))
            if os.path.isabs(config_path)
            else os.path.abspath(os.getcwd())
        )
        env_path = os.path.join(self.base_dir, ".env")
        load_dotenv(env_path, override=False)
        self.config = self._load_config(config_path)

        self.registry = SourceRegistry(self._resolve_path(self.config["storage"]["registry_path"]))
        self.chroma_manager = ChromaManager(
            self._resolve_path(self.config["storage"]["chroma_db_path"]),
            self.config["storage"]["collection_name"],
        )
        if os.getenv("BOT_DB_DISABLE_EMBEDDINGS") == "1":
            class _DummyModel:
                def encode(self, texts, convert_to_numpy=True):
                    import numpy as np
                    return np.zeros((len(texts), 3), dtype=float)

            self.chroma_manager._model = _DummyModel()
        self.json_exporter = JSONExporter(self._resolve_path(self.config["storage"]["json_export_dir"]))

        self.youtube_ingestor = YouTubeIngestor(
            self._resolve_path(self.config["pipeline"]["youtube"]["subtitles_dir"])
        )
        self.book_ingestor = BookIngestor()

        self.semantic_chunker = SemanticChunker(self.config.get("chunking", {}).get("youtube", {}))
        self.book_chunker = BookChunker(self.config.get("chunking", {}).get("book", {}))
        self.sd_labeler = SDLabeler(self.config.get("sd_labeling", {}))
        self.block_normalizer = BlockNormalizer()

        self.job_manager = job_manager

    async def run_youtube(self, url: str, author: str, author_id: str, job_id: str) -> dict:
        await self._update_progress(job_id, 0, "downloading")
        video_id = self.youtube_ingestor.extract_video_id(url)
        if not video_id:
            await self._update_job_failed(job_id, "invalid_url")
            return {"status": "failed", "error": "invalid_url"}

        if self.registry.is_processed(video_id):
            await self._update_progress(job_id, 100, "skipped")
            return {"status": "skipped", "source_id": video_id}

        record = SourceRecord(
            source_id=video_id,
            source_type="youtube",
            title="",
            author=author,
            author_id=author_id,
            language="",
            status="processing",
            added_at=datetime.utcnow().isoformat(),
            processed_at=None,
            blocks_count=0,
            sd_distribution={},
            file_paths={},
            error_message=None,
            pipeline_version="bot_data_base_v1.0",
        )
        self.registry.add_source(record)

        try:
            raw_text, metadata = self.youtube_ingestor.fetch_raw_text(video_id)
            await self._update_progress(job_id, 20, "chunking")

            blocks = self.semantic_chunker.chunk(
                raw_text,
                author=author,
                source_title=metadata.get("title", ""),
                source_id=video_id,
            )
            for b in blocks:
                b.author_id = author_id
                b.source_title = metadata.get("title", "")
                b.language = metadata.get("language", "") or b.language
                b.published_date = metadata.get("published_date", "")

            await self._update_progress(job_id, 40, "sd_labeling")
            blocks = self.sd_labeler.label_blocks(blocks)

            await self._update_progress(job_id, 60, "normalizing")
            blocks = self.block_normalizer.normalize(blocks)

            await self._update_progress(job_id, 75, "exporting")
            json_path = self.json_exporter.export(blocks, video_id, "youtube")

            await self._update_progress(job_id, 90, "indexing")
            added = self.chroma_manager.add_blocks(blocks)

            sd_dist = self._sd_distribution(blocks)
            self.registry.update_status(
                video_id,
                "done",
                processed_at=datetime.utcnow().isoformat(),
                blocks_count=len(blocks),
                sd_distribution=sd_dist,
                file_paths={"json": json_path, "chroma": True},
                error_message=None,
            )

            await self._update_progress(job_id, 100, "done")
            return {
                "status": "done",
                "source_id": video_id,
                "blocks_count": len(blocks),
                "json_path": json_path,
                "added_to_chroma": added,
            }
        except Exception as exc:
            self.registry.update_status(
                video_id,
                "failed",
                processed_at=datetime.utcnow().isoformat(),
                error_message=str(exc),
            )
            await self._update_job_failed(job_id, str(exc))
            return {"status": "failed", "error": str(exc)}

    async def run_book(
        self,
        file_path: str,
        author: str,
        author_id: str,
        book_title: str,
        language: str,
        job_id: str,
    ) -> dict:
        await self._update_progress(job_id, 0, "validating")
        valid, err = self.book_ingestor.validate_file(file_path)
        if not valid:
            await self._update_job_failed(job_id, err)
            return {"status": "failed", "error": err}

        source_id = self._make_book_source_id(author_id or author, book_title)
        if self.registry.is_processed(source_id):
            await self._update_progress(job_id, 100, "skipped")
            return {"status": "skipped", "source_id": source_id}

        record = SourceRecord(
            source_id=source_id,
            source_type="book",
            title=book_title,
            author=author,
            author_id=author_id,
            language=language,
            status="processing",
            added_at=datetime.utcnow().isoformat(),
            processed_at=None,
            blocks_count=0,
            sd_distribution={},
            file_paths={"upload": file_path},
            error_message=None,
            pipeline_version="bot_data_base_v1.0",
        )
        self.registry.add_source(record)

        try:
            await self._update_progress(job_id, 15, "loading")
            text = self.book_ingestor.load_text(file_path)

            await self._update_progress(job_id, 30, "chunking")
            blocks = self.book_chunker.chunk_file_from_text(
                text,
                author=author,
                book_title=book_title,
                language=language,
                author_id=author_id,
            )

            await self._update_progress(job_id, 50, "sd_labeling")
            blocks = self.sd_labeler.label_blocks(blocks)

            await self._update_progress(job_id, 70, "normalizing")
            blocks = self.block_normalizer.normalize(blocks)

            await self._update_progress(job_id, 80, "exporting")
            json_path = self.json_exporter.export(blocks, source_id, "book")

            await self._update_progress(job_id, 90, "indexing")
            added = self.chroma_manager.add_blocks(blocks)

            sd_dist = self._sd_distribution(blocks)
            self.registry.update_status(
                source_id,
                "done",
                processed_at=datetime.utcnow().isoformat(),
                blocks_count=len(blocks),
                sd_distribution=sd_dist,
                file_paths={"json": json_path, "chroma": True, "upload": file_path},
                error_message=None,
            )

            await self._update_progress(job_id, 100, "done")
            return {
                "status": "done",
                "source_id": source_id,
                "blocks_count": len(blocks),
                "json_path": json_path,
                "added_to_chroma": added,
            }
        except Exception as exc:
            self.registry.update_status(
                source_id,
                "failed",
                processed_at=datetime.utcnow().isoformat(),
                error_message=str(exc),
            )
            await self._update_job_failed(job_id, str(exc))
            return {"status": "failed", "error": str(exc)}

    async def _update_progress(self, job_id: str, progress: int, stage: str) -> None:
        if not self.job_manager or not job_id:
            return
        await self.job_manager.update_job(
            job_id=job_id,
            status="running" if progress < 100 else "done",
            progress=progress,
            current_stage=stage,
        )

    async def _update_job_failed(self, job_id: str, error: str) -> None:
        if not self.job_manager or not job_id:
            return
        await self.job_manager.update_job(
            job_id=job_id,
            status="failed",
            progress=100,
            current_stage="failed",
            error=error,
            finished_at=datetime.utcnow().isoformat(),
        )

    def _load_config(self, path: str) -> dict:
        with open(path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        before = copy.deepcopy(cfg)
        cfg = self._apply_env_overrides(cfg)
        if cfg != before:
            self._persist_config(path, cfg)
        return cfg

    def _persist_config(self, path: str, cfg: dict) -> None:
        try:
            with open(path, "w", encoding="utf-8") as f:
                yaml.safe_dump(cfg, f, allow_unicode=True, sort_keys=False)
        except Exception:
            return

    def _apply_env_overrides(self, cfg: dict) -> dict:
        def ensure(section: str) -> dict:
            if section not in cfg or not isinstance(cfg.get(section), dict):
                cfg[section] = {}
            return cfg[section]

        def ensure_nested(root: str, child: str) -> dict:
            root_obj = ensure(root)
            if child not in root_obj or not isinstance(root_obj.get(child), dict):
                root_obj[child] = {}
            return root_obj[child]

        def to_int(value: str) -> int:
            return int(float(value))

        def to_float(value: str) -> float:
            return float(value)

        def to_bool(value: str) -> bool:
            return str(value).strip().lower() in {"1", "true", "yes", "on"}

        def set_if_env(path: list, env_key: str, cast=None) -> None:
            raw = os.getenv(env_key)
            if raw is None or raw == "":
                return
            target = cfg
            for key in path[:-1]:
                if key not in target or not isinstance(target.get(key), dict):
                    target[key] = {}
                target = target[key]
            target[path[-1]] = cast(raw) if cast else raw

        # Pipeline paths
        set_if_env(["pipeline", "youtube", "subtitles_dir"], "PIPELINE_SUBTITLES_DIR")
        set_if_env(["pipeline", "youtube", "output_dir"], "PIPELINE_YOUTUBE_OUTPUT_DIR")
        set_if_env(["pipeline", "books", "uploads_dir"], "PIPELINE_BOOKS_UPLOADS_DIR")
        set_if_env(["pipeline", "books", "output_dir"], "PIPELINE_BOOKS_OUTPUT_DIR")

        # Chunking
        set_if_env(["chunking", "book", "target_tokens"], "CHUNKING_BOOK_TARGET_TOKENS", to_int)
        set_if_env(["chunking", "book", "min_tokens"], "CHUNKING_BOOK_MIN_TOKENS", to_int)
        set_if_env(["chunking", "book", "max_tokens"], "CHUNKING_BOOK_MAX_TOKENS", to_int)
        set_if_env(["chunking", "book", "overlap_tokens"], "CHUNKING_BOOK_OVERLAP_TOKENS", to_int)
        set_if_env(["chunking", "youtube", "min_tokens"], "CHUNKING_YOUTUBE_MIN_TOKENS", to_int)
        set_if_env(["chunking", "youtube", "max_tokens"], "CHUNKING_YOUTUBE_MAX_TOKENS", to_int)

        # SD labeling
        set_if_env(["sd_labeling", "enabled"], "SD_LABELING_ENABLED", to_bool)
        set_if_env(["sd_labeling", "model"], "SD_LABELING_MODEL")
        set_if_env(["sd_labeling", "temperature"], "SD_LABELING_TEMPERATURE", to_float)
        set_if_env(["sd_labeling", "max_tokens"], "SD_LABELING_MAX_TOKENS", to_int)
        set_if_env(["sd_labeling", "min_confidence"], "SD_LABELING_MIN_CONFIDENCE", to_float)
        set_if_env(["sd_labeling", "batch_size"], "SD_LABELING_BATCH_SIZE", to_int)

        # Embeddings
        set_if_env(["embedding", "model"], "SENTENCE_TRANSFORMERS_MODEL")

        # Storage
        set_if_env(["storage", "chroma_db_path"], "CHROMA_DB_PATH")
        set_if_env(["storage", "collection_name"], "CHROMA_COLLECTION_NAME")
        set_if_env(["storage", "json_export_dir"], "JSON_EXPORT_DIR")
        set_if_env(["storage", "registry_path"], "REGISTRY_PATH")

        # API
        set_if_env(["api", "host"], "API_HOST")
        set_if_env(["api", "port"], "API_PORT", to_int)

        # Logging
        set_if_env(["logging", "level"], "LOG_LEVEL")
        set_if_env(["logging", "log_file"], "LOG_FILE")

        return cfg

    def _resolve_path(self, value: str) -> str:
        if not value:
            return value
        if os.path.isabs(value):
            return value
        return os.path.abspath(os.path.join(self.base_dir, value))

    def _sd_distribution(self, blocks: List[UniversalBlock]) -> Dict[str, int]:
        dist: Dict[str, int] = {}
        for b in blocks:
            level = b.sd_level or ""
            if not level:
                continue
            dist[level] = dist.get(level, 0) + 1
        return dist

    def _make_book_source_id(self, author_or_id: str, book_title: str) -> str:
        return f"{self._slugify(author_or_id)}__{self._slugify(book_title)}"

    def _slugify(self, value: str) -> str:
        if not value:
            return ""
        value = value.strip().lower()
        value = "_".join(value.split())
        value = "".join(ch for ch in value if ch.isalnum() or ch == "_")
        return value
