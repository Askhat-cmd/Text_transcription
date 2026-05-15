"""Runtime governance filtering for knowledge hits (deterministic policy v1)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


KNOWLEDGE_POLICY_TRACE_VERSION = "knowledge_policy_trace_v1"
_POLICY_SANITIZED_MAX_CHARS = 240
_DEBUG_PREVIEW_MAX_CHARS = 120
_DEBUG_PREVIEW_QUOTE_MAX_CHARS = 80


@dataclass
class KnowledgePolicyDecision:
    chunk_id: str
    source: str
    score: float
    action: str
    allowed_for_writer: bool
    allowed_for_diagnostic: bool
    allowed_for_practice: bool
    sanitized_content: str
    governance: dict[str, Any] = field(default_factory=dict)
    reasons: list[str] = field(default_factory=list)
    risk_flags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "source": self.source,
            "score": float(self.score),
            "action": self.action,
            "allowed_for_writer": bool(self.allowed_for_writer),
            "allowed_for_diagnostic": bool(self.allowed_for_diagnostic),
            "allowed_for_practice": bool(self.allowed_for_practice),
            "sanitized_content": self.sanitized_content,
            "governance": dict(self.governance or {}),
            "reasons": list(self.reasons or []),
            "risk_flags": list(self.risk_flags or []),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "KnowledgePolicyDecision":
        return cls(
            chunk_id=str(payload.get("chunk_id", "") or ""),
            source=str(payload.get("source", "unknown") or "unknown"),
            score=float(payload.get("score", 0.0) or 0.0),
            action=str(payload.get("action", "drop") or "drop"),
            allowed_for_writer=bool(payload.get("allowed_for_writer", False)),
            allowed_for_diagnostic=bool(payload.get("allowed_for_diagnostic", False)),
            allowed_for_practice=bool(payload.get("allowed_for_practice", False)),
            sanitized_content=str(payload.get("sanitized_content", "") or ""),
            governance=(
                dict(payload.get("governance", {}))
                if isinstance(payload.get("governance"), dict)
                else {}
            ),
            reasons=[str(x) for x in payload.get("reasons", [])],
            risk_flags=[str(x) for x in payload.get("risk_flags", [])],
        )

    def to_writer_hit_dict(self) -> dict[str, Any]:
        governance = self.governance or {}
        return {
            "chunk_id": self.chunk_id,
            "source": self.source,
            "score": float(self.score),
            "content": self.sanitized_content,
            "governance_summary": {
                "chunk_type": str(governance.get("chunk_type", "") or ""),
                "allowed_use": list(governance.get("allowed_use", []) or []),
                "safety_flags": list(governance.get("safety_flags", []) or []),
                "policy_action": self.action,
                "policy_reasons": list(self.reasons or []),
            },
        }

    def to_safe_debug_dict(self) -> dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "source": self.source,
            "score": float(self.score),
            "action": self.action,
            "allowed_for_writer": bool(self.allowed_for_writer),
            "allowed_for_diagnostic": bool(self.allowed_for_diagnostic),
            "allowed_for_practice": bool(self.allowed_for_practice),
            "reasons": list(self.reasons or []),
            "risk_flags": list(self.risk_flags or []),
            "sanitized_content_len": len(self.sanitized_content or ""),
        }


def _split_csv(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    raw = str(value).strip()
    if not raw:
        return []
    return [part.strip() for part in raw.split(",") if part.strip()]


def _normalize_content(text: str) -> str:
    return " ".join((text or "").split())


def _trim_to_word_boundary(text: str, max_chars: int) -> str:
    normalized = _normalize_content(text)
    if len(normalized) <= max_chars:
        return normalized
    if max_chars <= 1:
        return "…"

    hard_limit = max(1, max_chars - 1)
    candidate = normalized[:hard_limit].rstrip()
    if not candidate:
        return "…"

    # Prefer sentence boundary near the tail.
    sentence_boundary = max(candidate.rfind("."), candidate.rfind("!"), candidate.rfind("?"))
    if sentence_boundary >= max(12, int(hard_limit * 0.6)):
        candidate = candidate[: sentence_boundary + 1].rstrip()
        if candidate:
            return candidate + "…"

    # Fallback to last word boundary.
    word_boundary = max(candidate.rfind(" "), candidate.rfind("\t"), candidate.rfind("\n"))
    if word_boundary >= max(8, int(hard_limit * 0.45)):
        candidate = candidate[:word_boundary].rstrip()
    if not candidate:
        candidate = normalized[:hard_limit].rstrip()
    return candidate + "…"


def _sanitize_preview(text: str, *, max_chars: int = _POLICY_SANITIZED_MAX_CHARS) -> str:
    normalized = _normalize_content(text)
    if len(normalized) <= max_chars:
        return normalized
    return _trim_to_word_boundary(normalized, max_chars)


def safe_knowledge_debug_preview_v1(
    text: str,
    governance: dict[str, Any],
    *,
    policy_action: str = "",
    max_chars: int = _DEBUG_PREVIEW_MAX_CHARS,
) -> str:
    allowed_use = _split_csv(governance.get("allowed_use"))
    safety_flags = _split_csv(governance.get("safety_flags"))
    action = str(policy_action or "").strip().lower()
    if action in {"drop", "internal_only"}:
        return ""
    if "do_not_use" in allowed_use:
        return ""
    if "internal_only" in allowed_use:
        return ""
    if "source_style_not_user_facing" in safety_flags:
        return ""

    normalized = _normalize_content(text)
    normalized = (
        normalized.replace('"', "")
        .replace("'", "")
        .replace("«", "")
        .replace("»", "")
    )
    if not normalized:
        return ""
    limit = int(max_chars)
    if "not_for_direct_quote" in safety_flags:
        limit = min(limit, _DEBUG_PREVIEW_QUOTE_MAX_CHARS)
    return _sanitize_preview(normalized, max_chars=max(1, limit))


def _safe_governance_dict(governance: object) -> dict[str, Any]:
    return dict(governance) if isinstance(governance, dict) else {}


def _safe_chunking_quality_dict(chunking_quality: object) -> dict[str, Any]:
    return dict(chunking_quality) if isinstance(chunking_quality, dict) else {}


def _extract_governance_from_hit(hit: object) -> tuple[dict[str, Any], dict[str, Any], bool]:
    # Returns governance, chunking_quality, has_governance.
    if isinstance(hit, dict):
        governance = _safe_governance_dict(hit.get("governance"))
        chunking_quality = _safe_chunking_quality_dict(hit.get("chunking_quality"))
        if not chunking_quality:
            chunking_quality = _safe_chunking_quality_dict(governance.get("chunking_quality"))
        return governance, chunking_quality, bool(governance)

    governance = _safe_governance_dict(getattr(hit, "governance", {}))
    chunking_quality = _safe_chunking_quality_dict(getattr(hit, "chunking_quality", {}))
    if not chunking_quality:
        chunking_quality = _safe_chunking_quality_dict(governance.get("chunking_quality"))
    return governance, chunking_quality, bool(governance)


def _build_trace(decisions: list[KnowledgePolicyDecision]) -> dict[str, Any]:
    drop_reasons: list[str] = []
    risk_flags_count: dict[str, int] = {}
    action_counts = {
        "include_writer_context": 0,
        "include_diagnostic_lens": 0,
        "include_practice_candidate": 0,
        "internal_only": 0,
        "drop": 0,
    }

    safe_decisions: list[dict[str, Any]] = []
    for decision in decisions:
        if decision.action in action_counts:
            action_counts[decision.action] += 1
        if decision.action == "drop":
            drop_reasons.extend(decision.reasons)
        for flag in decision.risk_flags:
            risk_flags_count[flag] = risk_flags_count.get(flag, 0) + 1
        safe_decisions.append(
            decision.to_safe_debug_dict()
        )

    return {
        "version": KNOWLEDGE_POLICY_TRACE_VERSION,
        "input_hits_count": len(decisions),
        "included_writer_count": action_counts["include_writer_context"],
        "included_diagnostic_count": action_counts["include_diagnostic_lens"],
        "included_practice_count": action_counts["include_practice_candidate"],
        "internal_only_count": action_counts["internal_only"],
        "dropped_count": action_counts["drop"],
        "drop_reasons": sorted(set(drop_reasons)),
        "risk_flags_count": risk_flags_count,
        "decisions": safe_decisions,
    }


def apply_knowledge_policy_v1(hits: list[Any]) -> tuple[list[KnowledgePolicyDecision], dict[str, Any]]:
    decisions: list[KnowledgePolicyDecision] = []

    for raw_hit in list(hits or []):
        chunk_id = str(getattr(raw_hit, "chunk_id", "") if not isinstance(raw_hit, dict) else raw_hit.get("chunk_id", ""))
        source = str(getattr(raw_hit, "source", "unknown") if not isinstance(raw_hit, dict) else raw_hit.get("source", "unknown"))
        score = float(getattr(raw_hit, "score", 0.0) if not isinstance(raw_hit, dict) else raw_hit.get("score", 0.0) or 0.0)
        content = str(getattr(raw_hit, "content", "") if not isinstance(raw_hit, dict) else raw_hit.get("content", ""))

        governance, chunking_quality, has_governance = _extract_governance_from_hit(raw_hit)
        allowed_use = _split_csv(governance.get("allowed_use"))
        safety_flags = _split_csv(governance.get("safety_flags"))
        chunk_type = str(governance.get("chunk_type", "") or "").strip().lower()

        reasons: list[str] = []
        risk_flags: list[str] = []

        if not has_governance:
            allowed_use = ["writer_context"]
            safety_flags = ["legacy_no_governance"]
            governance = {
                "chunk_type": "legacy",
                "allowed_use": allowed_use,
                "safety_flags": safety_flags,
            }
            reasons.append("legacy_no_governance")
            risk_flags.append("legacy_no_governance")

        mixed_risk = bool(chunking_quality.get("mixed_intent_risk"))
        mixed_severity = str(chunking_quality.get("mixed_intent_severity", "none") or "none").lower()

        if "do_not_use" in allowed_use or chunk_type == "excluded":
            decisions.append(
                KnowledgePolicyDecision(
                    chunk_id=chunk_id,
                    source=source,
                    score=score,
                    action="drop",
                    allowed_for_writer=False,
                    allowed_for_diagnostic=False,
                    allowed_for_practice=False,
                    sanitized_content="",
                    governance=governance,
                    reasons=reasons + ["do_not_use_or_excluded"],
                    risk_flags=risk_flags,
                )
            )
            continue

        if mixed_risk and mixed_severity == "high":
            decisions.append(
                KnowledgePolicyDecision(
                    chunk_id=chunk_id,
                    source=source,
                    score=score,
                    action="drop",
                    allowed_for_writer=False,
                    allowed_for_diagnostic=False,
                    allowed_for_practice=False,
                    sanitized_content="",
                    governance=governance,
                    reasons=reasons + ["mixed_intent_high_drop"],
                    risk_flags=risk_flags + ["mixed_intent_high"],
                )
            )
            continue

        internal_only = (
            "internal_only" in allowed_use
            or "source_style_not_user_facing" in safety_flags
        )

        allowed_for_practice = (
            "practice_suggestion" in allowed_use and chunk_type == "practice"
        )

        if "practice_suggestion" in allowed_use and chunk_type != "practice":
            reasons.append("practice_suggestion_blocked_non_practice")
            risk_flags.append("practice_suggestion_non_practice_guard")
            allowed_for_practice = False

        allowed_for_diagnostic = "diagnostic_lens" in allowed_use
        if mixed_risk and mixed_severity in {"medium", "high"} and chunk_type != "safety":
            allowed_for_diagnostic = False
            risk_flags.append("mixed_intent_restrict_diagnostic")

        if any(flag in safety_flags for flag in ("too_strong_claim", "spiritual_authority_risk", "clinical_risk")):
            allowed_for_diagnostic = False
            risk_flags.append("diagnostic_restricted_by_safety_flags")

        if internal_only:
            allowed_for_writer = False
            action = "internal_only"
            sanitized_content = ""
            reasons.append("internal_only_or_style_not_user_facing")
        else:
            allowed_for_writer = "writer_context" in allowed_use
            action = "include_writer_context" if allowed_for_writer else "drop"
            sanitized_content = _normalize_content(content)

            if "not_for_direct_quote" in safety_flags:
                sanitized_content = _sanitize_preview(sanitized_content)
                reasons.append("content_sanitized_not_for_direct_quote")

            if chunk_type == "safety" and "safety_protocol" in allowed_use:
                sanitized_content = _sanitize_preview(sanitized_content)
                reasons.append("safety_chunk_sanitized")

            if mixed_risk and mixed_severity == "medium" and chunk_type != "safety":
                action = "internal_only"
                allowed_for_writer = False
                sanitized_content = ""
                reasons.append("mixed_intent_medium_internal_only")
                risk_flags.append("mixed_intent_medium")

        practice_metadata = _safe_governance_dict(governance.get("practice_metadata"))
        if allowed_for_practice and not bool(practice_metadata.get("low_resource_safe", False)):
            reasons.append("practice_requires_low_resource_check")
            risk_flags.append("practice_requires_low_resource_check")

        if action == "drop":
            reasons.append("no_writer_path")

        if action == "drop" and allowed_for_diagnostic:
            action = "include_diagnostic_lens"
        if action == "drop" and allowed_for_practice:
            action = "include_practice_candidate"

        if action == "include_writer_context" and not sanitized_content:
            action = "drop"
            reasons.append("empty_content_after_sanitization")

        decisions.append(
            KnowledgePolicyDecision(
                chunk_id=chunk_id,
                source=source,
                score=score,
                action=action,
                allowed_for_writer=bool(action == "include_writer_context"),
                allowed_for_diagnostic=bool(allowed_for_diagnostic),
                allowed_for_practice=bool(allowed_for_practice),
                sanitized_content=sanitized_content if action == "include_writer_context" else "",
                governance=governance,
                reasons=list(dict.fromkeys(reasons)),
                risk_flags=list(dict.fromkeys(risk_flags)),
            )
        )

    trace = _build_trace(decisions)
    return decisions, trace


def build_safe_knowledge_debug_detail_v1(
    *,
    semantic_hits: list[Any],
    knowledge_policy_trace: dict[str, Any],
) -> list[dict[str, Any]]:
    decisions = knowledge_policy_trace.get("decisions", [])
    decisions_by_chunk_id: dict[str, dict[str, Any]] = {}
    if isinstance(decisions, list):
        for raw_decision in decisions:
            if not isinstance(raw_decision, dict):
                continue
            chunk_id = str(raw_decision.get("chunk_id", "") or "")
            if chunk_id and chunk_id not in decisions_by_chunk_id:
                decisions_by_chunk_id[chunk_id] = raw_decision

    safe_details: list[dict[str, Any]] = []
    for raw_hit in list(semantic_hits or []):
        if hasattr(raw_hit, "to_dict"):
            hit = raw_hit.to_dict()
        elif isinstance(raw_hit, dict):
            hit = dict(raw_hit)
        else:
            hit = {"chunk_id": "", "source": "unknown", "score": 0.0, "content": str(raw_hit)}

        chunk_id = str(hit.get("chunk_id", "") or "")
        governance = _safe_governance_dict(hit.get("governance"))
        decision = decisions_by_chunk_id.get(chunk_id, {})
        policy_action = str(decision.get("action", "") or "")
        reasons = [str(x) for x in decision.get("reasons", [])] if isinstance(decision.get("reasons"), list) else []
        risk_flags = [str(x) for x in decision.get("risk_flags", [])] if isinstance(decision.get("risk_flags"), list) else []
        content_raw = str(hit.get("content", "") or "")
        preview = safe_knowledge_debug_preview_v1(
            content_raw,
            governance,
            policy_action=policy_action,
            max_chars=_DEBUG_PREVIEW_MAX_CHARS,
        )
        safe_details.append(
            {
                "chunk_id": chunk_id,
                "source": str(hit.get("source", "unknown") or "unknown"),
                "score": float(hit.get("score", 0.0) or 0.0),
                "content_preview": preview,
                "content_len": len(content_raw),
                "content_redacted": True,
                "governance_summary": {
                    "chunk_type": str(governance.get("chunk_type", "") or ""),
                    "allowed_use": list(governance.get("allowed_use", []) or []),
                    "safety_flags": list(governance.get("safety_flags", []) or []),
                },
                "policy_action": policy_action,
                "policy_reasons": reasons,
                "risk_flags": risk_flags,
            }
        )
    return safe_details
