from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


SMOKE_QUERIES = [
    "я всё время стараюсь быть лучше и не могу остановиться",
    "я злюсь на себя, потому что опять не сделал обещанное",
    "я чувствую вину, когда выбираю себя",
    "нет сил, не хочу анализа, просто поддержи",
    "я боюсь показать проект и снова хочу отложить",
    "я раздражаюсь на близкого человека сильнее, чем ситуация того стоит",
]

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _preview(text: str, limit: int = 160) -> str:
    cleaned = " ".join(str(text or "").strip().split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: max(0, limit - 1)].rstrip() + "…"


def _http_json(method: str, url: str, payload: dict[str, Any] | None = None, timeout: float = 10.0) -> dict[str, Any]:
    body = None
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
    req = Request(url=url, data=body, method=method, headers={"Content-Type": "application/json"})
    try:
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            parsed = json.loads(raw) if raw else None
            return {"ok": True, "status_code": int(resp.status), "body": parsed, "error": None}
    except HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            body_data: Any = json.loads(raw) if raw else None
        except Exception:
            body_data = {"raw_text": raw[:500]}
        return {"ok": False, "status_code": int(exc.code), "body": body_data, "error": str(exc)}
    except URLError as exc:
        return {"ok": False, "status_code": None, "body": None, "error": str(exc)}
    except Exception as exc:  # pragma: no cover - defensive path
        return {"ok": False, "status_code": None, "body": None, "error": str(exc)}


def _normalize_query_row(query: str, response: dict[str, Any]) -> dict[str, Any]:
    body = response.get("body") if isinstance(response.get("body"), dict) else {}
    chunks = body.get("chunks") if isinstance(body, dict) else []
    if not isinstance(chunks, list):
        chunks = []
    top_hits = []
    for chunk in chunks[:3]:
        governance = chunk.get("governance") if isinstance(chunk, dict) else {}
        governance = governance if isinstance(governance, dict) else {}
        chunking_quality = governance.get("chunking_quality") if isinstance(governance.get("chunking_quality"), dict) else {}
        enrichment = governance.get("llm_enrichment") if isinstance(governance.get("llm_enrichment"), dict) else {}
        top_hits.append(
            {
                "id": chunk.get("chunk_id"),
                "score_or_distance": chunk.get("score"),
                "source_title": chunk.get("block_title"),
                "chapter_title": chunk.get("block_title"),
                "chunk_index": None,
                "chunk_type": governance.get("chunk_type"),
                "allowed_use": governance.get("allowed_use") or [],
                "safety_flags": governance.get("safety_flags") or [],
                "lens_family": governance.get("lens_family") or [],
                "not_for_direct_quote": governance.get("not_for_direct_quote"),
                "source_style_not_user_facing": governance.get("source_style_not_user_facing"),
                "boundary_confidence": None,
                "mixed_intent_severity": chunking_quality.get("mixed_intent_severity"),
                "heading_path_text": None,
                "content_preview": _preview(chunk.get("content") or ""),
                "llm_enrichment_summary": governance.get("llm_enrichment_summary") or enrichment.get("summary"),
                "llm_enrichment_tags": governance.get("llm_enrichment_tags") or enrichment.get("tags") or [],
                "llm_enrichment_use_when": governance.get("llm_enrichment_use_when") or enrichment.get("use_when") or [],
                "llm_enrichment_avoid_when": governance.get("llm_enrichment_avoid_when") or enrichment.get("avoid_when") or [],
                "llm_enrichment_confidence": governance.get("llm_enrichment_confidence")
                if governance.get("llm_enrichment_confidence") is not None
                else enrichment.get("confidence"),
                "llm_enrichment_review_status": governance.get("llm_enrichment_review_status")
                or enrichment.get("review_status"),
                "llm_enrichment_needs_human_review": governance.get("llm_enrichment_needs_human_review")
                if governance.get("llm_enrichment_needs_human_review") is not None
                else enrichment.get("needs_human_review"),
            }
        )
    return {
        "query": query,
        "status": "ok" if bool(response.get("ok")) else "error",
        "http_status": response.get("status_code"),
        "error": response.get("error"),
        "hits_count": len(chunks),
        "top_hits": top_hits,
    }


def run_smoke(*, api_base_url: str, top_k: int) -> dict[str, Any]:
    api_base = api_base_url.rstrip("/")
    status_resp = _http_json("GET", f"{api_base}/api/status/")
    registry_resp = _http_json("GET", f"{api_base}/api/registry/")
    query_rows = []
    for query in SMOKE_QUERIES:
        query_resp = _http_json(
            "POST",
            f"{api_base}/api/query/",
            payload={"query": query, "top_k": top_k, "pre_filter_k": max(10, top_k * 2), "use_rerank": False},
        )
        query_rows.append(_normalize_query_row(query, query_resp))
    return {
        "generated_at": _utc_now(),
        "api_base_url": api_base,
        "api_status": {"status_code": status_resp.get("status_code"), "ok": status_resp.get("ok"), "error": status_resp.get("error")},
        "api_registry": {"status_code": registry_resp.get("status_code"), "ok": registry_resp.get("ok"), "error": registry_resp.get("error")},
        "query_smoke": query_rows,
        "query_hits_positive": sum(1 for row in query_rows if int(row.get("hits_count") or 0) > 0),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Sanitized API smoke for /api/status, /api/registry, /api/query.")
    parser.add_argument("--api-base-url", default="http://127.0.0.1:8003")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--output-dir", default="TO_DO_LIST/logs/PRD-046.0.4.3")
    args = parser.parse_args()

    payload = run_smoke(api_base_url=args.api_base_url, top_k=max(1, int(args.top_k)))
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "api_status_snapshot.json").write_text(
        json.dumps(payload.get("api_status"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_dir / "api_registry_snapshot.json").write_text(
        json.dumps(payload.get("api_registry"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_dir / "api_query_smoke_snapshot.json").write_text(
        json.dumps(payload.get("query_smoke"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
