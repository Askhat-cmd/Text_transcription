"""Minimal multi-agent orchestrator for PRD-017 bootstrap."""

from __future__ import annotations

import asyncio
import logging

from .agents.memory_retrieval import memory_retrieval_agent
from .agents.state_analyzer import state_analyzer_agent
from .agents.thread_manager import thread_manager_agent
from .contracts.memory_bundle import MemoryBundle
from .thread_storage import thread_storage


logger = logging.getLogger(__name__)


class MultiAgentOrchestrator:
    """Coordinates StateSnapshot -> ThreadManager -> lightweight response."""

    async def run(self, *, query: str, user_id: str) -> dict:
        current_thread = thread_storage.load_active(user_id)
        archived_threads = thread_storage.load_archived(user_id)

        state_snapshot = await state_analyzer_agent.analyze(
            user_message=query,
            previous_thread=current_thread,
        )
        updated_thread = await thread_manager_agent.update(
            user_message=query,
            state_snapshot=state_snapshot,
            user_id=user_id,
            current_thread=current_thread,
            archived_threads=archived_threads,
        )
        if updated_thread.relation_to_thread == "new_thread" and current_thread is not None:
            thread_storage.archive_thread(current_thread, reason="new_thread")
        thread_storage.save_active(updated_thread)

        memory_bundle = await memory_retrieval_agent.assemble(
            user_message=query,
            thread_state=updated_thread,
            user_id=user_id,
        )
        answer = self._build_answer(query=query, thread=updated_thread, memory_bundle=memory_bundle)

        asyncio.create_task(
            memory_retrieval_agent.update(
                user_id=user_id,
                user_message=query,
                assistant_response=answer,
                thread_state=updated_thread,
            )
        )

        return {
            "status": "ok",
            "answer": answer,
            "thread_id": updated_thread.thread_id,
            "phase": updated_thread.phase,
            "response_mode": updated_thread.response_mode,
            "relation_to_thread": updated_thread.relation_to_thread,
            "continuity_score": updated_thread.continuity_score,
            "debug": {
                "multiagent_enabled": True,
                "thread_manager_model": "heuristic",
                "nervous_state": state_snapshot.nervous_state,
                "intent": state_snapshot.intent,
                "safety_flag": state_snapshot.safety_flag,
                "confidence": state_snapshot.confidence,
                "has_relevant_knowledge": memory_bundle.has_relevant_knowledge,
                "context_turns": memory_bundle.context_turns,
                "semantic_hits_count": len(memory_bundle.semantic_hits),
            },
        }

    def run_sync(self, *, query: str, user_id: str) -> dict:
        return asyncio.run(self.run(query=query, user_id=user_id))

    def _build_answer(self, *, query: str, thread, memory_bundle: MemoryBundle) -> str:
        _ = memory_bundle
        if thread.response_mode == "safe_override":
            return "I hear you. Lets slow down and keep this safe one step at a time."
        if thread.response_mode == "practice":
            return "I hear your request. Lets take one concrete next step and check the result."
        if thread.response_mode == "validate":
            return "I hear you. We can stay in contact and move at your pace."
        return f"I hear your topic: {query.strip()[:120]}"


orchestrator = MultiAgentOrchestrator()
