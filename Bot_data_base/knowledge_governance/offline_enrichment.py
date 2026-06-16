from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .mechanism_metadata import (
    CONTROLLED_CHUNK_TYPES,
    CONTROLLED_QUOTE_POLICY,
    MechanismAwareChunkMetadata,
    adapt_block_to_mechanism_metadata,
)


PRD_ID = "PRD-047.17"
ENRICHMENT_CANDIDATE_SCHEMA_VERSION = "mechanism_metadata_enrichment_candidate_v1"
LLM_PROMPT_VERSION = "kb_offline_enrichment_v1"
MAX_CONTENT_PREVIEW_CHARS = 300
MAX_PROVIDER_PREVIEW_CHARS = 1200
HIGH_VALUE_CHAPTERS = {1, 3, 5, 6, 7, 8, 10}
DEFAULT_MANUAL_REVIEW_REASON = "manual_review_required_by_prd"

PRACTICE_HEADING_HINTS = ("практик", "упражнен", "практикум")
DEEP_CHAPTER_HINTS = ("тень", "страх", "нейросталкинг", "инстинкт", "метабол")
STYLE_HEADING_HINTS = ("стиль", "голос", "тон")
LENS_TRANSLATIONS: dict[str, str] = {
    "control_as_safety": "Иногда контроль становится способом не чувствовать угрозу и вернуть себе ощущение опоры.",
    "shame_as_wrong_visibility": "Похоже, здесь есть страх быть увиденным как неправильный или недостаточный.",
    "panic_loss_of_control": "Это больше похоже на всплеск перегрузки и потери опоры, чем на реальную неспособность справиться.",
    "avoidance_as_protection": "Избегание здесь может быть не ленью, а способом защититься от перегрузки или боли.",
    "perfectionism_as_safety": "Перфекционизм может работать как попытка обезопасить себя от ошибки и оценки.",
    "self_criticism_as_control": "Самокритика здесь может быть способом держать себя под контролем и не столкнуться с более уязвимыми чувствами.",
    "parental_gaze": "Здесь может звучать внутренний оценивающий взгляд, который человек когда-то усвоил извне.",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def normalize_source_hint(value: Any) -> str:
    raw = normalize_text(value).lower()
    alias_map = {
        "kuznica": "кузница",
        "kuznitsa": "кузница",
        "kuznica duha": "кузница духа",
        "kuznitsa duha": "кузница духа",
    }
    return alias_map.get(raw, raw)


def safe_preview(text: Any, *, limit: int = MAX_CONTENT_PREVIEW_CHARS) -> str:
    cleaned = normalize_text(text)
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: max(0, limit - 3)].rstrip() + "..."


