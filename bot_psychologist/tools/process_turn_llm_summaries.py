#!/usr/bin/env python3
"""Process pending async per-turn LLM summaries."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from bot_agent.config import config
from bot_agent.conversation_memory import get_conversation_memory


def _resolve_provider(args: argparse.Namespace) -> str:
    if bool(args.mock):
        return "mock"
    value = str(args.provider or getattr(config, "TURN_LLM_SUMMARY_PROVIDER", "disabled") or "disabled").lower()
    return value


def _discover_user_ids() -> list[str]:
    memory_dir = Path(config.CACHE_DIR) / "conversations"
    if not memory_dir.exists():
        return []
    ids: list[str] = []
    for file in memory_dir.glob("*.json"):
        if file.is_file():
            ids.append(file.stem)
    return sorted(set(ids))


async def _process_for_user(user_id: str, limit: int, provider: str) -> dict[str, Any]:
    memory = get_conversation_memory(user_id=user_id)
    stats = await memory.process_pending_turn_summaries(limit=limit, provider=provider)
    return {"user_id": user_id, **stats}


async def _main_async(args: argparse.Namespace) -> int:
    provider = _resolve_provider(args)
    if provider == "openai" and not bool(args.confirm):
        print("[ERROR] openai provider requires --confirm")
        return 2

    user_ids = [str(args.user_id).strip()] if args.user_id else _discover_user_ids()
    if not user_ids:
        print(json.dumps({"status": "ok", "processed_users": 0, "items": []}, ensure_ascii=False))
        return 0

    items: list[dict[str, Any]] = []
    for user_id in user_ids:
        item = await _process_for_user(user_id=user_id, limit=int(args.limit), provider=provider)
        items.append(item)

    payload = {
        "status": "ok",
        "provider": provider,
        "processed_users": len(items),
        "items": items,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Process pending turn LLM summaries.")
    parser.add_argument("--limit", type=int, default=10, help="Max pending summaries per user")
    parser.add_argument("--provider", type=str, default=None, help="Provider: openai|mock|disabled")
    parser.add_argument("--mock", action="store_true", help="Shortcut for --provider mock")
    parser.add_argument("--confirm", action="store_true", help="Required for provider=openai")
    parser.add_argument("--user-id", type=str, default=None, help="Process only one user_id")
    args = parser.parse_args()
    return asyncio.run(_main_async(args))


if __name__ == "__main__":
    raise SystemExit(main())
