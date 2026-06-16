from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from bot_agent.feature_flags import feature_flags


OVERLAY_SHADOW_TRACE_VERSION = "overlay_shadow_trace_v1"
ALLOWED_OVERLAY_MODES = {"trace_only"}
REPO_ROOT = Path(__file__).resolve().parents[3]
_TOKEN_RE = re.compile(r"[0-9A-Za-zА-Яа-яЁё_]+", re.UNICODE)


def _safe_text(value: Any, *, limit: int = 220) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[: max(0, limit - 3)].rstrip() + "..."


def _safe_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _safe_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _tokenize(text: str) -> list[str]:
    tokens = [match.group(0).lower() for match in _TOKEN_RE.finditer(str(text or ""))]
    return [token for token in tokens if len(token) >= 3]


def _score_overlap(query_tokens: set[str], candidate_tokens: set[str]) -> tuple[float, list[str]]:
    matched = sorted(query_tokens.intersection(candidate_tokens))
    if not matched:
        return 0.0, []
    score = float(len(matched))
    long_hits = [token for token in matched if len(token) >= 6]
    score += min(len(long_hits) * 0.25, 1.0)
    return round(score, 3), matched[:6]


def _resolve_overlay_file(path_value: str) -> Path:
    candidate = Path(str(path_value or "").strip())
    if candidate.is_absolute():
        return candidate
    return (REPO_ROOT / candidate).resolve()


def get_overlay_shadow_trace_settings() -> dict[str, Any]:
    mode = str(feature_flags.value("OVERLAY_SHADOW_TRACE_MODE", "trace_only") or "trace_only").strip().lower()
    if mode not in ALLOWED_OVERLAY_MODES:
        mode = "trace_only"
    try:
        max_matches = max(1, int(feature_flags.value("OVERLAY_SHADOW_MAX_MATCHES", "5") or "5"))
    except ValueError:
        max_matches = 5
    try:
        min_score = float(feature_flags.value("OVERLAY_SHADOW_MIN_SCORE", "0.0") or "0.0")
    except ValueError:
        min_score = 0.0
    overlay_file = str(
        feature_flags.value(
            "OVERLAY_SHADOW_OVERLAY_FILE",
            "TO_DO_LIST/logs/PRD-047.20/batch_1_accepted_overlay_preview.json",
        )
        or "TO_DO_LIST/logs/PRD-047.20/batch_1_accepted_overlay_preview.json"
    ).strip()
    return {
        "enabled": bool(feature_flags.enabled("OVERLAY_SHADOW_TRACE_ENABLED")),
        "mode": mode,
        "overlay_file": overlay_file,
        "overlay_file_resolved": str(_resolve_overlay_file(overlay_file)),
        "max_matches": max_matches,
        "min_score": min_score,
        "schema_version": OVERLAY_SHADOW_TRACE_VERSION,
    }


def _load_overlay_document(overlay_file: str) -> tuple[dict[str, Any] | None, str | None]:
    path = _resolve_overlay_file(overlay_file)
    if not path.exists():
        return None, "overlay_file_missing"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None, "overlay_file_invalid"
    if not isinstance(payload, dict):
        return None, "overlay_file_invalid"
    return payload, None


def _candidate_cards(overlay_document: dict[str, Any]) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    for item in list(overlay_document.get("items") or []):
        if not isinstance(item, dict):
            continue
        accepted = _safe_dict(item.get("accepted_fields"))
        source_ref = _safe_dict(item.get("source_ref"))
        chunk_type = _safe_text(item.get("chunk_type"), limit=40)
        if not chunk_type:
            continue
        safe_user_translation = _safe_text(
            accepted.get("safe_user_translation_candidate") or accepted.get("summary_candidate"),
            limit=180,
        )
        allowed_writer_use = _safe_text(
            accepted.get("allowed_writer_use_candidate") or accepted.get("summary_candidate"),
            limit=180,
        )
        summary_preview = _safe_text(
            accepted.get("summary_candidate") or accepted.get("core_thesis_candidate"),
            limit=220,
        )
        candidate_terms = [
            safe_user_translation,
            allowed_writer_use,
            summary_preview,
            _safe_text(accepted.get("core_thesis_candidate"), limit=220),
            " ".join(_safe_list(source_ref.get("heading_path"))[:3]),
            " ".join(_safe_list(accepted.get("mechanism_hints_candidates"))[:4]),
            " ".join(_safe_list(accepted.get("recommended_moves_candidates"))[:4]),
            " ".join(_safe_list(accepted.get("use_when_candidates"))[:3]),
        ]
        tokens = set(_tokenize(" ".join(part for part in candidate_terms if part)))
        cards.append(
            {
                "candidate_id": _safe_text(item.get("candidate_id"), limit=80),
                "chunk_type": chunk_type,
                "risk_level": _safe_text(item.get("risk_level"), limit=24),
                "focus_tags": _safe_list(accepted.get("mechanism_hints_candidates"))[:4]
                or _safe_list(accepted.get("recommended_moves_candidates"))[:4],
                "safe_user_translation_preview": safe_user_translation,
                "allowed_writer_use_preview": allowed_writer_use,
                "summary_preview": summary_preview,
                "tokens": tokens,
            }
        )
    return cards