def dedupe(values: list[Any] | tuple[Any, ...] | None) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for raw in values or []:
        value = normalize_text(raw)
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any] | list[Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def relative_to_repo(path: Path, repo_root: Path) -> str:
    try:
        return str(path.resolve().relative_to(repo_root.resolve())).replace("\\", "/")
    except ValueError:
        return str(path.resolve()).replace("\\", "/")


def load_registry_entry(*, registry_path: Path, source_hint: str) -> dict[str, Any]:
    registry = read_json(registry_path)
    hint = normalize_source_hint(source_hint)
    if not isinstance(registry, list):
        raise ValueError("registry.json must contain a list")
    for entry in registry:
        joined = " ".join(
            [
                normalize_text(entry.get("source_id")),
                normalize_text(entry.get("title")),
                normalize_text(entry.get("author")),
                normalize_text((entry.get("file_paths") or {}).get("upload")),
                normalize_text((entry.get("file_paths") or {}).get("json")),
            ]
        ).lower()
        if hint in joined:
            return dict(entry)
    raise FileNotFoundError(f"Unable to resolve source from registry with hint={source_hint!r}")


def resolve_registry_paths(*, repo_root: Path, entry: dict[str, Any]) -> dict[str, Path]:
    file_paths = entry.get("file_paths") or {}
    processed_json = Path(str(file_paths.get("json") or "")).resolve()
    if not processed_json.is_absolute():
        processed_json = (repo_root / processed_json).resolve()

    upload_path_raw = Path(str(file_paths.get("upload") or ""))
    if upload_path_raw.is_absolute():
        upload_path = upload_path_raw.resolve()
    else:
        upload_path = (repo_root / "Bot_data_base" / str(upload_path_raw)).resolve()
        if not upload_path.exists():
            upload_path = (repo_root / str(upload_path_raw)).resolve()

    merged_path = (repo_root / "Bot_data_base" / "data" / "processed" / "all_blocks_merged.json").resolve()
    registry_path = (repo_root / "Bot_data_base" / "data" / "registry.json").resolve()
    return {
        "processed_json": processed_json,
        "upload_path": upload_path,
        "merged_path": merged_path,
        "registry_path": registry_path,
    }


def extract_headings(markdown_text: str) -> list[dict[str, Any]]:
    headings: list[dict[str, Any]] = []
    for line in markdown_text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("#"):
            continue
        level = len(stripped) - len(stripped.lstrip("#"))
        title = stripped[level:].strip()
        if title:
            headings.append({"level": level, "title": title})
    return headings


def parse_chapter_heading(value: str) -> dict[str, Any]:
    text = normalize_text(value)
    match = re.search(r"глава\s+(\d+)", text, flags=re.IGNORECASE)
    return {
        "number": int(match.group(1)) if match else None,
        "title": text,
    }


def block_chapter_info(block: dict[str, Any]) -> dict[str, Any]:
    metadata = block.get("metadata") if isinstance(block.get("metadata"), dict) else {}
    heading_path = metadata.get("heading_path") if isinstance(metadata.get("heading_path"), list) else []
    first_heading = normalize_text(heading_path[0] if heading_path else block.get("title"))
    return parse_chapter_heading(first_heading)


def available_metadata_fields(blocks: list[dict[str, Any]]) -> dict[str, list[str]]:
    metadata_keys: set[str] = set()
    governance_keys: set[str] = set()
    quality_keys: set[str] = set()
    for block in blocks:
        metadata = block.get("metadata") if isinstance(block.get("metadata"), dict) else {}
        governance = metadata.get("governance") if isinstance(metadata.get("governance"), dict) else {}
        quality = metadata.get("chunking_quality") if isinstance(metadata.get("chunking_quality"), dict) else {}
        metadata_keys.update(str(key) for key in metadata.keys())
        governance_keys.update(str(key) for key in governance.keys())
        quality_keys.update(str(key) for key in quality.keys())
    return {
        "metadata_keys": sorted(metadata_keys),
        "governance_keys": sorted(governance_keys),
        "chunking_quality_keys": sorted(quality_keys),
    }


def build_source_profile(
    *,
    repo_root: Path,
    entry: dict[str, Any],
    upload_path: Path,
    processed_path: Path,
    blocks: list[dict[str, Any]],
) -> dict[str, Any]:
    markdown_text = upload_path.read_text(encoding="utf-8")
    headings = extract_headings(markdown_text)
    chapter_headings = [item["title"] for item in headings if normalize_text(item["title"]).lower().startswith("глава ")]
    practice_headings = [
        item["title"]
        for item in headings
        if any(token in normalize_text(item["title"]).lower() for token in PRACTICE_HEADING_HINTS)
    ]
    chapter_numbers = [
        parse_chapter_heading(title)["number"]
        for title in chapter_headings
        if parse_chapter_heading(title)["number"] is not None
    ]
    missing_numbers: list[int] = []
    if chapter_numbers:
        for candidate in range(min(chapter_numbers), max(chapter_numbers) + 1):
            if candidate not in chapter_numbers:
                missing_numbers.append(candidate)
    levels = Counter(item["level"] for item in headings)
    anomalies: list[str] = []
    if missing_numbers:
        anomalies.append(f"missing_chapter_numbers:{missing_numbers}")
    if len(levels) > 3:
        anomalies.append(f"mixed_heading_levels:{dict(levels)}")
    if not practice_headings:
        anomalies.append("practice_headings_not_detected_in_markdown")

    chapter_counter: Counter[str] = Counter()
    for block in blocks:
        info = block_chapter_info(block)
        title = info["title"] or "unknown"
        chapter_counter[title] += 1

    return {
        "schema_version": "kuznica_source_profile_v1",
        "prd_id": PRD_ID,
        "source_id": normalize_text(entry.get("source_id")),
        "source_doc": normalize_text(entry.get("title")),
        "source_type": normalize_text(entry.get("source_type")),
        "upload_path": relative_to_repo(upload_path, repo_root),
        "processed_json_path": relative_to_repo(processed_path, repo_root),
        "file_size_bytes": upload_path.stat().st_size,
        "sha256": sha256_file(upload_path),
        "heading_count": len(headings),
        "chapter_headings": chapter_headings,
        "practice_headings": practice_headings,
        "processed_blocks_count": len(blocks),
        "chapter_block_counts": dict(sorted(chapter_counter.items())),
        "available_metadata_fields": available_metadata_fields(blocks),
        "detected_anomalies": anomalies,
    }


def build_source_profile_markdown(profile: dict[str, Any]) -> str:
    lines = [
        "# PRD-047.17 Kuznica Source Profile",
        "",
        f"- source_id: `{profile['source_id']}`",
        f"- source_doc: `{profile['source_doc']}`",
        f"- source_type: `{profile['source_type']}`",
        f"- upload_path: `{profile['upload_path']}`",
        f"- processed_json_path: `{profile['processed_json_path']}`",
        f"- file_size_bytes: `{profile['file_size_bytes']}`",
        f"- sha256: `{profile['sha256']}`",
        f"- heading_count: `{profile['heading_count']}`",
        f"- processed_blocks_count: `{profile['processed_blocks_count']}`",
        "",
        "## Chapters",
    ]
    for title in profile.get("chapter_headings", []):
        lines.append(f"- {title}")
    lines.extend(["", "## Practice Headings"])
    for title in profile.get("practice_headings", []):
        lines.append(f"- {title}")
    lines.extend(["", "## Detected Anomalies"])
    for item in profile.get("detected_anomalies", []) or ["none"]:
        lines.append(f"- {item}")
    return "\n".join(lines)


def build_chapter_coverage_report(blocks: list[dict[str, Any]]) -> dict[str, Any]:
    per_chapter: dict[str, dict[str, Any]] = {}
    for block in blocks:
        chapter = block_chapter_info(block)
        chapter_key = chapter["title"] or "unknown"
        data = per_chapter.setdefault(
            chapter_key,
            {
                "chapter_number": chapter["number"],
                "blocks": 0,
                "legacy_chunk_types": Counter(),
                "normalized_chunk_types": Counter(),
            },
        )
        data["blocks"] += 1
        metadata = block.get("metadata") if isinstance(block.get("metadata"), dict) else {}
        governance = metadata.get("governance") if isinstance(metadata.get("governance"), dict) else {}
        data["legacy_chunk_types"][normalize_text(governance.get("chunk_type")) or "unknown"] += 1
        normalized, _ = adapt_block_to_mechanism_metadata(block)
        data["normalized_chunk_types"][normalized.chunk_type] += 1

    normalized = {}
    high_value_coverage: dict[str, bool] = {}
    for chapter_key, data in sorted(per_chapter.items()):
        normalized[chapter_key] = {
            "chapter_number": data["chapter_number"],
            "blocks": data["blocks"],
            "legacy_chunk_types": dict(sorted(data["legacy_chunk_types"].items())),
            "normalized_chunk_types": dict(sorted(data["normalized_chunk_types"].items())),
        }
        number = data["chapter_number"]
        if number in HIGH_VALUE_CHAPTERS:
            high_value_coverage[str(number)] = data["blocks"] > 0

    return {
        "schema_version": "kuznica_chapter_coverage_report_v1",
        "prd_id": PRD_ID,
        "total_blocks": len(blocks),
        "high_value_chapter_coverage": high_value_coverage,
        "chapters": normalized,
    }


def build_chapter_coverage_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# PRD-047.17 Kuznica Chapter Coverage",
        "",
        f"- total_blocks: `{report['total_blocks']}`",
        f"- high_value_chapter_coverage: `{json.dumps(report['high_value_chapter_coverage'], ensure_ascii=False)}`",
        "",
        "## Chapters",
    ]
    for title, payload in report.get("chapters", {}).items():
        lines.append(f"- {title}: blocks={payload['blocks']}, normalized={payload['normalized_chunk_types']}")
    return "\n".join(lines)


