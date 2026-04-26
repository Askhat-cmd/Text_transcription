"""Minimal multi-agent orchestrator for PRD-017 bootstrap."""

from __future__ import annotations

import asyncio
import logging

from .agents.memory_retrieval import memory_retrieval_agent
from .agents.state_analyzer import state_analyzer_agent
from .agents.thread_manager import thread_manager_agent
from .agents.validator_agent import validator_agent
from .agents.writer_agent import writer_agent
from .contracts.writer_contract import WriterContract
from .thread_storage import thread_storage


logger = logging.getLogger(__name__)


class MultiAgentOrchestrator:
    """Coordinates StateSnapshot -> ThreadManager -> Memory -> Writer."""

    @staticmethod
    def _has_cyrillic(text: str) -> bool:
        return any(("А" <= ch <= "я") or ch in {"Ё", "ё"} for ch in text)

    @staticmethod
    def _looks_like_mojibake(text: str) -> bool:
        # Typical UTF-8->cp1251 mojibake contains many capital 'Р'/'С' markers.
        marker_count = text.count("Р") + text.count("С")
        return marker_count >= 3 and marker_count > max(2, len(text) // 10)

    def _normalize_query(self, query: str) -> str:
        if not query:
            return query

        if self._looks_like_mojibake(query):
            try:
                repaired = query.encode("cp1251").decode("utf-8")
                if self._has_cyrillic(repaired) and not self._looks_like_mojibake(repaired):
                    logger.warning("[MULTIAGENT] query mojibake repaired")
                    return repaired
            except (UnicodeEncodeError, UnicodeDecodeError):
                pass

        # Don't touch already-correct Cyrillic text.
        if self._has_cyrillic(query):
            return query

        # Attempt to repair cp1251/latin-1 mojibake from shell environments.
        try:
            repaired = query.encode("latin-1").decode("cp1251")
        except (UnicodeEncodeError, UnicodeDecodeError):
            return query

        if self._has_cyrillic(repaired):
            logger.warning("[MULTIAGENT] query encoding repaired")
            return repaired
        return query

    async def run(self, *, query: str, user_id: str) -> dict:
        query = self._normalize_query(query)

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

        writer_contract = WriterContract(
            user_message=query,
            thread_state=updated_thread,
            memory_bundle=memory_bundle,
        )
        draft_answer = await writer_agent.write(writer_contract)
        validation_result = validator_agent.validate(draft_answer, writer_contract)
        if validation_result.is_blocked:
            final_answer = validation_result.safe_replacement or draft_answer
        else:
            final_answer = draft_answer

        asyncio.create_task(
            memory_retrieval_agent.update(
                user_id=user_id,
                user_message=query,
                assistant_response=final_answer,
                thread_state=updated_thread,
            )
        )

        return {
            "status": "ok",
            "answer": final_answer,
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
                "validator_blocked": validation_result.is_blocked,
                "validator_block_reason": validation_result.block_reason,
                "validator_quality_flags": validation_result.quality_flags,
            },
        }

    def run_sync(self, *, query: str, user_id: str) -> dict:
        return asyncio.run(self.run(query=query, user_id=user_id))


orchestrator = MultiAgentOrchestrator()
