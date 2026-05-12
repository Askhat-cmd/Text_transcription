from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

CURRENT_DIR = Path(__file__).resolve().parent
BOTDB_DIR = CURRENT_DIR.parent
if str(BOTDB_DIR) not in sys.path:
    sys.path.insert(0, str(BOTDB_DIR))

from chunkers.book_chunker import BookChunker
from governance.chunking_quality import build_chunking_quality_v1
from governance.governance_adapter import apply_governance_to_blocks_v1, normalize_governance_profile
from ingestors.book_ingestor import BookIngestor
from processors.block_normalizer import BlockNormalizer


DEFAULT_SOURCE_PRD = "PRD-046.0.8"
DEFAULT_READINESS_JSON = "TO_DO_LIST/logs/PRD-046.0.7-HF2/reprocess_readiness_gate.json"
DEFAULT_OUTPUT_DIR = "TO_DO_LIST/logs/PRD-046.0.8"
DEFAULT_REPORTS_DIR = "TO_DO_LIST/reports"
DEFAULT_CONFIG_PATH = "Bot_data_base/config.yaml"
DEFAULT_REGISTRY_PATH = "Bot_data_base/data/registry.json"
DEFAULT_ALL_BLOCKS_PATH = "Bot_data_base/data/processed/all_blocks_merged.json"
DEFAULT_REVIEW_QUEUE_PATH = "TO_DO_LIST/logs/PRD-046.0.7/review_queue.json"

PRACTICE_MARKERS = (
    "**цель:**",
    "цель:",
    "**время:**",
    "время:",
    "шаг 1",
    "шаг 2",
    "упражнение",
    "практика",
    "практик",
)

DIRECT_PRACTICE_STRONG_MARKERS = (
    "цель:",
    "время:",
    "шаг 1",
    "шаг 2",
    "упражнение",
    "практика:",
)

CASE_OR_DIALOGUE_MARKERS = (
    "из сессии",
    "клиент",
    "кейс",
    "диалог",
    "вопрос:",
    "ответ:",
)

QUOTE_OR_SOURCE_MARKERS = (
    "> ",
    "цитата",
    "фрагмент",
    "источник",
    "автор",
    "исследован",
)

LOW_RESOURCE_REVIEW_MARKERS = (
    "паник",
    "суицид",
    "диссоциа",
    "травм",
    "самоповрежд",
)
def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize(value: Any) -> str:
    return str(value or "").strip()