def source_filter_match(*, block: dict[str, Any], source_hint: str, source_id: str, source_title: str) -> bool:
    metadata = block.get("metadata") if isinstance(block.get("metadata"), dict) else {}
    governance = metadata.get("governance") if isinstance(metadata.get("governance"), dict) else {}
    source_trace = governance.get("source_trace") if isinstance(governance.get("source_trace"), dict) else {}
    hint = normalize_source_hint(source_hint)
    block_source = normalize_text(block.get("source")).lower()
    block_title = normalize_text(metadata.get("source_title")).lower()
    block_source_id = normalize_text(source_trace.get("source_id")).lower()
    target_source_id = normalize_text(source_id).lower()
    target_source_title = normalize_text(source_title).lower()
    if target_source_id and target_source_id in {block_source_id, block_source.replace("book:", "")}:
        return True
    if target_source_title and target_source_title == block_title:
        return True
    joined = " ".join(
        [
            hint,
            block_source,
            block_title,
            block_source_id,
            normalize_text(source_trace.get("source_title")),
        ]
    ).lower()
    return hint in joined


def load_processed_blocks(*, processed_path: Path) -> list[dict[str, Any]]:
    payload = read_json(processed_path)
    blocks = payload.get("blocks", []) if isinstance(payload, dict) else payload
    if not isinstance(blocks, list):
        raise ValueError("Processed blocks payload must contain a list")
    return list(blocks)


@dataclass
class CandidateBuildResult:
    candidate: dict[str, Any]
    validation: dict[str, Any]
    selection_reasons: list[str]


def current_metadata_summary(metadata: MechanismAwareChunkMetadata) -> dict[str, Any]:
    payload = metadata.to_dict()
    return {
        "chunk_type": payload["chunk_type"],
        "core_thesis": safe_preview(payload["core_thesis"], limit=180),
        "mechanism_hints": list(payload["mechanism_hints"]),
        "use_when": list(payload["use_when"]),
        "avoid_when": list(payload["avoid_when"]),
        "contraindications": list(payload["contraindications"]),
        "allowed_use": list(payload["allowed_use"]),
        "quote_policy": payload["quote_policy"],
        "depth_level": payload["depth_level"],
        "quality_flags": list(payload["quality_flags"]),
    }


def build_source_ref(*, repo_root: Path, raw_block: dict[str, Any], source_doc: str, source_id: str) -> dict[str, Any]:
    metadata = raw_block.get("metadata") if isinstance(raw_block.get("metadata"), dict) else {}
    heading_path = metadata.get("heading_path") if isinstance(metadata.get("heading_path"), list) else []
    return {
        "source_id": source_id,
        "source_doc": source_doc,
        "block_id": normalize_text(raw_block.get("id") or raw_block.get("chunk_id")),
        "heading_path": dedupe(heading_path),
        "content_preview": safe_preview(raw_block.get("text") or raw_block.get("summary") or raw_block.get("title")),
        "source_path_hint": relative_to_repo(Path("Bot_data_base/data/processed/all_blocks_merged.json"), repo_root),
    }


def source_terms_used(metadata: MechanismAwareChunkMetadata, raw_block: dict[str, Any]) -> list[str]:
    title_terms = re.findall(r"[A-Za-zА-Яа-яЁё0-9_-]{4,}", normalize_text(raw_block.get("title")))
    terms = [
        *metadata.mechanism_hints,
        *metadata.emotional_markers,
        *metadata.body_markers,
        *metadata.underlying_need,
        *metadata.protective_parts,
        *title_terms[:4],
    ]
    return dedupe(terms)[:8]


