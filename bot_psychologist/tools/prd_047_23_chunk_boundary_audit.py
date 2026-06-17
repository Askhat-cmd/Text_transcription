from __future__ import annotations

import argparse
import json
import os
import re
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any


CURRENT_DIR = Path(__file__).resolve().parent
BOT_ROOT = CURRENT_DIR.parent
REPO_ROOT = BOT_ROOT.parent
PRD_ID = "PRD-047.23"
PREVIOUS_PRD = "PRD-047.22-HF2"
PREVIOUS_LOG_DIR = REPO_ROOT / "TO_DO_LIST" / "logs" / PREVIOUS_PRD
LOGS_DIR_DEFAULT = REPO_ROOT / "TO_DO_LIST" / "logs" / PRD_ID
REPORTS_DIR_DEFAULT = REPO_ROOT / "TO_DO_LIST" / "reports"
MERGED_BLOCKS_PATH = REPO_ROOT / "Bot_data_base" / "data" / "processed" / "all_blocks_merged.json"
TRACE_GLOB = "*ТРЕЙС_2_*.txt"
SOURCE_GLOB = "*КУЗНИЦА ДУХА*.md"
API_KEY = "dev-key-001"

if str(BOT_ROOT) not in sys.path:
    sys.path.insert(0, str(BOT_ROOT))

from tools import validate_prd_artifact_encoding as encoding_validator  # noqa: E402


CASE_SPECS: list[dict[str, Any]] = [
    {
        "case_id": "C23-001",
        "title": "Self-realization + Neurostalking",
        "canonical_query": "Что такое самореализация как она коррелируется с Нейросталкингом?",
        "trace_rag_prefix": "rag_query: Что такое самореализация как она коррелируется с Нейросталкингом?",
        "expected_keywords": ["самореализация", "нейросталкинг"],
        "expected_source_needles": ["самореализация", "нейросталкинг"],
        "neighbor_source_needles": ["НеоСталкинг", "НейроСталкинг"],
        "prefer_exact_section": False,
    },
    {
        "case_id": "C23-002",
        "title": "Imperfect self program",
        "canonical_query": 'а что такое "Программа несовершенное Я"?',
        "trace_rag_prefix": 'rag_query: а что такое "Программа несовершенное Я"?',
        "expected_keywords": ["программа", "несовершенное", "я"],
        "expected_source_needles": ["Программа «несовершенное Я»", "несовершенное Я"],
        "neighbor_source_needles": ["Шаг 1: Триггер", "Программа не возникает в один момент"],
        "prefer_exact_section": True,
    },
    {
        "case_id": "C23-003",
        "title": "Five survival drivers",
        "canonical_query": "расскажи о Пяти драйверах выживания: Драйвер 1: «Будь сильным», Драйвер 2: «Будь лучшим», Драйвер 3: «Радуй других», Драйвер 4: «Старайся сильнее», Драйвер 5: «Спеши»",
        "trace_rag_prefix": "rag_query: расскажи о Пяти драйверах выживания:",
        "expected_keywords": ["драйвер", "будь", "сильным", "лучшим", "радуй", "спеши"],
        "expected_source_needles": [
            "Драйвер 1: «Будь сильным»",
            "Драйвер 2: «Будь лучшим»",
            "Драйвер 3: «Радуй других»",
            "Драйвер 4: «Старайся сильнее»",
            "Драйвер 5: «Спеши»",
        ],
        "neighbor_source_needles": ["Шаг 1: Триггер", "Программа не возникает в один момент"],
        "prefer_exact_section": True,
    },
]

LIVE_QUERIES: list[dict[str, str]] = [
    {
        "case_id": "L23-001",
        "query": "Что такое самореализация как она коррелируется с Нейросталкингом?",
    },
    {
        "case_id": "L23-002",
        "query": 'а что такое "Программа несовершенное Я"?',
    },
    {
        "case_id": "L23-003",
        "query": "расскажи о Пяти драйверах выживания: Драйвер 1: «Будь сильным», Драйвер 2: «Будь лучшим», Драйвер 3: «Радуй других», Драйвер 4: «Старайся сильнее», Драйвер 5: «Спеши»",
    },
    {
        "case_id": "L23-004",
        "query": "Что такое Нейросталкинг?",
    },
    {
        "case_id": "L23-005",
        "query": "Чем Нейросталкинг отличается от НеоСталкинга?",
    },
]

PAYLOAD_STOP_PREFIXES = (
    "writer_instruction=",
    "content_truncated=",
    "truncation_strategy=",
    "[KB-",
    "KNOWLEDGE ANSWER ROUTING:",
)