def build_overlay_shadow_trace(
    *,
    user_message: str,
    retrieval_query: str | None,
    state_snapshot: dict | None,
    thread_state: dict | None,
    overlay_file: str,
    enabled: bool,
    max_matches: int = 5,
    min_score: float = 0.0,
) -> dict[str, Any]:
    mode = "trace_only"
    if not enabled:
        return {
            "schema_version": OVERLAY_SHADOW_TRACE_VERSION,
            "enabled": False,
            "mode": mode,
            "reason": "disabled_by_config",
            "used_for_writer": False,
            "used_for_retrieval_execution": False,
            "used_for_final_answer": False,
        }

    overlay_document, error_reason = _load_overlay_document(overlay_file)
    if overlay_document is None:
        return {
            "schema_version": OVERLAY_SHADOW_TRACE_VERSION,
            "enabled": True,
            "status": "skipped",
            "mode": mode,
            "reason": error_reason or "overlay_file_missing",
            "overlay_source_prd": "PRD-047.20",
            "used_for_writer": False,
            "used_for_retrieval_execution": False,
            "used_for_final_answer": False,
            "warnings": [error_reason or "overlay_file_missing"],
            "blockers": [],
            "safety_flags": [],
            "matched_candidates": [],
            "match_count": 0,
            "would_help": False,
        }

    query_parts = [
        str(user_message or ""),
        str(retrieval_query or ""),
        str(_safe_dict(state_snapshot).get("intent", "") or ""),
        str(_safe_dict(state_snapshot).get("nervous_state", "") or ""),
        str(_safe_dict(thread_state).get("phase", "") or ""),
        str(_safe_dict(_safe_dict(thread_state).get("active_frame")).get("active_concept", "") or ""),
    ]
    query_tokens = set(_tokenize(" ".join(part for part in query_parts if part)))
    cards = _candidate_cards(overlay_document)
    ranked: list[dict[str, Any]] = []
    for card in cards:
        score, matched_terms = _score_overlap(query_tokens, set(card.get("tokens") or set()))
        if score <= max(min_score, 0.0):
            continue
        ranked.append(
            {
                "candidate_id": str(card.get("candidate_id") or ""),
                "chunk_type": str(card.get("chunk_type") or ""),
                "risk_level": str(card.get("risk_level") or ""),
                "score": score,
                "matched_terms": matched_terms,
                "focus_tags": list(card.get("focus_tags") or []),
                "safe_user_translation_preview": str(card.get("safe_user_translation_preview") or ""),
                "allowed_writer_use_preview": str(card.get("allowed_writer_use_preview") or ""),
                "summary_preview": str(card.get("summary_preview") or ""),
                "trace_only": True,
            }
        )
    ranked.sort(key=lambda item: (-float(item.get("score", 0.0)), str(item.get("candidate_id", ""))))
    limited = ranked[: max(1, int(max_matches or 5))]
    warnings: list[str] = []
    if bool(overlay_document.get("evaluation_only")) or overlay_document.get("live_apply_allowed") is False:
        warnings.append("non_live_overlay_source")
    if overlay_document.get("human_final_approval") is False:
        warnings.append("human_final_approval_pending")
    return {
        "schema_version": OVERLAY_SHADOW_TRACE_VERSION,
        "enabled": True,
        "status": "ok",
        "mode": mode,
        "overlay_source_prd": _safe_text(overlay_document.get("prd_id") or "PRD-047.20", limit=40),
        "batch_id": _safe_text(overlay_document.get("batch_id") or "batch_1", limit=40),
        "overlay_item_count": int(((overlay_document.get("summary") or {}).get("accepted_item_count")) or len(cards)),
        "used_for_writer": False,
        "used_for_retrieval_execution": False,
        "used_for_final_answer": False,
        "would_help": bool(limited),
        "match_count": len(limited),
        "matched_candidates": limited,
        "safety_flags": ["trace_only", "writer_hidden", "retrieval_execution_unchanged"],
        "warnings": warnings,
        "blockers": [],
    }


__all__ = [
    "OVERLAY_SHADOW_TRACE_VERSION",
    "build_overlay_shadow_trace",
    "get_overlay_shadow_trace_settings",
]