def build_summary_candidate(metadata: MechanismAwareChunkMetadata, chapter_title: str) -> str:
    thesis = safe_preview(metadata.core_thesis, limit=220)
    if metadata.chunk_type == "practice":
        goal = normalize_text((metadata.practice or {}).get("goal"))
        if goal:
            return safe_preview(f"Практика из раздела «{chapter_title}» помогает {goal.lower()} и требует проверки времени, ресурса и готовности пользователя.", limit=220)
        return safe_preview(f"Практика из раздела «{chapter_title}» подходит как бережный следующий шаг только при явном запросе и достаточном ресурсе.", limit=220)
    if metadata.chunk_type == "diagnostic_lens":
        return safe_preview(f"Фрагмент из раздела «{chapter_title}» описывает повторяющийся внутренний паттерн, который полезно переводить в мягкую гипотезу, а не в диагноз. {thesis}", limit=220)
    if metadata.chunk_type == "mechanism":
        return safe_preview(f"Фрагмент из раздела «{chapter_title}» объясняет механизм, через который человек пытается сохранить безопасность или контроль. {thesis}", limit=220)
    if metadata.chunk_type == "safety":
        return safe_preview(f"Раздел «{chapter_title}» указывает, что стабилизация и безопасность должны идти раньше глубокого анализа. {thesis}", limit=220)
    if metadata.chunk_type == "source_fragment":
        return safe_preview(f"Исходный фрагмент из раздела «{chapter_title}» лучше использовать как опорный смысловой источник для derived candidate, а не как готовую реплику.", limit=220)
    return safe_preview(f"Раздел «{chapter_title}» даёт материал для компактного объяснения смысла в контексте пользователя. {thesis}", limit=220)


def build_use_when_candidates(metadata: MechanismAwareChunkMetadata, chapter_title: str) -> list[str]:
    chunk_type = metadata.chunk_type
    chapter_hint = normalize_text(chapter_title).lower()
    if chunk_type == "practice":
        items = [
            "Когда пользователь явно просит практику или следующий шаг.",
            "Когда у пользователя есть хотя бы минимальный ресурс на короткое действие.",
        ]
        if any(term in chapter_hint for term in ("страх", "паник", "нерв")):
            items.append("Когда нужен мягкий способ вернуть опору телу без глубокого анализа.")
        return dedupe(items)[:4]
    if chunk_type in {"mechanism", "diagnostic_lens"}:
        items = [
            "Когда пользователь просит понять, почему с ним это происходит.",
            "Когда повторяется один и тот же паттерн контроля, стыда, избегания или внутреннего давления.",
        ]
        if metadata.mechanism_hints:
            items.append(f"Когда полезно мягко подсветить механизм {metadata.mechanism_hints[0]} без категоричности.")
        return dedupe(items)[:4]
    if chunk_type == "safety":
        return [
            "Когда пользователь в перегрузке и сначала нужна опора, а не объяснение.",
            "Когда лучше сузить шаг до безопасной стабилизации.",
        ]
    if chunk_type == "source_fragment":
        return [
            "Когда нужен исходный смысл для derived concept или mechanism candidate.",
            "Когда важно сохранить provenance и не выдать фрагмент как прямую инструкцию.",
        ]
    return [
        "Когда пользователь просит объяснение, обзор или язык для понимания своего состояния.",
        "Когда нужен компактный смысловой ориентир без прямого цитирования источника.",
    ]


def build_avoid_when_candidates(metadata: MechanismAwareChunkMetadata, chapter_title: str) -> list[str]:
    chunk_type = metadata.chunk_type
    items = ["Не использовать как deterministic runtime routing или как готовую реплику Writer'у."]
    if chunk_type == "practice":
        items.extend(
            [
                "Не предлагать без явного запроса, если пользователь в острой дестабилизации или без ресурса.",
                "Не давать несколько практик подряд вместо ответа на вопрос.",
            ]
        )
    elif chunk_type in {"diagnostic_lens", "mechanism"}:
        items.extend(
            [
                "Не подавать как факт о личности пользователя или как скрытый диагноз.",
                "Не использовать, если пользователь просит только короткую опору без анализа.",
            ]
        )
    elif chunk_type == "safety":
        items.append("Не заменять этим психообразованием первичную стабилизацию или refer-out.")
    elif chunk_type == "source_fragment":
        items.append("Не цитировать дословно и не выдавать фрагмент как готовый ответ.")
    elif chunk_type == "style_voice":
        items.append("Не превращать stylistic guidance в factual user-facing content.")
    if any(term in normalize_text(chapter_title).lower() for term in DEEP_CHAPTER_HINTS):
        items.append("Не открывать глубинную интерпретацию раньше, чем появилась опора и согласие пользователя.")
    return dedupe(items)[:4]


def build_contraindications_candidates(metadata: MechanismAwareChunkMetadata, chapter_title: str) -> list[str]:
    if metadata.chunk_type != "practice":
        return []
    items = list((metadata.practice or {}).get("contraindications") or [])
    if not items:
        items.extend(
            [
                "Острая дестабилизация, когда пользователю трудно удерживать внимание даже на коротком действии.",
                "Состояние сильного истощения, где дополнительная практика может переживаться как давление.",
            ]
        )
    if any(term in normalize_text(chapter_title).lower() for term in ("паник", "страх")):
        items.append("Если усиливается страх или телесная перегрузка, лучше сначала сузить шаг до grounding/refer-out.")
    return dedupe(items)[:4]


def infer_safe_user_translation(metadata: MechanismAwareChunkMetadata) -> str:
    for hint in metadata.mechanism_hints:
        if hint in LENS_TRANSLATIONS:
            return LENS_TRANSLATIONS[hint]
    if metadata.chunk_type == "diagnostic_lens":
        return "Это лучше переводить как мягкую гипотезу о способе защиты, а не как утверждение о том, кто человек."
    return ""