def _to_int(value: Any) -> int:
    try:
        return int(value)
    except Exception:
        return 0


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _save_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _save_markdown(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _safe_preview(text: str, limit: int = 240) -> str:
    value = re.sub(r"\s+", " ", _normalize(text))
    if len(value) <= limit:
        return value
    return value[: max(0, limit - 3)].rstrip() + "..."


def _source_id_from_block(block: dict[str, Any]) -> str:
    source = _normalize(block.get("source"))
    if ":" in source:
        return source.split(":", 1)[1]
    meta = block.get("metadata") or {}
    return _normalize(meta.get("source_id")) or source


def _extract_blocks(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        blocks = payload.get("blocks")
        if isinstance(blocks, list):
            return [row for row in blocks if isinstance(row, dict)]
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    return []


def _load_all_blocks(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return _extract_blocks(_load_json(path))


def _resolve_upload_path(upload_value: str, botdb_dir: Path) -> Path:
    raw = Path(upload_value)
    if raw.is_absolute():
        return raw
    return (botdb_dir / raw).resolve()


def _find_focus_row(registry_records: list[dict[str, Any]], source_id: str) -> dict[str, Any] | None:
    for row in registry_records:
        if _normalize(row.get("source_id")) == source_id and _normalize(row.get("status")) == "done":
            return row
    for row in registry_records:
        if _normalize(row.get("source_id")) == source_id:
            return row
    return None


def _read_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _snapshot_hashes(
    *,
    all_blocks_path: Path,
    registry_path: Path,
    review_queue_path: Path,
    readiness_path: Path,
) -> dict[str, Any]:
    def info(path: Path) -> dict[str, Any]:
        if not path.exists():
            return {"exists": False, "sha256": ""}
        return {"exists": True, "sha256": _sha256(path)}

    return {
        "all_blocks_merged": info(all_blocks_path),
        "registry": info(registry_path),
        "review_queue": info(review_queue_path),
        "readiness_gate_hf2": info(readiness_path),
    }


def build_clean_reprocess_preflight(
    *,
    source_prd: str,
    readiness_payload: dict[str, Any],
    registry_records: list[dict[str, Any]],
    all_blocks: list[dict[str, Any]],
    botdb_dir: Path,
    hash_before: dict[str, Any],
) -> dict[str, Any]:
    blockers: list[str] = []
    ready_for_clean_reprocess = bool(readiness_payload.get("ready_for_clean_reprocess"))
    active_source_count = _to_int(readiness_payload.get("active_source_count"))
    active_source_id = _normalize(readiness_payload.get("active_source_id"))
    legacy_sd_active = bool(readiness_payload.get("legacy_sd_active"))
    chroma_count = _to_int(readiness_payload.get("chroma_count"))

    if not ready_for_clean_reprocess:
        blockers.append("readiness_gate_not_ready")
    if active_source_count != 1:
        blockers.append("active_source_count_not_one")
    if not active_source_id:
        blockers.append("active_source_id_missing")
    if legacy_sd_active:
        blockers.append("legacy_sd_active")

    focus_row = _find_focus_row(registry_records, active_source_id) if active_source_id else None
    if focus_row is None:
        blockers.append("active_source_missing_in_registry")
        focus_row = {}

    upload_value = _normalize(((focus_row or {}).get("file_paths") or {}).get("upload"))
    raw_path = _resolve_upload_path(upload_value, botdb_dir) if upload_value else None
    raw_markdown_found = bool(raw_path and raw_path.exists())
    if not raw_markdown_found:
        blockers.append("raw_markdown_missing")

    old_processed_blocks_count = sum(1 for block in all_blocks if _source_id_from_block(block) == active_source_id)
    if old_processed_blocks_count <= 0:
        blockers.append("old_processed_blocks_missing")

    return {
        "schema_version": "clean_reprocess_preflight_v1",
        "source_prd": source_prd,
        "generated_at": _utc_now(),
        "passed": len(blockers) == 0,
        "blockers": blockers,
        "ready_for_clean_reprocess": ready_for_clean_reprocess,
        "active_source_count": active_source_count,
        "active_source_id": active_source_id,
        "active_source_title": _normalize((focus_row or {}).get("title")),
        "active_source_type": _normalize((focus_row or {}).get("source_type")) or "unknown",
        "legacy_sd_active": legacy_sd_active,
        "raw_markdown_found": raw_markdown_found,
        "raw_markdown_path": str(raw_path) if raw_path else "",
        "old_processed_blocks_count": old_processed_blocks_count,
        "old_registry_blocks_count": _to_int((focus_row or {}).get("blocks_count")),
        "chroma_count_before": chroma_count,
        "hash_before": hash_before,
    }


def run_clean_reprocess_candidate(
    *,
    source_prd: str,
    preflight: dict[str, Any],
    config: dict[str, Any],
) -> dict[str, Any]:
    if not bool(preflight.get("passed")):
        raise RuntimeError("Cannot run candidate reprocess: preflight failed.")

    raw_path = Path(_normalize(preflight.get("raw_markdown_path")))
    source_id = _normalize(preflight.get("active_source_id"))
    source_title = _normalize(preflight.get("active_source_title"))
    source_type = _normalize(preflight.get("active_source_type")) or "book"

    # We preserve registry identity for candidate rebuild.
    registry_row = preflight.get("_registry_row") or {}
    author = _normalize(registry_row.get("author"))
    author_id = _normalize(registry_row.get("author_id"))
    language = _normalize(registry_row.get("language")) or "ru"

    ingestor = BookIngestor()
    text = ingestor.load_text(str(raw_path))

    chunking_cfg = {}
    if isinstance(config.get("chunking"), dict):
        chunking_cfg = config.get("chunking") or {}
    chunker = BookChunker(chunking_cfg)
    normalizer = BlockNormalizer()

    blocks = chunker.chunk_file_from_text(
        text=text,
        author=author,
        book_title=source_title,
        language=language,
        author_id=author_id,
    )
    blocks = normalizer.normalize(blocks)
    blocks = apply_governance_to_blocks_v1(
        blocks=blocks,
        source_id=source_id,
        source_title=source_title,
        source_type=source_type,
        source_kind="book",
        governance_profile=normalize_governance_profile("general_book"),
    )
    for block in blocks:
        block.source_id = source_id
        block.source_type = source_type
        block.source_title = source_title
        block.chunking_quality = build_chunking_quality_v1(block)

    candidate_blocks = [block.to_bot_format() for block in blocks]
    raw_sha = _sha256(raw_path)
    return {
        "schema_version": "clean_reprocess_candidate_v1",
        "source_prd": source_prd,
        "generated_at": _utc_now(),
        "mode": "candidate",
        "source": {
            "source_id": source_id,
            "title": source_title,
            "source_type": source_type,
            "raw_path": str(raw_path),
            "raw_sha256": raw_sha,
        },
        "candidate": {
            "blocks_count": len(candidate_blocks),
            "blocks": candidate_blocks,
        },
        "processing": {
            "chunker": "BookChunker",
            "normalizer": "BlockNormalizer",
            "governance": "governance_adapter_v1",
            "chunking_quality": "chunking_quality_v1",
            "sd_labeling_active": False,
        },
    }


def _collect_distribution(blocks: list[dict[str, Any]]) -> dict[str, Any]:
    chunk_type_dist: Counter[str] = Counter()
    allowed_use_dist: Counter[str] = Counter()
    safety_flags_dist: Counter[str] = Counter()
    lens_family_dist: Counter[str] = Counter()

    governance_present = 0
    chunking_quality_present = 0
    allowed_use_present = 0
    safety_flags_present = 0
    not_for_direct_quote_count = 0
    source_style_count = 0
    source_id_consistency_count = 0

    for block in blocks:
        if _source_id_from_block(block):
            source_id_consistency_count += 1
        meta = block.get("metadata") or {}
        governance = meta.get("governance") if isinstance(meta.get("governance"), dict) else {}
        if governance:
            governance_present += 1
        chunking_quality = meta.get("chunking_quality") if isinstance(meta.get("chunking_quality"), dict) else {}
        if chunking_quality:
            chunking_quality_present += 1

        chunk_type = _normalize(governance.get("chunk_type")) or "unknown"
        chunk_type_dist[chunk_type] += 1

        allowed_use = governance.get("allowed_use") if isinstance(governance.get("allowed_use"), list) else []
        if allowed_use:
            allowed_use_present += 1
        for item in allowed_use:
            allowed_use_dist[_normalize(item)] += 1

        safety_flags = governance.get("safety_flags") if isinstance(governance.get("safety_flags"), list) else []
        if safety_flags:
            safety_flags_present += 1
        for item in safety_flags:
            value = _normalize(item)
            safety_flags_dist[value] += 1
            if value == "not_for_direct_quote":
                not_for_direct_quote_count += 1
            if value == "source_style_not_user_facing":
                source_style_count += 1

        lens_family = governance.get("lens_family") if isinstance(governance.get("lens_family"), list) else []
        for item in lens_family:
            lens_family_dist[_normalize(item)] += 1

    total = len(blocks) or 1
    return {
        "total": len(blocks),
        "governance_present_rate": governance_present / total,
        "chunking_quality_present_rate": chunking_quality_present / total,
        "allowed_use_present_rate": allowed_use_present / total,
        "safety_flags_present_rate": safety_flags_present / total,
        "source_id_consistency_rate": source_id_consistency_count / total,
        "not_for_direct_quote_present_count": not_for_direct_quote_count,
        "source_style_not_user_facing_present_count": source_style_count,
        "chunk_type_distribution": dict(sorted(chunk_type_dist.items())),
        "allowed_use_distribution": dict(sorted(allowed_use_dist.items())),
        "safety_flags_distribution": dict(sorted(safety_flags_dist.items())),
        "lens_family_distribution": dict(sorted(lens_family_dist.items())),
    }


def build_candidate_stats(
    *,
    source_prd: str,
    source_id: str,
    old_blocks: list[dict[str, Any]],
    candidate_blocks: list[dict[str, Any]],
) -> dict[str, Any]:
    old_dist = _collect_distribution(old_blocks)
    new_dist = _collect_distribution(candidate_blocks)
    candidate_blocks_count = len(candidate_blocks)
    old_processed_blocks_count = len(old_blocks)
    return {
        "schema_version": "candidate_stats_v1",
        "source_prd": source_prd,
        "generated_at": _utc_now(),
        "source_id": source_id,
        "candidate_blocks_count": candidate_blocks_count,
        "old_processed_blocks_count": old_processed_blocks_count,
        "block_count_delta": candidate_blocks_count - old_processed_blocks_count,
        "source_id_consistency_rate": new_dist["source_id_consistency_rate"],
        "governance_present_rate": new_dist["governance_present_rate"],
        "chunking_quality_present_rate": new_dist["chunking_quality_present_rate"],
        "allowed_use_present_rate": new_dist["allowed_use_present_rate"],
        "safety_flags_present_rate": new_dist["safety_flags_present_rate"],
        "not_for_direct_quote_present_count": new_dist["not_for_direct_quote_present_count"],
        "source_style_not_user_facing_present_count": new_dist["source_style_not_user_facing_present_count"],
        "chunk_type_distribution": new_dist["chunk_type_distribution"],
        "allowed_use_distribution": new_dist["allowed_use_distribution"],
        "safety_flags_distribution": new_dist["safety_flags_distribution"],
        "lens_family_distribution": new_dist["lens_family_distribution"],
        "sd_labeling_active": False,
        "old_distribution": {
            "chunk_type_distribution": old_dist["chunk_type_distribution"],
            "allowed_use_distribution": old_dist["allowed_use_distribution"],
            "safety_flags_distribution": old_dist["safety_flags_distribution"],
        },
        "candidate_ready_for_next_step": (
            candidate_blocks_count > 0
            and new_dist["source_id_consistency_rate"] == 1.0
            and new_dist["governance_present_rate"] == 1.0
            and new_dist["chunking_quality_present_rate"] == 1.0
            and new_dist["allowed_use_present_rate"] == 1.0
            and new_dist["safety_flags_present_rate"] == 1.0
        ),
    }


def _dict_delta(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    keys = sorted(set(before.keys()) | set(after.keys()))
    payload: dict[str, Any] = {}
    for key in keys:
        b = _to_int(before.get(key, 0))
        a = _to_int(after.get(key, 0))
        payload[key] = {"before": b, "after": a, "delta": a - b}
    return payload


def build_candidate_diff_report(
    *,
    source_prd: str,
    source_id: str,
    old_blocks: list[dict[str, Any]],
    candidate_blocks: list[dict[str, Any]],
    candidate_stats: dict[str, Any],
) -> dict[str, Any]:
    old_dist = _collect_distribution(old_blocks)
    new_dist = _collect_distribution(candidate_blocks)
    risks: list[str] = []
    if candidate_stats.get("block_count_delta", 0) != 0:
        risks.append("block_count_changed")
    if candidate_stats.get("source_id_consistency_rate") != 1.0:
        risks.append("source_id_inconsistency")
    if candidate_stats.get("governance_present_rate") != 1.0:
        risks.append("governance_missing")
    if candidate_stats.get("chunking_quality_present_rate") != 1.0:
        risks.append("chunking_quality_missing")

    return {
        "schema_version": "candidate_diff_report_v1",
        "source_prd": source_prd,
        "generated_at": _utc_now(),
        "source_id": source_id,
        "old_block_count": len(old_blocks),
        "candidate_block_count": len(candidate_blocks),
        "block_count_delta": candidate_stats.get("block_count_delta"),
        "source_id_before_set": sorted({_source_id_from_block(block) for block in old_blocks}),
        "source_id_after_set": sorted({_source_id_from_block(block) for block in candidate_blocks}),
        "chunk_type_distribution_diff": _dict_delta(
            old_dist["chunk_type_distribution"],
            new_dist["chunk_type_distribution"],
        ),
        "allowed_use_distribution_diff": _dict_delta(
            old_dist["allowed_use_distribution"],
            new_dist["allowed_use_distribution"],
        ),
        "safety_flags_distribution_diff": _dict_delta(
            old_dist["safety_flags_distribution"],
            new_dist["safety_flags_distribution"],
        ),
        "governance_completeness_before": old_dist["governance_present_rate"],
        "governance_completeness_after": new_dist["governance_present_rate"],
        "top_risks": risks,
    }


def _as_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [_normalize(item) for item in value if _normalize(item)]
    return []


def _dedupe(items: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for item in items:
        value = _normalize(item)
        if not value or value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def _practice_markers(text: str) -> list[str]:
    low = _normalize(text).lower()
    return [marker for marker in PRACTICE_MARKERS if marker in low]


def _has_step_pair(text: str) -> bool:
    low = text.lower()
    if "шаг 1" in low and "шаг 2" in low:
        return True
    return bool(re.search(r"(?m)^\s*(?:1[\).]|-|\*)\s+", text)) and bool(re.search(r"(?m)^\s*(?:2[\).]|-|\*)\s+", text))


def _is_direct_practice_protocol(text: str) -> bool:
    low = _normalize(text).lower()
    goal = "цель:" in low or "**цель:**" in low
    duration = "время:" in low or "**время:**" in low
    steps = _has_step_pair(text) or "шаг 1" in low
    if goal and duration:
        return True
    if goal and steps:
        return True
    if duration and steps:
        return True
    return "шаг 1" in low and "шаг 2" in low


def _practice_taxonomy_for_text(text: str) -> tuple[str | None, list[str]]:
    markers = _practice_markers(text)
    if not markers:
        return None, []

    low = _normalize(text).lower()
    is_case_or_dialogue = any(marker in low for marker in CASE_OR_DIALOGUE_MARKERS)
    is_quote_or_source = low.lstrip().startswith(">") or any(marker in low for marker in QUOTE_OR_SOURCE_MARKERS)
    is_direct = _is_direct_practice_protocol(text)

    if is_direct and not is_case_or_dialogue and not is_quote_or_source:
        return "direct_practice_protocol", markers
    if is_case_or_dialogue:
        return "case_or_dialogue_about_practice", markers
    if is_quote_or_source:
        return "quote_or_source_fragment_with_practice_terms", markers
    return "practice_context_or_theory", markers


def _calibrate_governance_for_taxonomy(
    *,
    governance: dict[str, Any],
    taxonomy_label: str,
    text: str,
) -> tuple[dict[str, Any], bool]:
    updated = dict(governance or {})
    chunk_type_before = _normalize(updated.get("chunk_type")) or "unknown"
    allowed_use = _as_list(updated.get("allowed_use"))
    safety_flags = _as_list(updated.get("safety_flags"))

    mutated = False
    if taxonomy_label == "direct_practice_protocol":
        if chunk_type_before != "practice":
            updated["chunk_type"] = "practice"
            mutated = True
        new_allowed = _dedupe(allowed_use + ["practice_suggestion"])
        if new_allowed != allowed_use:
            updated["allowed_use"] = new_allowed
            mutated = True
        new_flags = _dedupe(safety_flags + ["not_for_direct_quote", "practice_requires_low_resource_check"])
        if any(marker in _normalize(text).lower() for marker in LOW_RESOURCE_REVIEW_MARKERS):
            new_flags = _dedupe(new_flags + ["needs_review"])
        if new_flags != safety_flags:
            updated["safety_flags"] = new_flags
            mutated = True
        return updated, mutated

    # Conservative behavior for non-direct mentions: no practice_suggestion.
    if "practice_suggestion" in allowed_use:
        updated["allowed_use"] = [item for item in allowed_use if item != "practice_suggestion"]
        mutated = True

    if taxonomy_label == "case_or_dialogue_about_practice" and chunk_type_before == "practice":
        updated["chunk_type"] = "case"
        mutated = True
    elif taxonomy_label == "quote_or_source_fragment_with_practice_terms" and chunk_type_before == "practice":
        updated["chunk_type"] = "quote"
        mutated = True
    elif taxonomy_label == "practice_context_or_theory" and chunk_type_before == "practice":
        updated["chunk_type"] = "lens"
        mutated = True

    new_flags = _dedupe(_as_list(updated.get("safety_flags")) + ["not_for_direct_quote"])
    if new_flags != _as_list(updated.get("safety_flags")):
        updated["safety_flags"] = new_flags
        mutated = True

    return updated, mutated


def build_practice_taxonomy_report(
    *,
    source_prd: str,
    candidate_blocks: list[dict[str, Any]],
) -> dict[str, Any]:
    practice_marker_hits_count = 0
    direct_practice_protocol_count = 0
    practice_context_or_theory_count = 0
    case_or_dialogue_about_practice_count = 0
    quote_or_source_fragment_with_practice_terms_count = 0
    direct_practice_misclassified_count = 0
    contextual_false_positive_count = 0
    unsafe_practice_suggestion_count = 0
    examples: list[dict[str, Any]] = []

    for block in candidate_blocks:
        text = _normalize(block.get("text"))
        taxonomy_label, markers = _practice_taxonomy_for_text(text)
        if taxonomy_label is None:
            continue

        practice_marker_hits_count += len(markers)
        meta = block.get("metadata") or {}
        governance = meta.get("governance") if isinstance(meta.get("governance"), dict) else {}
        chunk_type_before = _normalize(governance.get("chunk_type")) or "unknown"
        calibrated, _ = _calibrate_governance_for_taxonomy(governance=governance, taxonomy_label=taxonomy_label, text=text)
        meta["governance"] = calibrated
        quality = meta.get("chunking_quality") if isinstance(meta.get("chunking_quality"), dict) else {}
        quality["practice_taxonomy_v1"] = {
            "label": taxonomy_label,
            "markers": markers,
        }
        meta["chunking_quality"] = quality
        block["metadata"] = meta

        chunk_type_after = _normalize(calibrated.get("chunk_type")) or "unknown"
        allowed_after = _as_list(calibrated.get("allowed_use"))
        safety_after = _as_list(calibrated.get("safety_flags"))

        if taxonomy_label == "direct_practice_protocol":
            direct_practice_protocol_count += 1
            if chunk_type_after != "practice":
                direct_practice_misclassified_count += 1
            required_flags = {"not_for_direct_quote", "practice_requires_low_resource_check"}
            if "practice_suggestion" not in allowed_after or not required_flags.issubset(set(safety_after)):
                unsafe_practice_suggestion_count += 1
        elif taxonomy_label == "practice_context_or_theory":
            practice_context_or_theory_count += 1
        elif taxonomy_label == "case_or_dialogue_about_practice":
            case_or_dialogue_about_practice_count += 1
        elif taxonomy_label == "quote_or_source_fragment_with_practice_terms":
            quote_or_source_fragment_with_practice_terms_count += 1

        if taxonomy_label != "direct_practice_protocol" and chunk_type_after == "practice":
            contextual_false_positive_count += 1
        if taxonomy_label != "direct_practice_protocol" and "practice_suggestion" in allowed_after:
            unsafe_practice_suggestion_count += 1

        if len(examples) < 20:
            examples.append(
                {
                    "block_id": _normalize(block.get("id")),
                    "taxonomy": taxonomy_label,
                    "chunk_type_before": chunk_type_before,
                    "chunk_type_after": chunk_type_after,
                    "markers": markers,
                    "safe_preview": _safe_preview(text, 220),
                }
            )

    return {
        "schema_version": "candidate_practice_taxonomy_report_v1",
        "source_prd": source_prd,
        "generated_at": _utc_now(),
        "candidate_blocks_count": len(candidate_blocks),
        "practice_marker_hits_count": practice_marker_hits_count,
        "direct_practice_protocol_count": direct_practice_protocol_count,
        "practice_context_or_theory_count": practice_context_or_theory_count,
        "case_or_dialogue_about_practice_count": case_or_dialogue_about_practice_count,
        "quote_or_source_fragment_with_practice_terms_count": quote_or_source_fragment_with_practice_terms_count,
        "direct_practice_misclassified_count": direct_practice_misclassified_count,
        "contextual_false_positive_count": contextual_false_positive_count,
        "unsafe_practice_suggestion_count": unsafe_practice_suggestion_count,
        "examples": examples,
    }


def build_practice_like_report(
    *,
    source_prd: str,
    candidate_blocks: list[dict[str, Any]],
) -> dict[str, Any]:
    practice_like_candidates_count = 0
    practice_like_as_practice_count = 0
    misclassified_examples: list[dict[str, Any]] = []

    for block in candidate_blocks:
        text = _normalize(block.get("text"))
        taxonomy_label, markers = _practice_taxonomy_for_text(text)
        if taxonomy_label is None:
            continue
        practice_like_candidates_count += 1
        meta = block.get("metadata") or {}
        governance = meta.get("governance") if isinstance(meta.get("governance"), dict) else {}
        chunk_type = _normalize(governance.get("chunk_type")) or "unknown"
        if chunk_type == "practice":
            practice_like_as_practice_count += 1
        if taxonomy_label == "direct_practice_protocol" and chunk_type != "practice":
            misclassified_examples.append(
                {
                    "block_id": _normalize(block.get("id")),
                    "chunk_type": chunk_type,
                    "allowed_use": _as_list(governance.get("allowed_use")),
                    "safety_flags": _as_list(governance.get("safety_flags")),
                    "markers": markers,
                    "safe_preview": _safe_preview(text, 240),
                }
            )

    return {
        "schema_version": "practice_like_report_v1",
        "source_prd": source_prd,
        "generated_at": _utc_now(),
        "practice_like_candidates_count": practice_like_candidates_count,
        "practice_like_as_practice_count": practice_like_as_practice_count,
        "practice_like_misclassified_count": len(misclassified_examples),
        "misclassified_examples": misclassified_examples[:30],
    }


def _is_dialogue_or_case_text(text: str) -> bool:
    low = _normalize(text).lower()
    if low.lstrip().startswith(">"):
        return True
    return any(marker in low for marker in CASE_OR_DIALOGUE_MARKERS)


def _mixed_intent_resolution_for_block(block: dict[str, Any]) -> dict[str, Any] | None:
    meta = block.get("metadata") or {}
    quality = meta.get("chunking_quality") if isinstance(meta.get("chunking_quality"), dict) else {}
    if not isinstance(quality, dict):
        return None
    if not bool(quality.get("mixed_intent_risk")):
        return None
    severity_before = _normalize(quality.get("mixed_intent_severity")).lower()
    if severity_before not in {"high", "medium"}:
        return None

    governance = meta.get("governance") if isinstance(meta.get("governance"), dict) else {}
    text = _normalize(block.get("text"))
    taxonomy = (quality.get("practice_taxonomy_v1") or {}).get("label")
    if not taxonomy:
        taxonomy, _ = _practice_taxonomy_for_text(text)
    chunk_type_before = _normalize(governance.get("chunk_type")) or _normalize(quality.get("primary_role")) or "unknown"
    secondary_before = _as_list(quality.get("secondary_role_markers"))
    if not secondary_before and _practice_markers(text):
        secondary_before = ["practice"]

    is_direct = _is_direct_practice_protocol(text)
    is_dialogue_case = _is_dialogue_or_case_text(text)
    is_quote = _normalize(text).startswith(">")

    resolution = "primary_role_resolved"
    split_merge_suggestion = "no_split_required"
    review_reasons: list[str] = []
    primary_after = chunk_type_before
    secondary_after = _dedupe(secondary_before)
    severity_after = "low"
    mixed_risk_after = False

    if is_direct and is_dialogue_case:
        resolution = "review_only"
        split_merge_suggestion = "manual_review_no_auto_split"
        review_reasons = ["dialogue_contains_instructional_segments"]
        primary_after = "case"
        secondary_after = _dedupe(secondary_after + ["practice"])
        severity_after = "low"
        mixed_risk_after = False
    elif is_dialogue_case and not is_direct:
        resolution = "false_positive"
        split_merge_suggestion = "no_split_required"
        review_reasons = []
        primary_after = "case" if not is_quote else "quote"
        secondary_after = _dedupe([marker for marker in secondary_after if marker != "practice"])
    elif is_direct and ("цель:" in text.lower() and "время:" in text.lower() and "шаг 1" in text.lower()):
        # Protocol + long narrative in one block can require manual split.
        resolution = "split_required"
        split_merge_suggestion = "candidate_manual_split_review"
        review_reasons = ["direct_practice_with_heavy_narrative_context"]
        primary_after = "practice"
        secondary_after = _dedupe(secondary_after + ["case"])
        severity_after = "high"
        mixed_risk_after = True
    else:
        resolution = "primary_role_resolved"
        split_merge_suggestion = "no_split_required"
        review_reasons = []
        primary_after = chunk_type_before
        secondary_after = _dedupe(secondary_after)

    if primary_after and primary_after != "unknown" and isinstance(governance, dict):
        governance["chunk_type"] = primary_after
        allowed_use = _as_list(governance.get("allowed_use"))
        safety_flags = _as_list(governance.get("safety_flags"))
        if primary_after != "practice" and "practice_suggestion" in allowed_use:
            allowed_use = [item for item in allowed_use if item != "practice_suggestion"]
        governance["allowed_use"] = _dedupe(allowed_use)
        governance["safety_flags"] = _dedupe(safety_flags + ["not_for_direct_quote"])
        meta["governance"] = governance

    quality["mixed_intent_resolution"] = resolution
    quality["primary_role_after"] = primary_after
    quality["secondary_role_markers_after"] = secondary_after
    quality["split_merge_suggestion"] = split_merge_suggestion
    quality["review_reasons"] = review_reasons
    quality["mixed_intent_severity_before"] = severity_before
    quality["mixed_intent_severity_after"] = severity_after
    quality["mixed_intent_risk_before"] = True
    quality["mixed_intent_risk"] = mixed_risk_after
    quality["mixed_intent_severity"] = severity_after
    quality["mixed_intent_reason_after"] = "resolved_by_candidate_calibration"
    meta["chunking_quality"] = quality
    block["metadata"] = meta

    return {
        "block_id": _normalize(block.get("id")),
        "current_chunk_type": chunk_type_before,
        "primary_role_before": _normalize(quality.get("primary_role")) or chunk_type_before,
        "secondary_role_markers_before": secondary_before,
        "mixed_intent_severity_before": severity_before,
        "taxonomy": taxonomy or "unknown",
        "recommended_resolution": resolution,
        "safe_preview": _safe_preview(text, 220),
        "primary_role_after": primary_after,
        "secondary_role_markers_after": secondary_after,
        "mixed_intent_severity_after": severity_after,
        "review_reasons": review_reasons,
    }


def build_mixed_intent_audit_report(
    *,
    source_prd: str,
    candidate_blocks: list[dict[str, Any]],
) -> dict[str, Any]:
    mixed_intent_cases: list[dict[str, Any]] = []
    mixed_intent_alerts_before = 0
    split_required_count = 0
    review_only_count = 0
    false_positive_count = 0
    primary_role_resolved_count = 0
    unresolved_count = 0

    for block in candidate_blocks:
        row = _mixed_intent_resolution_for_block(block)
        if row is None:
            continue
        mixed_intent_alerts_before += 1
        mixed_intent_cases.append(row)
        resolution = _normalize(row.get("recommended_resolution"))
        if resolution == "split_required":
            split_required_count += 1
            unresolved_count += 1
        elif resolution == "review_only":
            review_only_count += 1
        elif resolution == "false_positive":
            false_positive_count += 1
        elif resolution == "primary_role_resolved":
            primary_role_resolved_count += 1
        else:
            unresolved_count += 1

    return {
        "schema_version": "candidate_mixed_intent_audit_v1",
        "source_prd": source_prd,
        "generated_at": _utc_now(),
        "candidate_blocks_count": len(candidate_blocks),
        "mixed_intent_alerts_before": mixed_intent_alerts_before,
        "mixed_intent_unresolved_count": unresolved_count,
        "mixed_intent_split_required_count": split_required_count,
        "mixed_intent_review_only_count": review_only_count,
        "mixed_intent_false_positive_count": false_positive_count,
        "mixed_intent_primary_role_resolved_count": primary_role_resolved_count,
        "mixed_intent_cases": mixed_intent_cases,
    }


def build_no_mutation_check(
    *,
    source_prd: str,
    hash_before: dict[str, Any],
    hash_after: dict[str, Any],
    chroma_count_before: int,
    chroma_count_after: int,
) -> dict[str, Any]:
    all_blocks_mutated = hash_before["all_blocks_merged"]["sha256"] != hash_after["all_blocks_merged"]["sha256"]
    registry_mutated = hash_before["registry"]["sha256"] != hash_after["registry"]["sha256"]
    review_queue_mutated = hash_before["review_queue"]["sha256"] != hash_after["review_queue"]["sha256"]
    readiness_hf2_mutated = hash_before["readiness_gate_hf2"]["sha256"] != hash_after["readiness_gate_hf2"]["sha256"]
    chroma_mutated = int(chroma_count_before) != int(chroma_count_after)

    return {
        "schema_version": "no_mutation_check_v1",
        "source_prd": source_prd,
        "generated_at": _utc_now(),
        "all_blocks_merged_mutated": all_blocks_mutated,
        "registry_mutated": registry_mutated,
        "review_queue_mutated": review_queue_mutated,
        "readiness_hf2_mutated": readiness_hf2_mutated,
        "chroma_count_before": int(chroma_count_before),
        "chroma_count_after": int(chroma_count_after),
        "chroma_mutated": chroma_mutated,
        "passed": not any([all_blocks_mutated, registry_mutated, review_queue_mutated, readiness_hf2_mutated, chroma_mutated]),
    }


def build_candidate_governance_gate(
    *,
    source_prd: str,
    preflight: dict[str, Any],
    candidate_stats: dict[str, Any],
    practice_like_report: dict[str, Any],
    no_mutation_check: dict[str, Any],
    candidate_blocks: list[dict[str, Any]],
    practice_taxonomy_report: dict[str, Any] | None = None,
    mixed_intent_audit_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    blockers: list[str] = []
    warnings: list[str] = []

    if not bool(preflight.get("passed")):
        blockers.append("preflight_failed")
    if _to_int(candidate_stats.get("candidate_blocks_count")) <= 0:
        blockers.append("candidate_blocks_zero")
    if float(candidate_stats.get("source_id_consistency_rate") or 0.0) < 1.0:
        blockers.append("source_id_consistency_not_full")
    if float(candidate_stats.get("governance_present_rate") or 0.0) < 1.0:
        blockers.append("governance_missing")
    if float(candidate_stats.get("chunking_quality_present_rate") or 0.0) < 1.0:
        blockers.append("chunking_quality_missing")
    if float(candidate_stats.get("allowed_use_present_rate") or 0.0) < 1.0:
        blockers.append("allowed_use_missing")
    if float(candidate_stats.get("safety_flags_present_rate") or 0.0) < 1.0:
        blockers.append("safety_flags_missing")
    if bool(candidate_stats.get("sd_labeling_active")):
        blockers.append("sd_labeling_active_detected")
    if not bool(no_mutation_check.get("passed")):
        blockers.append("no_mutation_check_failed")

    mixed_intent_alerts = 0
    for block in candidate_blocks:
        quality = ((block.get("metadata") or {}).get("chunking_quality") or {})
        if not isinstance(quality, dict):
            continue
        if _normalize(quality.get("mixed_intent_severity")) in {"high", "medium"} and bool(quality.get("mixed_intent_risk")):
            mixed_intent_alerts += 1
    if mixed_intent_alerts > 0:
        warnings.append("mixed_intent_high_medium_detected")

    taxonomy = practice_taxonomy_report or {}
    misclassified_count = _to_int(taxonomy.get("direct_practice_misclassified_count"))
    if not taxonomy:
        misclassified_count = _to_int(practice_like_report.get("practice_like_misclassified_count"))
    contextual_false_positive_count = _to_int(taxonomy.get("contextual_false_positive_count"))
    unsafe_practice_suggestion_count = _to_int(taxonomy.get("unsafe_practice_suggestion_count"))

    if contextual_false_positive_count > 0:
        warnings.append("contextual_false_positive_detected")
    if unsafe_practice_suggestion_count > 0:
        warnings.append("unsafe_practice_suggestion_detected")

    if mixed_intent_audit_report is not None:
        mixed_before = _to_int(mixed_intent_audit_report.get("mixed_intent_alerts_before"))
        mixed_unresolved = _to_int(mixed_intent_audit_report.get("mixed_intent_unresolved_count"))
        mixed_split_required = _to_int(mixed_intent_audit_report.get("mixed_intent_split_required_count"))
        mixed_review_only = _to_int(mixed_intent_audit_report.get("mixed_intent_review_only_count"))
        mixed_false_positive = _to_int(mixed_intent_audit_report.get("mixed_intent_false_positive_count"))
        if mixed_review_only > 0:
            warnings.append("review_only_mixed_intent_detected")

        candidate_ready_for_apply = (
            len(blockers) == 0
            and misclassified_count == 0
            and unsafe_practice_suggestion_count == 0
            and contextual_false_positive_count == 0
            and mixed_unresolved == 0
            and mixed_split_required == 0
            and float(candidate_stats.get("source_id_consistency_rate") or 0.0) == 1.0
            and float(candidate_stats.get("governance_present_rate") or 0.0) == 1.0
            and float(candidate_stats.get("chunking_quality_present_rate") or 0.0) == 1.0
            and float(candidate_stats.get("allowed_use_present_rate") or 0.0) == 1.0
            and float(candidate_stats.get("safety_flags_present_rate") or 0.0) == 1.0
            and not bool(candidate_stats.get("sd_labeling_active"))
            and bool(no_mutation_check.get("passed"))
        )

        if blockers:
            status = "failed"
            next_prd = "PRD-046.0.8-HF2-BLOCKER — Candidate Governance Blocker Fix v1"
        elif mixed_split_required > 0:
            status = "candidate_needs_manual_split_review"
            next_prd = "PRD-046.0.8-HF3 — Candidate Manual Split Review / Deterministic Split v1"
        elif misclassified_count > 0 or unsafe_practice_suggestion_count > 0 or mixed_unresolved > 0:
            status = "candidate_needs_governance_calibration"
            next_prd = "PRD-046.0.8-HF2-FIX — Remaining Governance Calibration Fix v1"
        elif candidate_ready_for_apply:
            status = "passed"
            next_prd = "PRD-046.0.8.1 — Controlled Candidate Apply + Chroma Reindex + KB Quality Re-Audit v1"
        else:
            status = "candidate_needs_governance_calibration"
            next_prd = "PRD-046.0.8-HF2-FIX — Remaining Governance Calibration Fix v1"

        return {
            "schema_version": "candidate_governance_gate_v3",
            "source_prd": source_prd,
            "generated_at": _utc_now(),
            "status": status,
            "blockers": blockers,
            "warnings": warnings,
            "direct_practice_misclassified_count": misclassified_count,
            "unsafe_practice_suggestion_count": unsafe_practice_suggestion_count,
            "contextual_false_positive_count": contextual_false_positive_count,
            "mixed_intent_alerts_before": mixed_before,
            "mixed_intent_unresolved_count": mixed_unresolved,
            "mixed_intent_split_required_count": mixed_split_required,
            "mixed_intent_review_only_count": mixed_review_only,
            "mixed_intent_false_positive_count": mixed_false_positive,
            "candidate_ready_for_apply": candidate_ready_for_apply,
            "mixed_intent_alerts": mixed_intent_alerts,
            "next_recommended_prd": next_prd,
        }

    if blockers:
        status = "failed"
        next_prd = "PRD-046.0.8-HF1-FIX — Candidate Governance Blocker Fix v1"
    elif misclassified_count > 0 or unsafe_practice_suggestion_count > 0:
        status = "candidate_needs_governance_calibration"
        next_prd = "PRD-046.0.8-HF1-FIX — Candidate Governance Blocker Fix v1"
    elif mixed_intent_alerts > 0 or contextual_false_positive_count > 0:
        status = "candidate_needs_governance_calibration"
        next_prd = "PRD-046.0.8-HF2 — Remaining Candidate Governance Warning Calibration v1"
    else:
        status = "passed"
        next_prd = "PRD-046.0.8.1 — Controlled Candidate Apply + Chroma Reindex + KB Quality Re-Audit v1"

    return {
        "schema_version": "candidate_governance_gate_v2",
        "source_prd": source_prd,
        "generated_at": _utc_now(),
        "status": status,
        "blockers": blockers,
        "warnings": warnings,
        "direct_practice_misclassified_count": misclassified_count,
        "unsafe_practice_suggestion_count": unsafe_practice_suggestion_count,
        "contextual_false_positive_count": contextual_false_positive_count,
        "practice_like_misclassified_count": misclassified_count,
        "mixed_intent_alerts": mixed_intent_alerts,
        "next_recommended_prd": next_prd,
    }


def _render_preflight_report(preflight: dict[str, Any], source_prd: str) -> str:
    lines = [
        f"# {source_prd} PREFLIGHT REPORT",
        "",
        "## Status",
        f"- passed: `{preflight.get('passed')}`",
        f"- ready_for_clean_reprocess: `{preflight.get('ready_for_clean_reprocess')}`",
        f"- active_source_count: `{preflight.get('active_source_count')}`",
        f"- active_source_id: `{preflight.get('active_source_id')}`",
        f"- raw_markdown_found: `{preflight.get('raw_markdown_found')}`",
        f"- legacy_sd_active: `{preflight.get('legacy_sd_active')}`",
        "",
        "## Blockers",
    ]
    blockers = preflight.get("blockers") or []
    lines.extend([f"- `{item}`" for item in blockers] or ["- none"])
    lines.append("")
    return "\n".join(lines)


def _render_candidate_stats_report(stats: dict[str, Any], source_prd: str) -> str:
    lines = [
        f"# {source_prd} CANDIDATE STATS REPORT",
        "",
        "## Core",
        f"- candidate_blocks_count: `{stats.get('candidate_blocks_count')}`",
        f"- old_processed_blocks_count: `{stats.get('old_processed_blocks_count')}`",
        f"- block_count_delta: `{stats.get('block_count_delta')}`",
        f"- source_id_consistency_rate: `{stats.get('source_id_consistency_rate')}`",
        "",
        "## Governance Completeness",
        f"- governance_present_rate: `{stats.get('governance_present_rate')}`",
        f"- chunking_quality_present_rate: `{stats.get('chunking_quality_present_rate')}`",
        f"- allowed_use_present_rate: `{stats.get('allowed_use_present_rate')}`",
        f"- safety_flags_present_rate: `{stats.get('safety_flags_present_rate')}`",
        "",
        "## Candidate Readiness",
        f"- candidate_ready_for_next_step: `{stats.get('candidate_ready_for_next_step')}`",
        f"- sd_labeling_active: `{stats.get('sd_labeling_active')}`",
        "",
    ]
    return "\n".join(lines)


def _render_diff_report(diff_report: dict[str, Any], source_prd: str) -> str:
    lines = [
        f"# {source_prd} CANDIDATE DIFF REPORT",
        "",
        "## Summary",
        f"- old_block_count: `{diff_report.get('old_block_count')}`",
        f"- candidate_block_count: `{diff_report.get('candidate_block_count')}`",
        f"- block_count_delta: `{diff_report.get('block_count_delta')}`",
        f"- source_id_before_set: `{diff_report.get('source_id_before_set')}`",
        f"- source_id_after_set: `{diff_report.get('source_id_after_set')}`",
        "",
        "## Top Risks",
    ]
    risks = diff_report.get("top_risks") or []
    lines.extend([f"- `{item}`" for item in risks] or ["- none"])
    lines.append("")
    return "\n".join(lines)


def _render_governance_gate_report(gate: dict[str, Any], source_prd: str) -> str:
    lines = [
        f"# {source_prd} GOVERNANCE GATE REPORT",
        "",
        "## Status",
        f"- status: `{gate.get('status')}`",
        f"- direct_practice_misclassified_count: `{gate.get('direct_practice_misclassified_count', gate.get('practice_like_misclassified_count'))}`",
        f"- unsafe_practice_suggestion_count: `{gate.get('unsafe_practice_suggestion_count', 0)}`",
        f"- contextual_false_positive_count: `{gate.get('contextual_false_positive_count', 0)}`",
        f"- mixed_intent_alerts_before: `{gate.get('mixed_intent_alerts_before', gate.get('mixed_intent_alerts'))}`",
        f"- mixed_intent_unresolved_count: `{gate.get('mixed_intent_unresolved_count', 0)}`",
        f"- mixed_intent_split_required_count: `{gate.get('mixed_intent_split_required_count', 0)}`",
        f"- mixed_intent_review_only_count: `{gate.get('mixed_intent_review_only_count', 0)}`",
        f"- mixed_intent_false_positive_count: `{gate.get('mixed_intent_false_positive_count', 0)}`",
        f"- candidate_ready_for_apply: `{gate.get('candidate_ready_for_apply', False)}`",
        f"- next_recommended_prd: `{gate.get('next_recommended_prd')}`",
        "",
        "## Blockers",
    ]
    blockers = gate.get("blockers") or []
    lines.extend([f"- `{item}`" for item in blockers] or ["- none"])
    lines.extend(["", "## Warnings"])
    warnings = gate.get("warnings") or []
    lines.extend([f"- `{item}`" for item in warnings] or ["- none"])
    lines.append("")
    return "\n".join(lines)


def _render_practice_like_report(report: dict[str, Any], source_prd: str) -> str:
    lines = [
        f"# {source_prd} PRACTICE-LIKE REPORT",
        "",
        "## Metrics",
        f"- practice_like_candidates_count: `{report.get('practice_like_candidates_count')}`",
        f"- practice_like_as_practice_count: `{report.get('practice_like_as_practice_count')}`",
        f"- practice_like_misclassified_count: `{report.get('practice_like_misclassified_count')}`",
        "",
        "## Misclassified Examples (Safe Preview)",
    ]
    rows = report.get("misclassified_examples") or []
    if not rows:
        lines.append("- none")
    else:
        for row in rows[:15]:
            lines.append(
                f"- `{row.get('block_id')}` type=`{row.get('chunk_type')}` markers=`{row.get('markers')}` preview=`{row.get('safe_preview')}`"
            )
    lines.append("")
    return "\n".join(lines)


def _render_practice_taxonomy_report(report: dict[str, Any], source_prd: str) -> str:
    lines = [
        f"# {source_prd} PRACTICE TAXONOMY REPORT",
        "",
        "## Metrics",
        f"- candidate_blocks_count: `{report.get('candidate_blocks_count')}`",
        f"- practice_marker_hits_count: `{report.get('practice_marker_hits_count')}`",
        f"- direct_practice_protocol_count: `{report.get('direct_practice_protocol_count')}`",
        f"- practice_context_or_theory_count: `{report.get('practice_context_or_theory_count')}`",
        f"- case_or_dialogue_about_practice_count: `{report.get('case_or_dialogue_about_practice_count')}`",
        f"- quote_or_source_fragment_with_practice_terms_count: `{report.get('quote_or_source_fragment_with_practice_terms_count')}`",
        f"- direct_practice_misclassified_count: `{report.get('direct_practice_misclassified_count')}`",
        f"- contextual_false_positive_count: `{report.get('contextual_false_positive_count')}`",
        f"- unsafe_practice_suggestion_count: `{report.get('unsafe_practice_suggestion_count')}`",
        "",
        "## Examples",
    ]
    examples = report.get("examples") or []
    if not examples:
        lines.append("- none")
    else:
        for row in examples[:15]:
            lines.append(
                f"- `{row.get('block_id')}` taxonomy=`{row.get('taxonomy')}` before=`{row.get('chunk_type_before')}` after=`{row.get('chunk_type_after')}`"
            )
    lines.append("")
    return "\n".join(lines)


def _render_mixed_intent_audit_report(report: dict[str, Any], source_prd: str) -> str:
    lines = [
        f"# {source_prd} MIXED INTENT AUDIT REPORT",
        "",
        "## Metrics",
        f"- candidate_blocks_count: `{report.get('candidate_blocks_count')}`",
        f"- mixed_intent_alerts_before: `{report.get('mixed_intent_alerts_before')}`",
        f"- mixed_intent_unresolved_count: `{report.get('mixed_intent_unresolved_count')}`",
        f"- mixed_intent_split_required_count: `{report.get('mixed_intent_split_required_count')}`",
        f"- mixed_intent_review_only_count: `{report.get('mixed_intent_review_only_count')}`",
        f"- mixed_intent_false_positive_count: `{report.get('mixed_intent_false_positive_count')}`",
        "",
        "## Cases",
    ]
    rows = report.get("mixed_intent_cases") or []
    if not rows:
        lines.append("- none")
    else:
        for row in rows[:20]:
            lines.append(
                f"- `{row.get('block_id')}` severity_before=`{row.get('mixed_intent_severity_before')}` resolution=`{row.get('recommended_resolution')}` primary_after=`{row.get('primary_role_after')}`"
            )
    lines.append("")
    return "\n".join(lines)


def _render_no_mutation_report(report: dict[str, Any], source_prd: str) -> str:
    lines = [
        f"# {source_prd} NO-MUTATION REPORT",
        "",
        "## Status",
        f"- passed: `{report.get('passed')}`",
        f"- all_blocks_merged_mutated: `{report.get('all_blocks_merged_mutated')}`",
        f"- registry_mutated: `{report.get('registry_mutated')}`",
        f"- review_queue_mutated: `{report.get('review_queue_mutated')}`",
        f"- readiness_hf2_mutated: `{report.get('readiness_hf2_mutated')}`",
        f"- chroma_count_before: `{report.get('chroma_count_before')}`",
        f"- chroma_count_after: `{report.get('chroma_count_after')}`",
        f"- chroma_mutated: `{report.get('chroma_mutated')}`",
        "",
    ]
    return "\n".join(lines)


def _render_next_prd_report(gate: dict[str, Any], source_prd: str) -> str:
    return "\n".join(
        [
            f"# {source_prd} NEXT PRD RECOMMENDATION",
            "",
            f"- governance_gate_status: `{gate.get('status')}`",
            f"- recommendation: `{gate.get('next_recommended_prd')}`",
            "",
        ]
    )


def _render_implementation_report(
    *,
    source_prd: str,
    candidate_stats: dict[str, Any],
    practice_taxonomy_report: dict[str, Any],
    mixed_intent_audit_report: dict[str, Any] | None,
    governance_gate: dict[str, Any],
    no_mutation_check: dict[str, Any],
) -> str:
    mixed = mixed_intent_audit_report or {}
    return "\n".join(
        [
            f"# {source_prd} IMPLEMENTATION REPORT",
            "",
            "## Status",
            "- Implementation: done",
            "- Branch: main",
            "- Runtime behavior changed: false",
            "- Writer changed: false",
            "- DiagnosticCard changed: false",
            "- Thread Manager changed: false",
            "- State Analyzer changed: false",
            "- Context Assembly changed: false",
            "- Knowledge blocks mutated: false",
            "- Registry mutated: false",
            "- Chroma reindex performed: false",
            "- Production apply performed: false",
            "- Reprocess mode: candidate warning calibration",
            "",
            "## Candidate",
            f"- candidate_blocks_count: `{candidate_stats.get('candidate_blocks_count')}`",
            f"- source_id_consistency_rate: `{candidate_stats.get('source_id_consistency_rate')}`",
            f"- governance_present_rate: `{candidate_stats.get('governance_present_rate')}`",
            f"- chunking_quality_present_rate: `{candidate_stats.get('chunking_quality_present_rate')}`",
            f"- allowed_use_present_rate: `{candidate_stats.get('allowed_use_present_rate')}`",
            f"- safety_flags_present_rate: `{candidate_stats.get('safety_flags_present_rate')}`",
            f"- sd_labeling_active: `{candidate_stats.get('sd_labeling_active')}`",
            "",
            "## Practice Calibration",
            f"- practice_marker_hits_count: `{practice_taxonomy_report.get('practice_marker_hits_count')}`",
            f"- direct_practice_protocol_count: `{practice_taxonomy_report.get('direct_practice_protocol_count')}`",
            f"- direct_practice_misclassified_count: `{practice_taxonomy_report.get('direct_practice_misclassified_count')}`",
            f"- contextual_false_positive_count: `{practice_taxonomy_report.get('contextual_false_positive_count')}`",
            f"- unsafe_practice_suggestion_count: `{practice_taxonomy_report.get('unsafe_practice_suggestion_count')}`",
            "",
            "## Mixed Intent",
            f"- mixed_intent_alerts_before: `{mixed.get('mixed_intent_alerts_before', governance_gate.get('mixed_intent_alerts_before', governance_gate.get('mixed_intent_alerts')) )}`",
            f"- mixed_intent_unresolved_count: `{governance_gate.get('mixed_intent_unresolved_count', mixed.get('mixed_intent_unresolved_count', 0))}`",
            f"- mixed_intent_split_required_count: `{governance_gate.get('mixed_intent_split_required_count', mixed.get('mixed_intent_split_required_count', 0))}`",
            f"- mixed_intent_review_only_count: `{governance_gate.get('mixed_intent_review_only_count', mixed.get('mixed_intent_review_only_count', 0))}`",
            f"- mixed_intent_false_positive_count: `{governance_gate.get('mixed_intent_false_positive_count', mixed.get('mixed_intent_false_positive_count', 0))}`",
            "",
            "## Governance Gate",
            f"- status: `{governance_gate.get('status')}`",
            f"- candidate_ready_for_apply: `{governance_gate.get('candidate_ready_for_apply', False)}`",
            f"- blockers: `{governance_gate.get('blockers')}`",
            f"- warnings: `{governance_gate.get('warnings')}`",
            f"- next_recommended_prd: `{governance_gate.get('next_recommended_prd')}`",
            "",
            "## No Mutation",
            f"- all_blocks_merged_mutated: `{no_mutation_check.get('all_blocks_merged_mutated')}`",
            f"- registry_mutated: `{no_mutation_check.get('registry_mutated')}`",
            f"- chroma_mutated: `{no_mutation_check.get('chroma_mutated')}`",
            f"- review_queue_mutated: `{no_mutation_check.get('review_queue_mutated')}`",
            "",
        ]
    )


def run_clean_source_reprocess_cli(
    *,
    source_prd: str,
    mode: str,
    readiness_json: Path,
    output_dir: Path,
    reports_dir: Path,
    config_path: Path,
    registry_path: Path,
    all_blocks_path: Path,
    review_queue_path: Path,
) -> dict[str, Any]:
    if mode != "candidate":
        raise RuntimeError("Only --mode candidate is allowed in PRD-046.0.8.")

    root = Path.cwd()
    botdb_dir = root / "Bot_data_base"

    readiness_payload = _load_json(readiness_json) if readiness_json.exists() else {}
    registry_records = _load_json(registry_path) if registry_path.exists() else []
    if not isinstance(registry_records, list):
        registry_records = []
    all_blocks = _load_all_blocks(all_blocks_path)

    hash_before = _snapshot_hashes(
        all_blocks_path=all_blocks_path,
        registry_path=registry_path,
        review_queue_path=review_queue_path,
        readiness_path=readiness_json,
    )

    preflight = build_clean_reprocess_preflight(
        source_prd=source_prd,
        readiness_payload=readiness_payload if isinstance(readiness_payload, dict) else {},
        registry_records=registry_records,
        all_blocks=all_blocks,
        botdb_dir=botdb_dir,
        hash_before=hash_before,
    )
    focus_row = _find_focus_row(registry_records, _normalize(preflight.get("active_source_id")))
    preflight["_registry_row"] = focus_row or {}

    output_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)
    _save_json(output_dir / "preflight.json", preflight)
    _save_markdown(reports_dir / f"{source_prd}_PREFLIGHT_REPORT.md", _render_preflight_report(preflight, source_prd))

    if not bool(preflight.get("passed")):
        failed_gate = {
            "schema_version": "candidate_governance_gate_v3",
            "source_prd": source_prd,
            "generated_at": _utc_now(),
            "status": "failed",
            "blockers": ["preflight_failed"],
            "warnings": [],
            "direct_practice_misclassified_count": 0,
            "unsafe_practice_suggestion_count": 0,
            "contextual_false_positive_count": 0,
            "mixed_intent_alerts_before": 0,
            "mixed_intent_unresolved_count": 0,
            "mixed_intent_split_required_count": 0,
            "mixed_intent_review_only_count": 0,
            "mixed_intent_false_positive_count": 0,
            "candidate_ready_for_apply": False,
            "practice_like_misclassified_count": 0,
            "mixed_intent_alerts": 0,
            "next_recommended_prd": "PRD-046.0.8-HF2-BLOCKER — Candidate Governance Blocker Fix v1",
        }
        _save_json(output_dir / "governance_gate.json", failed_gate)
        _save_markdown(
            reports_dir / f"{source_prd}_GOVERNANCE_GATE_REPORT.md",
            _render_governance_gate_report(failed_gate, source_prd),
        )
        raise RuntimeError(f"Preflight failed: {preflight.get('blockers')}")

    config = _read_config(config_path)
    candidate_payload = run_clean_reprocess_candidate(
        source_prd=source_prd,
        preflight=preflight,
        config=config,
    )
    _save_json(output_dir / "clean_reprocess_candidate.json", candidate_payload)

    source_id = _normalize(preflight.get("active_source_id"))
    old_blocks = [block for block in all_blocks if _source_id_from_block(block) == source_id]
    candidate_blocks = _extract_blocks(candidate_payload.get("candidate") or {})
    practice_taxonomy_report = build_practice_taxonomy_report(
        source_prd=source_prd,
        candidate_blocks=candidate_blocks,
    )
    _save_json(output_dir / "practice_taxonomy_report.json", practice_taxonomy_report)
    _save_markdown(
        reports_dir / f"{source_prd}_PRACTICE_TAXONOMY_REPORT.md",
        _render_practice_taxonomy_report(practice_taxonomy_report, source_prd),
    )
    _save_json(output_dir / "clean_reprocess_candidate.json", candidate_payload)

    candidate_stats = build_candidate_stats(
        source_prd=source_prd,
        source_id=source_id,
        old_blocks=old_blocks,
        candidate_blocks=candidate_blocks,
    )
    _save_json(output_dir / "candidate_stats.json", candidate_stats)
    _save_markdown(
        reports_dir / f"{source_prd}_CANDIDATE_STATS_REPORT.md",
        _render_candidate_stats_report(candidate_stats, source_prd),
    )

    diff_report = build_candidate_diff_report(
        source_prd=source_prd,
        source_id=source_id,
        old_blocks=old_blocks,
        candidate_blocks=candidate_blocks,
        candidate_stats=candidate_stats,
    )
    _save_json(output_dir / "candidate_diff_report.json", diff_report)
    _save_markdown(
        reports_dir / f"{source_prd}_CANDIDATE_DIFF_REPORT.md",
        _render_diff_report(diff_report, source_prd),
    )

    practice_like_report = build_practice_like_report(
        source_prd=source_prd,
        candidate_blocks=candidate_blocks,
    )
    _save_json(output_dir / "practice_like_report.json", practice_like_report)
    _save_markdown(
        reports_dir / f"{source_prd}_PRACTICE_LIKE_REPORT.md",
        _render_practice_like_report(practice_like_report, source_prd),
    )
    mixed_intent_audit_report = build_mixed_intent_audit_report(
        source_prd=source_prd,
        candidate_blocks=candidate_blocks,
    )
    _save_json(output_dir / "mixed_intent_audit.json", mixed_intent_audit_report)
    _save_markdown(
        reports_dir / f"{source_prd}_MIXED_INTENT_AUDIT_REPORT.md",
        _render_mixed_intent_audit_report(mixed_intent_audit_report, source_prd),
    )
    _save_json(output_dir / "clean_reprocess_candidate.json", candidate_payload)

    hash_after = _snapshot_hashes(
        all_blocks_path=all_blocks_path,
        registry_path=registry_path,
        review_queue_path=review_queue_path,
        readiness_path=readiness_json,
    )
    no_mutation_check = build_no_mutation_check(
        source_prd=source_prd,
        hash_before=hash_before,
        hash_after=hash_after,
        chroma_count_before=_to_int(preflight.get("chroma_count_before")),
        chroma_count_after=_to_int(readiness_payload.get("chroma_count")),
    )
    _save_json(output_dir / "no_mutation_check.json", no_mutation_check)
    _save_markdown(
        reports_dir / f"{source_prd}_NO_MUTATION_REPORT.md",
        _render_no_mutation_report(no_mutation_check, source_prd),
    )

    governance_gate = build_candidate_governance_gate(
        source_prd=source_prd,
        preflight=preflight,
        candidate_stats=candidate_stats,
        practice_like_report=practice_like_report,
        no_mutation_check=no_mutation_check,
        candidate_blocks=candidate_blocks,
        practice_taxonomy_report=practice_taxonomy_report,
        mixed_intent_audit_report=mixed_intent_audit_report,
    )
    _save_json(output_dir / "governance_gate.json", governance_gate)
    _save_markdown(
        reports_dir / f"{source_prd}_GOVERNANCE_GATE_REPORT.md",
        _render_governance_gate_report(governance_gate, source_prd),
    )
    _save_markdown(
        reports_dir / f"{source_prd}_NEXT_PRD_RECOMMENDATION.md",
        _render_next_prd_report(governance_gate, source_prd),
    )
    _save_markdown(
        reports_dir / f"{source_prd}_IMPLEMENTATION_REPORT.md",
        _render_implementation_report(
            source_prd=source_prd,
            candidate_stats=candidate_stats,
            practice_taxonomy_report=practice_taxonomy_report,
            mixed_intent_audit_report=mixed_intent_audit_report,
            governance_gate=governance_gate,
            no_mutation_check=no_mutation_check,
        ),
    )

    (output_dir / "sanitized_runtime_logs.txt").write_text(
        "\n".join(
            [
                f"[{_utc_now()}] {source_prd} candidate clean reprocess run",
                "mode=candidate",
                f"source_id={source_id}",
                f"candidate_blocks_count={candidate_stats.get('candidate_blocks_count')}",
                f"direct_practice_misclassified_count={practice_taxonomy_report.get('direct_practice_misclassified_count')}",
                f"mixed_intent_alerts_before={mixed_intent_audit_report.get('mixed_intent_alerts_before')}",
                f"mixed_intent_unresolved_count={mixed_intent_audit_report.get('mixed_intent_unresolved_count')}",
                f"governance_gate_status={governance_gate.get('status')}",
                f"no_mutation_passed={no_mutation_check.get('passed')}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    return {
        "source_prd": source_prd,
        "mode": "candidate",
        "preflight_passed": bool(preflight.get("passed")),
        "candidate_blocks_count": _to_int(candidate_stats.get("candidate_blocks_count")),
        "governance_gate_status": _normalize(governance_gate.get("status")),
        "next_recommended_prd": _normalize(governance_gate.get("next_recommended_prd")),
        "no_mutation_passed": bool(no_mutation_check.get("passed")),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build clean source reprocess candidate artifacts without production mutation.")
    parser.add_argument("--source-prd", default=DEFAULT_SOURCE_PRD)
    parser.add_argument("--mode", default="candidate")
    parser.add_argument("--readiness-json", default=DEFAULT_READINESS_JSON)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--reports-dir", default=DEFAULT_REPORTS_DIR)
    parser.add_argument("--config-path", default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--registry-path", default=DEFAULT_REGISTRY_PATH)
    parser.add_argument("--all-blocks-path", default=DEFAULT_ALL_BLOCKS_PATH)
    parser.add_argument("--review-queue-path", default=DEFAULT_REVIEW_QUEUE_PATH)
    args = parser.parse_args()

    payload = run_clean_source_reprocess_cli(
        source_prd=_normalize(args.source_prd),
        mode=_normalize(args.mode),
        readiness_json=Path(args.readiness_json),
        output_dir=Path(args.output_dir),
        reports_dir=Path(args.reports_dir),
        config_path=Path(args.config_path),
        registry_path=Path(args.registry_path),
        all_blocks_path=Path(args.all_blocks_path),
        review_queue_path=Path(args.review_queue_path),
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

