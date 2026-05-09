from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from openai import OpenAI

CURRENT_DIR = Path(__file__).resolve().parent
BOTDB_DIR = CURRENT_DIR.parent
if str(BOTDB_DIR) not in sys.path:
    sys.path.insert(0, str(BOTDB_DIR))

from knowledge_governance.enrichment_contracts import (  # noqa: E402
    ENRICHMENT_SCHEMA_VERSION,
    EnrichmentCandidate,
    LLMMetadata,
)
from knowledge_governance.enrichment_validators import (  # noqa: E402
    LENS_FAMILY_ALLOWLIST,
    check_forbidden_keys,
    validate_candidate,
    validate_governance_invariants,
)
from tools.kb_quality_audit import load_processed_blocks  # noqa: E402

TARGET_TAG = "PRD-046.0.5"
TARGET_SOURCE_DEFAULT = "КУЗНИЦА ДУХА"
DEFAULT_BLOCKS_PATH = Path("Bot_data_base/data/processed/all_blocks_merged.json")
DEFAULT_OUTPUT_DIR = Path(f"TO_DO_LIST/logs/{TARGET_TAG}")
DEFAULT_REPORTS_DIR = Path("TO_DO_LIST/reports")
DEFAULT_PROMPT_PATH = Path("Bot_data_base/knowledge_governance/prompts/kb_enrichment_v1.md")
DEFAULT_OVERLAY_PATH = Path("Bot_data_base/data/processed/enrichment_overlays/kuznitsa_llm_enrichment_v1.jsonl")

BASE_QUOTAS = {
    "case": 6,
    "lens": 6,
    "practice": 6,
    "safety": 3,
    "style": 3,
    "theory": 3,
}
TYPE_ORDER = ("case", "lens", "practice", "safety", "style", "theory")

SAMPLE_QUERIES = (
    "я всё время стараюсь быть лучше и не могу остановиться",
    "я злюсь на себя, потому что опять не сделал обещанное",
    "я чувствую вину, когда выбираю себя",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_preview(text: str, limit: int = 160) -> str:
    cleaned = re.sub(r"\s+", " ", str(text or "").strip())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: max(0, limit - 3)].rstrip() + "..."


def _normalize_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    raw = str(value).strip()
    if not raw:
        return []
    return [part.strip() for part in raw.split(",") if part.strip()]


