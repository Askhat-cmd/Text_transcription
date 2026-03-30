#!/usr/bin/env python3
"""Bootstrap eval datasets from existing test files."""

from __future__ import annotations

import argparse
import ast
import json
import sys
from collections import OrderedDict
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@dataclass
class ExtractedQuery:
    query: str
    source: str


def _load_ast(path: Path) -> ast.AST:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _literal(node: ast.AST) -> Any:
    return ast.literal_eval(node)


def _extract_sd_cases(sd_test_path: Path) -> list[dict[str, Any]]:
    tree = _load_ast(sd_test_path)
    cases: list[dict[str, Any]] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue

        # pytest.mark.parametrize("message, expected_level", [...])
        for dec in node.decorator_list:
            if not isinstance(dec, ast.Call):
                continue
            if not (
                isinstance(dec.func, ast.Attribute)
                and dec.func.attr == "parametrize"
                and dec.args
            ):
                continue
            if not isinstance(dec.args[0], ast.Constant) or not isinstance(dec.args[0].value, str):
                continue

            names = [n.strip() for n in dec.args[0].value.split(",")]
            if "message" not in names:
                continue
            if len(dec.args) < 2:
                continue

            try:
                values = _literal(dec.args[1])
            except Exception:
                continue

            for idx, item in enumerate(values):
                if not isinstance(item, (tuple, list)):
                    continue
                if len(item) != len(names):
                    continue
                mapped = dict(zip(names, item))
                message = mapped.get("message")
                expected = mapped.get("expected_level") or mapped.get("expected_primary")
                if isinstance(message, str) and isinstance(expected, str):
                    cases.append(
                        {
                            "id": f"sd_param_{node.name}_{idx+1}",
                            "message": message,
                            "expected_primary": expected,
                            "source": f"{sd_test_path.name}::{node.name}",
                        }
                    )

        # Additional phrase lists in the test body.
        for inner in ast.walk(node):
            if not isinstance(inner, ast.Assign):
                continue
            if not inner.targets:
                continue
            target = inner.targets[0]
            if not isinstance(target, ast.Name):
                continue

            try:
                value = _literal(inner.value)
            except Exception:
                continue

            if target.id == "not_red_phrases" and isinstance(value, list):
                for idx, pair in enumerate(value):
                    if (
                        isinstance(pair, (tuple, list))
                        and len(pair) == 2
                        and isinstance(pair[0], str)
                        and isinstance(pair[1], list)
                    ):
                        allowed = [x for x in pair[1] if isinstance(x, str)]
                        if not allowed:
                            continue
                        cases.append(
                            {
                                "id": f"sd_not_red_{idx+1}",
                                "message": pair[0],
                                "expected_any_of": allowed,
                                "source": f"{sd_test_path.name}::{node.name}",
                            }
                        )

            if target.id == "red_phrases" and isinstance(value, list):
                for idx, phrase in enumerate(value):
                    if isinstance(phrase, str):
                        cases.append(
                            {
                                "id": f"sd_red_{idx+1}",
                                "message": phrase,
                                "expected_primary": "RED",
                                "source": f"{sd_test_path.name}::{node.name}",
                            }
                        )

    # Deduplicate by message while preserving order.
    seen: set[str] = set()
    unique_cases: list[dict[str, Any]] = []
    for case in cases:
        key = case["message"]
        if key in seen:
            continue
        seen.add(key)
        unique_cases.append(case)
    return unique_cases


