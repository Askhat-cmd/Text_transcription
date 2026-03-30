"""Progressive RAG block weighting persisted in SQLite."""

from __future__ import annotations

import argparse
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ProgressiveRAG:
    """
    Keep per-block weights based on positive feedback.

    Weights are applied after retrieval and before reranker.
    """

    def __init__(self, db_path: str = "data/bot_sessions.db"):
        self.db_path = str(db_path)
        db_file = Path(self.db_path)
        if self.db_path != ":memory:":
            db_file.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS block_weights (
                    block_id TEXT PRIMARY KEY,
                    weight REAL NOT NULL DEFAULT 1.0,
                    positive_hits INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL
                )
                """
            )

    def reset_weights(self) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM block_weights")

    def get_weight(self, block_id: str) -> float:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT weight FROM block_weights WHERE block_id = ?",
                (block_id,),
            ).fetchone()
        return float(row["weight"]) if row else 1.0

    def record_positive_feedback(self, block_id: str) -> float:
        current_weight = self.get_weight(block_id)
        new_weight = min(current_weight * 1.1, 2.0)
        now = _utc_now_iso()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO block_weights (block_id, weight, positive_hits, updated_at)
                VALUES (?, ?, 1, ?)
                ON CONFLICT(block_id) DO UPDATE SET
                    weight = excluded.weight,
                    positive_hits = block_weights.positive_hits + 1,
                    updated_at = excluded.updated_at
                """,
                (block_id, new_weight, now),
            )
        return new_weight

    def _extract_block_id(self, block) -> str:
        if isinstance(block, dict):
            return str(block.get("block_id", "")).strip()
        return str(getattr(block, "block_id", "")).strip()

    def rerank_by_weights(self, blocks: List) -> List:
        """Apply weights to retrieval result list and sort by weighted score."""
        weighted_items: List[Tuple[float, object]] = []
        for item in blocks or []:
            if isinstance(item, tuple) and len(item) == 2:
                block, score = item
                block_id = self._extract_block_id(block)
                weight = self.get_weight(block_id) if block_id else 1.0
                weighted_score = float(score) * weight
                weighted_items.append((weighted_score, (block, weighted_score)))
            elif isinstance(item, dict):
                block_id = self._extract_block_id(item)
                weight = self.get_weight(block_id) if block_id else 1.0
                original_score = float(item.get("score", 0.0) or 0.0)
                weighted_score = original_score * weight
                payload = dict(item)
                payload["progressive_weight"] = weight
                payload["score"] = weighted_score
                weighted_items.append((weighted_score, payload))
            else:
                weighted_items.append((0.0, item))

        weighted_items.sort(key=lambda pair: pair[0], reverse=True)
        return [item for _, item in weighted_items]


_PROGRESSIVE_RAG_CACHE: Dict[str, ProgressiveRAG] = {}


def get_progressive_rag(db_path: str = "data/bot_sessions.db") -> ProgressiveRAG:
    if db_path not in _PROGRESSIVE_RAG_CACHE:
        _PROGRESSIVE_RAG_CACHE[db_path] = ProgressiveRAG(db_path=db_path)
    return _PROGRESSIVE_RAG_CACHE[db_path]


def _main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Progressive RAG weights admin tool")
    parser.add_argument("--db-path", default="data/bot_sessions.db")
    parser.add_argument("--reset-weights", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)

    rag = ProgressiveRAG(db_path=args.db_path)
    if args.reset_weights:
        rag.reset_weights()
        print("OK: all progressive RAG weights reset to 1.0")
    else:
        print("No action. Use --reset-weights to clear all weights.")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())

