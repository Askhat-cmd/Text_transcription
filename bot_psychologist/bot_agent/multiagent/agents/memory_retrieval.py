"""Memory + Retrieval agent for multi-agent runtime."""

from __future__ import annotations

import asyncio
import inspect
import logging
from typing import Any

from ..contracts.memory_bundle import MemoryBundle, SemanticHit, UserProfile
from ..contracts.thread_state import ThreadState
from ..knowledge_policy import apply_knowledge_policy_v1
from .memory_retrieval_config import (
    CONVERSATION_TURNS_BY_PHASE,
    CONVERSATION_TURNS_DEFAULT,
    CONVERSATION_TURNS_NEW_THREAD,
    CORE_DIRECTION_MIN_LEN,
    RAG_LOW_SCORE_SALVAGE_ENABLED,
    RAG_LOW_SCORE_SALVAGE_MAX_HITS,
    RAG_LOW_SCORE_SALVAGE_MIN_TOP_SCORE,
    RAG_MIN_SCORE,
    RAG_N_RESULTS,
    RAG_QUERY_MAX_LEN,
    RAG_SCORE_POLICY_V1_ENABLED,
)


logger = logging.getLogger(__name__)


def _sanitize_query_preview(query: str, *, max_len: int = 160) -> str:
    normalized = " ".join((query or "").split())
    if len(normalized) <= max_len:
        return normalized
    return normalized[: max_len - 1].rstrip() + "…"


