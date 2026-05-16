from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


RAW_LEAK_KEYS = {
    "content_full",
    "raw_text",
    "full_text",
    "chapter_text",
    "source_raw",
    "embedding",
    "vector",
}


@dataclass
class CandidateEvaluation:
    path: str
    file_sha256: str
    blocks_total: int
    queue_block_ids_present_count: int
    queue_block_ids_missing_count: int
    source_ids: list[str]
    governance_present_rate: float
    allowed_use_present_rate: float
    safety_flags_present_rate: float
    raw_full_text_leak_detected: bool
    candidate_is_authoritative: bool
    reasons: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "sha256": self.file_sha256,
            "blocks_total": self.blocks_total,
            "queue_block_ids_present_count": self.queue_block_ids_present_count,
            "queue_block_ids_missing_count": self.queue_block_ids_missing_count,
            "source_ids": self.source_ids,
            "governance_present_rate": self.governance_present_rate,
            "allowed_use_present_rate": self.allowed_use_present_rate,
            "safety_flags_present_rate": self.safety_flags_present_rate,
            "raw_full_text_leak_detected": self.raw_full_text_leak_detected,
            "candidate_is_authoritative": self.candidate_is_authoritative,
            "reasons": self.reasons,
        }


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _extract_blocks(container: Any) -> list[dict[str, Any]]:
    if isinstance(container, dict):
        if isinstance(container.get("blocks"), list):
            return [item for item in container.get("blocks") if isinstance(item, dict)]
        candidate = container.get("candidate")
        if isinstance(candidate, dict) and isinstance(candidate.get("blocks"), list):
            return [item for item in candidate.get("blocks") if isinstance(item, dict)]
    if isinstance(container, list):
        return [item for item in container if isinstance(item, dict)]
    return []


def _extract_queue_block_ids(queue_payload: dict[str, Any]) -> set[str]:
    items = queue_payload.get("items") if isinstance(queue_payload.get("items"), list) else []
    result: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        block_id = str(item.get("block_id") or "").strip()
        if block_id:
            result.add(block_id)
    return result


def _extract_block_ids(blocks: list[dict[str, Any]]) -> set[str]:
    ids: set[str] = set()
    for block in blocks:
        block_id = str(block.get("id") or block.get("chunk_id") or "").strip()
        if block_id:
            ids.add(block_id)
    return ids


def _extract_source_id(block: dict[str, Any]) -> str:
    metadata = block.get("metadata") if isinstance(block.get("metadata"), dict) else {}
    source_id = str(metadata.get("source_id") or "").strip()
    if source_id:
        return source_id
    governance = metadata.get("governance") if isinstance(metadata.get("governance"), dict) else {}
    source_trace = governance.get("source_trace") if isinstance(governance.get("source_trace"), dict) else {}
    trace_source = str(source_trace.get("source_id") or "").strip()
    if trace_source:
        return trace_source
    source = str(block.get("source") or "").strip()
    if ":" in source:
        return source.split(":", 1)[1]
    return source


def _contains_raw_leak_key(payload: Any) -> bool:
    if isinstance(payload, dict):
        for key, value in payload.items():
            if str(key).strip().lower() in RAW_LEAK_KEYS:
                return True
            if _contains_raw_leak_key(value):
                return True
    elif isinstance(payload, list):
        for item in payload:
            if _contains_raw_leak_key(item):
                return True
    return False


def _focus_source_like(value: str) -> bool:
    text = str(value or "").strip()
    if not text:
        return False
    if text.startswith("123__"):
        return True
    normalized = text.lower()
    if normalized.startswith("123__"):
        return True
    return False


def _registry_focus_blocks(registry_payload: Any, expected_source_id: str) -> int:
    rows = registry_payload if isinstance(registry_payload, list) else []
    exact = [row for row in rows if isinstance(row, dict) and str(row.get("source_id") or "") == expected_source_id]
    if exact:
        try:
            return int(exact[0].get("blocks_count") or 0)
        except Exception:
            return 0

    fuzzy = [
        row
        for row in rows
        if isinstance(row, dict) and _focus_source_like(str(row.get("source_id") or ""))
    ]
    if fuzzy:
        try:
            return int(fuzzy[0].get("blocks_count") or 0)
        except Exception:
            return 0
    return 0


def _read_optional_chroma_count(chroma_snapshot_path: Path) -> int | None:
    if not chroma_snapshot_path.exists():
        return None
    try:
        payload = read_json(chroma_snapshot_path)
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    for key in ("dashboard_chroma_count", "registry_chroma_count", "chroma_count", "chroma_count_after", "count"):
        value = payload.get(key)
        try:
            if value is not None:
                return int(value)
        except Exception:
            continue
    return None