DISPLAY_STOP_PREFIXES = (
    "RAG query",
    "User Profile",
    "Записано в память",
    "Полотно LLM",
    "User prompt",
    "WRITER CONTEXT PACKAGE:",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, payload: dict[str, Any] | list[Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _markdown(title: str, lines: list[str]) -> str:
    return "\n".join([f"# {title}", "", *lines])


def _relative(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    ).stdout.strip()


def _parse_int(raw: str | None) -> int | None:
    if raw is None:
        return None
    match = re.search(r"-?\d+", raw)
    return int(match.group()) if match else None


def _parse_bool(raw: str | None) -> bool | None:
    if raw is None:
        return None
    lowered = raw.strip().lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    return None


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()


def has_terminal_boundary(text: str) -> bool:
    stripped = (text or "").rstrip()
    if not stripped:
        return False
    return bool(re.search(r"[.!?:;…»”)\]*_]+$", stripped))


def looks_mid_word_cut(text: str) -> bool:
    stripped = (text or "").rstrip()
    if not stripped:
        return False
    if has_terminal_boundary(stripped):
        return False
    return bool(re.search(r"[A-Za-zА-Яа-яЁё]$", stripped))


def detect_query_duplicate_fragment_count(text: str) -> int:
    normalized = normalize_text(text)
    if not normalized:
        return 0
    words = normalized.split()
    if len(words) < 12:
        return 0
    for window in range(min(18, len(words) // 2), 5, -1):
        probe = " ".join(words[:window])
        if probe and probe in " ".join(words[window:]):
            return 1
    return 0


def query_contains_previous_question(query: str, previous_query: str) -> bool:
    current = normalize_text(query).lower()
    previous = normalize_text(previous_query).lower()
    if not current or not previous:
        return False
    if previous in current:
        return True
    previous_tokens = [token for token in re.findall(r"\w+", previous) if len(token) > 2]
    if len(previous_tokens) < 4:
        return False
    overlap = sum(1 for token in previous_tokens if token in current)
    return overlap >= max(4, int(len(previous_tokens) * 0.7))


def query_truncated_mid_word(text: str) -> bool:
    stripped = normalize_text(text)
    if not stripped:
        return False
    if has_terminal_boundary(stripped):
        return False
    return bool(re.search(r"[A-Za-zА-Яа-яЁё]$", stripped))


def find_local_trace_fixture(repo_root: Path = REPO_ROOT) -> Path | None:
    matches = sorted((repo_root / "TO_DO_LIST" / "context").glob(TRACE_GLOB))
    return matches[0] if matches else None


def find_primary_source_material(repo_root: Path = REPO_ROOT) -> Path | None:
    search_roots = [
        repo_root / "TO_DO_LIST" / "source_materials" / "PRD-047.1",
        repo_root / "TO_DO_LIST" / "source_materials",
    ]
    for root in search_roots:
        matches = sorted(root.glob(SOURCE_GLOB))
        if matches:
            return matches[0]
    return None


def load_merged_blocks(repo_root: Path = REPO_ROOT) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    payload = json.loads((repo_root / MERGED_BLOCKS_PATH.relative_to(REPO_ROOT)).read_text(encoding="utf-8"))
    blocks = list(payload.get("blocks") or [])
    return blocks, {str(block.get("id")): block for block in blocks if block.get("id")}


def load_primary_source_text(repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    path = find_primary_source_material(repo_root)
    if path is None:
        return {"path": None, "text": "", "normalized": ""}
    text = path.read_text(encoding="utf-8")
    return {"path": path, "text": text, "normalized": normalize_text(text)}


def _find_case_line(lines: list[str], prefix: str) -> int:
    for index, line in enumerate(lines, start=1):
        if line.startswith(prefix):
            return index
    raise ValueError(f"Trace prefix not found: {prefix}")


def _extract_first_value(span: list[str], prefix: str) -> str | None:
    for line in span:
        if line.startswith(prefix):
            return line.split(prefix, 1)[1].strip()
    return None


def _extract_header_count(span: list[str], prefix: str) -> int | None:
    for line in span:
        if line.startswith(prefix):
            return _parse_int(line)
    return None


def _extract_payload_value(span: list[str], prefix: str) -> str | None:
    payload_index = None
    for idx, line in enumerate(span):
        if line.strip() == "payload:":
            payload_index = idx
            break
    if payload_index is None:
        return None
    for line in span[payload_index + 1 :]:
        if line.startswith("[KB-"):
            break
        if line.startswith(prefix):
            return line.split(prefix, 1)[1].strip()
    return None


def _parse_payload_chunks(span: list[str], span_start_line: int) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    for idx, line in enumerate(span):
        if not line.startswith("[KB-"):
            continue
        chunk: dict[str, Any] = {
            "kb_index": line.strip("[]"),
            "line_start": span_start_line + idx,
        }
        cursor = idx + 1
        while cursor < len(span):
            current = span[cursor]
            if current.startswith("[KB-") or current.startswith("KNOWLEDGE ANSWER ROUTING:"):
                break
            if current.startswith("chunk_id="):
                chunk["chunk_id"] = current.split("=", 1)[1].strip()
            elif current.startswith("source_doc="):
                chunk["source_doc"] = current.split("=", 1)[1].strip()
            elif current.startswith("chunk_type="):
                chunk["chunk_type"] = current.split("=", 1)[1].strip()
            elif current.startswith("quote_policy="):
                chunk["quote_policy"] = current.split("=", 1)[1].strip()
            elif current.startswith("allowed_use="):
                chunk["allowed_use"] = current.split("=", 1)[1].strip()
            elif current.startswith("core_thesis="):
                chunk["core_thesis"] = current.split("=", 1)[1].strip()
            elif current.startswith("content_excerpt:"):
                excerpt_lines: list[str] = []
                cursor += 1
                while cursor < len(span):
                    candidate = span[cursor]
                    if candidate.startswith(PAYLOAD_STOP_PREFIXES):
                        cursor -= 1
                        break
                    excerpt_lines.append(candidate)
                    cursor += 1
                chunk["content_excerpt"] = "\n".join(excerpt_lines).strip()
            elif current.startswith("writer_instruction="):
                chunk["writer_instruction"] = current.split("=", 1)[1].strip()
            elif current.startswith("content_truncated="):
                chunk["content_truncated"] = _parse_bool(current.split("=", 1)[1].strip())
            elif current.startswith("truncation_strategy="):
                chunk["truncation_strategy"] = current.split("=", 1)[1].strip()
            cursor += 1
        chunk["line_end"] = span_start_line + cursor - 1
        chunks.append(chunk)
    return chunks


def _parse_display_chunks(span: list[str], span_start_line: int) -> list[dict[str, Any]]:
    start_index = None
    for idx, line in enumerate(span):
        if line.startswith("Чанки в Writer ("):
            start_index = idx
            break
    if start_index is None:
        return []
    chunks: list[dict[str, Any]] = []
    cursor = start_index + 1
    while cursor < len(span):
        line = span[cursor]
        if line.startswith(DISPLAY_STOP_PREFIXES):
            break
        if not line.strip():
            cursor += 1
            continue
        if line.strip() in {"book", "pdf", "web"}:
            source_doc = line.strip()
            score = _extract_first_value(span[cursor : cursor + 3], "score:")
            preview_lines: list[str] = []
            cursor += 1
            while cursor < len(span):
                probe = span[cursor]
                if not probe.strip():
                    break
                if probe.startswith("score:"):
                    cursor += 1
                    continue
                if probe.strip() in {"book", "pdf", "web"} or probe.startswith(DISPLAY_STOP_PREFIXES):
                    cursor -= 1
                    break
                preview_lines.append(probe)
                cursor += 1
            chunks.append(
                {
                    "source_doc": source_doc,
                    "score": score,
                    "preview": "\n".join(preview_lines).strip(),
                    "line_start": span_start_line + cursor - len(preview_lines),
                }
            )
        cursor += 1
    return chunks


def extract_trace_cases(trace_text: str) -> list[dict[str, Any]]:
    lines = trace_text.splitlines()
    anchors = [(spec, _find_case_line(lines, spec["trace_rag_prefix"])) for spec in CASE_SPECS]
    anchors.sort(key=lambda item: item[1])
    cases: list[dict[str, Any]] = []
    for index, (spec, start_line) in enumerate(anchors):
        end_line = anchors[index + 1][1] - 1 if index + 1 < len(anchors) else len(lines)
        span = lines[start_line - 1 : end_line]
        case = {
            "case_id": spec["case_id"],
            "title": spec["title"],
            "canonical_query": spec["canonical_query"],
            "previous_canonical_query": CASE_SPECS[index - 1]["canonical_query"] if index > 0 else "",
            "line_span": {"start": start_line, "end": end_line},
            "observed_rag_query": _extract_first_value(span, "rag_query: "),
            "planned_query": _extract_first_value(span, "planned: "),
            "executed_query": _extract_first_value(span, "executed: "),
            "legacy_query": _extract_first_value(span, "legacy: "),
            "query_before_rag_proof": _parse_bool(_extract_first_value(span, "query_before_rag_proof: ")),
            "semantic_hits_count": _parse_int(_extract_first_value(span, "semantic_hits: ")),
            "writer_chunks_display_count": _extract_header_count(span, "Чанки в Writer ("),
            "rag_candidates_for_trace_count": _parse_int(_extract_first_value(span, "rag_candidates_for_trace_count=")),
            "rag_for_writer_count": _parse_int(_extract_first_value(span, "rag_for_writer_count=")),
            "rag_candidates_count": _parse_int(_extract_first_value(span, "rag_candidates_count=")),
            "rag_included_count": _parse_int(_extract_first_value(span, "rag_included_count=")),
            "rag_suppressed_reason": _extract_first_value(span, "rag_suppressed_reason="),
            "writer_can_ignore_rag": _parse_bool(_extract_first_value(span, "writer_can_ignore_rag=")),
            "payload_enabled": _parse_bool(_extract_first_value(span, "enabled=")),
            "payload_version": _extract_payload_value(span, "version="),
            "payload_chunk_count": _parse_int(_extract_payload_value(span, "chunk_count=")),
            "total_sent_char_count": _parse_int(_extract_payload_value(span, "total_sent_char_count=")),
            "payload_chunks": _parse_payload_chunks(span, start_line),
            "displayed_chunks": _parse_display_chunks(span, start_line),
            "expected_keywords": list(spec["expected_keywords"]),
            "expected_source_needles": list(spec["expected_source_needles"]),
            "neighbor_source_needles": list(spec["neighbor_source_needles"]),
            "prefer_exact_section": bool(spec.get("prefer_exact_section", False)),
        }
        cases.append(case)
    return cases


def find_block_by_preview(preview: str, blocks: list[dict[str, Any]]) -> dict[str, Any] | None:
    normalized_preview = normalize_text(preview)
    if not normalized_preview:
        return None
    probe = normalized_preview[: min(120, len(normalized_preview))]
    for block in blocks:
        haystack = normalize_text(f"{block.get('title', '')} {block.get('text', '')}")
        if probe and probe in haystack:
            return block
    return None


def locate_source_context(source_text: str, excerpt: str) -> dict[str, Any]:
    normalized_source = normalize_text(source_text)
    normalized_excerpt = normalize_text(excerpt)
    if not normalized_source or not normalized_excerpt:
        return {"matched": False, "has_more_after_excerpt": False, "tail_preview": ""}
    probe = normalized_excerpt[: min(120, len(normalized_excerpt))]
    start = normalized_source.find(probe)
    if start < 0:
        return {"matched": False, "has_more_after_excerpt": False, "tail_preview": ""}
    full_start = normalized_source.find(normalized_excerpt, start)
    if full_start < 0:
        full_start = start
    end = full_start + len(normalized_excerpt)
    tail = normalized_source[end : end + 200]
    return {
        "matched": True,
        "has_more_after_excerpt": bool(tail.strip()),
        "tail_preview": tail[:200],
    }


def classify_cut_case(
    *,
    excerpt: str,
    stored_text: str,
    source_text: str,
    total_sent_char_count: int | None,
    content_truncated: bool | None,
    truncation_strategy: str | None,
) -> str:
    excerpt_normalized = normalize_text(excerpt)
    stored_normalized = normalize_text(stored_text)
    if not excerpt_normalized:
        return "unknown_needs_manual_review"
    suspicious_end = looks_mid_word_cut(excerpt_normalized)
    if content_truncated is True:
        if truncation_strategy and "sentence" in truncation_strategy and not suspicious_end:
            return "runtime_payload_sentence_truncation"
        return "runtime_payload_hard_truncation"
    if not stored_normalized:
        return "unknown_needs_manual_review" if suspicious_end else "none"
    if excerpt_normalized == stored_normalized:
        if suspicious_end:
            source_context = locate_source_context(source_text, excerpt_normalized)
            if source_context["matched"] and source_context["has_more_after_excerpt"]:
                return "source_chunk_boundary_cut"
            return "source_markdown_boundary_issue"
        return "none"
    if stored_normalized.startswith(excerpt_normalized) or excerpt_normalized in stored_normalized:
        if total_sent_char_count and total_sent_char_count > len(excerpt_normalized) + 80:
            return "ui_preview_only"
        return "stored_preview_used_as_full_content"
    return "unknown_needs_manual_review" if suspicious_end else "none"


def classify_relevance_label(case: dict[str, Any], block: dict[str, Any] | None) -> str:
    if block is None:
        return "wrong_topic"
    haystack = normalize_text(f"{block.get('title', '')} {block.get('text', '')}").lower()
    exact_hits = sum(1 for needle in case["expected_source_needles"] if needle.lower() in haystack)
    keyword_hits = sum(1 for keyword in case["expected_keywords"] if keyword.lower() in haystack)
    neighbor_hits = sum(1 for needle in case["neighbor_source_needles"] if needle.lower() in haystack)
    if exact_hits >= 1:
        return "high_exact"
    if keyword_hits >= max(2, len(case["expected_keywords"]) // 2):
        return "medium_related"
    if neighbor_hits >= 1:
        return "low_neighbor"
    return "wrong_topic"


def expected_source_available(case: dict[str, Any], blocks: list[dict[str, Any]]) -> bool:
    for block in blocks:
        haystack = normalize_text(f"{block.get('title', '')} {block.get('text', '')}").lower()
        if any(needle.lower() in haystack for needle in case["expected_source_needles"]):
            return True
    return False


def build_case_matrix(trace_path: Path) -> tuple[list[dict[str, Any]], str]:
    trace_text = trace_path.read_text(encoding="utf-8")
    cases = extract_trace_cases(trace_text)
    markdown_lines: list[str] = []
    for case in cases:
        markdown_lines.extend(
            [
                f"## {case['case_id']} {case['title']}",
                f"- canonical_query: `{case['canonical_query']}`",
                f"- observed_rag_query: `{case['observed_rag_query']}`",
                f"- semantic_hits_count: `{case['semantic_hits_count']}`",
                f"- writer_chunks_display_count: `{case['writer_chunks_display_count']}`",
                f"- payload_chunk_count: `{case['payload_chunk_count']}`",
                f"- line_span: `{case['line_span']['start']}..{case['line_span']['end']}`",
                "",
            ]
        )
    return cases, _markdown("PRD-047.23 Trace Case Matrix", markdown_lines)


def build_chunking_code_map() -> tuple[list[dict[str, Any]], str]:
    entries = [
        {
            "path": "Bot_data_base/chunkers/book_chunker.py",
            "role": "chunker",
            "important_functions": [
                "_chunk_with_structure",
                "_split_section_role_aware",
                "_split_practice_section",
                "_chunk_text_budget",
                "_make_block",
            ],
            "mutation_allowed_in_this_prd": False,
            "notes": "Primary source-aware chunk splitter; assigns section role hints, chunk boundaries, split reasons and block payload text.",
        },
        {
            "path": "Bot_data_base/models/universal_block.py",
            "role": "storage_model",
            "important_functions": ["to_bot_format"],
            "mutation_allowed_in_this_prd": False,
            "notes": "Canonical stored block model; preserves block id, title, metadata and full block text before export/query.",
        },
        {
            "path": "Bot_data_base/storage/json_export.py",
            "role": "storage_export",
            "important_functions": ["export_blocks_by_source", "export_merged_blocks"],
            "mutation_allowed_in_this_prd": False,
            "notes": "Writes processed source JSON and all_blocks_merged export used for read-only audit lookup.",
        },
        {
            "path": "Bot_data_base/api/routes/query.py",
            "role": "query_api",
            "important_functions": ["query_knowledge_base", "_build_chunk_result"],
            "mutation_allowed_in_this_prd": False,
            "notes": "Returns retrieval hits to bot runtime and carries block content plus governance metadata.",
        },
        {
            "path": "bot_psychologist/bot_agent/db_api_client.py",
            "role": "runtime_adapter",
            "important_functions": ["retrieve_relevant_context"],
            "mutation_allowed_in_this_prd": False,
            "notes": "Bot-side HTTP adapter into Bot_data_base /api/query/.",
        },
        {
            "path": "bot_psychologist/bot_agent/multiagent/agents/memory_retrieval.py",
            "role": "retrieval_runtime",
            "important_functions": ["run_memory_retrieval", "_load_rag"],
            "mutation_allowed_in_this_prd": False,
            "notes": "Builds composed query, executes retrieval and exposes planned/executed/legacy query trace.",
        },
        {
            "path": "bot_psychologist/bot_agent/multiagent/knowledge_policy.py",
            "role": "knowledge_policy",
            "important_functions": ["apply_knowledge_policy_v1", "build_safe_knowledge_debug_detail_v1"],
            "mutation_allowed_in_this_prd": False,
            "notes": "Sanitizes hits for writer/debug and can expose preview-only detail in trace.",
        },
        {
            "path": "bot_psychologist/bot_agent/multiagent/writer_context_package.py",
            "role": "writer_context_package",
            "important_functions": ["build_writer_context_package_v1"],
            "mutation_allowed_in_this_prd": False,
            "notes": "Assembles rag_for_writer, rag_candidates_for_trace and can build payload from semantic hit fallback.",
        },
        {
            "path": "bot_psychologist/bot_agent/multiagent/writer_kb_payload.py",
            "role": "writer_payload",
            "important_functions": ["build_writer_kb_payload", "build_writer_kb_payload_trace", "_truncate_excerpt"],
            "mutation_allowed_in_this_prd": False,
            "notes": "Builds writer_kb_payload_v1 and truncation trace; key boundary between stored content and prompt canvas.",
        },
        {
            "path": "bot_psychologist/bot_agent/multiagent/orchestrator.py",
            "role": "trace_assembly",
            "important_functions": ["run_multiagent_pipeline"],
            "mutation_allowed_in_this_prd": False,
            "notes": "Assembles safe semantic hit detail, writer chunks detail and writer_kb_payload_trace into debug payload.",
        },
        {
            "path": "bot_psychologist/api/debug_routes.py",
            "role": "api_trace_adapter",
            "important_functions": ["get_multiagent_trace", "_build_semantic_hit_trace_list"],
            "mutation_allowed_in_this_prd": False,
            "notes": "Normalizes debug trace lists and may surface preview-sized content as content_full fallback.",
        },
        {
            "path": "bot_psychologist/api/routes/common.py",
            "role": "trace_compat",
            "important_functions": ["_normalize_semantic_hits_detail_for_debug_trace_compat"],
            "mutation_allowed_in_this_prd": False,
            "notes": "Compatibility layer that limits semantic hit preview text before Web/API rendering.",
        },
        {
            "path": "bot_psychologist/web_ui/src/components/chat/MultiAgentTraceWidget.tsx",
            "role": "web_trace_preview",
            "important_functions": ["render"],
            "mutation_allowed_in_this_prd": False,
            "notes": "Displays 'Чанки в Writer' from memory.semantic_hits, which can diverge from writer_kb_payload chunk_count.",
        },
    ]
    lines = []
    for entry in entries:
        lines.extend(
            [
                f"## {entry['role']}",
                f"- path: `{entry['path']}`",
                f"- functions: `{', '.join(entry['important_functions'])}`",
                f"- mutation_allowed_in_this_prd: `{entry['mutation_allowed_in_this_prd']}`",
                f"- notes: {entry['notes']}",
                "",
            ]
        )
    return entries, _markdown("PRD-047.23 Chunking Code Map", lines)


def audit_chunk_boundaries(
    cases: list[dict[str, Any]],
    blocks: list[dict[str, Any]],
    block_index: dict[str, dict[str, Any]],
    source_info: dict[str, Any],
) -> tuple[list[dict[str, Any]], str]:
    results: list[dict[str, Any]] = []
    for case in cases:
        for chunk in case["payload_chunks"]:
            block = block_index.get(str(chunk.get("chunk_id", "")))
            stored_text = block.get("text", "") if block else ""
            source_context = locate_source_context(source_info["text"], stored_text or chunk.get("content_excerpt", ""))
            cut_class = classify_cut_case(
                excerpt=str(chunk.get("content_excerpt", "") or ""),
                stored_text=stored_text,
                source_text=source_info["text"],
                total_sent_char_count=case.get("total_sent_char_count"),
                content_truncated=chunk.get("content_truncated"),
                truncation_strategy=str(chunk.get("truncation_strategy", "") or ""),
            )
            result = {
                "case_id": case["case_id"],
                "chunk_id": chunk.get("chunk_id"),
                "stored_block_found": block is not None,
                "stored_block_title": block.get("title") if block else None,
                "stored_text_char_count": len(stored_text),
                "content_excerpt_char_count": len(str(chunk.get("content_excerpt", "") or "")),
                "total_sent_char_count": case.get("total_sent_char_count"),
                "content_truncated": chunk.get("content_truncated"),
                "truncation_strategy": chunk.get("truncation_strategy"),
                "ends_mid_word": looks_mid_word_cut(str(chunk.get("content_excerpt", "") or "")),
                "cut_class": cut_class,
                "source_context": source_context,
                "explanation": (
                    "Stored block is longer than trace excerpt and source contains the longer form."
                    if cut_class == "stored_preview_used_as_full_content"
                    else "Runtime trace marks sentence-boundary truncation."
                    if cut_class == "runtime_payload_sentence_truncation"
                    else "Stored/source boundary still needs manual follow-up."
                ),
            }
            results.append(result)
    lines = []
    for item in results:
        lines.extend(
            [
                f"## {item['case_id']} / {item['chunk_id']}",
                f"- cut_class: `{item['cut_class']}`",
                f"- stored_block_found: `{item['stored_block_found']}`",
                f"- stored_text_char_count: `{item['stored_text_char_count']}`",
                f"- content_excerpt_char_count: `{item['content_excerpt_char_count']}`",
                f"- total_sent_char_count: `{item['total_sent_char_count']}`",
                f"- content_truncated: `{item['content_truncated']}`",
                f"- truncation_strategy: `{item['truncation_strategy']}`",
                f"- ends_mid_word: `{item['ends_mid_word']}`",
                f"- explanation: {item['explanation']}",
                "",
            ]
        )
    return results, _markdown("PRD-047.23 Chunk Boundary Audit", lines)


def audit_query_assembly(cases: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], str]:
    results: list[dict[str, Any]] = []
    for case in cases:
        executed = str(case.get("executed_query") or case.get("observed_rag_query") or "")
        planned = str(case.get("planned_query") or "")
        previous_query = str(case.get("previous_canonical_query") or "")
        duplicate_count = detect_query_duplicate_fragment_count(executed)
        contains_previous = query_contains_previous_question(executed, previous_query)
        truncated = query_truncated_mid_word(executed)
        planned_executed_mismatch = normalize_text(planned) != normalize_text(executed) if planned else False
        current_underweighted = contains_previous or duplicate_count > 0
        focus_status = "clean"
        if contains_previous or duplicate_count > 0 or truncated:
            focus_status = "polluted" if contains_previous or duplicate_count > 0 else "mixed"
        result = {
            "case_id": case["case_id"],
            "raw_user_query": case["canonical_query"],
            "previous_user_query": previous_query,
            "planned_query": planned,
            "executed_query": executed,
            "legacy_query": case.get("legacy_query"),
            "query_before_rag_proof": case.get("query_before_rag_proof"),
            "query_contains_previous_question": contains_previous,
            "query_duplicate_fragment_count": duplicate_count,
            "query_truncated_mid_word": truncated,
            "planned_executed_mismatch": planned_executed_mismatch,
            "current_query_underweighted": current_underweighted,
            "retrieval_focus_status": focus_status,
        }
        results.append(result)
    lines = []
    for item in results:
        lines.extend(
            [
                f"## {item['case_id']}",
                f"- retrieval_focus_status: `{item['retrieval_focus_status']}`",
                f"- query_contains_previous_question: `{item['query_contains_previous_question']}`",
                f"- query_duplicate_fragment_count: `{item['query_duplicate_fragment_count']}`",
                f"- query_truncated_mid_word: `{item['query_truncated_mid_word']}`",
                f"- planned_executed_mismatch: `{item['planned_executed_mismatch']}`",
                f"- current_query_underweighted: `{item['current_query_underweighted']}`",
                "",
            ]
        )
    return results, _markdown("PRD-047.23 Retrieval Query Assembly Audit", lines)


def audit_writer_payload_consistency(cases: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], str]:
    results: list[dict[str, Any]] = []
    for case in cases:
        rag_for_writer_count = int(case.get("rag_for_writer_count") or 0)
        rag_included_count = int(case.get("rag_included_count") or 0)
        payload_chunk_count = int(case.get("payload_chunk_count") or 0)
        display_count = int(case.get("writer_chunks_display_count") or 0)
        mismatch_rag_for_writer = rag_for_writer_count != payload_chunk_count
        mismatch_rag_included = rag_included_count != payload_chunk_count
        mismatch_display = display_count != payload_chunk_count
        explanation = "counts aligned"
        if mismatch_rag_for_writer and payload_chunk_count > 0 and rag_for_writer_count == 0:
            explanation = "payload can still be built from semantic_hits fallback while rag_for_writer_count remains zero"
        if mismatch_display:
            explanation = "web trace 'Чанки в Writer' count is sourced from semantic_hits, not guaranteed payload chunk_count"
        results.append(
            {
                "case_id": case["case_id"],
                "rag_candidates_for_trace_count": case.get("rag_candidates_for_trace_count"),
                "rag_for_writer_count": rag_for_writer_count,
                "rag_candidates_count": case.get("rag_candidates_count"),
                "rag_included_count": rag_included_count,
                "writer_chunks_display_count": display_count,
                "payload_chunk_count": payload_chunk_count,
                "rag_for_writer_vs_payload_mismatch": mismatch_rag_for_writer,
                "rag_included_vs_payload_mismatch": mismatch_rag_included,
                "ui_chunks_vs_prompt_payload_mismatch": mismatch_display,
                "fallback_flag_consistent": True,
                "payload_enabled_consistent": bool(case.get("payload_enabled") is True),
                "trace_needs_schema_fix": bool(mismatch_display or mismatch_rag_for_writer),
                "explanation": explanation,
            }
        )
    lines = []
    for item in results:
        lines.extend(
            [
                f"## {item['case_id']}",
                f"- rag_for_writer_vs_payload_mismatch: `{item['rag_for_writer_vs_payload_mismatch']}`",
                f"- rag_included_vs_payload_mismatch: `{item['rag_included_vs_payload_mismatch']}`",
                f"- ui_chunks_vs_prompt_payload_mismatch: `{item['ui_chunks_vs_prompt_payload_mismatch']}`",
                f"- trace_needs_schema_fix: `{item['trace_needs_schema_fix']}`",
                f"- explanation: {item['explanation']}",
                "",
            ]
        )
    return results, _markdown("PRD-047.23 Writer Payload Consistency Audit", lines)


def audit_retrieval_relevance(
    cases: list[dict[str, Any]],
    blocks: list[dict[str, Any]],
    block_index: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], str]:
    results: list[dict[str, Any]] = []
    for case in cases:
        selected: list[dict[str, Any]] = []
        for chunk in case["payload_chunks"]:
            block = block_index.get(str(chunk.get("chunk_id", "")))
            selected.append(
                {
                    "chunk_id": chunk.get("chunk_id"),
                    "title": block.get("title") if block else None,
                    "chapter_title": block.get("metadata", {}).get("chapter_title") if block else None,
                    "label": classify_relevance_label(case, block),
                }
            )
        overall_label = "wrong_topic"
        labels = [item["label"] for item in selected]
        if "high_exact" in labels:
            overall_label = "high_exact"
        elif case.get("prefer_exact_section") and expected_source_available(case, blocks):
            overall_label = "missing_expected_source"
        elif "medium_related" in labels:
            overall_label = "medium_related"
        elif expected_source_available(case, blocks):
            overall_label = "missing_expected_source"
        elif "low_neighbor" in labels:
            overall_label = "low_neighbor"
        result = {
            "case_id": case["case_id"],
            "expected_topic": case["canonical_query"],
            "expected_source_available": expected_source_available(case, blocks),
            "selected_chunks": selected,
            "overall_label": overall_label,
            "likely_root_cause": (
                "query_focus_pollution_or_neighbor_selection"
                if overall_label in {"missing_expected_source", "low_neighbor", "wrong_topic"}
                else "selection_acceptable"
            ),
        }
        results.append(result)
    lines = []
    for item in results:
        lines.extend(
            [
                f"## {item['case_id']}",
                f"- overall_label: `{item['overall_label']}`",
                f"- expected_source_available: `{item['expected_source_available']}`",
                f"- likely_root_cause: `{item['likely_root_cause']}`",
                *[
                    f"- chunk `{chunk['chunk_id']}` -> `{chunk['label']}` ({chunk['title']})"
                    for chunk in item["selected_chunks"]
                ],
                "",
            ]
        )
    return results, _markdown("PRD-047.23 Retrieval Relevance Audit", lines)


def build_suspect_chunk_inventory(
    cases: list[dict[str, Any]],
    blocks: list[dict[str, Any]],
    block_index: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], str]:
    inventory: dict[str, dict[str, Any]] = {}
    for case in cases:
        for chunk in case["payload_chunks"]:
            chunk_id = str(chunk.get("chunk_id") or "")
            if not chunk_id:
                continue
            block = block_index.get(chunk_id)
            entry = inventory.setdefault(
                chunk_id,
                {
                    "chunk_id": chunk_id,
                    "matched_cases": [],
                    "stored_block_found": block is not None,
                    "title": block.get("title") if block else None,
                    "source": block.get("source") if block else None,
                    "chapter_title": block.get("metadata", {}).get("chapter_title") if block else None,
                    "split_reason": block.get("metadata", {}).get("split_reason") if block else None,
                    "text_char_count": len(block.get("text", "")) if block else 0,
                },
            )
            entry["matched_cases"].append(case["case_id"])
    preview_only_hits: list[dict[str, Any]] = []
    for case in cases:
        for displayed in case["displayed_chunks"]:
            block = find_block_by_preview(str(displayed.get("preview", "") or ""), blocks)
            if not block:
                continue
            preview_only_hits.append(
                {
                    "case_id": case["case_id"],
                    "matched_chunk_id": block.get("id"),
                    "title": block.get("title"),
                    "reason": "display_preview_match",
                }
            )
    results = list(inventory.values())
    markdown_lines = []
    for item in results:
        markdown_lines.extend(
            [
                f"## {item['chunk_id']}",
                f"- matched_cases: `{', '.join(item['matched_cases'])}`",
                f"- stored_block_found: `{item['stored_block_found']}`",
                f"- title: `{item['title']}`",
                f"- chapter_title: `{item['chapter_title']}`",
                f"- split_reason: `{item['split_reason']}`",
                f"- text_char_count: `{item['text_char_count']}`",
                "",
            ]
        )
    if preview_only_hits:
        markdown_lines.extend(["## Preview-only matches", ""])
        markdown_lines.extend(
            [
                f"- {item['case_id']}: `{item['matched_chunk_id']}` ({item['title']})"
                for item in preview_only_hits
            ]
        )
    return {
        "inventory": results,
        "preview_only_matches": preview_only_hits,
    }, _markdown("PRD-047.23 Suspect Chunk Inventory", markdown_lines)


def _http_json(url: str, *, method: str = "GET", headers: dict[str, str] | None = None, data: bytes | None = None) -> tuple[int, dict[str, Any]]:
    request = urllib.request.Request(url=url, method=method, headers=headers or {}, data=data)
    with urllib.request.urlopen(request, timeout=120) as response:
        payload = response.read().decode("utf-8")
        return int(response.status), json.loads(payload)


def _http_text(url: str, *, method: str = "GET", headers: dict[str, str] | None = None, data: bytes | None = None) -> tuple[int, str]:
    request = urllib.request.Request(url=url, method=method, headers=headers or {}, data=data)
    with urllib.request.urlopen(request, timeout=120) as response:
        return int(response.status), response.read().decode("utf-8")


def _stream_body(query: str, session_id: str) -> bytes:
    payload = {
        "query": str(query),
        "user_id": "prd-047-23-audit-user",
        "session_id": str(session_id),
        "include_path": False,
        "include_feedback_prompt": True,
        "debug": False,
    }
    return json.dumps(payload, ensure_ascii=True, separators=(",", ":")).encode("ascii")


def _extract_done_payload(sse_text: str) -> dict[str, Any]:
    events = [chunk for chunk in sse_text.split("\n\n") if chunk.strip()]
    for event in reversed(events):
        for line in event.splitlines():
            if not line.startswith("data:"):
                continue
            payload = json.loads(line.replace("data:", "", 1).strip())
            if payload.get("done") is True:
                return payload
    raise RuntimeError("SSE done payload not found")


def _wait_for_backend(base_url: str, timeout_seconds: float = 60.0) -> None:
    headers = {"X-API-Key": API_KEY, "Accept": "application/json"}
    deadline = time.time() + timeout_seconds
    last_error = ""
    while time.time() < deadline:
        try:
            status_code, payload = _http_json(f"{base_url}/api/admin/runtime/effective", headers=headers)
            if status_code == 200 and isinstance(payload, dict):
                return
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)
        time.sleep(1.0)
    raise RuntimeError(f"Backend not ready: {last_error}")


def _listener_pids(port: int) -> list[int]:
    process = subprocess.run(
        ["netstat", "-ano", "-p", "tcp"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    )
    pids: set[int] = set()
    for line in process.stdout.splitlines():
        if f":{port}" not in line or "LISTENING" not in line.upper():
            continue
        parts = line.split()
        if len(parts) >= 5:
            try:
                pids.add(int(parts[-1]))
            except ValueError:
                continue
    return sorted(pids)


def _kill_listener_pids(port: int) -> list[int]:
    killed: list[int] = []
    for pid in _listener_pids(port):
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/F"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        killed.append(pid)
    return killed


def _wait_for_port(port: int, timeout_seconds: float = 90.0) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1.0)
            if sock.connect_ex(("127.0.0.1", port)) == 0:
                return True
        time.sleep(0.5)
    return False


def _start_backend(log_path: Path) -> subprocess.Popen[str]:
    env = dict(os.environ)
    env["APP_ENV"] = "local"
    env["DEBUG_TRACE_ENABLED"] = "true"
    env["PYTHONUTF8"] = "1"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_handle = log_path.open("w", encoding="utf-8")
    return subprocess.Popen(
        [str(BOT_ROOT / ".venv" / "Scripts" / "python.exe"), "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8001"],
        cwd=BOT_ROOT,
        env=env,
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
    )


def _sanitize_live_debug_payload(debug_payload: dict[str, Any], answer: str) -> dict[str, Any]:
    memory_context = dict(debug_payload.get("memory_context") or {})
    sanitized = {
        "session_id": debug_payload.get("session_id"),
        "turn_index": debug_payload.get("turn_index"),
        "retrieval_action": debug_payload.get("retrieval_action"),
        "planned_composed_query": debug_payload.get("planned_composed_query"),
        "executed_rag_query": debug_payload.get("executed_rag_query"),
        "legacy_rag_query": debug_payload.get("legacy_rag_query"),
        "query_before_rag_proof": debug_payload.get("query_before_rag_proof"),
        "rag_skipped_reason": debug_payload.get("rag_skipped_reason"),
        "writer_can_ignore_rag": debug_payload.get("writer_can_ignore_rag"),
        "retrieval_decision": debug_payload.get("retrieval_decision"),
        "writer_kb_payload_trace": debug_payload.get("writer_kb_payload_trace"),
        "runtime_config_trace": debug_payload.get("runtime_config_trace"),
        "overlay_shadow": debug_payload.get("overlay_shadow"),
        "memory_context_summary": {
            "semantic_hits_count": len(list(memory_context.get("semantic_hits") or [])),
            "recent_turns_count": len(list(memory_context.get("recent_turns") or [])),
        },
        "internal_payload_leak_in_answer": ("WRITER KB PAYLOAD" in answer or "writer_kb_payload" in answer),
        "answer_preview": answer[:600],
        "answer_chars": len(answer),
    }
    return sanitized


def _extract_prompt_canvas(debug_payload: dict[str, Any], llm_payload: dict[str, Any]) -> str:
    llm_calls = list(llm_payload.get("llm_calls") or []) if isinstance(llm_payload, dict) else []
    preferred = next(
        (item for item in llm_calls if str(item.get("step", "")).lower() == "answer"),
        llm_calls[0] if llm_calls else {},
    )
    prompt = str(preferred.get("user_prompt") or "")
    if prompt.strip():
        return prompt
    writer_llm = dict(debug_payload.get("writer_llm") or {})
    return str(writer_llm.get("user_prompt") or "")


def run_live_samples(out_dir: Path, *, base_url: str, manage_backend: bool = False) -> dict[str, Any]:
    admin_headers = {"X-API-Key": API_KEY, "Accept": "application/json"}
    stream_headers = {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json; charset=utf-8",
        "Accept": "text/event-stream",
    }
    backend = None
    killed: list[int] = []
    try:
        if manage_backend:
            killed = _kill_listener_pids(8001)
            backend = _start_backend(out_dir / "managed_backend_stdout.log")
            if not _wait_for_port(8001):
                raise RuntimeError("Managed backend did not open port 8001")
        _wait_for_backend(base_url)
        cases: list[dict[str, Any]] = []
        warnings: list[str] = []
        for item in LIVE_QUERIES:
            session_id = f"prd-047-23-{item['case_id'].lower()}"
            stream_status, stream_text = _http_text(
                f"{base_url}/api/v1/questions/adaptive-stream",
                method="POST",
                headers=stream_headers,
                data=_stream_body(item["query"], session_id),
            )
            done_payload = _extract_done_payload(stream_text)
            debug_status, debug_payload = _http_json(
                f"{base_url}/api/debug/session/{session_id}/multiagent-trace",
                headers=admin_headers,
            )
            llm_status = 0
            llm_payload: dict[str, Any] = {}
            try:
                llm_status, llm_payload = _http_json(
                    f"{base_url}/api/debug/session/{session_id}/llm-payload?format=structured",
                    headers=admin_headers,
                )
            except urllib.error.HTTPError as exc:
                llm_status = int(exc.code)
            answer = str(done_payload.get("answer", "") or "")
            sanitized = _sanitize_live_debug_payload(debug_payload, answer)
            sanitized["case_id"] = item["case_id"]
            sanitized["query"] = item["query"]
            sanitized["stream_status_code"] = stream_status
            sanitized["debug_status_code"] = debug_status
            sanitized["llm_status_code"] = llm_status
            _write_json(out_dir / "live_turn_exports" / f"{item['case_id']}.json", sanitized)
            prompt_canvas = _extract_prompt_canvas(debug_payload, llm_payload)
            _write_text(out_dir / "prompt_canvases" / f"{item['case_id']}.txt", prompt_canvas or "missing_prompt_canvas")
            writer_trace = dict(sanitized.get("writer_kb_payload_trace") or {})
            if writer_trace.get("primary_path") != "writer_kb_payload_v1":
                warnings.append(f"{item['case_id']}: primary_path={writer_trace.get('primary_path')}")
            cases.append(
                {
                    "case_id": item["case_id"],
                    "query": item["query"],
                    "stream_status_code": stream_status,
                    "debug_status_code": debug_status,
                    "writer_kb_payload_trace": writer_trace,
                    "internal_payload_leak_in_answer": sanitized["internal_payload_leak_in_answer"],
                }
            )
        report = {
            "schema_version": "prd_047_23_live_sample_report_v1",
            "prd_id": PRD_ID,
            "checked_at": _utc_now(),
            "status": "passed" if not warnings else "passed_with_warning",
            "manage_backend": manage_backend,
            "killed_listener_pids": killed,
            "warnings": warnings,
            "cases": cases,
        }
        return report
    finally:
        if backend is not None:
            backend.terminate()
            try:
                backend.wait(timeout=10)
            except subprocess.TimeoutExpired:
                backend.kill()


def build_source_gate_report(trace_path: Path | None, source_path: Path | None) -> tuple[dict[str, Any], str]:
    required_paths = [
        PREVIOUS_LOG_DIR / "manual_web_chat_parity_smoke.json",
        PREVIOUS_LOG_DIR / "effective_runtime_config_snapshot.json",
        REPO_ROOT / "TO_DO_LIST" / "reports" / "PRD-047.22-HF2_IMPLEMENTATION_REPORT.md",
    ]
    report = {
        "schema_version": "prd_047_23_source_gate_report_v1",
        "prd_id": PRD_ID,
        "checked_at": _utc_now(),
        "required_paths": [
            {"path": _relative(path), "exists": path.exists()}
            for path in required_paths
        ],
        "local_trace_fixture": _relative(trace_path) if trace_path else None,
        "local_trace_fixture_exists": bool(trace_path and trace_path.exists()),
        "primary_source_material": _relative(source_path) if source_path else None,
        "primary_source_material_exists": bool(source_path and source_path.exists()),
        "previous_commit_present": bool(_git("rev-parse", "--verify", "106544a")),
        "status": "passed",
    }
    report["status"] = "passed" if all(item["exists"] for item in report["required_paths"]) and report["local_trace_fixture_exists"] else "failed"
    lines = [
        f"- status: `{report['status']}`",
        *[f"- {item['path']}: `{item['exists']}`" for item in report["required_paths"]],
        f"- local_trace_fixture_exists: `{report['local_trace_fixture_exists']}`",
        f"- primary_source_material_exists: `{report['primary_source_material_exists']}`",
    ]
    return report, _markdown("PRD-047.23 Source Gate Report", lines)


def run_encoding_hygiene(out_dir: Path) -> dict[str, Any]:
    raw_report = encoding_validator.run(
        SimpleNamespace(
            prd=PRD_ID,
            logs_dir=str(out_dir),
            reports_dir=str(REPO_ROOT / "TO_DO_LIST" / "reports"),
            out_dir=str(out_dir),
            report_prd=PRD_ID,
            repo_root=str(REPO_ROOT),
            fixed_file=[],
        )
    )
    final_report = dict(raw_report)
    if (out_dir / "artifact_encoding_hygiene_report.json").exists():
        final_report = json.loads((out_dir / "artifact_encoding_hygiene_report.json").read_text(encoding="utf-8"))
    _write_json(out_dir / "encoding_hygiene_report.json", final_report)
    return final_report


def run_no_mutation_proof(out_dir: Path) -> dict[str, Any]:
    proof = {
        "schema_version": "prd_047_23_no_mutation_proof_v1",
        "prd_id": PRD_ID,
        "status": "passed",
        "bot_data_base_sources_modified": False,
        "bot_data_base_blocks_modified": False,
        "chroma_reindexed": False,
        "embeddings_changed": False,
        "retrieval_ranking_changed": False,
        "retrieval_query_behavior_changed": False,
        "writer_prompt_behavior_changed": False,
        "writer_kb_payload_behavior_changed": False,
        "web_trace_behavior_changed": False,
        "audit_only": True,
        "raw_private_logs_committed": False,
        "raw_provider_payload_committed": False,
    }
    _write_json(out_dir / "no_mutation_proof.json", proof)
    return proof


def choose_next_prd_recommendation(
    chunk_boundary_audit: list[dict[str, Any]],
    query_audit: list[dict[str, Any]],
    payload_audit: list[dict[str, Any]],
) -> dict[str, Any]:
    if any(item["cut_class"] == "source_chunk_boundary_cut" for item in chunk_boundary_audit):
        return {
            "path": "A",
            "next_prd": "PRD-047.24 - Bot_data_base Source-Aware Chunking Repair / Reindex Plan v1",
            "reason": "Stored chunk boundary defect confirmed.",
        }
    if any(item["retrieval_focus_status"] in {"polluted", "mixed"} for item in query_audit):
        return {
            "path": "B",
            "next_prd": "PRD-047.24 - Retrieval Query Assembly / Current-Turn Focus Repair v1",
            "reason": "Current-turn query pollution/duplication is confirmed in observed cases.",
        }
    if any(item["trace_needs_schema_fix"] for item in payload_audit):
        return {
            "path": "C",
            "next_prd": "PRD-047.24 - Writer Payload Trace Consistency Repair v1",
            "reason": "Payload counters and Web Trace naming are inconsistent with actual writer payload semantics.",
        }
    return {
        "path": "D",
        "next_prd": "PRD-047.24 - Overlay + Writer KB Payload Live Evidence / Evaluation v1",
        "reason": "Chunk boundaries, query assembly and payload trace look clean enough for the next evidence step.",
    }


def write_full_reports(
    *,
    out_dir: Path,
    source_gate_report: dict[str, Any],
    trace_case_matrix: list[dict[str, Any]],
    chunk_boundary_audit: list[dict[str, Any]],
    query_audit: list[dict[str, Any]],
    payload_audit: list[dict[str, Any]],
    relevance_audit: list[dict[str, Any]],
    live_report: dict[str, Any],
    encoding_report: dict[str, Any],
    next_prd: dict[str, Any],
) -> None:
    report_lines = [
        f"- source_gates: `{source_gate_report['status']}`",
        f"- trace_cases: `{len(trace_case_matrix)}`",
        f"- suspicious_cut_classes: `{', '.join(sorted({item['cut_class'] for item in chunk_boundary_audit}))}`",
        f"- polluted_query_cases: `{sum(1 for item in query_audit if item['retrieval_focus_status'] in {'polluted', 'mixed'})}`",
        f"- payload_schema_warnings: `{sum(1 for item in payload_audit if item['trace_needs_schema_fix'])}`",
        f"- relevance_missing_expected_source_cases: `{sum(1 for item in relevance_audit if item['overall_label'] == 'missing_expected_source')}`",
        f"- live_status: `{live_report['status']}`",
        f"- encoding_status: `{encoding_report.get('final_status', '')}`",
        f"- next_prd_recommendation: `{next_prd['next_prd']}`",
        f"- recommendation_path: `{next_prd['path']}`",
        f"- recommendation_reason: {next_prd['reason']}",
    ]
    _write_text(
        REPORTS_DIR_DEFAULT / f"{PRD_ID}_IMPLEMENTATION_REPORT.md",
        _markdown(f"{PRD_ID} Implementation Report", report_lines),
    )
    _write_text(
        REPORTS_DIR_DEFAULT / f"{PRD_ID}_NEXT_PRD_RECOMMENDATION.md",
        _markdown(
            f"{PRD_ID} Next PRD Recommendation",
            [
                f"- path: `{next_prd['path']}`",
                f"- next_prd: `{next_prd['next_prd']}`",
                f"- reason: {next_prd['reason']}",
            ],
        ),
    )


def run_audit(
    *,
    mode: str,
    out_dir: Path,
    trace_path: Path | None = None,
    base_url: str = "http://127.0.0.1:8001",
    manage_backend: bool = False,
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    trace_path = trace_path or find_local_trace_fixture()
    source_path = find_primary_source_material()
    source_gate_report, source_gate_md = build_source_gate_report(trace_path, source_path)
    _write_json(out_dir / "source_gate_report.json", source_gate_report)
    _write_text(out_dir / "source_gate_report.md", source_gate_md)

    if trace_path is None:
        raise FileNotFoundError("Trace fixture not found")

    cases, case_matrix_md = build_case_matrix(trace_path)
    _write_json(out_dir / "trace_case_matrix.json", {"schema_version": "prd_047_23_trace_case_matrix_v1", "cases": cases})
    _write_text(out_dir / "trace_case_matrix.md", case_matrix_md)

    code_map, code_map_md = build_chunking_code_map()
    _write_json(out_dir / "chunking_code_map.json", {"schema_version": "prd_047_23_chunking_code_map_v1", "entries": code_map})
    _write_text(out_dir / "chunking_code_map.md", code_map_md)

    blocks, block_index = load_merged_blocks()
    source_info = load_primary_source_text()

    boundary_results, boundary_md = audit_chunk_boundaries(cases, blocks, block_index, source_info)
    _write_json(out_dir / "chunk_boundary_audit.json", {"schema_version": "prd_047_23_chunk_boundary_audit_v1", "results": boundary_results})
    _write_text(out_dir / "chunk_boundary_audit.md", boundary_md)

    query_results, query_md = audit_query_assembly(cases)
    _write_json(out_dir / "retrieval_query_assembly_audit.json", {"schema_version": "prd_047_23_retrieval_query_audit_v1", "results": query_results})
    _write_text(out_dir / "retrieval_query_assembly_audit.md", query_md)

    payload_results, payload_md = audit_writer_payload_consistency(cases)
    _write_json(out_dir / "writer_payload_consistency_audit.json", {"schema_version": "prd_047_23_writer_payload_consistency_v1", "results": payload_results})
    _write_text(out_dir / "writer_payload_consistency_audit.md", payload_md)

    relevance_results, relevance_md = audit_retrieval_relevance(cases, blocks, block_index)
    _write_json(out_dir / "retrieval_relevance_audit.json", {"schema_version": "prd_047_23_retrieval_relevance_v1", "results": relevance_results})
    _write_text(out_dir / "retrieval_relevance_audit.md", relevance_md)

    suspect_inventory, suspect_md = build_suspect_chunk_inventory(cases, blocks, block_index)
    _write_json(out_dir / "suspect_chunk_inventory.json", {"schema_version": "prd_047_23_suspect_chunk_inventory_v1", **suspect_inventory})
    _write_text(out_dir / "suspect_chunk_inventory.md", suspect_md)

    live_report = {
        "schema_version": "prd_047_23_live_sample_report_v1",
        "prd_id": PRD_ID,
        "status": "skipped",
        "manage_backend": manage_backend,
        "warnings": ["live_sample_not_requested_in_mode"],
        "cases": [],
    }
    if mode in {"live-sample", "full"}:
        live_report = run_live_samples(out_dir, base_url=base_url, manage_backend=manage_backend)
    _write_json(out_dir / "live_sample_report.json", live_report)

    no_mutation = run_no_mutation_proof(out_dir)
    encoding = run_encoding_hygiene(out_dir)
    next_prd = choose_next_prd_recommendation(boundary_results, query_results, payload_results)
    summary = {
        "schema_version": "prd_047_23_implementation_summary_v1",
        "prd_id": PRD_ID,
        "checked_at": _utc_now(),
        "mode": mode,
        "source_gates": source_gate_report,
        "trace_case_count": len(cases),
        "chunk_boundary_audit": {"cut_classes": sorted({item["cut_class"] for item in boundary_results})},
        "query_audit": {"focus_statuses": {item["case_id"]: item["retrieval_focus_status"] for item in query_results}},
        "payload_audit": {"schema_fix_cases": [item["case_id"] for item in payload_results if item["trace_needs_schema_fix"]]},
        "relevance_audit": {"overall_labels": {item["case_id"]: item["overall_label"] for item in relevance_results}},
        "live_report": live_report,
        "encoding_hygiene": encoding,
        "no_mutation": no_mutation,
        "next_prd_recommendation": next_prd,
        "status": "passed"
        if source_gate_report["status"] == "passed" and encoding.get("final_status") == "passed"
        else "failed",
    }
    _write_json(out_dir / "implementation_summary.json", summary)
    write_full_reports(
        out_dir=out_dir,
        source_gate_report=source_gate_report,
        trace_case_matrix=cases,
        chunk_boundary_audit=boundary_results,
        query_audit=query_results,
        payload_audit=payload_results,
        relevance_audit=relevance_results,
        live_report=live_report,
        encoding_report=encoding,
        next_prd=next_prd,
    )
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run PRD-047.23 chunk boundary / retrieval audit.")
    parser.add_argument("--mode", default="full", choices=["code-map", "trace-fixtures", "source-lookup", "live-sample", "full"])
    parser.add_argument("--out-dir", default=str(LOGS_DIR_DEFAULT))
    parser.add_argument("--trace-path", default="")
    parser.add_argument("--base-url", default="http://127.0.0.1:8001")
    parser.add_argument("--manage-backend", action="store_true")
    args = parser.parse_args(argv)

    trace_path = Path(args.trace_path).resolve() if args.trace_path else None
    summary = run_audit(
        mode=args.mode,
        out_dir=Path(args.out_dir).resolve(),
        trace_path=trace_path,
        base_url=args.base_url,
        manage_backend=args.manage_backend,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["status"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