def rag_score_policy_v1(
    *,
    raw_hits: list[SemanticHit],
    rag_min_score: float,
    retrieval_source_used: str,
    query: str,
) -> dict[str, Any]:
    valid_hits = [hit for hit in list(raw_hits or []) if isinstance(hit, SemanticHit)]
    raw_scores = [float(hit.score) for hit in valid_hits]
    filtered_hits = [hit for hit in valid_hits if float(hit.score) >= float(rag_min_score)]
    filtered_hits.sort(
        key=lambda h: (1 if getattr(h, "governance", {}) else 0, float(h.score)),
        reverse=True,
    )

    trace: dict[str, Any] = {
        "raw_hits_count": len(valid_hits),
        "raw_scores": raw_scores,
        "filtered_hits_count": len(filtered_hits),
        "filtered_by_score_count": max(0, len(valid_hits) - len(filtered_hits)),
        "salvaged_hits_count": 0,
        "score_policy_mode": "standard_threshold",
        "reasons": [],
    }

    if not valid_hits:
        trace["score_policy_mode"] = "empty"
        trace["reasons"] = ["no_raw_hits"]
        return {
            "filtered_hits": [],
            "trace": trace,
        }

    if not RAG_SCORE_POLICY_V1_ENABLED:
        trace["reasons"] = ["score_policy_v1_disabled"]
        return {
            "filtered_hits": filtered_hits,
            "trace": trace,
        }

    if filtered_hits:
        trace["reasons"] = ["standard_threshold_passed"]
        return {
            "filtered_hits": filtered_hits,
            "trace": trace,
        }

    top_score = max(raw_scores) if raw_scores else 0.0
    source_used = str(retrieval_source_used or "unknown").strip().lower() or "unknown"
    salvage_allowed_source = source_used in {"api", "semantic_fallback", "tfidf_fallback", "unknown"}
    salvage_allowed = (
        RAG_LOW_SCORE_SALVAGE_ENABLED
        and salvage_allowed_source
        and top_score >= float(RAG_LOW_SCORE_SALVAGE_MIN_TOP_SCORE)
        and top_score > 0.0
    )
    if not salvage_allowed:
        reason = "salvage_disabled_or_threshold_not_met"
        if not RAG_LOW_SCORE_SALVAGE_ENABLED:
            reason = "low_score_salvage_disabled"
        elif not salvage_allowed_source:
            reason = "salvage_source_not_allowed"
        elif top_score <= 0.0:
            reason = "top_score_non_positive"
        elif top_score < float(RAG_LOW_SCORE_SALVAGE_MIN_TOP_SCORE):
            reason = "top_score_below_salvage_min"
        trace["reasons"] = ["all_hits_below_min_score", reason]
        return {
            "filtered_hits": [],
            "trace": trace,
        }

    salvage_cap = max(1, int(RAG_LOW_SCORE_SALVAGE_MAX_HITS))
    salvaged_hits = sorted(valid_hits, key=lambda hit: float(hit.score), reverse=True)[:salvage_cap]
    trace.update(
        {
            "filtered_hits_count": len(salvaged_hits),
            "salvaged_hits_count": len(salvaged_hits),
            "score_policy_mode": "source_aware_salvage",
            "reasons": [
                "all_hits_below_min_score",
                "low_score_salvage_applied",
                f"source={source_used}",
            ],
        }
    )
    return {
        "filtered_hits": salvaged_hits,
        "trace": trace,
    }


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
            self._load_conversation(user_id, n_turns, user_message),
            self._load_profile(user_id),
            self._load_rag(rag_query),
            self._load_recent_turns(user_id, n_turns),
            self._load_personal_history_context(user_id),
            self._load_semantic_memory_hits(user_id, user_message),
            return_exceptions=True,
        )

        conversation_context = results[0] if not isinstance(results[0], Exception) else ""
        user_profile = results[1] if not isinstance(results[1], Exception) else UserProfile()
        rag_result = results[2] if not isinstance(results[2], Exception) else ([], {})
        recent_turns = results[3] if not isinstance(results[3], Exception) else []
        personal_history_context = results[4] if not isinstance(results[4], Exception) else []
        semantic_memory_hits = results[5] if not isinstance(results[5], Exception) else []

        for label, result in zip(
            ("conversation", "profile", "rag", "recent_turns", "personal_history", "semantic_memory"),
            results,
        ):
            if isinstance(result, Exception):
                logger.warning("[MRA] %s load failed: %s", label, result)

        raw_hits: list[SemanticHit]
        retrieval_debug: dict[str, Any]
        if (
            isinstance(rag_result, tuple)
            and len(rag_result) >= 2
            and isinstance(rag_result[0], list)
            and isinstance(rag_result[1], dict)
        ):
            raw_hits = [h for h in rag_result[0] if isinstance(h, SemanticHit)]
            retrieval_debug = dict(rag_result[1])
        elif isinstance(rag_result, list):
            raw_hits = [h for h in rag_result if isinstance(h, SemanticHit)]
            retrieval_debug = {}
        else:
            raw_hits = []
            retrieval_debug = {}

        retrieval_source_attempted = str(
            retrieval_debug.get("retrieval_source_attempted", "api") or "api"
        )
        retrieval_source_used = str(
            retrieval_debug.get("retrieval_source_used", "unknown") or "unknown"
        )

        score_policy = rag_score_policy_v1(
            raw_hits=raw_hits,
            rag_min_score=float(RAG_MIN_SCORE),
            retrieval_source_used=retrieval_source_used,
            query=rag_query,
        )
        filtered_hits = [
            hit for hit in list(score_policy.get("filtered_hits", [])) if isinstance(hit, SemanticHit)
        ]
        trace_payload = (
            dict(score_policy.get("trace", {}))
            if isinstance(score_policy.get("trace", {}), dict)
            else {}
        )
        raw_scores_value = trace_payload.get("raw_scores", [])
        if not isinstance(raw_scores_value, list):
            raw_scores_value = []
        reasons_value = trace_payload.get("reasons", [])
        if not isinstance(reasons_value, list):
            reasons_value = []

        rag_retrieval_trace = {
            "version": "rag_retrieval_trace_v1",
            "query": _sanitize_query_preview(rag_query),
            "retrieval_source_attempted": retrieval_source_attempted,
            "retrieval_source_used": retrieval_source_used,
            "raw_hits_count": int(trace_payload.get("raw_hits_count", len(raw_hits)) or 0),
            "raw_scores": [float(x) for x in raw_scores_value],
            "rag_min_score": float(RAG_MIN_SCORE),
            "filtered_hits_count": int(trace_payload.get("filtered_hits_count", len(filtered_hits)) or 0),
            "filtered_by_score_count": int(trace_payload.get("filtered_by_score_count", 0) or 0),
            "salvaged_hits_count": int(trace_payload.get("salvaged_hits_count", 0) or 0),
            "score_policy_mode": str(trace_payload.get("score_policy_mode", "standard_threshold") or "standard_threshold"),
            "score_policy_reasons": [str(item) for item in reasons_value],
        }
        policy_decisions, knowledge_policy_trace = apply_knowledge_policy_v1(filtered_hits)
        knowledge_rag_hits = [
            decision.to_writer_hit_dict()
            for decision in policy_decisions
            if decision.allowed_for_writer
        ]

        return MemoryBundle(
            conversation_context=conversation_context if isinstance(conversation_context, str) else "",
            rag_query=rag_query,
            user_profile=user_profile if isinstance(user_profile, UserProfile) else UserProfile(),
            semantic_hits=filtered_hits,
            recent_turns=list(recent_turns) if isinstance(recent_turns, list) else [],
            personal_history_context=(
                list(personal_history_context) if isinstance(personal_history_context, list) else []
            ),
            semantic_memory_hits=(
                list(semantic_memory_hits) if isinstance(semantic_memory_hits, list) else []
            ),
            knowledge_rag_hits=knowledge_rag_hits,
            retrieved_chunks=[h.content for h in filtered_hits],
            has_relevant_knowledge=len(knowledge_rag_hits) > 0,
            context_turns=n_turns,
            knowledge_policy_trace=knowledge_policy_trace,
            rag_retrieval_trace=rag_retrieval_trace,
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

        # Защитная дедупликация: каждый смысловой кусок должен попасть в query один раз.
        parts = list(dict.fromkeys(p.strip() for p in parts if p.strip()))
        return " ".join(parts)[:RAG_QUERY_MAX_LEN]

    @staticmethod
    async def _load_conversation(user_id: str, n_turns: int, user_message: str = "") -> str:
        try:
            from ...conversation_memory import get_conversation_memory  # noqa: PLC0415

            memory = get_conversation_memory(user_id=user_id)
            if not getattr(memory, "turns", None):
                return ""

            # Reuse adaptive context logic from cascade runtime:
            # short-term turns + summary + semantic memory.
            context = memory.get_adaptive_context_text(user_message or "")
            if context:
                return str(context)

            # Defensive fallback if adaptive context is empty.
            turns = memory.get_last_turns(n=n_turns)
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
    async def _load_recent_turns(user_id: str, n_turns: int) -> list[dict[str, Any]]:
        try:
            from ...conversation_memory import get_conversation_memory  # noqa: PLC0415

            memory = get_conversation_memory(user_id=user_id)
            turns = memory.get_last_turns(n=n_turns)
            total = len(getattr(memory, "turns", []) or [])
            start_index = max(1, total - len(turns) + 1)
            result: list[dict[str, Any]] = []
            for offset, turn in enumerate(turns):
                result.append(
                    {
                        "turn_index": start_index + offset,
                        "timestamp": str(getattr(turn, "timestamp", "") or ""),
                        "user_input": str(getattr(turn, "user_input", "") or ""),
                        "bot_response": str(getattr(turn, "bot_response", "") or ""),
                        "user_state": str(getattr(turn, "user_state", "") or ""),
                        "turn_llm_summary": (
                            dict(getattr(turn, "turn_llm_summary", {}) or {})
                            if isinstance(getattr(turn, "turn_llm_summary", None), dict)
                            else {}
                        ),
                    }
                )
            return result
        except Exception as exc:
            logger.warning("[MRA] recent turns load error: %s", exc)
            return []

    @staticmethod
    async def _load_personal_history_context(user_id: str) -> list[dict[str, Any]]:
        try:
            from ...conversation_memory import get_conversation_memory  # noqa: PLC0415

            memory = get_conversation_memory(user_id=user_id)
            summary = memory.get_summary()
            items: list[dict[str, Any]] = []
            conversation_summary = str(summary.get("conversation_summary", "") or "").strip()
            if conversation_summary:
                items.append(
                    {
                        "source": "conversation_summary",
                        "content": conversation_summary,
                    }
                )
            working_state = summary.get("working_state")
            if isinstance(working_state, dict) and working_state:
                active_track = str(working_state.get("active_track", "") or "").strip()
                core_theme = str(working_state.get("core_theme", "") or "").strip()
                state_fragments = [x for x in (active_track, core_theme) if x]
                if state_fragments:
                    items.append(
                        {
                            "source": "working_state",
                            "content": "; ".join(state_fragments),
                        }
                    )
            interests = [str(x) for x in summary.get("primary_interests", []) if str(x).strip()]
            if interests:
                items.append(
                    {
                        "source": "primary_interests",
                        "content": ", ".join(interests[:5]),
                    }
                )
            return items
        except Exception as exc:
            logger.warning("[MRA] personal history load error: %s", exc)
            return []

    @staticmethod
    async def _load_semantic_memory_hits(user_id: str, query: str) -> list[dict[str, Any]]:
        try:
            from ...conversation_memory import get_conversation_memory  # noqa: PLC0415

            if not query.strip():
                return []
            memory = get_conversation_memory(user_id=user_id)
            semantic_memory = getattr(memory, "semantic_memory", None)
            if semantic_memory is None:
                return []
            hits = semantic_memory.search_similar_turns(
                query=query,
                top_k=3,
                min_similarity=0.6,
                exclude_last_n=1,
            )
            result: list[dict[str, Any]] = []
            for turn_emb, score in hits:
                result.append(
                    {
                        "turn_id": f"turn_{int(getattr(turn_emb, 'turn_index', 0) or 0)}",
                        "source": "semantic_memory",
                        "score": float(score),
                        "content": (
                            f"User: {str(getattr(turn_emb, 'user_input', '') or '')}\n"
                            f"Assistant: {str(getattr(turn_emb, 'bot_response_preview', '') or '')}"
                        ).strip(),
                    }
                )
            return result
        except Exception as exc:
            logger.warning("[MRA] semantic memory hits load error: %s", exc)
            return []

    @staticmethod
    async def _load_rag(query: str) -> tuple[list[SemanticHit], dict[str, Any]]:
        try:
            from ...retriever import get_retriever  # noqa: PLC0415

            if not query.strip():
                return [], {}

            retriever = get_retriever()
            results = retriever.retrieve(query, top_k=RAG_N_RESULTS)
            retrieval_debug = {}
            if hasattr(retriever, "get_last_retrieval_debug"):
                try:
                    retrieval_debug = retriever.get_last_retrieval_debug()  # type: ignore[assignment]
                except Exception:
                    retrieval_debug = {}
            hits: list[SemanticHit] = []
            for item in results:
                if isinstance(item, tuple) and len(item) >= 2:
                    block, score = item[0], float(item[1] or 0.0)
                else:
                    block = item
                    score = 0.5

                chunk_id = str(getattr(block, "block_id", "") or "")
                content = str(getattr(block, "content", "") or "")
                source = str(
                    getattr(block, "document_title", "")
                    or getattr(block, "source_type", "")
                    or "unknown"
                )
                governance = getattr(block, "governance", {})
                chunking_quality = getattr(block, "chunking_quality", {})
                if not content:
                    continue

                hits.append(
                    SemanticHit(
                        chunk_id=chunk_id,
                        content=content,
                        source=source,
                        score=score,
                        governance=governance if isinstance(governance, dict) else {},
                        chunking_quality=chunking_quality if isinstance(chunking_quality, dict) else {},
                    )
                )
            logger.info(
                "[MRA] rag hits=%d query='%s...' retrieval_source_used=%s circuit_open=%s",
                len(hits),
                query[:50],
                str(retrieval_debug.get("retrieval_source_used", "unknown")),
                bool(retrieval_debug.get("bot_db_circuit_open", False)),
            )
            return hits, dict(retrieval_debug or {})
        except Exception as exc:
            logger.warning("[MRA] rag load error: %s", exc)
            return [], {}


memory_retrieval_agent = MemoryRetrievalAgent()