def infer_risk_if_exposed(metadata: MechanismAwareChunkMetadata) -> str:
    if metadata.chunk_type == "diagnostic_lens":
        return "В сыром виде может прозвучать как диагноз, обвинение или навешивание роли."
    if metadata.chunk_type == "mechanism":
        return "Слишком прямое объяснение механизма может переживаться как разоблачение вместо поддержки."
    if metadata.chunk_type == "practice":
        return "Без проверки времени и ресурса практика может ощущаться как давление или ещё одна задача."
    if metadata.chunk_type == "source_fragment":
        return "Дословное вынесение фрагмента создаёт риск цитатного шума и ложной авторитетности."
    return ""


def infer_allowed_writer_use(metadata: MechanismAwareChunkMetadata) -> str:
    if metadata.chunk_type in {"diagnostic_lens", "mechanism"}:
        return "Только мягкая парафраза как объяснительная гипотеза, связанная с контекстом пользователя."
    if metadata.chunk_type == "practice":
        return "Только как один ограниченный next step после ответа и при явном timing fit."
    if metadata.chunk_type == "source_fragment":
        return "Только как provenance seed для derived candidate, не как прямая реплика."
    if metadata.chunk_type == "safety":
        return "Короткая безопасная ориентация и стабилизация без перегруза философией."
    return "Компактная парафраза без прямого цитирования и без утверждений о пользователе как о факте."


def infer_chunk_type_review_suggestion(metadata: MechanismAwareChunkMetadata, raw_block: dict[str, Any]) -> str | None:
    if metadata.chunk_type != "source_fragment":
        return None
    lowered = normalize_text(raw_block.get("title")).lower()
    if metadata.mechanism_hints or any(term in lowered for term in ("механизм", "как работает", "почему")):
        return "mechanism"
    return "concept"


def infer_depth_suggestion(metadata: MechanismAwareChunkMetadata, chapter_number: int | None, chapter_title: str) -> int | None:
    depth = int(metadata.depth_level)
    lowered = normalize_text(chapter_title).lower()
    if chapter_number in HIGH_VALUE_CHAPTERS and metadata.chunk_type in {"mechanism", "diagnostic_lens", "practice"}:
        depth = max(depth, 2)
    if any(term in lowered for term in DEEP_CHAPTER_HINTS):
        depth = max(depth, 2)
    return min(depth, 3)


def infer_risk_level(metadata: MechanismAwareChunkMetadata, chapter_number: int | None) -> str:
    if metadata.chunk_type == "safety":
        return "high"
    if metadata.chunk_type == "practice" and (metadata.intensity == "high" or chapter_number in {7, 10}):
        return "high"
    if metadata.chunk_type in {"practice", "diagnostic_lens", "mechanism"}:
        return "medium"
    if chapter_number in {5, 7, 10}:
        return "medium"
    return "low"


def base_manual_review_reasons(metadata: MechanismAwareChunkMetadata, chapter_number: int | None) -> list[str]:
    reasons = [DEFAULT_MANUAL_REVIEW_REASON]
    reasons.extend(list(metadata.quality_flags))
    if metadata.chunk_type == "source_fragment":
        reasons.append("source_fragment_requires_derived_candidate_review")
    if metadata.chunk_type == "practice":
        reasons.append("practice_candidate_needs_timing_review")
    if metadata.chunk_type == "diagnostic_lens":
        reasons.append("diagnostic_lens_requires_safe_translation_review")
    if chapter_number in HIGH_VALUE_CHAPTERS:
        reasons.append("high_value_chapter_review")
    return dedupe(reasons)


def candidate_confidence(metadata: MechanismAwareChunkMetadata, chapter_number: int | None) -> float:
    confidence = 0.35
    if metadata.mechanism_hints:
        confidence += 0.1
    if metadata.core_thesis:
        confidence += 0.05
    if metadata.chunk_type == "practice" and list((metadata.practice or {}).get("steps_short") or []):
        confidence += 0.05
    if chapter_number in HIGH_VALUE_CHAPTERS:
        confidence += 0.05
    return round(min(confidence, 0.65), 3)