def _dedupe(values: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        item = str(value or "").strip()
        if not item or item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _extract_source_id(raw: dict[str, Any]) -> str:
    source = str(raw.get("source") or "")
    if ":" in source:
        return source.split(":", 1)[1]
    return source


def _block_governance(raw: dict[str, Any]) -> dict[str, Any]:
    metadata = raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {}
    governance = metadata.get("governance") if isinstance(metadata.get("governance"), dict) else {}
    return governance


def _block_quality(raw: dict[str, Any]) -> dict[str, Any]:
    metadata = raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {}
    quality = metadata.get("chunking_quality") if isinstance(metadata.get("chunking_quality"), dict) else {}
    return quality


def _block_chunk_type(raw: dict[str, Any]) -> str:
    governance = _block_governance(raw)
    chunk_type = str(governance.get("chunk_type") or "").strip().lower()
    return chunk_type or "theory"


def _block_source_title(raw: dict[str, Any]) -> str:
    metadata = raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {}
    return str(metadata.get("source_title") or "")


def _source_match(raw: dict[str, Any], source_hint: str) -> bool:
    hint = str(source_hint or "").strip().lower()
    if not hint:
        return True
    source = str(raw.get("source") or "").lower()
    source_id = _extract_source_id(raw).lower()
    source_title = _block_source_title(raw).lower()
    return hint in " ".join([source, source_id, source_title])


def _mixed_intent_severity(raw: dict[str, Any]) -> str:
    quality = _block_quality(raw)
    return str(quality.get("mixed_intent_severity") or "none").strip().lower() or "none"


def _stable_block_key(raw: dict[str, Any]) -> str:
    block_id = str(raw.get("id") or raw.get("chunk_id") or "")
    return block_id or f"chunk_{hash(str(raw))}"


def _select_stratified_blocks(blocks: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    if limit <= 0:
        return []
    sorted_blocks = sorted(blocks, key=_stable_block_key)
    by_type: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for raw in sorted_blocks:
        by_type[_block_chunk_type(raw)].append(raw)

    selected: list[dict[str, Any]] = []
    selected_ids: set[str] = set()

    mixed_priority = [
        raw
        for raw in sorted_blocks
        if _mixed_intent_severity(raw) in {"medium", "high"}
    ]
    for raw in mixed_priority[: min(3, limit)]:
        block_id = _stable_block_key(raw)
        if block_id in selected_ids:
            continue
        selected.append(raw)
        selected_ids.add(block_id)

    for chunk_type in TYPE_ORDER:
        need = BASE_QUOTAS.get(chunk_type, 0)
        for raw in by_type.get(chunk_type, []):
            if len(selected) >= limit or need <= 0:
                break
            block_id = _stable_block_key(raw)
            if block_id in selected_ids:
                continue
            selected.append(raw)
            selected_ids.add(block_id)
            need -= 1

    if len(selected) < limit:
        for raw in sorted_blocks:
            if len(selected) >= limit:
                break
            block_id = _stable_block_key(raw)
            if block_id in selected_ids:
                continue
            selected.append(raw)
            selected_ids.add(block_id)

    return selected[:limit]


def _parse_llm_json(raw: str) -> dict[str, Any]:
    text = str(raw or "").strip()
    if "```" in text:
        text = re.sub(r"```(?:json)?", "", text, flags=re.IGNORECASE).strip()
    payload = json.loads(text)
    if not isinstance(payload, dict):
        raise ValueError("LLM response must be JSON object")
    return payload


class _MockLLMClient:
    provider = "mock"
    model = "mock-kb-enrichment-v1"
    mock = True

    @staticmethod
    def _guess_lens(text: str, chunk_type: str) -> list[str]:
        low = text.lower()
        guessed: list[str] = []
        keyword_map = {
            "shame": ("стыд", "стыдно"),
            "guilt": ("вина", "виноват"),
            "self_criticism": ("критик", "недостат"),
            "procrastination": ("откладыв", "прокрастин"),
            "avoidance": ("избега", "уклон"),
            "body_awareness": ("тело", "дых"),
            "low_resource": ("нет сил", "пусто"),
            "anger": ("злю", "гнев", "раздраж"),
            "boundaries": ("границ", "нет"),
            "meaning": ("смысл", "пустота"),
        }
        for lens, markers in keyword_map.items():
            if any(marker in low for marker in markers):
                guessed.append(lens)
        if not guessed:
            by_type = {
                "practice": ["practice_integration", "body_awareness"],
                "safety": ["safety", "low_resource"],
                "lens": ["self_criticism", "meaning"],
                "case": ["relationships", "boundaries"],
                "style": ["values", "identity"],
                "theory": ["meaning", "values"],
            }
            guessed.extend(by_type.get(chunk_type, ["meaning"]))
        return [x for x in _dedupe(guessed) if x in LENS_FAMILY_ALLOWLIST][:4]

    def enrich(self, context: dict[str, Any]) -> dict[str, Any]:
        excerpt = str(context.get("content_excerpt") or "")
        chunk_type = str(context.get("chunk_type_original") or "theory")
        summary = _safe_preview(excerpt, limit=320)
        if len(summary) < 120:
            summary = (summary + " " + str(context.get("current_summary") or "")).strip()
            summary = _safe_preview(summary, limit=320)
        if len(summary) < 120:
            summary = (
                "Фрагмент описывает психологический паттерн и условия его проявления, "
                "задавая безопасную внутреннюю линзу для дальнейшего осмысления и выбора следующего шага."
            )

        lens = self._guess_lens(excerpt, chunk_type)
        tags = _dedupe(
            [
                chunk_type,
                *(lens[:3]),
                "governed_chunk",
                "offline_enrichment",
            ]
        )[:8]
        use_when = {
            "practice": ["когда нужен мягкий структурный шаг без перегруза"],
            "safety": ["когда нужно удержать контакт и не форсировать интерпретации"],
            "lens": ["когда полезно увидеть повторяющийся механизм реакции"],
            "case": ["когда нужно распознать знакомый паттерн в живой ситуации"],
            "style": ["когда нужна внутренняя опора на язык и тон рамки"],
            "theory": ["когда нужно объяснение механизма без директивности"],
        }.get(chunk_type, ["когда нужен аккуратный фокус на механизме переживания"])
        avoid_when = ["когда состояние остро нестабильно и нужен кризисный протокол"]
        if "practice_requires_low_resource_check" in _normalize_list(context.get("safety_flags_original")):
            avoid_when.append("когда мало ресурса или выраженная перегрузка")

        return {
            "summary_candidate": summary,
            "lens_family_candidates": lens,
            "tags": tags,
            "use_when": use_when[:4],
            "avoid_when": _dedupe(avoid_when)[:4],
            "self_contained_score": 0.74,
            "self_contained_reason": "Кандидат отражает ядро смысла и условия применения без цитирования.",
            "split_merge_suggestion": {"action": "keep", "reason": "Содержательная целостность сохранена."},
            "confidence": 0.72,
            "needs_human_review": False,
            "review_reasons": [],
        }


class _OpenAILLMClient:
    provider = "openai"
    mock = False

    def __init__(self, *, model: str, prompt_text: str, timeout_seconds: float, max_retries: int) -> None:
        self.model = model
        self.prompt_text = prompt_text
        self.timeout_seconds = timeout_seconds
        self.max_retries = max(1, int(max_retries))
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY not configured.")
        self.client = OpenAI(api_key=api_key, timeout=timeout_seconds)

    def enrich(self, context: dict[str, Any]) -> dict[str, Any]:
        payload_text = json.dumps(context, ensure_ascii=False)
        last_error: Exception | None = None
        for _ in range(self.max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    temperature=0.1,
                    max_tokens=1200,
                    messages=[
                        {"role": "system", "content": self.prompt_text},
                        {"role": "user", "content": payload_text},
                    ],
                )
                text = str((response.choices[0].message.content or "")).strip()
                return _parse_llm_json(text)
            except Exception as exc:  # pragma: no cover - network/runtime dependent
                last_error = exc
        raise RuntimeError(f"LLM enrichment failed after retries: {last_error}")


def _build_context(raw: dict[str, Any]) -> dict[str, Any]:
    metadata = raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {}
    governance = _block_governance(raw)
    text = str(raw.get("text") or "")
    return {
        "block_id": _stable_block_key(raw),
        "title": str(raw.get("title") or ""),
        "source_title": str(metadata.get("source_title") or ""),
        "chapter_title": str(metadata.get("chapter_title") or ""),
        "chunk_type_original": str(governance.get("chunk_type") or ""),
        "allowed_use_original": _normalize_list(governance.get("allowed_use")),
        "safety_flags_original": _normalize_list(governance.get("safety_flags")),
        "lens_family_current": _normalize_list(governance.get("lens_family")),
        "current_summary": str(raw.get("summary") or ""),
        "content_excerpt": _safe_preview(text, limit=1600),
        "mixed_intent_severity": _mixed_intent_severity(raw),
    }


def _evaluate_preflight() -> dict[str, Any]:
    impl_report = Path("TO_DO_LIST/reports/PRD-046.0.4.3_IMPLEMENTATION_REPORT.md")
    reindex_snapshot = Path("TO_DO_LIST/logs/PRD-046.0.4.3/chroma_reindex_snapshot.json")
    api_smoke = Path("TO_DO_LIST/logs/PRD-046.0.4.3/api_query_smoke_snapshot.json")
    bot_smoke = Path("TO_DO_LIST/logs/PRD-046.0.4.3/bot_retrieval_path_smoke.json")

    reasons: list[str] = []
    if not impl_report.exists():
        reasons.append("missing_prd_046043_implementation_report")
    if not reindex_snapshot.exists():
        reasons.append("missing_prd_046043_reindex_snapshot")
    if not api_smoke.exists():
        reasons.append("missing_prd_046043_api_smoke")
    if not bot_smoke.exists():
        reasons.append("missing_prd_046043_bot_smoke")

    impl_text = impl_report.read_text(encoding="utf-8") if impl_report.exists() else ""
    lowered_impl = impl_text.lower()
    if (
        "commit hash: `pending`" in lowered_impl
        or "push status: `pending`" in lowered_impl
        or "report sync: `pending`" in lowered_impl
    ):
        reasons.append("prd_046043_report_contains_pending_markers")

    snapshot_payload = {}
    if reindex_snapshot.exists():
        snapshot_payload = json.loads(reindex_snapshot.read_text(encoding="utf-8"))
        if str(snapshot_payload.get("governed_gate_status_after") or "") != "ready":
            reasons.append("governed_gate_not_ready_after_046043")
        if int(snapshot_payload.get("indexed_blocks_count") or 0) <= 0:
            reasons.append("reindex_indexed_blocks_missing")

    api_hits_positive = 0
    if api_smoke.exists():
        api_rows = json.loads(api_smoke.read_text(encoding="utf-8"))
        if isinstance(api_rows, list):
            api_hits_positive = sum(1 for row in api_rows if int(row.get("hits_count") or 0) > 0)
        if api_hits_positive <= 0:
            reasons.append("api_query_smoke_no_positive_hits")

    bot_payload = {}
    if bot_smoke.exists():
        bot_payload = json.loads(bot_smoke.read_text(encoding="utf-8"))
        if bool(bot_payload.get("fallback_used", True)):
            reasons.append("bot_smoke_fallback_used_true")
        if str(bot_payload.get("retrieval_source") or "") != "botdb_api":
            reasons.append("bot_smoke_not_using_botdb_api")

    return {
        "preflight_passed": len(reasons) == 0,
        "reasons": reasons,
        "observed": {
            "api_hits_positive": api_hits_positive,
            "reindex_indexed_blocks_count": snapshot_payload.get("indexed_blocks_count"),
            "collection_count_after": snapshot_payload.get("after_health", {}).get("collection_count")
            if isinstance(snapshot_payload.get("after_health"), dict)
            else None,
            "bot_fallback_used": bot_payload.get("fallback_used"),
            "bot_retrieval_source": bot_payload.get("retrieval_source"),
        },
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _select_report_recommendation(
    *,
    real_llm_run: bool,
    validation_failed: int,
    unknown_lens_count: int,
) -> str:
    if validation_failed > 0 or unknown_lens_count > 0:
        return "PRD-046.0.5-HF1 - Enrichment Prompt/Validator Calibration"
    if not real_llm_run:
        return "PRD-046.0.5-RUN1 - Real LLM Enrichment Batch Run"
    return "PRD-046.0.5.1 - Full Enrichment Apply + Chroma Refresh v1"


def run_enrichment(
    *,
    source_hint: str,
    blocks_path: Path,
    output_dir: Path,
    reports_dir: Path,
    prompt_path: Path,
    limit: int,
    offset: int,
    chunk_type_filter: str,
    dry_run: bool,
    write_overlay: bool,
    apply_changes: bool,
    confirm: bool,
    mock_llm: bool,
    max_concurrency: int,  # noqa: ARG001 - reserved for v2 async path
    max_retries: int,
    timeout_seconds: float,
) -> dict[str, Any]:
    load_dotenv()
    output_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)
    if write_overlay and not confirm:
        raise RuntimeError("Write-overlay mode requires --confirm.")
    if apply_changes and not confirm:
        raise RuntimeError("Apply mode requires --confirm.")

    preflight = _evaluate_preflight()
    run_config = {
        "generated_at": _utc_now(),
        "tag": TARGET_TAG,
        "source_hint": source_hint,
        "blocks_path": str(blocks_path),
        "output_dir": str(output_dir),
        "reports_dir": str(reports_dir),
        "limit": limit,
        "offset": offset,
        "chunk_type_filter": chunk_type_filter,
        "dry_run": dry_run,
        "write_overlay": write_overlay,
        "apply": apply_changes,
        "confirm": confirm,
        "mock_llm_requested": mock_llm,
        "production_blocks_mutated": False,
        "chroma_reindex_performed": False,
        "runtime_behavior_changed": False,
        "preflight": preflight,
    }
    _write_json(output_dir / "enrichment_run_config.json", run_config)

    if not preflight["preflight_passed"]:
        return {
            "status": "blocked",
            "reason": "preflight_failed",
            "preflight_reasons": preflight["reasons"],
            "run_config_path": str(output_dir / "enrichment_run_config.json"),
        }

    all_blocks = load_processed_blocks(blocks_path)
    source_blocks = [raw for raw in all_blocks if _source_match(raw, source_hint)]
    if chunk_type_filter:
        chunk_type_filter = chunk_type_filter.strip().lower()
        source_blocks = [raw for raw in source_blocks if _block_chunk_type(raw) == chunk_type_filter]
    if offset > 0:
        source_blocks = source_blocks[offset:]
    selected_blocks = _select_stratified_blocks(source_blocks, limit=limit)
    if not selected_blocks:
        raise RuntimeError("No chunks selected for enrichment.")

    prompt_text = prompt_path.read_text(encoding="utf-8") if prompt_path.exists() else ""
    model_name = os.getenv("KB_ENRICHMENT_MODEL") or "gpt-4o-mini"
    llm_mode_reason = ""
    if mock_llm:
        llm_client: Any = _MockLLMClient()
        real_llm_run = False
        mock_llm_run = True
        llm_mode_reason = "mock_requested"
    else:
        try:
            llm_client = _OpenAILLMClient(
                model=model_name,
                prompt_text=prompt_text,
                timeout_seconds=timeout_seconds,
                max_retries=max_retries,
            )
            real_llm_run = True
            mock_llm_run = False
            llm_mode_reason = "real_llm_available"
        except Exception:
            llm_client = _MockLLMClient()
            real_llm_run = False
            mock_llm_run = True
            llm_mode_reason = "real_llm_unavailable_fallback_to_mock"

    candidates: list[dict[str, Any]] = []
    validation_failed = 0
    needs_human_review_count = 0
    unknown_lens_count = 0
    invariant_violations = 0
    summary_warnings = 0
    validation_reasons_counter: Counter[str] = Counter()
    selected_type_distribution = Counter(_block_chunk_type(raw) for raw in selected_blocks)

    for raw in selected_blocks:
        context = _build_context(raw)
        block_id = context["block_id"]
        governance = _block_governance(raw)
        llm_metadata = LLMMetadata(
            provider=str(getattr(llm_client, "provider", "mock")),
            model=str(getattr(llm_client, "model", "mock-kb-enrichment-v1")),
            prompt_version="kb_enrichment_v1",
            generated_at=_utc_now(),
            mock=bool(getattr(llm_client, "mock", True)),
        )
        try:
            llm_payload = llm_client.enrich(context)
            llm_error = ""
        except Exception as exc:
            llm_payload = _MockLLMClient().enrich(context)
            llm_error = str(exc)
            llm_metadata.mock = True
            llm_metadata.provider = "mock_on_error"
            llm_metadata.model = "mock-kb-enrichment-v1"

        candidate = EnrichmentCandidate.from_llm_payload(
            llm_payload=llm_payload,
            block_id=block_id,
            source_title=context["source_title"],
            chunk_type_original=str(context["chunk_type_original"]),
            allowed_use_original=_normalize_list(governance.get("allowed_use")),
            safety_flags_original=_normalize_list(governance.get("safety_flags")),
            llm_metadata=llm_metadata,
        )
        result = validate_candidate(candidate=candidate, source_text=str(raw.get("text") or ""))
        if result.warnings:
            summary_warnings += 1
        invariant_reasons = validate_governance_invariants(candidate=candidate, source_block=raw)
        if invariant_reasons:
            invariant_violations += 1
        review_reasons = _dedupe(candidate.review_reasons + result.reasons + invariant_reasons)
        candidate.review_reasons = review_reasons
        candidate.needs_human_review = bool(candidate.needs_human_review or review_reasons)
        if candidate.needs_human_review:
            needs_human_review_count += 1
        if not result.passed or invariant_reasons:
            validation_failed += 1
        for reason in review_reasons:
            validation_reasons_counter[reason] += 1
        unknown_lens = [lens for lens in candidate.lens_family_candidates if lens not in LENS_FAMILY_ALLOWLIST]
        if unknown_lens:
            unknown_lens_count += 1

        payload = candidate.to_dict()
        payload["validation"] = {
            "passed": result.passed and len(invariant_reasons) == 0,
            "reasons": result.reasons,
            "warnings": result.warnings,
            "invariant_violations": invariant_reasons,
        }
        payload["source_preview"] = _safe_preview(str(raw.get("text") or ""), limit=160)
        payload["llm_error"] = _safe_preview(llm_error, limit=160)
        candidates.append(payload)

    forbidden_hits = check_forbidden_keys({"candidates": candidates})
    if forbidden_hits:
        raise RuntimeError(f"Forbidden raw keys detected in artifacts: {sorted(set(forbidden_hits))}")

    candidates_path = output_dir / "enrichment_candidates.jsonl"
    with candidates_path.open("w", encoding="utf-8") as handle:
        for row in candidates:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    if write_overlay and confirm:
        DEFAULT_OVERLAY_PATH.parent.mkdir(parents=True, exist_ok=True)
        with DEFAULT_OVERLAY_PATH.open("w", encoding="utf-8") as handle:
            for row in candidates:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        overlay_written = True
    else:
        overlay_written = False

    validation_report = {
        "generated_at": _utc_now(),
        "schema_version": ENRICHMENT_SCHEMA_VERSION,
        "chunks_selected": len(selected_blocks),
        "chunks_enriched": len(candidates),
        "validation_passed": len(candidates) - validation_failed,
        "validation_failed": validation_failed,
        "needs_human_review": needs_human_review_count,
        "unknown_lens_candidates": unknown_lens_count,
        "summary_quality_warnings": summary_warnings,
        "safety_governance_invariant_violations": invariant_violations,
        "validation_reasons_distribution": dict(sorted(validation_reasons_counter.items())),
        "raw_text_leak_check": "pass" if not forbidden_hits else "fail",
    }
    _write_json(output_dir / "enrichment_validation_report.json", validation_report)

    diff_summary = {
        "generated_at": _utc_now(),
        "chunks_total": len(candidates),
        "summary_changed_count": sum(
            1 for row in candidates if str(row.get("summary_candidate") or "").strip()
        ),
        "lens_candidates_distribution": dict(
            sorted(Counter(len(row.get("lens_family_candidates") or []) for row in candidates).items())
        ),
        "chunk_type_distribution_selected": dict(sorted(selected_type_distribution.items())),
        "mixed_intent_selected_medium_high": sum(
            1
            for raw in selected_blocks
            if _mixed_intent_severity(raw) in {"medium", "high"}
        ),
        "production_blocks_mutated": False,
        "chroma_reindex_performed": False,
    }
    _write_json(output_dir / "enrichment_diff_summary.json", diff_summary)

    (output_dir / "sanitized_runtime_logs.txt").write_text(
        "\n".join(
            [
                f"[{_utc_now()}] {TARGET_TAG} enrichment run",
                f"real_llm_run={real_llm_run}",
                f"mock_llm_run={mock_llm_run}",
                f"llm_mode_reason={llm_mode_reason}",
                f"chunks_selected={len(selected_blocks)}",
                f"validation_failed={validation_failed}",
                f"needs_human_review={needs_human_review_count}",
                "production_blocks_mutated=false",
                "chroma_reindex_performed=false",
                "runtime_behavior_changed=false",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    next_prd = _select_report_recommendation(
        real_llm_run=real_llm_run,
        validation_failed=validation_failed,
        unknown_lens_count=unknown_lens_count,
    )

    _write_reports(
        reports_dir=reports_dir,
        run_config=run_config,
        validation_report=validation_report,
        diff_summary=diff_summary,
        next_prd=next_prd,
        llm_mode_reason=llm_mode_reason,
        overlay_written=overlay_written,
        real_llm_run=real_llm_run,
        mock_llm_run=mock_llm_run,
    )

    return {
        "status": "done",
        "real_llm_run": real_llm_run,
        "mock_llm_run": mock_llm_run,
        "llm_mode_reason": llm_mode_reason,
        "chunks_selected": len(selected_blocks),
        "chunks_enriched": len(candidates),
        "validation_failed": validation_failed,
        "needs_human_review": needs_human_review_count,
        "next_prd": next_prd,
        "candidates_path": str(candidates_path),
    }


def _write_reports(
    *,
    reports_dir: Path,
    run_config: dict[str, Any],
    validation_report: dict[str, Any],
    diff_summary: dict[str, Any],
    next_prd: str,
    llm_mode_reason: str,
    overlay_written: bool,
    real_llm_run: bool,
    mock_llm_run: bool,
) -> None:
    reports_dir.mkdir(parents=True, exist_ok=True)

    impl_report = reports_dir / f"{TARGET_TAG}_IMPLEMENTATION_REPORT.md"
    llm_report = reports_dir / f"{TARGET_TAG}_LLM_ENRICHMENT_REPORT.md"
    audit_report = reports_dir / f"{TARGET_TAG}_ENRICHMENT_QUALITY_AUDIT.md"
    next_report = reports_dir / f"{TARGET_TAG}_NEXT_PRD_RECOMMENDATION.md"

    impl_report.write_text(
        "\n".join(
            [
                f"# {TARGET_TAG} IMPLEMENTATION REPORT",
                "",
                "## Status",
                "- Implementation: done",
                "- Branch: `main`",
                "- Runtime behavior changed: false",
                "- Writer changed: false",
                "- DiagnosticCard changed: false",
                "- Thread Manager changed: false",
                "- State Analyzer changed: false",
                "- Chroma production reindex performed: false",
                "- all_blocks_merged mutated: false",
                "",
                "## Preflight",
                f"- preflight_passed: `{run_config.get('preflight', {}).get('preflight_passed')}`",
                f"- preflight_reasons: `{run_config.get('preflight', {}).get('reasons')}`",
                "",
                "## Enrichment Run",
                f"- real_llm_run: `{real_llm_run}`",
                f"- mock_llm_run: `{mock_llm_run}`",
                f"- chunks_selected: `{validation_report.get('chunks_selected')}`",
                f"- chunks_enriched: `{validation_report.get('chunks_enriched')}`",
                f"- validation_passed: `{validation_report.get('validation_passed')}`",
                f"- validation_failed: `{validation_report.get('validation_failed')}`",
                f"- needs_human_review: `{validation_report.get('needs_human_review')}`",
                "",
                "## Safety Invariants",
                "- allowed_use mutated: false",
                "- safety_flags mutated: false",
                "- chunk_type mutated: false",
                f"- raw full text leak detected: `{validation_report.get('raw_text_leak_check') != 'pass'}`",
                "",
                "## Overlay",
                f"- overlay_written: `{overlay_written}`",
                "",
                "## Commit / Push",
                "- Commit hash: `pending`",
                "- Push status: `pending`",
                "- Report sync: `pending`",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    llm_report.write_text(
        "\n".join(
            [
                f"# {TARGET_TAG} LLM ENRICHMENT REPORT",
                "",
                "## Run Mode",
                f"- dry_run: `{run_config.get('dry_run')}`",
                f"- write_overlay: `{run_config.get('write_overlay')}`",
                f"- mock_llm_requested: `{run_config.get('mock_llm_requested')}`",
                f"- real_llm_run: `{real_llm_run}`",
                f"- mock_llm_run: `{mock_llm_run}`",
                f"- llm_mode_reason: `{llm_mode_reason}`",
                "",
                "## Summary",
                f"- chunks_selected: `{validation_report.get('chunks_selected')}`",
                f"- chunks_enriched: `{validation_report.get('chunks_enriched')}`",
                f"- validation_passed: `{validation_report.get('validation_passed')}`",
                f"- validation_failed: `{validation_report.get('validation_failed')}`",
                f"- needs_human_review: `{validation_report.get('needs_human_review')}`",
                f"- unknown_lens_candidates: `{validation_report.get('unknown_lens_candidates')}`",
                "",
                "## Runtime Invariants",
                "- runtime_behavior_changed: false",
                "- writer_changed: false",
                "- diagnosticcard_changed: false",
                "- thread_manager_changed: false",
                "- state_analyzer_changed: false",
                "- chroma_reindex_performed: false",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    audit_report.write_text(
        "\n".join(
            [
                f"# {TARGET_TAG} ENRICHMENT QUALITY AUDIT",
                "",
                "## Validation Metrics",
                f"- validation_passed: `{validation_report.get('validation_passed')}`",
                f"- validation_failed: `{validation_report.get('validation_failed')}`",
                f"- needs_human_review: `{validation_report.get('needs_human_review')}`",
                f"- summary_quality_warnings: `{validation_report.get('summary_quality_warnings')}`",
                f"- invariant_violations: `{validation_report.get('safety_governance_invariant_violations')}`",
                f"- raw_text_leak_check: `{validation_report.get('raw_text_leak_check')}`",
                "",
                "## Stratified Selection",
                f"- selected_distribution: `{diff_summary.get('chunk_type_distribution_selected')}`",
                f"- mixed_intent_medium_high_selected: `{diff_summary.get('mixed_intent_selected_medium_high')}`",
                "",
                "## Review Reasons",
                f"- distribution: `{validation_report.get('validation_reasons_distribution')}`",
                "",
                "## Safety Note",
                "- Artifacts contain only sanitized previews; raw full chunk text is not persisted.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    next_report.write_text(
        "\n".join(
            [
                f"# {TARGET_TAG} NEXT PRD RECOMMENDATION",
                "",
                f"- Recommended: `{next_prd}`",
                "",
                "## Inputs",
                f"- validation_failed: `{validation_report.get('validation_failed')}`",
                f"- unknown_lens_candidates: `{validation_report.get('unknown_lens_candidates')}`",
                f"- raw_text_leak_check: `{validation_report.get('raw_text_leak_check')}`",
                f"- llm_mode_reason: `{llm_mode_reason}`",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=f"{TARGET_TAG} offline LLM summary/lens enrichment CLI.")
    parser.add_argument("--source", default=TARGET_SOURCE_DEFAULT)
    parser.add_argument("--blocks-path", default=str(DEFAULT_BLOCKS_PATH))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--reports-dir", default=str(DEFAULT_REPORTS_DIR))
    parser.add_argument("--prompt-path", default=str(DEFAULT_PROMPT_PATH))
    parser.add_argument("--limit", type=int, default=30)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--chunk-type", default="")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--write-overlay", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm", action="store_true")
    parser.add_argument("--mock-llm", action="store_true")
    parser.add_argument("--resume", action="store_true")  # noqa: ARG001 - reserved for future
    parser.add_argument("--max-concurrency", type=int, default=1)
    parser.add_argument("--max-retries", type=int, default=2)
    parser.add_argument("--timeout-seconds", type=float, default=30.0)
    args = parser.parse_args()

    result = run_enrichment(
        source_hint=str(args.source),
        blocks_path=Path(args.blocks_path),
        output_dir=Path(args.output_dir),
        reports_dir=Path(args.reports_dir),
        prompt_path=Path(args.prompt_path),
        limit=max(1, int(args.limit)),
        offset=max(0, int(args.offset)),
        chunk_type_filter=str(args.chunk_type or ""),
        dry_run=bool(args.dry_run),
        write_overlay=bool(args.write_overlay),
        apply_changes=bool(args.apply),
        confirm=bool(args.confirm),
        mock_llm=bool(args.mock_llm),
        max_concurrency=max(1, int(args.max_concurrency)),
        max_retries=max(1, int(args.max_retries)),
        timeout_seconds=max(1.0, float(args.timeout_seconds)),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "done" else 2


if __name__ == "__main__":
    raise SystemExit(main())
