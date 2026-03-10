"""
SD Filter - фильтрует блоки по динамической совместимости с уровнем СД пользователя.
Применяется после retrieval, до генерации ответа.
"""

from __future__ import annotations

import logging
from typing import List, Optional, Tuple

from ..sd_classifier import SD_LEVELS_ORDER, sd_compatibility_resolver

logger = logging.getLogger(__name__)

# Расширенные уровни для fallback — добавляет соседние уровни СД
SD_EXTENDED_FALLBACK = {
    "BEIGE": ["BEIGE", "PURPLE", "RED"],
    "PURPLE": ["PURPLE", "BEIGE", "RED"],
    "RED": ["RED", "BLUE", "PURPLE", "ORANGE"],
    "BLUE": ["BLUE", "RED", "ORANGE"],
    "ORANGE": ["ORANGE", "BLUE", "GREEN"],
    "GREEN": ["GREEN", "ORANGE", "YELLOW"],
    "YELLOW": ["YELLOW", "GREEN", "TURQUOISE"],
    "TURQUOISE": ["TURQUOISE", "YELLOW"],
}


def _get_extended_allowed(user_sd_level: str) -> List[str]:
    """Вернуть расширенный список допустимых уровней для fallback."""
    return SD_EXTENDED_FALLBACK.get(user_sd_level.upper(), [user_sd_level.upper()])


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

    # Если мало блоков — добавить неразмеченные
    if len(filtered) < min_blocks:
        needed = min_blocks - len(filtered)
        filtered += no_sd_metadata[:needed]
        logger.warning(
            f"[SD_FILTER] Added {min(needed, len(no_sd_metadata))} untagged blocks as fallback"
        )

    # Шаг 2: Если всё ещё мало — расширить допустимые уровни (мягкий fallback)
    if len(filtered) < min_blocks:
        extended_allowed = _get_extended_allowed(user_sd_level)
        filtered_extended = []
        for block, score in blocks_with_scores:
            block_sd = getattr(block, "sd_level", None) or (getattr(block, "metadata", {}) or {}).get("sd_level", None)
            if block_sd and block_sd.upper() in extended_allowed:
                filtered_extended.append((block, score))

        if len(filtered_extended) >= min_blocks:
            logger.info(f"[SD_FILTER] Extended fallback: {len(filtered_extended)} blocks (allowed={extended_allowed})")
            return filtered_extended[:min_blocks]

        # Шаг 3: Если всё ещё мало — вернуть отфильтрованные + лучшие по score из остатка
        if len(filtered_extended) < min_blocks:
            remaining = sorted(
                [(b, s) for b, s in blocks_with_scores if (b, s) not in filtered_extended],
                key=lambda x: x[1], reverse=True
            )
            result = filtered_extended + remaining[:min_blocks - len(filtered_extended)]
            logger.warning(f"[SD_FILTER] Soft fallback: {len(result)} blocks (mixed SD)")
            return result

    return filtered
