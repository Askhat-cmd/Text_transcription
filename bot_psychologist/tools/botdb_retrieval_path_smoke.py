from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bot_agent.config import config
from bot_agent.retriever import SimpleRetriever


SMOKE_PROMPTS = [
    "я всё время стараюсь быть лучше и не могу остановиться",
    "я злюсь на себя, потому что опять всё откладываю",
    "мне пусто и нет сил, не хочу анализа",
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _preview(text: str, limit: int = 160) -> str:
    cleaned = " ".join(str(text or "").strip().split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: max(0, limit - 1)].rstrip() + "…"


def _summarize_hit(item: tuple[Any, float]) -> dict[str, Any]:
    block, score = item
    governance = getattr(block, "governance", {}) or {}
    return {
        "id": str(getattr(block, "block_id", "") or ""),
        "score": float(score or 0.0),
        "title": str(getattr(block, "title", "") or ""),
        "source_type": str(getattr(block, "source_type", "") or ""),
        "chunk_type": str(governance.get("chunk_type") or ""),
        "allowed_use": list(governance.get("allowed_use") or []),
        "safety_flags": list(governance.get("safety_flags") or []),
        "lens_family": list(governance.get("lens_family") or []),
        "not_for_direct_quote": bool("not_for_direct_quote" in (governance.get("safety_flags") or [])),
        "content_preview": _preview(str(getattr(block, "content", "") or "")),
    }


def run_smoke(*, api_base_url: str, top_k: int) -> dict[str, Any]:
    config.KNOWLEDGE_SOURCE = "api"
    config.BOT_DB_URL = api_base_url.rstrip("/")
    retriever = SimpleRetriever()

    rows: list[dict[str, Any]] = []
    api_path_ok = 0
    for prompt in SMOKE_PROMPTS:
        hits = retriever.retrieve(prompt, top_k=top_k)
        retrieval_debug = retriever.get_last_retrieval_debug()
        retrieval_source_used = str(retrieval_debug.get("retrieval_source_used") or "")
        if retrieval_source_used == "api" and len(hits) > 0:
            api_path_ok += 1
        rows.append(
            {
                "query": prompt,
                "retrieval_source_attempted": retrieval_debug.get("retrieval_source_attempted"),
                "retrieval_source_used": retrieval_source_used,
                "bot_db_circuit_open": bool(retrieval_debug.get("bot_db_circuit_open", False)),
                "bot_db_last_error_kind": retrieval_debug.get("bot_db_last_error_kind"),
                "bot_db_last_status_code": retrieval_debug.get("bot_db_last_status_code"),
                "knowledge_hits_count": len(hits),
                "top_hits": [_summarize_hit(item) for item in hits[:3]],
            }
        )

    fallback_used = any(str(row.get("retrieval_source_used")) != "api" for row in rows)
    circuit_open = any(bool(row.get("bot_db_circuit_open", False)) for row in rows)
    return {
        "generated_at": _utc_now(),
        "api_base_url": api_base_url.rstrip("/"),
        "botdb_api_attempted": all(row.get("retrieval_source_attempted") == "api" for row in rows),
        "botdb_api_status": "ok" if api_path_ok >= 2 else "degraded",
        "retrieval_source": "botdb_api" if api_path_ok >= 2 else "fallback_or_mixed",
        "fallback_used": fallback_used,
        "circuit_breaker_open": circuit_open,
        "knowledge_hits_count": [int(row.get("knowledge_hits_count") or 0) for row in rows],
        "queries": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="BotDB retrieval path smoke for multiagent runtime.")
    parser.add_argument("--api-base-url", default="http://127.0.0.1:8003")
    parser.add_argument("--top-k", type=int, default=4)
    parser.add_argument(
        "--output",
        default="TO_DO_LIST/logs/PRD-046.0.4.3/bot_retrieval_path_smoke.json",
    )
    args = parser.parse_args()

    payload = run_smoke(api_base_url=args.api_base_url, top_k=max(1, int(args.top_k)))
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
