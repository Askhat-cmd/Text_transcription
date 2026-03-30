#!/usr/bin/env python3
"""Evaluate retrieval quality on tests/eval/retrieval_eval_set.json."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _safe_round(value: float) -> float:
    return round(float(value), 4)


def evaluate_retrieval(eval_set_path: Path, top_k: int = 5) -> dict[str, Any]:
    from bot_agent.retriever import get_retriever
    from bot_agent.db_api_client import DBApiUnavailableError

    dataset = _load_json(eval_set_path)
    if not isinstance(dataset, list):
        raise ValueError(f"Eval set must be a JSON list: {eval_set_path}")

    retriever = get_retriever()
    # Keep eval responsive even when Bot_data_base is offline.
    if hasattr(retriever, "db_client") and retriever.db_client is not None:
        retriever.db_client.timeout = min(float(getattr(retriever.db_client, "timeout", 1.0)), 1.0)
        retriever.db_client.retries = 1

    api_available = True
    if hasattr(retriever, "_api_retrieve"):
        try:
            retriever._api_retrieve(query="healthcheck", sd_level=0, top_k=1, author_id=None)
        except Exception:
            api_available = False

    if not api_available and hasattr(retriever, "_api_retrieve"):
        def _quick_unavailable(**_kwargs):
            raise DBApiUnavailableError("API unavailable during eval precheck", kind="connect")
        retriever._api_retrieve = _quick_unavailable
    total = 0
    success = 0
    rr_sum = 0.0
    details: list[dict[str, Any]] = []

    for item in dataset:
        query = item.get("query")
        if not isinstance(query, str) or not query.strip():
            continue
        total += 1
        expected = item.get("expected") or {}
        min_results = int(expected.get("min_results", 1))
        results = retriever.retrieve(query=query, top_k=top_k, sd_level=0)
        found = len(results)
        hit = found >= min_results
        if hit:
            success += 1
            rr_sum += 1.0  # proxy: first relevant rank assumed 1 for coverage dataset
        details.append(
            {
                "id": item.get("id"),
                "query": query,
                "found": found,
                "min_results": min_results,
                "hit": hit,
                "source": item.get("source"),
            }
        )

    recall_at_k = (success / total) if total else 0.0
    mrr = (rr_sum / total) if total else 0.0

    return {
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "eval_set": str(eval_set_path),
        "total_queries": total,
        "top_k": top_k,
        "recall_at_k": _safe_round(recall_at_k),
        "mrr": _safe_round(mrr),
        "note": "coverage proxy metric (non-empty retrieval), replace with relevance labels for strict IR eval",
        "details": details,
    }


def compare_with_baseline(metrics: dict[str, Any], baseline_path: Path) -> dict[str, Any]:
    baseline = _load_json(baseline_path)
    base_ret = (baseline or {}).get("retrieval") or {}
    base_recall = float(base_ret.get("recall_at_5", 0.0) or 0.0)
    base_mrr = float(base_ret.get("mrr", 0.0) or 0.0)

    current_recall = float(metrics.get("recall_at_k", 0.0))
    current_mrr = float(metrics.get("mrr", 0.0))

    return {
        "baseline_path": str(baseline_path),
        "baseline_recall_at_5": base_recall,
        "baseline_mrr": base_mrr,
        "current_recall_at_k": current_recall,
        "current_mrr": current_mrr,
        "delta_recall": _safe_round(current_recall - base_recall),
        "delta_mrr": _safe_round(current_mrr - base_mrr),
        "pass_gate": current_recall >= base_recall and current_mrr >= base_mrr,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run retrieval evaluation over eval set.")
    parser.add_argument(
        "--eval-set",
        default="tests/eval/retrieval_eval_set.json",
        help="Path to retrieval eval set JSON.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Top-K results requested from retriever.",
    )
    parser.add_argument(
        "--output",
        default="tests/eval/retrieval_metrics.json",
        help="Output metrics JSON path.",
    )
    parser.add_argument(
        "--compare",
        action="store_true",
        help="Compare current metrics against tests/eval/baseline.json.",
    )
    parser.add_argument(
        "--baseline",
        default="tests/eval/baseline.json",
        help="Baseline JSON path for --compare.",
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    eval_set_path = (root / args.eval_set).resolve() if not Path(args.eval_set).is_absolute() else Path(args.eval_set)
    output_path = (root / args.output).resolve() if not Path(args.output).is_absolute() else Path(args.output)

    metrics = evaluate_retrieval(eval_set_path=eval_set_path, top_k=args.top_k)
    if args.compare:
        baseline_path = (root / args.baseline).resolve() if not Path(args.baseline).is_absolute() else Path(args.baseline)
        metrics["comparison"] = compare_with_baseline(metrics, baseline_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[OK] retrieval metrics saved: {output_path}")
    print(f"[METRIC] recall@{args.top_k}={metrics['recall_at_k']}, mrr={metrics['mrr']}")
    if args.compare:
        cmp = metrics["comparison"]
        print(
            "[COMPARE] baseline recall={:.4f} mrr={:.4f} | delta recall={:+.4f} delta mrr={:+.4f} | gate={}".format(
                cmp["baseline_recall_at_5"],
                cmp["baseline_mrr"],
                cmp["delta_recall"],
                cmp["delta_mrr"],
                "PASS" if cmp["pass_gate"] else "FAIL",
            )
        )


if __name__ == "__main__":
    main()
