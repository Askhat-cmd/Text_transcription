from __future__ import annotations

import logging
from typing import List

from models.universal_block import UniversalBlock

logger = logging.getLogger(__name__)


class BlockNormalizer:
    """
    Финальная нормализация UniversalBlock перед сохранением.
    """

    VALID_SD_LEVELS = {
        "BEIGE",
        "PURPLE",
        "RED",
        "BLUE",
        "ORANGE",
        "GREEN",
        "YELLOW",
        "TURQUOISE",
        "UNCERTAIN",
    }

    def normalize(self, blocks: List[UniversalBlock]) -> List[UniversalBlock]:
        if not blocks:
            return []

        total = len(blocks)
        for block in blocks:
            block.total_chunks = total
            if not (block.title or "").strip():
                block.title = self._auto_title(block.text)

            errors = self.validate_block(block)
            if errors:
                logger.warning(f"[BLOCK_NORMALIZER] block_id={block.block_id} issues: {errors}")
        return blocks

    def validate_block(self, block: UniversalBlock) -> List[str]:
        errors: List[str] = []
        if not (block.text or "").strip():
            errors.append("missing_text")
        if not (block.author or "").strip():
            errors.append("missing_author")
        if (block.sd_level or "").strip() not in self.VALID_SD_LEVELS:
            errors.append("invalid_sd_level")
        return errors

    def _auto_title(self, text: str, max_words: int = 10) -> str:
        words = (text or "").strip().split()
        return " ".join(words[:max_words]) if words else ""
