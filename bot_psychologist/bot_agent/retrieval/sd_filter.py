"""
SD Filter - фильтрует блоки по динамической совместимости с уровнем СД пользователя.
Применяется после retrieval, до генерации ответа.
"""

from __future__ import annotations

import logging
from typing import List, Optional, Tuple

from ..sd_classifier import sd_compatibility_resolver

logger = logging.getLogger(__name__)


def filter_by_sd_level(
    blocks_with_scores: List[Tuple],
    user_sd_level: str,
    user_state: Optional[str] = None,
    sd_secondary: Optional[str] = None,
    sd_confidence: float = 1.0,
    is_first_session: bool = False,
    min_blocks: int = 3,
) -> List[Tuple]:
    """
    Фильтровать блоки по совместимости уровней СД.

    Args:
        blocks_with_scores: [(Block, score), ...]
        user_sd_level: основной уровень СД пользователя
        user_state: эмоциональное состояние (overwhelmed/crisis/resistant/etc.)
        sd_secondary: вторичный уровень
        sd_confidence: уверенность SD-классификации
        is_first_session: первый диалог
        min_blocks: минимум блоков на выходе

    Returns:
        Отфильтрованный список (block, score)
    """
    allowed_levels = sd_compatibility_resolver.get_allowed_levels(
        sd_level=user_sd_level,
        user_state=user_state,
        sd_secondary=sd_secondary,
        sd_confidence=sd_confidence,
        is_first_session=is_first_session,
    )

    filtered = []
    no_sd_metadata = []  # блоки без SD-разметки (старые данные)

    for block, score in blocks_with_scores:
        block_sd = getattr(block, "sd_level", None) or (getattr(block, "metadata", {}) or {}).get(
            "sd_level", None
        )

        if block_sd is None:
            no_sd_metadata.append((block, score))
            continue

        if block_sd in allowed_levels:
            filtered.append((block, score))

    logger.info(
        f"[SD_FILTER] {len(blocks_with_scores)} -> {len(filtered)} filtered "
        f"(user={user_sd_level}, state={user_state}, allowed={allowed_levels}, "
        f"untagged={len(no_sd_metadata)})"
    )

    # Если мало блоков - добавить неразмеченные
    if len(filtered) < min_blocks:
        needed = min_blocks - len(filtered)
        filtered += no_sd_metadata[:needed]
        logger.warning(
            f"[SD_FILTER] Added {min(needed, len(no_sd_metadata))} untagged blocks as fallback"
        )

    # Крайний случай - вернуть исходные
    if len(filtered) < min_blocks:
        logger.warning("[SD_FILTER] Critical fallback: returning original blocks")
        return blocks_with_scores[: min_blocks * 2]

    return filtered
