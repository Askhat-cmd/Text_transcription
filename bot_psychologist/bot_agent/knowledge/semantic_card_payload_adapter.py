"""Convert advisory semantic cards into Writer KB payload candidates."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from ..feature_flags import FeatureFlags, feature_flags
from .semantic_chunk_card import SemanticChunkCard
from .semantic_card_loader import load_semantic_cards


SEMANTIC_CARDS_PILOT_TRACE_VERSION = "semantic_cards_pilot_trace_v1"
SEMANTIC_CARDS_RUNTIME_STATUS_VERSION = "semantic_cards_runtime_status_v1"
SEMANTIC_CARDS_PACK_ID = "semantic_cards_pilot_v1"
_LOCAL_ENVS = {"local", "dev", "test"}
_NO_THEORY_MARKERS = (
    "без теории",
    "не хочу теорию",
    "просто ответь",
    "по-человечески",
    "пару слов",
)
_GREETING_MARKERS = ("привет", "здравствуй", "добрый день", "добрый вечер")
_PRACTICE_REQUEST_MARKERS = ("практик", "упражнен", "одну короткую", "один шаг")


@dataclass(frozen=True)
class SemanticCardsPilotConfig:
    enabled: bool
    enabled_requested: bool
    source: str
    runtime_mode: str
    max_cards: int = 3


def get_semantic_cards_pilot_config() -> SemanticCardsPilotConfig:
    resolution = feature_flags.resolve_bool("SEMANTIC_CARDS_PILOT_ENABLED")
    runtime_mode = FeatureFlags.app_env()
    enabled_requested = bool(resolution.get("effective_value", False))
    return SemanticCardsPilotConfig(
        enabled=enabled_requested and runtime_mode in _LOCAL_ENVS,
        enabled_requested=enabled_requested,
        source=str(resolution.get("source", "") or ""),
        runtime_mode=runtime_mode,
        max_cards=max(1, min(3, _to_int(feature_flags.value("SEMANTIC_CARDS_PILOT_MAX_CARDS", "3"), 3))),
    )


def card_to_writer_payload_item(card: SemanticChunkCard) -> dict[str, Any]:
    return {
        "chunk_id": f"semantic_card:{card.card_id}",
        "source": SEMANTIC_CARDS_PACK_ID,
        "source_id": SEMANTIC_CARDS_PACK_ID,
        "source_doc": str(card.source_ref.get("source_doc", "") or SEMANTIC_CARDS_PACK_ID),
        "chunk_type": card.chunk_type,
        "core_thesis": card.core_thesis,
        "content": card.core_thesis,
        "mechanism_hints": list(card.mechanism_hints),
        "user_markers_examples": list(card.user_markers_examples[:3]),
        "use_when": list(card.user_markers_examples[:3]),
        "avoid_when": list(card.avoid_when),
        "allowed_use": list(card.allowed_use),
        "quote_policy": card.quote_policy,
        "practice_policy": card.practice_policy,
        "writer_instruction": card.writer_instruction,
        "recommended_moves": [],
        "forbidden_moves": list(card.avoid_when),
        "semantic_card_id": card.card_id,
        "semantic_card_pack_id": SEMANTIC_CARDS_PACK_ID,
        "payload_item_origin": "semantic_card",
        "writer_can_ignore": True,
        "applied_as_authority": False,
    }


def build_semantic_cards_runtime_status() -> dict[str, Any]:
    cfg = get_semantic_cards_pilot_config()
    writer_payload = feature_flags.resolve_bool("WRITER_KB_PAYLOAD_ENABLED")
    payload: dict[str, Any] = {
        "schema_version": SEMANTIC_CARDS_RUNTIME_STATUS_VERSION,
        "enabled": bool(cfg.enabled),
        "enabled_requested": bool(cfg.enabled_requested),
        "enabled_source": cfg.source,
        "runtime_mode": cfg.runtime_mode,
        "pack_id": SEMANTIC_CARDS_PACK_ID,
        "loaded_card_count": 0,
        "adapter_enabled": True,
        "writer_payload_enabled": bool(writer_payload.get("effective_value", False)),
        "writer_payload_enabled_source": str(writer_payload.get("source", "") or ""),
        "selection_surface": "per_turn_trace_only",
        "selected_cards_visible_in_turn_trace": True,
        "last_selected_count": None,
        "last_selected_ids": [],
        "authority": "advisory_only",
        "writer_can_ignore": True,
        "applied_as_authority": False,
        "status": "ready",
        "reason": "",
        "error": "",
    }
    if not cfg.enabled:
        payload["status"] = "disabled"
        payload["reason"] = (
            "unsupported_runtime_mode"
            if cfg.enabled_requested and cfg.runtime_mode not in _LOCAL_ENVS
            else "disabled_by_config"
        )
    try:
        payload["loaded_card_count"] = len(load_semantic_cards())
    except Exception as exc:
        payload["loaded_card_count"] = 0
        payload["status"] = "pack_not_loaded"
        payload["reason"] = "pack_not_loaded"
        payload["error"] = str(exc)
    return payload


def build_semantic_cards_pilot_selection(
    *,
    user_message: str,
    retrieval_decision: dict[str, Any] | None = None,
    cards: list[SemanticChunkCard] | None = None,
    config: SemanticCardsPilotConfig | None = None,
) -> dict[str, Any]:
    cfg = config or get_semantic_cards_pilot_config()
    text = _normalize(user_message)
    retrieval = dict(retrieval_decision or {})
    trace = {
        "schema_version": SEMANTIC_CARDS_PILOT_TRACE_VERSION,
        "enabled": bool(cfg.enabled),
        "enabled_requested": bool(cfg.enabled_requested),
        "enabled_source": cfg.source,
        "runtime_mode": cfg.runtime_mode,
        "pack_id": SEMANTIC_CARDS_PACK_ID,
        "loaded_card_count": 0,
        "adapter_enabled": True,
        "writer_payload_enabled": bool(feature_flags.resolve_bool("WRITER_KB_PAYLOAD_ENABLED").get("effective_value", False)),
        "authority": "advisory_only",
        "selected_card_count": 0,
        "selected_card_ids": [],
        "selection_reason": "",
        "writer_can_ignore": True,
        "applied_as_authority": False,
        "suppressed_reason": "",
        "writer_payload_enriched": False,
        "status": "ready",
        "error": "",
        "candidate_scores": [],
        "payload_items": [],
    }
    if not cfg.enabled:
        trace["status"] = "disabled"
        trace["suppressed_reason"] = (
            "unsupported_runtime_mode"
            if cfg.enabled_requested and cfg.runtime_mode not in _LOCAL_ENVS
            else "disabled_by_config"
        )
        return trace
    try:
        loaded_cards = list(cards) if cards is not None else load_semantic_cards()
    except Exception as exc:
        trace["status"] = "pack_not_loaded"
        trace["suppressed_reason"] = "pack_not_loaded"
        trace["error"] = str(exc)
        return trace
    trace["loaded_card_count"] = len(loaded_cards)
    if not text:
        trace["status"] = "suppressed"
        trace["suppressed_reason"] = "empty_user_message"
        return trace
    if _is_greeting_only(text):
        trace["status"] = "suppressed"
        trace["suppressed_reason"] = "greeting_or_contact"
        return trace
    if _contains_any(text, _NO_THEORY_MARKERS):
        trace["status"] = "suppressed"
        trace["suppressed_reason"] = "user_requested_no_theory"
        return trace

    terms = set(_tokens(text))
    hints = set(_tokens(" ".join(_string_list(retrieval.get("mechanism_hints")))))
    scored: list[tuple[int, SemanticChunkCard, list[str]]] = []
    practice_requested = _contains_any(text, _PRACTICE_REQUEST_MARKERS)
    for card in loaded_cards:
        if card.chunk_type == "practice" and not practice_requested:
            continue
        if "user_asked_no_theory" in card.avoid_when and _contains_any(text, _NO_THEORY_MARKERS):
            continue
        haystacks = [
            card.title,
            card.core_thesis,
            " ".join(card.mechanism_hints),
            " ".join(card.user_markers_examples),
        ]
        card_terms = set(_tokens(" ".join(haystacks)))
        overlap = terms & card_terms
        hint_overlap = hints & set(_tokens(" ".join(card.mechanism_hints)))
        alias_score = _alias_score(text, card.card_id)
        score = len(overlap) + (2 * len(hint_overlap)) + alias_score
        if score <= 0:
            continue
        reasons = []
        if overlap:
            reasons.append("current_turn_overlap")
        if hint_overlap:
            reasons.append("retrieval_hint_overlap")
        if alias_score:
            reasons.append("topic_alias")
        scored.append((score, card, reasons))
    scored.sort(key=lambda item: (-item[0], item[1].card_id))
    selected = scored[: cfg.max_cards]
    trace["candidate_scores"] = [
        {"card_id": card.card_id, "score": score, "reasons": reasons}
        for score, card, reasons in scored[:8]
    ]
    trace["selected_card_ids"] = [card.card_id for _score, card, _reasons in selected]
    trace["selected_card_count"] = len(selected)
    trace["selection_reason"] = (
        "title/core_thesis/current_turn_overlap" if selected else "no_relevant_card"
    )
    trace["payload_items"] = [card_to_writer_payload_item(card) for _score, card, _reasons in selected]
    trace["writer_payload_enriched"] = bool(trace["payload_items"])
    trace["status"] = "selected" if selected else "suppressed"
    if not selected:
        trace["suppressed_reason"] = "no_relevant_card"
    return trace


def _to_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _normalize(text: str) -> str:
    return str(text or "").lower().replace("ё", "е")


def _tokens(text: str) -> list[str]:
    return [part for part in re.findall(r"[a-zа-я0-9_]{3,}", _normalize(text)) if len(part) >= 3]


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    lowered = _normalize(text)
    return any(marker in lowered for marker in markers)


def _is_greeting_only(text: str) -> bool:
    lowered = _normalize(text).strip(" !?.")
    return any(lowered.startswith(marker) for marker in _GREETING_MARKERS) and len(_tokens(lowered)) <= 6


def _alias_score(text: str, card_id: str) -> int:
    aliases = {
        "program_imperfect_self": ("несовершенное я", "со мной что-то не так", "недостаточ"),
        "five_survival_drivers": ("пять драйвер", "драйверы выживания", "драйверов"),
        "be_strong_driver": ("будь сильным", "держаться через силу"),
        "be_best_driver": ("будь лучшим", "идеально", "лучшим"),
        "please_others_driver": ("радуй других", "угожд", "понравиться"),
        "try_harder_driver": ("старайся", "усилие", "сильнее"),
        "hurry_up_driver": ("спеши", "тороп", "быстрее"),
        "control_as_safety": ("контроль как безопасность", "контроль", "безопасност"),
        "fact_vs_interpretation": ("факт", "интерпретац", "доказательств"),
        "panic_control_support": ("паник", "контроль", "накрывает"),
        "one_bounded_practice_not_self_improvement_whip": ("одну короткую практику", "практик", "самосовершенств"),
        "neurostalking_basic_lens": ("нейросталкинг", "наблюдение механизм", "нейросталк"),
    }
    lowered = _normalize(text)
    base_id = str(card_id).removesuffix("_v1")
    return sum(3 for marker in aliases.get(base_id, ()) if marker in lowered)


__all__ = [
    "SEMANTIC_CARDS_PILOT_TRACE_VERSION",
    "SEMANTIC_CARDS_RUNTIME_STATUS_VERSION",
    "SEMANTIC_CARDS_PACK_ID",
    "SemanticCardsPilotConfig",
    "build_semantic_cards_runtime_status",
    "build_semantic_cards_pilot_selection",
    "card_to_writer_payload_item",
    "get_semantic_cards_pilot_config",
]
