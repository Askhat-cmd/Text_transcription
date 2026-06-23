"""Live Turn Note generator for PRD-047.28 variant C."""

from __future__ import annotations

from typing import Any


def build_live_turn_note(context: dict[str, Any]) -> str:
    message = str(context.get("current_user_message", "") or "")
    lowered = message.lower()
    constraints = list(context.get("explicit_constraints", []) or [])
    parts: list[str] = []

    if "слишком сложно" in lowered or "скажи проще" in lowered or "проще" in lowered:
        parts.append("The user wants a simpler answer without lecture-like complexity.")
    if "практик" in lowered or "дыхани" in lowered or "упражн" in lowered:
        parts.append("Do not push practice unless it is explicitly asked for and clearly welcome.")
    if "внутреннюю бд" in lowered or "internal db" in lowered:
        parts.append("Respect the explicit request to avoid internal DB grounding.")
    if "долгосроч" in lowered or "перспектив" in lowered:
        parts.append("Focus on the long-term perspective rather than only what to do right now.")
    if "гнев" in lowered or "зл" in lowered:
        parts.append("Acknowledge anger directly and stay concrete.")
    if "паничес" in lowered or "медицин" in lowered:
        parts.append("Keep the safety floor visible and avoid overclaiming or diagnosing.")
    if "нет других способов кроме дыхания" in lowered:
        parts.append("Offer alternatives beyond breathing and do not narrow the answer to one tool.")
    if constraints:
        parts.append("Key constraints: " + "; ".join(str(item) for item in constraints[:3]))
    if not parts:
        parts.append("Answer directly, warmly, and with the right depth for this turn.")
    note = " ".join(parts).strip()
    if note.startswith("{") or note.startswith("["):
        note = "Answer directly. " + note
    return note[:420]