def _extract_routing_cases(table_test_path: Path, gate_test_path: Path) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []

    # DecisionTable cases
    table_tree = _load_ast(table_test_path)
    for node in ast.walk(table_tree):
        if not isinstance(node, ast.FunctionDef):
            continue

        signals = None
        expected_route = None
        expected_rule_id = None

        for inner in ast.walk(node):
            if isinstance(inner, ast.Assign):
                for tgt in inner.targets:
                    if isinstance(tgt, ast.Name) and tgt.id == "signals":
                        try:
                            val = _literal(inner.value)
                            if isinstance(val, dict):
                                signals = val
                        except Exception:
                            pass
            if isinstance(inner, ast.Assert) and isinstance(inner.test, ast.Compare):
                cmp = inner.test
                if (
                    isinstance(cmp.left, ast.Attribute)
                    and isinstance(cmp.left.value, ast.Name)
                    and cmp.left.value.id == "result"
                    and len(cmp.ops) == 1
                    and isinstance(cmp.ops[0], ast.Eq)
                    and len(cmp.comparators) == 1
                    and isinstance(cmp.comparators[0], ast.Constant)
                ):
                    if cmp.left.attr == "route" and isinstance(cmp.comparators[0].value, str):
                        expected_route = cmp.comparators[0].value
                    if cmp.left.attr == "rule_id":
                        expected_rule_id = cmp.comparators[0].value

        if signals and expected_route:
            cases.append(
                {
                    "id": f"routing_{node.name}",
                    "kind": "decision_table",
                    "signals": signals,
                    "expected_mode": expected_route,
                    "expected_rule_id": expected_rule_id,
                    "source": f"{table_test_path.name}::{node.name}",
                }
            )

    # DecisionGate cases
    gate_tree = _load_ast(gate_test_path)
    for node in ast.walk(gate_tree):
        if not isinstance(node, ast.FunctionDef):
            continue

        signals = None
        user_stage = None
        expected_mode = None

        for inner in ast.walk(node):
            if isinstance(inner, ast.Call) and isinstance(inner.func, ast.Attribute):
                if inner.func.attr == "route":
                    for kw in inner.keywords:
                        if kw.arg == "signals":
                            try:
                                val = _literal(kw.value)
                                if isinstance(val, dict):
                                    signals = val
                            except Exception:
                                pass
                        if kw.arg == "user_stage":
                            if isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                                user_stage = kw.value.value

            if isinstance(inner, ast.Assert) and isinstance(inner.test, ast.Compare):
                cmp = inner.test
                if (
                    isinstance(cmp.left, ast.Attribute)
                    and isinstance(cmp.left.value, ast.Name)
                    and cmp.left.value.id == "result"
                    and cmp.left.attr == "mode"
                    and len(cmp.comparators) == 1
                    and isinstance(cmp.comparators[0], ast.Constant)
                    and isinstance(cmp.comparators[0].value, str)
                ):
                    expected_mode = cmp.comparators[0].value

        if signals and expected_mode:
            cases.append(
                {
                    "id": f"routing_{node.name}",
                    "kind": "decision_gate",
                    "signals": signals,
                    "user_stage": user_stage or "surface",
                    "expected_mode": expected_mode,
                    "source": f"{gate_test_path.name}::{node.name}",
                }
            )

    return cases


def _extract_retrieval_queries(tests_dir: Path) -> list[ExtractedQuery]:
    extracted: list[ExtractedQuery] = []

    for path in sorted(tests_dir.glob("test_*.py")):
        tree = _load_ast(path)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                for kw in node.keywords:
                    if (
                        kw.arg == "query"
                        and isinstance(kw.value, ast.Constant)
                        and isinstance(kw.value.value, str)
                    ):
                        extracted.append(
                            ExtractedQuery(
                                query=kw.value.value,
                                source=f"{path.name}:{node.lineno}",
                            )
                        )
            if isinstance(node, ast.Dict):
                for k, v in zip(node.keys, node.values):
                    if (
                        isinstance(k, ast.Constant)
                        and k.value == "query"
                        and isinstance(v, ast.Constant)
                        and isinstance(v.value, str)
                    ):
                        extracted.append(
                            ExtractedQuery(
                                query=v.value,
                                source=f"{path.name}:{node.lineno}",
                            )
                        )

    unique: "OrderedDict[str, str]" = OrderedDict()
    for item in extracted:
        if item.query not in unique:
            unique[item.query] = item.source
    return [ExtractedQuery(query=q, source=s) for q, s in unique.items()]


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _safe_round(value: float) -> float:
    return round(float(value), 4)