def _evaluate_candidate(
    *,
    path: Path,
    expected_blocks_total: int,
    queue_block_ids: set[str],
) -> CandidateEvaluation | None:
    try:
        payload = read_json(path)
    except Exception:
        return None
    blocks = _extract_blocks(payload)
    if not blocks:
        return None

    block_ids = _extract_block_ids(blocks)
    present = len(queue_block_ids.intersection(block_ids))
    missing = len(queue_block_ids.difference(block_ids))

    source_ids = sorted({sid for sid in (_extract_source_id(block) for block in blocks) if sid})
    governance_present = 0
    allowed_use_present = 0
    safety_flags_present = 0

    for block in blocks:
        metadata = block.get("metadata") if isinstance(block.get("metadata"), dict) else {}
        governance = metadata.get("governance") if isinstance(metadata.get("governance"), dict) else {}
        if governance:
            governance_present += 1
        allowed_use = governance.get("allowed_use")
        if isinstance(allowed_use, list) and len(allowed_use) > 0:
            allowed_use_present += 1
        safety_flags = governance.get("safety_flags")
        if isinstance(safety_flags, list) and len(safety_flags) > 0:
            safety_flags_present += 1

    total = max(1, len(blocks))
    governance_rate = governance_present / total
    allowed_use_rate = allowed_use_present / total
    safety_flags_rate = safety_flags_present / total
    raw_leak = _contains_raw_leak_key(blocks)

    reasons: list[str] = []
    if len(blocks) != expected_blocks_total:
        reasons.append("blocks_total_mismatch")
    if missing > 0:
        reasons.append("queue_block_ids_missing")
    if governance_rate < 1.0:
        reasons.append("governance_missing")
    if allowed_use_rate < 1.0:
        reasons.append("allowed_use_missing")
    if safety_flags_rate < 1.0:
        reasons.append("safety_flags_missing")
    if raw_leak:
        reasons.append("raw_full_text_leak_detected")
    if not source_ids:
        reasons.append("source_ids_missing")
    elif not all(_focus_source_like(value) for value in source_ids):
        reasons.append("unexpected_source_ids")

    authoritative = len(reasons) == 0

    return CandidateEvaluation(
        path=path.as_posix(),
        file_sha256=sha256_file(path),
        blocks_total=len(blocks),
        queue_block_ids_present_count=present,
        queue_block_ids_missing_count=missing,
        source_ids=source_ids,
        governance_present_rate=round(governance_rate, 6),
        allowed_use_present_rate=round(allowed_use_rate, 6),
        safety_flags_present_rate=round(safety_flags_rate, 6),
        raw_full_text_leak_detected=raw_leak,
        candidate_is_authoritative=authoritative,
        reasons=reasons,
    )


def discover_candidate_paths(*, blocks_path: Path, scan_roots: list[Path]) -> list[Path]:
    patterns = ("*.json",)
    candidates: list[Path] = []
    seen: set[str] = set()

    def _add(path: Path) -> None:
        norm = path.resolve().as_posix()
        if norm in seen:
            return
        seen.add(norm)
        candidates.append(path)

    if blocks_path.exists():
        _add(blocks_path)

    for root in scan_roots:
        if not root.exists():
            continue
        if root.is_file() and root.suffix.lower() == ".json":
            _add(root)
            continue
        for pattern in patterns:
            for path in root.rglob(pattern):
                name = path.name.lower()
                if any(token in name for token in ("all_blocks", "candidate", "snapshot", "blocks", "apply")):
                    _add(path)

    return candidates


def build_alignment_audit(
    *,
    queue_payload: dict[str, Any],
    blocks_payload: Any,
    registry_payload: Any,
    queue_path: Path,
    blocks_path: Path,
    registry_path: Path,
    expected_blocks_total: int,
    expected_source_id: str,
    scan_roots: list[Path],
    chroma_snapshot_path: Path,
    source_prd: str,
) -> dict[str, Any]:
    queue_block_ids = _extract_queue_block_ids(queue_payload)
    queue_items_count = len(queue_block_ids)

    current_blocks = _extract_blocks(blocks_payload)
    current_block_ids = _extract_block_ids(current_blocks)

    queue_present = len(queue_block_ids.intersection(current_block_ids))
    queue_missing = len(queue_block_ids.difference(current_block_ids))
    blocks_total = len(current_blocks)

    registry_focus_blocks = _registry_focus_blocks(registry_payload, expected_source_id=expected_source_id)
    chroma_count = _read_optional_chroma_count(chroma_snapshot_path)

    candidate_paths = discover_candidate_paths(blocks_path=blocks_path, scan_roots=scan_roots)
    candidate_evaluations: list[CandidateEvaluation] = []
    for path in candidate_paths:
        evaluation = _evaluate_candidate(
            path=path,
            expected_blocks_total=expected_blocks_total,
            queue_block_ids=queue_block_ids,
        )
        if evaluation is not None:
            candidate_evaluations.append(evaluation)

    candidate_evaluations.sort(
        key=lambda item: (
            0 if item.candidate_is_authoritative else 1,
            item.queue_block_ids_missing_count,
            -item.blocks_total,
            item.path,
        )
    )

    authoritative_candidates = [item.to_dict() for item in candidate_evaluations if item.candidate_is_authoritative]

    status = "aligned"
    if blocks_total != expected_blocks_total or queue_missing > 0:
        status = "not_aligned"

    return {
        "schema_version": "blocks_snapshot_alignment_audit_v1",
        "source_prd": source_prd,
        "generated_at": utc_now_iso(),
        "review_queue_path": queue_path.as_posix(),
        "review_queue_source_prd": str(queue_payload.get("source_prd") or ""),
        "review_queue_hash": sha256_file(queue_path),
        "blocks_path": blocks_path.as_posix(),
        "blocks_hash": sha256_file(blocks_path),
        "registry_path": registry_path.as_posix(),
        "registry_hash": sha256_file(registry_path) if registry_path.exists() else "",
        "expected_blocks_total": expected_blocks_total,
        "expected_source_id": expected_source_id,
        "blocks_total": blocks_total,
        "queue_items_count": queue_items_count,
        "queue_block_ids_present_count": queue_present,
        "queue_block_ids_missing_count": queue_missing,
        "chroma_count": chroma_count,
        "registry_focus_blocks": registry_focus_blocks,
        "status": status,
        "authoritative_candidates_found": len(authoritative_candidates),
        "authoritative_candidates": authoritative_candidates,
        "candidate_snapshots": [item.to_dict() for item in candidate_evaluations],
    }


