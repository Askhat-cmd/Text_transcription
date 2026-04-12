#!/usr/bin/env python3
"""Measure conditional reranker activation ratio on eval queries."""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _load_eval_queries(path: Path, sample_size: int) -> list[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    queries = [str(item.get("query", "")).strip() for item in data if str(item.get("query", "")).strip()]
    if not queries:
        return []
    if sample_size <= len(queries):
        return queries[:sample_size]
    repeats = int(math.ceil(sample_size / len(queries)))
    return (queries * repeats)[:sample_size]


def evaluate_reranker_usage(
    eval_set_path: Path,
    sample_size: int = 100,
    top_k: int | None = None,
) -> dict[str, Any]:
    from bot_agent.answer_adaptive import _fallback_state_analysis
    from bot_agent.config import config
    from bot_agent.db_api_client import DBApiUnavailableError
    from bot_agent.decision import DecisionGate, detect_routing_signals
    from bot_agent.reranker_gate import should_rerank
    from bot_agent.retriever import get_retriever

    queries = _load_eval_queries(eval_set_path, sample_size)
    if not queries:
        raise ValueError(f"No queries found in eval set: {eval_set_path}")

    effective_top_k = int(top_k or config.RETRIEVAL_TOP_K or 5)

    retriever = get_retriever()
    if hasattr(retriever, "db_client") and retriever.db_client is not None:
        retriever.db_client.timeout = min(float(getattr(retriever.db_client, "timeout", 1.0)), 1.0)
        retriever.db_client.retries = 1

    api_available = True
    if hasattr(retriever, "_api_retrieve"):
        try:
            retriever._api_retrieve(query="healthcheck", top_k=1, author_id=None)
        except Exception:
            api_available = False
    if not api_available and hasattr(retriever, "_api_retrieve"):
        def _quick_unavailable(**_kwargs):
            raise DBApiUnavailableError("API unavailable during reranker usage eval", kind="connect")
        retriever._api_retrieve = _quick_unavailable

    decision_gate = DecisionGate()
    state_analysis = _fallback_state_analysis()
    reasons: Counter[str] = Counter()
    modes: Counter[str] = Counter()
    activations = 0

    flags = {
        "legacy_always_on": bool(config.VOYAGE_ENABLED and not config.RERANKER_ENABLED),
        "RERANKER_ENABLED": bool(config.RERANKER_ENABLED),
        "RERANKER_CONFIDENCE_THRESHOLD": float(config.RERANKER_CONFIDENCE_THRESHOLD),
        "RERANKER_MODE_WHITELIST": str(config.RERANKER_MODE_WHITELIST),
        "RERANKER_BLOCK_THRESHOLD": int(config.RERANKER_BLOCK_THRESHOLD),
    }

    for query in queries:
        retrieved = retriever.retrieve(query=query, top_k=effective_top_k)
        signals = detect_routing_signals(query, retrieved, state_analysis)
        routing = decision_gate.route(signals, user_stage="intermediate")
        run, reason = should_rerank(
            confidence_score=routing.confidence_score,
            routing_mode=routing.mode,
            retrieved_block_count=len(retrieved),
            flags=flags,
        )
        activations += 1 if run else 0
        reasons[reason] += 1
        modes[routing.mode] += 1

    total = len(queries)
    ratio = (activations / total) if total else 0.0
    return {
        "eval_set": str(eval_set_path),
        "sample_size": total,
        "top_k": effective_top_k,
        "reranker_calls": activations,
        "reranker_ratio": round(ratio, 4),
        "threshold": 0.25,
        "pass_gate": ratio <= 0.25,
        "reasons": dict(reasons),
        "modes": dict(modes),
        "flags": flags,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate conditional reranker call ratio.")
    parser.add_argument(
        "--eval-set",
        default="tests/eval/retrieval_eval_set.json",
        help="Path to retrieval eval set JSON.",
    )
    parser.add_argument("--sample-size", type=int, default=100, help="Number of requests to evaluate.")
    parser.add_argument(
        "--top-k",
        type=int,
        default=None,
        help="Retrieved block count passed to gate (default: RETRIEVAL_TOP_K).",
    )
    parser.add_argument(
        "--output",
        default="tests/eval/reranker_usage_metrics.json",
        help="Output JSON path.",
    )
    parser.add_argument("--enforce", action="store_true", help="Exit with code 1 if gate fails (>25%).")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    eval_set_path = (root / args.eval_set).resolve() if not Path(args.eval_set).is_absolute() else Path(args.eval_set)
    output_path = (root / args.output).resolve() if not Path(args.output).is_absolute() else Path(args.output)

    metrics = evaluate_reranker_usage(eval_set_path=eval_set_path, sample_size=args.sample_size, top_k=args.top_k)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[OK] reranker usage metrics saved: {output_path}")
    print(
        "[METRIC] calls={}/{} ratio={:.2%} threshold<=25% gate={}".format(
            metrics["reranker_calls"],
            metrics["sample_size"],
            float(metrics["reranker_ratio"]),
            "PASS" if metrics["pass_gate"] else "FAIL",
        )
    )
    if args.enforce and not metrics["pass_gate"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
