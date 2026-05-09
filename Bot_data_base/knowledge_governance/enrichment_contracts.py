from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


ENRICHMENT_SCHEMA_VERSION = "kb_llm_enrichment_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    raw = str(value).strip()
    if not raw:
        return []
    return [part.strip() for part in raw.split(",") if part.strip()]


@dataclass
class SplitMergeSuggestion:
    action: str = "keep"
    reason: str = ""


@dataclass
class LLMMetadata:
    provider: str = "mock"
    model: str = "mock-kb-enrichment-v1"
    prompt_version: str = "kb_enrichment_v1"
    generated_at: str = field(default_factory=_utc_now)
    mock: bool = True


@dataclass
class EnrichmentCandidate:
    schema_version: str = ENRICHMENT_SCHEMA_VERSION
    block_id: str = ""
    source_title: str = ""
    chunk_type_original: str = ""
    allowed_use_original: list[str] = field(default_factory=list)
    safety_flags_original: list[str] = field(default_factory=list)

    summary_candidate: str = ""
    lens_family_candidates: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    use_when: list[str] = field(default_factory=list)
    avoid_when: list[str] = field(default_factory=list)
    self_contained_score: float = 0.0
    self_contained_reason: str = ""
    split_merge_suggestion: SplitMergeSuggestion = field(default_factory=SplitMergeSuggestion)
    confidence: float = 0.0
    needs_human_review: bool = False
    review_reasons: list[str] = field(default_factory=list)

    llm_metadata: LLMMetadata = field(default_factory=LLMMetadata)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["allowed_use_original"] = _as_list(payload.get("allowed_use_original"))
        payload["safety_flags_original"] = _as_list(payload.get("safety_flags_original"))
        payload["lens_family_candidates"] = _as_list(payload.get("lens_family_candidates"))
        payload["tags"] = _as_list(payload.get("tags"))
        payload["use_when"] = _as_list(payload.get("use_when"))
        payload["avoid_when"] = _as_list(payload.get("avoid_when"))
        payload["review_reasons"] = _as_list(payload.get("review_reasons"))
        return payload

    @classmethod
    def from_llm_payload(
        cls,
        *,
        llm_payload: dict[str, Any],
        block_id: str,
        source_title: str,
        chunk_type_original: str,
        allowed_use_original: list[str],
        safety_flags_original: list[str],
        llm_metadata: LLMMetadata,
    ) -> "EnrichmentCandidate":
        split_payload = llm_payload.get("split_merge_suggestion") or {}
        split = SplitMergeSuggestion(
            action=str(split_payload.get("action") or "keep").strip() or "keep",
            reason=str(split_payload.get("reason") or "").strip(),
        )
        return cls(
            block_id=str(block_id),
            source_title=str(source_title),
            chunk_type_original=str(chunk_type_original),
            allowed_use_original=_as_list(allowed_use_original),
            safety_flags_original=_as_list(safety_flags_original),
            summary_candidate=str(llm_payload.get("summary_candidate") or "").strip(),
            lens_family_candidates=_as_list(llm_payload.get("lens_family_candidates")),
            tags=_as_list(llm_payload.get("tags")),
            use_when=_as_list(llm_payload.get("use_when")),
            avoid_when=_as_list(llm_payload.get("avoid_when")),
            self_contained_score=float(llm_payload.get("self_contained_score") or 0.0),
            self_contained_reason=str(llm_payload.get("self_contained_reason") or "").strip(),
            split_merge_suggestion=split,
            confidence=float(llm_payload.get("confidence") or 0.0),
            needs_human_review=bool(llm_payload.get("needs_human_review", False)),
            review_reasons=_as_list(llm_payload.get("review_reasons")),
            llm_metadata=llm_metadata,
        )