def choose_authoritative_candidate(audit_payload: dict[str, Any]) -> dict[str, Any] | None:
    candidates = audit_payload.get("candidate_snapshots") if isinstance(audit_payload.get("candidate_snapshots"), list) else []
    for candidate in candidates:
        if isinstance(candidate, dict) and bool(candidate.get("candidate_is_authoritative")):
            return candidate
    return None


def load_blocks_payload_from_candidate(path: Path) -> dict[str, Any]:
    payload = read_json(path)
    if isinstance(payload, dict) and isinstance(payload.get("blocks"), list):
        blocks = payload.get("blocks")
    elif isinstance(payload, dict) and isinstance((payload.get("candidate") or {}).get("blocks"), list):
        blocks = (payload.get("candidate") or {}).get("blocks")
    elif isinstance(payload, list):
        blocks = payload
    else:
        raise RuntimeError("candidate_payload_has_no_blocks")

    block_list = [item for item in blocks if isinstance(item, dict)]
    return {
        "schema_version": "bot_data_base_v1.0",
        "generated_at": utc_now_iso(),
        "blocks_count": len(block_list),
        "blocks": block_list,
    }


def update_registry_focus_blocks(*, registry_payload: Any, expected_source_id: str, blocks_count: int) -> tuple[Any, bool]:
    rows = registry_payload if isinstance(registry_payload, list) else []
    mutated = False

    for row in rows:
        if not isinstance(row, dict):
            continue
        source_id = str(row.get("source_id") or "")
        if source_id == expected_source_id or _focus_source_like(source_id):
            if int(row.get("blocks_count") or 0) != int(blocks_count):
                row["blocks_count"] = int(blocks_count)
                mutated = True
            if str(row.get("status") or "") != "done":
                row["status"] = "done"
                mutated = True
            break

    return rows, mutated


def render_alignment_report(audit_payload: dict[str, Any], source_prd: str) -> str:
    lines = [
        f"# {source_prd} BLOCKS ALIGNMENT AUDIT REPORT",
        "",
        "## Summary",
        f"- status: {audit_payload.get('status')}",
        f"- blocks_total: {audit_payload.get('blocks_total')}",
        f"- expected_blocks_total: {audit_payload.get('expected_blocks_total')}",
        f"- queue_items_count: {audit_payload.get('queue_items_count')}",
        f"- queue_block_ids_present_count: {audit_payload.get('queue_block_ids_present_count')}",
        f"- queue_block_ids_missing_count: {audit_payload.get('queue_block_ids_missing_count')}",
        f"- registry_focus_blocks: {audit_payload.get('registry_focus_blocks')}",
        f"- chroma_count: {audit_payload.get('chroma_count')}",
        f"- authoritative_candidates_found: {audit_payload.get('authoritative_candidates_found')}",
        "",
        "## Top Candidates",
    ]

    candidates = audit_payload.get("candidate_snapshots") if isinstance(audit_payload.get("candidate_snapshots"), list) else []
    if not candidates:
        lines.append("- none")
    else:
        for candidate in candidates[:5]:
            lines.append(
                "- "
                + f"{candidate.get('path')} | blocks={candidate.get('blocks_total')} "
                + f"present={candidate.get('queue_block_ids_present_count')} "
                + f"missing={candidate.get('queue_block_ids_missing_count')} "
                + f"authoritative={candidate.get('candidate_is_authoritative')}"
            )

    return "\n".join(lines).rstrip() + "\n"


def sanitize_runtime_log_lines(lines: list[str]) -> list[str]:
    result: list[str] = []
    for line in lines:
        text = re.sub(r"\s+", " ", str(line or "").strip())
        if text:
            result.append(text)
    return result
