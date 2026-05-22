from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

CURRENT_FILE = Path(__file__).resolve()
BOT_PSYCHOLOGIST_ROOT = CURRENT_FILE.parents[1]
if str(BOT_PSYCHOLOGIST_ROOT) not in sys.path:
    sys.path.insert(0, str(BOT_PSYCHOLOGIST_ROOT))

from bot_agent.multiagent import creator_live_rag_delivery_hf2 as hf2
from bot_agent.multiagent.agents.memory_retrieval import memory_retrieval_agent
from bot_agent.multiagent.context_assembly import build_context_assembly_package_v1
from bot_agent.multiagent.contracts.thread_state import ThreadState
from bot_agent.multiagent.contracts.writer_contract import WriterContract


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


async def _run_memory_agent_probe(*, query: str, user_id: str) -> dict:
    thread_state = ThreadState(
        thread_id=f"hf2_probe_{user_id}",
        user_id=user_id,
        core_direction=query,
        phase="explore",
    )
    memory_bundle = await memory_retrieval_agent.assemble(
        user_message=query,
        thread_state=thread_state,
        user_id=user_id,
    )
    context_package = build_context_assembly_package_v1(
        user_message=query,
        thread_state=thread_state,
        memory_bundle=memory_bundle,
    )
    writer_contract = WriterContract(
        user_message=query,
        thread_state=thread_state,
        memory_bundle=memory_bundle,
        context_package=context_package,
    )
    prompt_context = writer_contract.to_prompt_context()
    return {
        "schema_version": "hf2_memory_agent_probe_v1",
        "query": query,
        "user_id": user_id,
        "rag_retrieval_trace": dict(memory_bundle.rag_retrieval_trace or {}),
        "knowledge_policy_trace": dict(memory_bundle.knowledge_policy_trace or {}),
        "memory_semantic_hits_count": len(memory_bundle.semantic_hits),
        "knowledge_rag_hits_count": len(memory_bundle.knowledge_rag_hits),
        "context_assembly_trace": context_package.trace.to_dict(),
        "context_assembly_knowledge_hits_count": len(context_package.knowledge_rag_hits),
        "writer_prompt_knowledge_hits_count": len(list(prompt_context.get("semantic_hits", []) or [])),
        "writer_prompt_context_preview": {
            "has_relevant_knowledge": bool(prompt_context.get("has_relevant_knowledge", False)),
            "semantic_hits_count": len(list(prompt_context.get("semantic_hits", []) or [])),
        },
    }


def run(args: argparse.Namespace) -> dict:
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.mode == "botdb":
        payload = hf2.probe_botdb_query(
            query=args.query,
            botdb_base_url=args.botdb_base_url,
        )
        _write_json(output_dir / "botdb_direct_query_probe.json", payload)
        return payload

    payload = asyncio.run(
        _run_memory_agent_probe(
            query=args.query,
            user_id=args.user_id,
        )
    )
    _write_json(output_dir / "memory_agent_delivery_probe.json", payload)
    _write_json(output_dir / "rag_score_policy_trace.json", dict(payload.get("rag_retrieval_trace", {})))
    return payload


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Probe BotDB and Memory retrieval chain for PRD-046.1.35-HF2")
    parser.add_argument("--mode", choices=["botdb", "memory-agent"], default="botdb")
    parser.add_argument("--query", required=True)
    parser.add_argument("--user-id", default="user_1772172411219_kamh0")
    parser.add_argument("--botdb-base-url", default="http://localhost:8003")
    parser.add_argument("--output-dir", default="TO_DO_LIST/logs/PRD-046.1.35-HF2")
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    payload = run(args)
    print(json.dumps(payload, ensure_ascii=True, indent=2))
    if args.mode == "botdb":
        return 0 if int(payload.get("botdb_http_status", 0)) == 200 else 2
    return 0 if int(payload.get("memory_semantic_hits_count", 0)) >= 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
