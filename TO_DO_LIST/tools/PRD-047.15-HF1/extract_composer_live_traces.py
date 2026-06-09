from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
PRD_ID = "PRD-047.15-HF1"
LOG_DIR = ROOT / "TO_DO_LIST" / "logs" / PRD_ID
OUT_JSON = LOG_DIR / "live_trace_inventory.json"
OUT_MD = LOG_DIR / "live_trace_inventory.md"
SEARCH_ROOTS = [ROOT / "TO_DO_LIST" / "logs", ROOT / "bot_psychologist" / "logs"]
TERMS = [
    "contextual_retrieval_query_composer",
    "retrieval_query_source",
    "composed_retrieval_query",
    "retrieval_need",
    "retrieval_action",
    "writer_can_ignore_rag",
    "final_answer_acceptance_gate",
]
TEXT_SUFFIXES = {".json", ".md", ".txt", ".log", ".jsonl"}
MAX_FILE_BYTES = 5_000_000


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _scan_file(path: Path) -> dict[str, Any] | None:
    try:
        if path.suffix.lower() not in TEXT_SUFFIXES or path.stat().st_size > MAX_FILE_BYTES:
            return None
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None
    matched_terms = [term for term in TERMS if term in text]
    if not matched_terms:
        return None
    rel = path.relative_to(ROOT).as_posix()
    live_hint = any(marker in rel.lower() for marker in ("live", "turn_evidence", "raw_trace", "web_chat", "browser"))
    return {"path": rel, "matched_terms": matched_terms, "live_hint": live_hint}


def run(mode: str) -> dict[str, Any]:
    del mode
    matches: list[dict[str, Any]] = []
    for root in SEARCH_ROOTS:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.is_file():
                item = _scan_file(path)
                if item:
                    matches.append(item)
    live_candidates = [item for item in matches if item["live_hint"]]
    status = "available" if live_candidates else "not_available"
    payload = {
        "prd_id": PRD_ID,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "live_trace_status": status,
        "matches_count": len(matches),
        "live_candidates_count": len(live_candidates),
        "matches": matches[:200],
        "live_candidates": live_candidates[:100],
    }
    _write_json(OUT_JSON, payload)
    lines = [
        "# PRD-047.15-HF1 Live Trace Inventory",
        "",
        f"- live_trace_status: `{status}`",
        f"- matches_count: `{len(matches)}`",
        f"- live_candidates_count: `{len(live_candidates)}`",
        "",
        "| Path | Live hint | Terms |",
        "| --- | --- | --- |",
    ]
    for item in matches[:200]:
        lines.append(f"| {item['path']} | {item['live_hint']} | {', '.join(item['matched_terms'])} |")
    _write_text(OUT_MD, "\n".join(lines) + "\n")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", default="best_effort", choices=["best_effort"])
    args = parser.parse_args()
    payload = run(args.mode)
    print(json.dumps({"status": "ok", "live_trace_status": payload["live_trace_status"], "matches_count": payload["matches_count"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