def build_deterministic_candidate(
    *,
    repo_root: Path,
    source_id: str,
    source_doc: str,
    raw_block: dict[str, Any],
    metadata: MechanismAwareChunkMetadata,
    selection_reasons: list[str],
) -> CandidateBuildResult:
    chapter_info = block_chapter_info(raw_block)
    chapter_title = chapter_info["title"] or metadata.title
    chapter_number = chapter_info["number"]
    current_summary = current_metadata_summary(metadata)
    source_ref = build_source_ref(
        repo_root=repo_root,
        raw_block=raw_block,
        source_doc=source_doc,
        source_id=source_id,
    )
    candidate = {
        "schema_version": ENRICHMENT_CANDIDATE_SCHEMA_VERSION,
        "source_ref": source_ref,
        "current_metadata_summary": current_summary,
        "candidate_fields": {
            "summary_candidate": build_summary_candidate(metadata, chapter_title),
            "core_thesis_candidate": safe_preview(metadata.core_thesis, limit=180),
            "mechanism_hints_candidates": list(metadata.mechanism_hints),
            "use_when_candidates": build_use_when_candidates(metadata, chapter_title),
            "avoid_when_candidates": build_avoid_when_candidates(metadata, chapter_title),
            "contraindications_candidates": build_contraindications_candidates(metadata, chapter_title),
            "safe_user_translation_candidate": infer_safe_user_translation(metadata),
            "risk_if_exposed_candidate": infer_risk_if_exposed(metadata),
            "allowed_writer_use_candidate": infer_allowed_writer_use(metadata),
            "recommended_moves_candidates": list(metadata.recommended_moves),
            "forbidden_moves_candidates": list(metadata.forbidden_moves),
            "depth_level_suggestion": infer_depth_suggestion(metadata, chapter_number, chapter_title),
            "quote_policy_suggestion": metadata.quote_policy or None,
            "chunk_type_review_suggestion": infer_chunk_type_review_suggestion(metadata, raw_block),
        },
        "grounding": {
            "grounded_in_source_preview": bool(source_ref["content_preview"]),
            "source_terms_used": source_terms_used(metadata, raw_block),
            "unsupported_claims": [],
            "needs_source_context": len(source_ref["content_preview"]) < 90,
        },
        "governance_review": {
            "safe_to_apply_automatically": False,
            "manual_review_required": True,
            "manual_review_reasons": base_manual_review_reasons(metadata, chapter_number),
            "blocked_reasons": [],
            "risk_level": infer_risk_level(metadata, chapter_number),
        },
        "generation": {
            "mode": "deterministic",
            "model": "",
            "prompt_version": "",
            "provider_payload_committed": False,
            "created_at": utc_now(),
        },
        "confidence": candidate_confidence(metadata, chapter_number),
        "status": "candidate_only",
    }
    validation = validate_enrichment_candidate(candidate)
    if selection_reasons:
        candidate["governance_review"]["manual_review_reasons"] = dedupe(
            candidate["governance_review"]["manual_review_reasons"] + selection_reasons + validation["warnings"]
        )
    return CandidateBuildResult(candidate=candidate, validation=validation, selection_reasons=selection_reasons)


def validate_enrichment_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    blocked: list[str] = []

    if candidate.get("schema_version") != ENRICHMENT_CANDIDATE_SCHEMA_VERSION:
        errors.append("invalid_schema_version")
    if candidate.get("status") != "candidate_only":
        errors.append("status_must_be_candidate_only")

    source_ref = candidate.get("source_ref") if isinstance(candidate.get("source_ref"), dict) else {}
    preview = normalize_text(source_ref.get("content_preview"))
    if not preview:
        errors.append("content_preview_required")
    if len(preview) > MAX_CONTENT_PREVIEW_CHARS:
        errors.append("content_preview_too_long")

    governance_review = candidate.get("governance_review") if isinstance(candidate.get("governance_review"), dict) else {}
    if governance_review.get("safe_to_apply_automatically") is not False:
        errors.append("safe_to_apply_automatically_must_be_false")
    if governance_review.get("manual_review_required") is not True:
        errors.append("manual_review_required_must_be_true")

    generation = candidate.get("generation") if isinstance(candidate.get("generation"), dict) else {}
    mode = normalize_text(generation.get("mode")).lower()
    if mode == "llm_candidate" and governance_review.get("manual_review_required") is not True:
        errors.append("llm_candidate_requires_manual_review")
    if generation.get("provider_payload_committed") is not False:
        errors.append("provider_payload_committed_must_be_false")

    fields = candidate.get("candidate_fields") if isinstance(candidate.get("candidate_fields"), dict) else {}
    depth_suggestion = fields.get("depth_level_suggestion")
    if depth_suggestion is not None and int(depth_suggestion) not in {0, 1, 2, 3}:
        errors.append("invalid_depth_level_suggestion")
    quote_policy = fields.get("quote_policy_suggestion")
    if quote_policy is not None and quote_policy not in CONTROLLED_QUOTE_POLICY:
        errors.append("invalid_quote_policy_suggestion")
    chunk_type_review = fields.get("chunk_type_review_suggestion")
    if chunk_type_review is not None and chunk_type_review not in CONTROLLED_CHUNK_TYPES:
        warnings.append("chunk_type_review_suggestion_outside_controlled_vocab")

    chunk_type = normalize_text((candidate.get("current_metadata_summary") or {}).get("chunk_type"))
    if chunk_type == "practice" and not list(fields.get("contraindications_candidates") or []):
        warnings.append("practice_candidate_missing_contraindications")
    if chunk_type == "practice" and not list((candidate.get("current_metadata_summary") or {}).get("contraindications") or []):
        warnings.append("practice_current_metadata_missing_contraindications")
    if chunk_type == "diagnostic_lens" and not normalize_text(fields.get("safe_user_translation_candidate")):
        warnings.append("diagnostic_lens_missing_safe_user_translation")
    if chunk_type == "safety" and not list(fields.get("forbidden_moves_candidates") or []):
        warnings.append("safety_candidate_missing_forbidden_moves")
    if chunk_type == "style_voice" and "пользователь" in normalize_text(fields.get("summary_candidate")).lower():
        warnings.append("style_voice_summary_may_sound_user_facing")

    grounding = candidate.get("grounding") if isinstance(candidate.get("grounding"), dict) else {}
    if list(grounding.get("unsupported_claims") or []):
        blocked.append("unsupported_claims_present")
    if grounding.get("grounded_in_source_preview") is not True:
        blocked.append("not_grounded_in_source_preview")
    if mode not in {"deterministic", "llm_candidate", "hybrid"}:
        errors.append("invalid_generation_mode")

    forbidden_hits = recursive_forbidden_keys(candidate)
    if forbidden_hits:
        errors.append("forbidden_keys_present")

    return {
        "passed": not errors,
        "errors": dedupe(errors),
        "warnings": dedupe(warnings),
        "blocked": dedupe(blocked),
    }


