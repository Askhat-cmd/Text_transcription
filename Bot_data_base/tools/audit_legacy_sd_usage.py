from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_SOURCE_PRD = "PRD-046.0.10"
DEFAULT_OUTPUT_JSON = "TO_DO_LIST/logs/PRD-046.0.10/legacy_sd_usage_audit.json"
DEFAULT_OUTPUT_MD = "TO_DO_LIST/reports/PRD-046.0.10_LEGACY_SD_USAGE_AUDIT.md"

TOKEN_RE = re.compile(
    r"\bsd_level\b|sd_distribution|sd_label|spiral_dynamics|spiral dynamics|spiral|legacy_sd",
    re.IGNORECASE,
)

ACTIVE_RUNTIME_PATTERNS = (
    'where_filter["sd_level"]',
    "where_filter['sd_level']",
    "_sd_int_to_names(",
    "$gte\": request.sd_level",
)
ACTIVE_INGESTION_PATTERNS = (
    "sd_labeler.label_blocks(",
)

CATEGORIES = (
    "active_runtime",
    "active_ingestion",
    "api_backward_compat",
    "dashboard_display",
    "legacy_metadata",
    "docs_active",
    "docs_legacy",
    "tests",
    "safe_comment",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _repo_root() -> Path:
    cwd = Path.cwd()
    if (cwd / "Bot_data_base").exists():
        return cwd
    if cwd.name == "Bot_data_base":
        return cwd.parent
    return cwd


def _iter_target_files(bot_root: Path) -> list[Path]:
    excluded_dirs = {".venv", "venv", "__pycache__", ".git", "node_modules"}

    def _is_allowed(path: Path) -> bool:
        parts = path.parts
        if any(part in excluded_dirs for part in parts):
            return False
        if any(part.startswith(".venv_migrated_backup") for part in parts):
            return False
        normalized = path.as_posix().lower()
        if "/data/uploads/" in normalized:
            return False
        return True

    files: list[Path] = []
    for ext in ("*.py", "*.yaml", "*.yml", "*.md"):
        files.extend(p for p in bot_root.rglob(ext) if _is_allowed(p))
    env_example = bot_root / ".env.example"
    if env_example.exists():
        files.append(env_example)
    unique_files = sorted({p.resolve() for p in files if p.is_file()})
    return [Path(p) for p in unique_files]


def _is_comment_line(path: Path, stripped: str) -> bool:
    if not stripped:
        return False
    suffix = path.suffix.lower()
    if suffix in {".py", ".yaml", ".yml"}:
        return stripped.startswith("#")
    if suffix == ".md":
        return stripped.startswith("<!--")
    return stripped.startswith("#")


def _categorize(path: Path, line: str) -> str:
    rel = path.as_posix().lower()
    stripped = line.strip()
    line_l = line.lower()

    if _is_comment_line(path, stripped):
        return "safe_comment"
    if "/tests/" in rel:
        return "tests"
    if rel.endswith("/api/routes/query.py") or rel.endswith("/api/schemas.py"):
        return "api_backward_compat"
    if "/api/routes/dashboard.py" in rel or "/web_ui/" in rel:
        return "dashboard_display"
    if any(pattern.lower() in line_l for pattern in ACTIVE_INGESTION_PATTERNS):
        return "active_ingestion"
    if any(pattern.lower() in line_l for pattern in ACTIVE_RUNTIME_PATTERNS):
        return "active_runtime"
    if rel.endswith(".md"):
        if "legacy" in rel or "deprecated" in line_l or "legacy" in line_l:
            return "docs_legacy"
        return "docs_active"
    return "legacy_metadata"


def _scan_file(path: Path, root: Path) -> list[dict[str, Any]]:
    rel = path.relative_to(root).as_posix()
    text = path.read_text(encoding="utf-8", errors="replace")
    hits: list[dict[str, Any]] = []
    for idx, line in enumerate(text.splitlines(), start=1):
        if not TOKEN_RE.search(line):
            continue
        category = _categorize(path, line)
        hits.append(
            {
                "path": rel,
                "line": idx,
                "category": category,
                "text": line.strip()[:300],
            }
        )
    return hits


def run_audit_legacy_sd_usage(*, source_prd: str, output_json: Path, output_md: Path) -> dict[str, Any]:
    root = _repo_root()
    bot_root = root / "Bot_data_base"
    files = _iter_target_files(bot_root)
    all_hits: list[dict[str, Any]] = []
    scanned_files: list[str] = []
    for file_path in files:
        scanned_files.append(file_path.relative_to(root).as_posix())
        all_hits.extend(_scan_file(file_path, root))

    category_counter = Counter(hit["category"] for hit in all_hits)
    active_counter = sum(
        category_counter.get(category, 0) for category in ("active_runtime", "active_ingestion")
    )
    payload = {
        "schema_version": "legacy_sd_usage_audit_v1",
        "source_prd": source_prd,
        "generated_at": _utc_now(),
        "files_scanned_count": len(scanned_files),
        "sd_mentions_total": len(all_hits),
        "active_mentions_total": active_counter,
        "categories": {name: int(category_counter.get(name, 0)) for name in CATEGORIES},
        "hits": all_hits,
        "files_scanned": scanned_files,
    }

    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md_lines = [
        f"# {source_prd} Legacy SD Usage Audit",
        "",
        "## Summary",
        f"- files_scanned_count: `{payload['files_scanned_count']}`",
        f"- sd_mentions_total: `{payload['sd_mentions_total']}`",
        f"- active_mentions_total: `{payload['active_mentions_total']}`",
        "",
        "## Category Counts",
    ]
    for name in CATEGORIES:
        md_lines.append(f"- {name}: `{payload['categories'][name]}`")
    md_lines.extend(["", "## Sample Hits (first 40)"])
    for hit in all_hits[:40]:
        md_lines.append(
            f"- `{hit['category']}` [{hit['path']}:{hit['line']}] `{hit['text']}`"
        )
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit legacy SD usage in Bot_data_base.")
    parser.add_argument("--source-prd", default=DEFAULT_SOURCE_PRD)
    parser.add_argument("--output-json", default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", default=DEFAULT_OUTPUT_MD)
    args = parser.parse_args()

    payload = run_audit_legacy_sd_usage(
        source_prd=args.source_prd,
        output_json=Path(args.output_json),
        output_md=Path(args.output_md),
    )
    summary = {
        "schema_version": payload["schema_version"],
        "source_prd": payload["source_prd"],
        "generated_at": payload["generated_at"],
        "files_scanned_count": payload["files_scanned_count"],
        "sd_mentions_total": payload["sd_mentions_total"],
        "active_mentions_total": payload["active_mentions_total"],
        "categories": payload["categories"],
    }
    print(json.dumps(summary, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
