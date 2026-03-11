"""
UniversalBlock — единый формат чанка для Bot_data_base.
Совместим с bot_psychologist/bot_agent/data_loader.py (Block dataclass).
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional
import uuid


@dataclass
class UniversalBlock:
    # === Идентификация ===
    block_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_type: str = ""  # "youtube" | "book"
    source_id: str = ""  # video_id | "author_slug__book_slug"

    # === Контент ===
    text: str = ""
    title: str = ""
    summary: str = ""

    # === SD-разметка ===
    sd_level: str = "GREEN"  # BEIGE|PURPLE|RED|BLUE|ORANGE|GREEN|YELLOW|TURQUOISE
    sd_confidence: float = 0.0
    sd_secondary: str = ""
    complexity: float = 0.5

    # === Метаданные источника ===
    author: str = ""
    author_id: str = ""
    source_title: str = ""
    language: str = "ru"  # "ru" | "en"
    published_date: str = ""

    # === Для книг ===
    chapter_title: str = ""
    chapter_index: int = 0
    chunk_index: int = 0
    total_chunks: int = 0

    # === Служебные ===
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    pipeline_version: str = "bot_data_base_v1.0"

    def to_dict(self) -> dict:
        return asdict(self)

    def to_bot_format(self) -> dict:
        """
        Формат совместимый с bot_psychologist data_loader.py Block.
        ВАЖНО: бот читает поля text, sd_level, complexity, source, metadata.
        """
        return {
            "id": self.block_id,
            "text": self.text,
            "title": self.title,
            "summary": self.summary,
            "sd_level": self.sd_level,
            "sd_confidence": self.sd_confidence,
            "complexity": self.complexity,
            "source": f"{self.source_type}:{self.source_id}",
            "metadata": {
                "author": self.author,
                "author_id": self.author_id,
                "source_title": self.source_title,
                "language": self.language,
                "published_date": self.published_date,
                "chapter_title": self.chapter_title,
                "chunk_index": self.chunk_index,
                "source_type": self.source_type,
            },
        }