def recursive_forbidden_keys(obj: Any) -> list[str]:
    forbidden = {
        "content_full",
        "raw_full_text",
        "provider_payload",
        "raw_provider_payload",
        "raw_llm_response",
        "raw_llm_prompt",
        "api_key",
    }
    hits: list[str] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            token = normalize_text(key).lower()
            if token in forbidden:
                hits.append(token)
            hits.extend(recursive_forbidden_keys(value))
    elif isinstance(obj, list):
        for item in obj:
            hits.extend(recursive_forbidden_keys(item))
    return dedupe(hits)


def selection_reason_bundle(metadata: MechanismAwareChunkMetadata, chapter_number: int | None) -> list[str]:
    reasons: list[str] = []
    flags = set(metadata.quality_flags)
    if "missing_mechanism_hints" in flags:
        reasons.append("missing_mechanism_hints")
    if "practice_missing_steps_short" in flags:
        reasons.append("practice_missing_steps_short")
    if "practice_missing_avoid_when" in flags:
        reasons.append("practice_missing_avoid_when")
    if metadata.chunk_type == "practice" and not metadata.contraindications:
        reasons.append("practice_missing_contraindications")
    if metadata.chunk_type == "diagnostic_lens":
        reasons.append("diagnostic_lens_enrichment_priority")
    if metadata.chunk_type == "source_fragment":
        reasons.append("source_fragment_candidate_review")
    if chapter_number in HIGH_VALUE_CHAPTERS:
        reasons.append("high_value_chapter_priority")
    return dedupe(reasons)


