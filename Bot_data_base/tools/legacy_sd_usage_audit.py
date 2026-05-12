from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_SOURCE_PRD = "PRD-046.0.7-HF1"
PATTERNS = [
    "sd_level",
    "SD_LEVELS_ORDER",
    "spiral",
    "spiral_dynamics",
    "GREEN",
    "BLUE",
    "YELLOW",
    "RED",
    "ORANGE",
    "BEIGE",
    "PURPLE",
    "TURQUOISE",
    "UNCERTAIN",
]
ACTIVE_SD_PATTERNS = [
    'where_filter["sd_level"]',
    "_sd_int_to_names(",
    "SD_LEVELS_ORDER",
    "SD-filter fallback",
    "SD‑распределение",
    "<th>SD</th>",
]
TARGET_FILES = [
    "Bot_data_base/api/routes/query.py",
    "Bot_data_base/api/schemas.py",
    "Bot_data_base/web_ui/index.html",
    "Bot_data_base/web_ui/registry.html",
    "Bot_data_base/web_ui/static/app.js",
    "Bot_data_base/web_ui/static/registry.js",
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _save_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _save_markdown(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _scan_file(path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not path.exists():
        missing = [{"line": 0, "pattern": "file_missing", "text": str(path)}]
        return missing, []
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    hits: list[dict[str, Any]] = []
    active_hits: list[dict[str, Any]] = []
    for idx, line in enumerate(lines, start=1):
        for pattern in PATTERNS:
            if re.search(re.escape(pattern), line):
                hits.append({"line": idx, "pattern": pattern, "text": line.strip()[:240]})
        for pattern in ACTIVE_SD_PATTERNS:
            if pattern in line:
                active_hits.append({"line": idx, "pattern": pattern, "text": line.strip()[:240]})
    return hits, active_hits


def run_legacy_sd_usage_audit(*, source_prd: str, output_json: Path, output_md: Path) -> dict[str, Any]:
    cwd = Path.cwd()
    if (cwd / "Bot_data_base").exists():
        root = cwd
    elif cwd.name == "Bot_data_base" and (cwd / "api").exists():
        root = cwd.parent
    else:
        root = cwd
    files_payload: list[dict[str, Any]] = []
    active_hits = 0
    for rel_path in TARGET_FILES:
        full_path = root / rel_path
        hits, active = _scan_file(full_path)
        active_hits += len(active)
        files_payload.append(
            {
                "path": rel_path,
                "exists": full_path.exists(),
                "hit_count": len(hits),
                "active_hit_count": len(active),
                "hits": hits,
                "active_hits": active,
            }
        )

    query_hits = next((item for item in files_payload if item["path"].endswith("api/routes/query.py")), {})
    ui_hits = [
        item for item in files_payload if item["path"].startswith("Bot_data_base/web_ui/")
    ]
    ui_hit_count = sum(item.get("active_hit_count", 0) for item in ui_hits)

    payload = {
        "schema_version": "legacy_sd_usage_report_v1",
        "source_prd": source_prd,
        "generated_at": _utc_now(),
        "files_scanned_count": len(files_payload),
        "active_legacy_sd_hits_count": active_hits,
        "api_query_legacy_hits_count": int(query_hits.get("active_hit_count", 0) or 0),
        "ui_legacy_hits_count": ui_hit_count,
        "legacy_sd_filter_still_active": int(query_hits.get("active_hit_count", 0) or 0) > 0,
        "files": files_payload,
    }
    _save_json(output_json, payload)

    md_lines = [
        f"# {source_prd} LEGACY SD DECOMMISSION REPORT",
        "",
        "## Summary",
        f"- files_scanned_count: `{payload['files_scanned_count']}`",
        f"- active_legacy_sd_hits_count: `{payload['active_legacy_sd_hits_count']}`",
        f"- api_query_legacy_hits_count: `{payload['api_query_legacy_hits_count']}`",
        f"- ui_legacy_hits_count: `{payload['ui_legacy_hits_count']}`",
        f"- legacy_sd_filter_still_active: `{payload['legacy_sd_filter_still_active']}`",
        "",
        "## Files",
    ]
    for file_row in files_payload:
        md_lines.append(f"- `{file_row['path']}`: `{file_row['hit_count']}` hits")
    md_lines.extend(
        [
            "",
            "## Manual UI Checklist",
            "- Dashboard: SD block removed: yes/no",
            "- Dashboard: Chroma count visible: yes/no",
            "- Dashboard: Sources count visible: yes/no",
            "- Registry: SD column removed: yes/no",
            "- Registry: zero-block sources visible/classified: yes/no",
            "",
        ]
    )
    _save_markdown(output_md, "\n".join(md_lines))
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit active legacy SD usage in BotDB admin/API surfaces.")
    parser.add_argument(
        "--output-json",
        default="TO_DO_LIST/logs/PRD-046.0.7-HF1/legacy_sd_usage_report.json",
    )
    parser.add_argument(
        "--output-md",
        default="TO_DO_LIST/reports/PRD-046.0.7-HF1_LEGACY_SD_DECOMMISSION_REPORT.md",
    )
    parser.add_argument("--source-prd", default=DEFAULT_SOURCE_PRD)
    args = parser.parse_args()

    payload = run_legacy_sd_usage_audit(
        source_prd=args.source_prd,
        output_json=Path(args.output_json),
        output_md=Path(args.output_md),
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
