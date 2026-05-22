from __future__ import annotations

from pathlib import Path
import sys

CURRENT_FILE = Path(__file__).resolve()
BOT_PSYCHOLOGIST_ROOT = CURRENT_FILE.parents[2]
if str(BOT_PSYCHOLOGIST_ROOT) not in sys.path:
    sys.path.insert(0, str(BOT_PSYCHOLOGIST_ROOT))

from bot_agent.multiagent.context_assembly import build_context_assembly_package_v1
from bot_agent.multiagent.contracts.memory_bundle import MemoryBundle, UserProfile
from bot_agent.multiagent.contracts.thread_state import ThreadState
from bot_agent.multiagent.contracts.writer_contract import WriterContract


def test_hf2_writer_contract_prompt_contains_knowledge() -> None:
    bundle = MemoryBundle(
        conversation_context="",
        rag_query="что такое нейросталкинг",
        user_profile=UserProfile(),
        knowledge_rag_hits=[{"chunk_id": "k1", "content": "Нейросталкинг — форма цифрового преследования.", "score": 0.09}],
        has_relevant_knowledge=True,
    )
    thread_state = ThreadState(thread_id="t1", user_id="u1", core_direction="support", phase="explore")
    package = build_context_assembly_package_v1(
        user_message="что такое нейросталкинг",
        thread_state=thread_state,
        memory_bundle=bundle,
    )
    contract = WriterContract(
        user_message="что такое нейросталкинг",
        thread_state=thread_state,
        memory_bundle=bundle,
        context_package=package,
    )

    ctx = contract.to_prompt_context()
    assert len(list(ctx.get("semantic_hits", []) or [])) >= 1
