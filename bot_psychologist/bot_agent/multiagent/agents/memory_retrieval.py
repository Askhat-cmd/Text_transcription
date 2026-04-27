"""Memory + Retrieval agent for multi-agent runtime."""

from __future__ import annotations

import asyncio
import inspect
import logging
from typing import Any

from ..contracts.memory_bundle import MemoryBundle, SemanticHit, UserProfile
from ..contracts.thread_state import ThreadState
from .memory_retrieval_config import (
    CONVERSATION_TURNS_BY_PHASE,
    CONVERSATION_TURNS_DEFAULT,
    CONVERSATION_TURNS_NEW_THREAD,
    CORE_DIRECTION_MIN_LEN,
    RAG_MIN_SCORE,
    RAG_N_RESULTS,
    RAG_QUERY_MAX_LEN,
)


logger = logging.getLogger(__name__)


class MemoryRetrievalAgent:
    """Assembles conversation context, user profile, and RAG hits in parallel."""

    async def assemble(
        self,
        *,
        user_message: str,
        thread_state: ThreadState,
        user_id: str,
    ) -> MemoryBundle:
        n_turns = self._resolve_n_turns(thread_state)
        rag_query = self._build_rag_query(user_message, thread_state)

        results = await asyncio.gather(
            self._load_conversation(user_id, n_turns),
            self._load_profile(user_id),
            self._load_rag(rag_query),
            return_exceptions=True,
        )

        conversation_context = results[0] if not isinstance(results[0], Exception) else ""
        user_profile = results[1] if not isinstance(results[1], Exception) else UserProfile()
        raw_hits = results[2] if not isinstance(results[2], Exception) else []

        for label, result in zip(("conversation", "profile", "rag"), results):
            if isinstance(result, Exception):
                logger.warning("[MRA] %s load failed: %s", label, result)

        valid_hits = [h for h in raw_hits if isinstance(h, SemanticHit)]
        filtered_hits = [h for h in valid_hits if float(h.score) >= RAG_MIN_SCORE]
        filtered_hits.sort(key=lambda h: float(h.score), reverse=True)

        return MemoryBundle(
            conversation_context=conversation_context if isinstance(conversation_context, str) else "",
            rag_query=rag_query,
            user_profile=user_profile if isinstance(user_profile, UserProfile) else UserProfile(),
            semantic_hits=filtered_hits,
            retrieved_chunks=[h.content for h in filtered_hits],
            has_relevant_knowledge=len(filtered_hits) > 0,
            context_turns=n_turns,
        )

    async def update(
        self,
        *,
        user_id: str,
        user_message: str,
        assistant_response: str,
        thread_state: ThreadState,
    ) -> None:
        """Non-blocking memory writeback for completed orchestrator turn."""
        try:
            from ...conversation_memory import get_conversation_memory  # noqa: PLC0415

            memory = get_conversation_memory(user_id=user_id)
            add_turn = getattr(memory, "add_turn", None)
            if not callable(add_turn):
                logger.warning(
                    "[MRA] update skipped: add_turn missing user_id=%s thread_id=%s",
                    user_id,
                    thread_state.thread_id,
                )
                return

            kwargs: dict[str, Any] = {
                "user_input": user_message,
                "bot_response": assistant_response,
            }
            try:
                signature = inspect.signature(add_turn)
                if "metadata" in signature.parameters:
                    kwargs["metadata"] = {
                        "phase": thread_state.phase,
                        "response_mode": thread_state.response_mode,
                        "thread_id": thread_state.thread_id,
                        "continuity_score": thread_state.continuity_score,
                    }
            except Exception:
                # Defensive fallback: call with baseline arguments only.
                pass

            add_turn(**kwargs)
            logger.debug(
                "[MRA] update ok user_id=%s thread_id=%s",
                user_id,
                thread_state.thread_id,
            )
        except Exception as exc:
            logger.warning("[MRA] update failed (non-blocking): %s", exc)

    @staticmethod
    def _resolve_n_turns(thread_state: ThreadState) -> int:
        if thread_state.relation_to_thread == "new_thread":
            return CONVERSATION_TURNS_NEW_THREAD
        return CONVERSATION_TURNS_BY_PHASE.get(thread_state.phase, CONVERSATION_TURNS_DEFAULT)

    @staticmethod
    def _build_rag_query(user_message: str, thread_state: ThreadState) -> str:
        parts: list[str] = []
        text = (user_message or "").strip()
        if text:
            parts.append(text)

        core_direction = (thread_state.core_direction or "").strip()
        if len(core_direction) >= CORE_DIRECTION_MIN_LEN:
            parts.append(core_direction)

        if thread_state.open_loops:
            first_loop = str(thread_state.open_loops[0]).strip()
            if first_loop:
                parts.append(first_loop)

        return " ".join(parts)[:RAG_QUERY_MAX_LEN]

    @staticmethod
    async def _load_conversation(user_id: str, n_turns: int) -> str:
        try:
            from ...conversation_memory import get_conversation_memory  # noqa: PLC0415

            memory = get_conversation_memory(user_id=user_id)
            turns = memory.get_last_turns(n=n_turns)
            if not turns:
                return ""

            lines: list[str] = []
            for turn in turns:
                user_input = (turn.user_input or "").strip()
                bot_response = (turn.bot_response or "").strip()
                if user_input:
                    lines.append(f"User: {user_input}")
                if bot_response:
                    lines.append(f"Assistant: {bot_response}")
                lines.append("---")
            return "\n".join(lines)
        except Exception as exc:
            logger.warning("[MRA] conversation load error: %s", exc)
            return ""

    @staticmethod
    async def _load_profile(user_id: str) -> UserProfile:
        try:
            from ...conversation_memory import get_conversation_memory  # noqa: PLC0415

            memory = get_conversation_memory(user_id=user_id)
            summary = memory.get_summary()
            working_state = summary.get("working_state") or {}
            patterns = []
            if isinstance(working_state, dict):
                active_track = working_state.get("active_track")
                if active_track:
                    patterns.append(str(active_track))
                core_theme = working_state.get("core_theme")
                if core_theme:
                    patterns.append(str(core_theme))
                active_quadrant = working_state.get("active_quadrant")
                if active_quadrant:
                    patterns.append(str(active_quadrant))
            values = [str(x) for x in summary.get("primary_interests", [])]
            progress_notes = []
            if summary.get("conversation_summary"):
                progress_notes.append(str(summary.get("conversation_summary")))
            return UserProfile(
                patterns=patterns,
                triggers=[],
                values=values,
                progress_notes=progress_notes,
            )
        except Exception as exc:
            logger.warning("[MRA] profile load error: %s", exc)
            return UserProfile()

    @staticmethod
    async def _load_rag(query: str) -> list[SemanticHit]:
        try:
            from ...chroma_loader import ChromaLoader  # noqa: PLC0415

            if not query.strip():
                return []

            loader = ChromaLoader()
            results = loader.query_blocks(query_text=query, top_k=RAG_N_RESULTS)
            hits: list[SemanticHit] = []
            for item in results:
                block = None
                score = 0.0
                if isinstance(item, tuple) and len(item) >= 2:
                    block, score = item[0], float(item[1] or 0.0)
                elif isinstance(item, dict):
                    score = float(item.get("score", 0.0) or 0.0)
                if block is not None:
                    chunk_id = str(getattr(block, "block_id", ""))
                    content = str(getattr(block, "content", "") or "")
                    source = str(getattr(block, "document_title", "") or "unknown")
                else:
                    chunk_id = str(item.get("id", "")) if isinstance(item, dict) else ""
                    content = str(item.get("content", "")) if isinstance(item, dict) else ""
                    source = (
                        str(item.get("source", item.get("collection", "unknown")))
                        if isinstance(item, dict)
                        else "unknown"
                    )
                hits.append(
                    SemanticHit(
                        chunk_id=chunk_id,
                        content=content,
                        source=source,
                        score=score,
                    )
                )
            return hits
        except Exception as exc:
            logger.warning("[MRA] rag load error: %s", exc)
            return []


memory_retrieval_agent = MemoryRetrievalAgent()
