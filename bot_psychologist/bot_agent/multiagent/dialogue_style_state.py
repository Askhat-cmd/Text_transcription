"""Dialogue style preference state for the current conversation."""

from __future__ import annotations

import re
from typing import Any


DIALOGUE_STYLE_STATE_VERSION = "dialogue_style_state_v1"


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip().lower())


def _append_unique(target: list[str], value: str) -> None:
    normalized = str(value or "").strip()
    if normalized and normalized not in target:
        target.append(normalized)


def build_dialogue_style_state_v1(
    *,
    previous_state: dict[str, Any] | None,
    user_message: str,
    dialogue_act_resolution: dict[str, Any] | None = None,
) -> dict[str, Any]:
    previous = dict(previous_state or {})
    lowered = _normalize(user_message)
    act = str((dialogue_act_resolution or {}).get("dialogue_act", "unknown") or "unknown")

    tone = str(previous.get("tone", "neutral") or "neutral")
    length_preference = str(previous.get("length_preference", "adaptive") or "adaptive")
    complexity_preference = str(previous.get("complexity_preference", "normal") or "normal")
    avoid = [str(item) for item in list(previous.get("avoid", []) or []) if str(item).strip()]

    touched = False
    if "спокойнее" in lowered or "спокойно" in lowered:
        tone = "calm"
        touched = True
    elif "теплее" in lowered or "мягче" in lowered:
        tone = "warm"
        touched = True
    elif "по сути" in lowered or "прямо" in lowered:
        tone = "direct"
        touched = True

    if "короче" in lowered or "коротко" in lowered or "в двух словах" in lowered:
        length_preference = "short"
        _append_unique(avoid, "overexplaining")
        touched = True
    elif "развернуто" in lowered or "развёрнуто" in lowered or "подробно" in lowered:
        length_preference = "detailed"
        complexity_preference = "deep"
        touched = True

    if "проще" in lowered or "понятнее" in lowered or "объясни нормально" in lowered:
        complexity_preference = "simple"
        touched = True

    if "без практик" in lowered or "без упражнений" in lowered:
        _append_unique(avoid, "unrequested_practice")
        touched = True
    if "без вопросов" in lowered:
        _append_unique(avoid, "forced_question")
        touched = True
    if "без воды" in lowered:
        _append_unique(avoid, "overexplaining")
        touched = True
    if "не как робот" in lowered or "не по-канцелярски" in lowered:
        _append_unique(avoid, "patronizing_tone")
        touched = True

    return {
        "version": DIALOGUE_STYLE_STATE_VERSION,
        "tone": tone,
        "length_preference": length_preference,
        "complexity_preference": complexity_preference,
        "avoid": avoid,
        "updated_by_turn_index": int(previous.get("updated_by_turn_index", 0) or 0),
        "source": "style_preference_update" if touched or act == "repair_complaint" else str(previous.get("source", "carry_forward") or "carry_forward"),
    }


def finalize_dialogue_style_state_v1(
    *,
    current_state: dict[str, Any] | None,
    turn_index: int,
) -> dict[str, Any]:
    state = dict(current_state or {})
    state["version"] = DIALOGUE_STYLE_STATE_VERSION
    if state.get("source") == "style_preference_update":
        state["updated_by_turn_index"] = int(turn_index)
    else:
        state.setdefault("updated_by_turn_index", int(turn_index))
    return state


__all__ = [
    "DIALOGUE_STYLE_STATE_VERSION",
    "build_dialogue_style_state_v1",
    "finalize_dialogue_style_state_v1",
]