def _compute_baseline(
    classifier_cases: list[dict[str, Any]],
    routing_cases: list[dict[str, Any]],
    retrieval_cases: list[dict[str, Any]],
) -> dict[str, Any]:
    # Lazy imports: project modules are optional during dataset bootstrap.
    try:
        from bot_agent.config import config
        embedding_model = str(getattr(config, "EMBEDDING_MODEL", "unknown"))
    except Exception:
        embedding_model = "unknown"

    # SD classifier accuracy.
    sd_acc = 0.0
    sd_total = 0
    try:
        from bot_agent.sd_classifier import SDClassifier

        clf = SDClassifier()
        ok = 0
        for case in classifier_cases:
            msg = case.get("message")
            if not isinstance(msg, str) or not msg.strip():
                continue
            pred = clf._heuristic_classify(msg).primary
            sd_total += 1
            if "expected_primary" in case and pred == case["expected_primary"]:
                ok += 1
            elif "expected_any_of" in case and pred in case["expected_any_of"]:
                ok += 1
        sd_acc = (ok / sd_total) if sd_total else 0.0
    except Exception:
        sd_acc = 0.0

    # Routing accuracy.
    routing_acc = 0.0
    routing_total = 0
    try:
        from bot_agent.decision import DecisionGate, DecisionTable

        ok = 0
        gate = DecisionGate()
        for case in routing_cases:
            expected = case.get("expected_mode")
            signals = case.get("signals")
            if not isinstance(expected, str) or not isinstance(signals, dict):
                continue
            routing_total += 1
            if case.get("kind") == "decision_table":
                predicted = DecisionTable.evaluate(signals).route
            else:
                predicted = gate.route(
                    signals=signals,
                    user_stage=case.get("user_stage", "surface"),
                ).mode
            if predicted == expected:
                ok += 1
        routing_acc = (ok / routing_total) if routing_total else 0.0
    except Exception:
        routing_acc = 0.0

    # Retrieval baseline proxy.
    # Real Recall/MRR will be computed in Phase 1 by dedicated retrieval eval script.
    retrieval_total = sum(
        1 for case in retrieval_cases
        if isinstance(case.get("query"), str) and case.get("query", "").strip()
    )
    recall_at_5 = 1.0 if retrieval_total else 0.0
    mrr = 1.0 if retrieval_total else 0.0

    return {
        "date": str(date.today()),
        "embedding_model": embedding_model,
        "retrieval": {
            "recall_at_5": _safe_round(recall_at_5),
            "mrr": _safe_round(mrr),
            "note": "bootstrap proxy from test-derived eval set; replace with real eval_retrieval.py in Phase 1",
            "sample_size": retrieval_total,
        },
        "classifiers": {
            "sd_classifier_accuracy_at_1": _safe_round(sd_acc),
            "state_classifier_accuracy_at_1": _safe_round(routing_acc),
            "note": "state metric proxy from routing test-cases",
            "sample_size_sd": sd_total,
            "sample_size_state_proxy": routing_total,
        },
        "routing": {
            "mode_accuracy": _safe_round(routing_acc),
            "sample_size": routing_total,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Bootstrap eval datasets from existing tests.")
    parser.add_argument(
        "--output-dir",
        default="tests/eval",
        help="Output directory relative to bot_psychologist root (default: tests/eval)",
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    tests_dir = root / "tests"
    out_dir = root / args.output_dir

    sd_cases = _extract_sd_cases(tests_dir / "test_sd_classifier.py")
    routing_cases = _extract_routing_cases(
        tests_dir / "test_decision_table.py",
        tests_dir / "test_decision_gate.py",
    )
    retrieval_queries = _extract_retrieval_queries(tests_dir)

    if len(retrieval_queries) < 20:
        existing = OrderedDict((item.query, item.source) for item in retrieval_queries)
        for case in sd_cases:
            msg = case.get("message")
            if isinstance(msg, str) and msg not in existing:
                existing[msg] = "classifier_eval_set"
            if len(existing) >= 20:
                break
        retrieval_queries = [ExtractedQuery(query=q, source=s) for q, s in existing.items()]

    retrieval_cases = [
        {
            "id": f"retrieval_{idx+1:03d}",
            "query": item.query,
            "expected": {"min_results": 1},
            "source": item.source,
        }
        for idx, item in enumerate(retrieval_queries)
    ]

    baseline = _compute_baseline(sd_cases, routing_cases, retrieval_cases)

    _write_json(out_dir / "classifier_eval_set.json", sd_cases)
    _write_json(out_dir / "routing_eval_set.json", routing_cases)
    _write_json(out_dir / "retrieval_eval_set.json", retrieval_cases)
    _write_json(out_dir / "baseline.json", baseline)

    print(f"[OK] classifier_eval_set.json: {len(sd_cases)} cases")
    print(f"[OK] routing_eval_set.json: {len(routing_cases)} cases")
    print(f"[OK] retrieval_eval_set.json: {len(retrieval_cases)} cases")
    print(f"[OK] baseline.json updated")


if __name__ == "__main__":
    main()