def prioritized_selection(blocks: list[dict[str, Any]], *, limit: int) -> list[dict[str, Any]]:
    if limit <= 0:
        return []
    scored: list[tuple[int, str, str, dict[str, Any]]] = []
    for block in blocks:
        metadata, _ = adapt_block_to_mechanism_metadata(block)
        chapter_number = block_chapter_info(block)["number"]
        reasons = selection_reason_bundle(metadata, chapter_number)
        score = 0
        score += 5 if "missing_mechanism_hints" in reasons else 0
        score += 4 if metadata.chunk_type == "practice" else 0
        score += 3 if metadata.chunk_type == "diagnostic_lens" else 0
        score += 2 if metadata.chunk_type == "source_fragment" else 0
        score += 2 if chapter_number in HIGH_VALUE_CHAPTERS else 0
        score += len(reasons)
        scored.append((score, metadata.chunk_type, normalize_text(block.get("id")), block))
    scored.sort(key=lambda item: (-item[0], item[2]))

    quotas = {
        "practice": max(6, limit // 4),
        "diagnostic_lens": max(6, limit // 5),
        "source_fragment": max(6, limit // 5),
        "mechanism": max(4, limit // 8),
        "concept": max(4, limit // 8),
        "case_example": max(2, limit // 20),
        "safety": max(2, limit // 20),
        "style_voice": max(1, limit // 40),
    }
    selected: list[dict[str, Any]] = []
    selected_ids: set[str] = set()
    for chunk_type, quota in quotas.items():
        taken = 0
        for score, current_chunk_type, block_id, block in scored:
            if len(selected) >= limit or taken >= quota or current_chunk_type != chunk_type or block_id in selected_ids:
                continue
            selected.append(block)
            selected_ids.add(block_id)
            taken += 1
    if len(selected) < limit:
        for _, _, block_id, block in scored:
            if len(selected) >= limit:
                break
            if block_id in selected_ids:
                continue
            selected.append(block)
            selected_ids.add(block_id)
    return selected[:limit]


def build_manual_review_pack(candidates: list[dict[str, Any]], validations: list[dict[str, Any]]) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    for candidate, validation in zip(candidates, validations):
        if candidate.get("governance_review", {}).get("manual_review_required") is not True:
            continue
        entries.append(
            {
                "source_ref": candidate.get("source_ref"),
                "chunk_type": candidate.get("current_metadata_summary", {}).get("chunk_type"),
                "risk_level": candidate.get("governance_review", {}).get("risk_level"),
                "manual_review_reasons": candidate.get("governance_review", {}).get("manual_review_reasons"),
                "validation_warnings": validation.get("warnings"),
                "validation_blocked": validation.get("blocked"),
                "candidate_summary": candidate.get("candidate_fields", {}).get("summary_candidate"),
                "safe_user_translation_candidate": candidate.get("candidate_fields", {}).get("safe_user_translation_candidate"),
                "allowed_writer_use_candidate": candidate.get("candidate_fields", {}).get("allowed_writer_use_candidate"),
            }
        )
    return {
        "schema_version": "manual_review_pack_v1",
        "prd_id": PRD_ID,
        "candidate_count": len(entries),
        "entries": entries,
    }


def build_manual_review_markdown(pack: dict[str, Any]) -> str:
    lines = [
        "# PRD-047.17 Manual Review Pack",
        "",
        f"- candidate_count: `{pack['candidate_count']}`",
        "",
    ]
    for entry in pack.get("entries", [])[:40]:
        source_ref = entry.get("source_ref") or {}
        lines.append(f"## {source_ref.get('block_id', 'unknown')}")
        lines.append(f"- chunk_type: `{entry.get('chunk_type')}`")
        lines.append(f"- risk_level: `{entry.get('risk_level')}`")
        lines.append(f"- manual_review_reasons: `{entry.get('manual_review_reasons')}`")
        lines.append(f"- validation_warnings: `{entry.get('validation_warnings')}`")
        lines.append(f"- preview: `{source_ref.get('content_preview')}`")
        lines.append(f"- summary_candidate: `{entry.get('candidate_summary')}`")
        lines.append("")
    return "\n".join(lines)


def build_candidates_sample_markdown(candidates: list[dict[str, Any]]) -> str:
    lines = [
        "# PRD-047.17 Enrichment Candidate Sample",
        "",
        f"- candidate_count: `{len(candidates)}`",
        "",
    ]
    for candidate in candidates[:20]:
        source_ref = candidate.get("source_ref") or {}
        fields = candidate.get("candidate_fields") or {}
        lines.append(f"## {source_ref.get('block_id', 'unknown')}")
        lines.append(f"- heading_path: `{source_ref.get('heading_path')}`")
        lines.append(f"- chunk_type: `{candidate.get('current_metadata_summary', {}).get('chunk_type')}`")
        lines.append(f"- preview: `{source_ref.get('content_preview')}`")
        lines.append(f"- summary_candidate: `{fields.get('summary_candidate')}`")
        lines.append(f"- mechanism_hints_candidates: `{fields.get('mechanism_hints_candidates')}`")
        lines.append(f"- use_when_candidates: `{fields.get('use_when_candidates')}`")
        lines.append(f"- avoid_when_candidates: `{fields.get('avoid_when_candidates')}`")
        lines.append("")
    return "\n".join(lines)


def build_quality_report(
    *,
    source_id: str,
    source_doc: str,
    total_source_blocks: int,
    selected_blocks: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    validations: list[dict[str, Any]],
) -> dict[str, Any]:
    by_chunk_type = Counter()
    by_risk = Counter()
    by_manual_reason = Counter()
    warning_counter = Counter()
    blocked_counter = Counter()
    chapter_numbers_selected: Counter[str] = Counter()
    for block, candidate, validation in zip(selected_blocks, candidates, validations):
        by_chunk_type[str(candidate.get("current_metadata_summary", {}).get("chunk_type") or "unknown")] += 1
        by_risk[str(candidate.get("governance_review", {}).get("risk_level") or "unknown")] += 1
        for item in candidate.get("governance_review", {}).get("manual_review_reasons", []):
            by_manual_reason[str(item)] += 1
        for item in validation.get("warnings", []):
            warning_counter[str(item)] += 1
        for item in validation.get("blocked", []):
            blocked_counter[str(item)] += 1
        chapter_info = block_chapter_info(block)
        if chapter_info["number"] is not None:
            chapter_numbers_selected[str(chapter_info["number"])] += 1

    return {
        "schema_version": "mechanism_metadata_enrichment_quality_report_v1",
        "prd_id": PRD_ID,
        "source_id": source_id,
        "source_doc": source_doc,
        "mode": "deterministic",
        "status": "passed" if all(validation["passed"] for validation in validations) else "warning",
        "total_source_blocks": total_source_blocks,
        "selected_blocks": len(selected_blocks),
        "candidate_count": len(candidates),
        "by_chunk_type": dict(sorted(by_chunk_type.items())),
        "by_risk_level": dict(sorted(by_risk.items())),
        "by_manual_review_reason": dict(sorted(by_manual_reason.items())),
        "validation_warning_counts": dict(sorted(warning_counter.items())),
        "validation_blocked_counts": dict(sorted(blocked_counter.items())),
        "selected_chapter_numbers": dict(sorted(chapter_numbers_selected.items())),
        "high_value_chapter_hits": {
            str(number): chapter_numbers_selected.get(str(number), 0) > 0
            for number in sorted(HIGH_VALUE_CHAPTERS)
        },
        "notes": [
            "Deterministic candidates are manual-review inputs only.",
            "Candidates are not applied to live metadata, Writer, runtime, DB, or Chroma.",
            "LLM candidate mode is deferred/skipped unless explicitly confirmed and safely configured.",
        ],
    }


def build_quality_report_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# PRD-047.17 Enrichment Quality Report",
        "",
        f"- status: `{report['status']}`",
        f"- source_id: `{report['source_id']}`",
        f"- source_doc: `{report['source_doc']}`",
        f"- total_source_blocks: `{report['total_source_blocks']}`",
        f"- selected_blocks: `{report['selected_blocks']}`",
        f"- candidate_count: `{report['candidate_count']}`",
        f"- by_chunk_type: `{json.dumps(report['by_chunk_type'], ensure_ascii=False)}`",
        f"- by_risk_level: `{json.dumps(report['by_risk_level'], ensure_ascii=False)}`",
        f"- validation_warning_counts: `{json.dumps(report['validation_warning_counts'], ensure_ascii=False)}`",
        f"- validation_blocked_counts: `{json.dumps(report['validation_blocked_counts'], ensure_ascii=False)}`",
        "",
        "## Notes",
    ]
    for note in report.get("notes", []):
        lines.append(f"- {note}")
    return "\n".join(lines)


def build_enrichment_schema_snapshot() -> dict[str, Any]:
    return {
        "schema_version": ENRICHMENT_CANDIDATE_SCHEMA_VERSION,
        "required_fields": [
            "schema_version",
            "source_ref",
            "current_metadata_summary",
            "candidate_fields",
            "grounding",
            "governance_review",
            "generation",
            "confidence",
            "status",
        ],
        "source_ref_contract": {
            "required": ["source_id", "source_doc", "block_id", "heading_path", "content_preview"],
            "content_preview_max_chars": MAX_CONTENT_PREVIEW_CHARS,
        },
        "invariants": {
            "safe_to_apply_automatically": False,
            "manual_review_required_default": True,
            "content_full_forbidden": True,
            "provider_payload_committed": False,
        },
    }
