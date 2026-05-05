"""Minimal multi-agent orchestrator for PRD-017 bootstrap."""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone

from bot_agent.config import config
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

    def __init__(self) -> None:
        self.pipeline_version = "multiagent_v1"
        self._agent_metrics: dict[str, dict] = {
            "state_analyzer": {"call_count": 0, "total_ms": 0, "error_count": 0, "last_run": None, "enabled": True},
            "thread_manager": {"call_count": 0, "total_ms": 0, "error_count": 0, "last_run": None, "enabled": True},
            "memory_retrieval": {"call_count": 0, "total_ms": 0, "error_count": 0, "last_run": None, "enabled": True},
            "writer": {"call_count": 0, "total_ms": 0, "error_count": 0, "last_run": None, "enabled": True},
            "validator": {"call_count": 0, "total_ms": 0, "error_count": 0, "last_run": None, "enabled": True},
        }
        self._agent_traces: list[dict] = []

    def _record_agent_metric(
        self,
        *,
        agent_id: str,
        latency_ms: int,
        user_id: str,
        input_preview: str,
        output_preview: str = "",
        error: str | None = None,
    ) -> None:
        metric = self._agent_metrics.setdefault(
            agent_id,
            {"call_count": 0, "total_ms": 0, "error_count": 0, "last_run": None, "enabled": True},
        )
        metric["call_count"] = int(metric.get("call_count", 0)) + 1
        metric["total_ms"] = int(metric.get("total_ms", 0)) + int(latency_ms)
        if error:
            metric["error_count"] = int(metric.get("error_count", 0)) + 1
        metric["last_run"] = datetime.now(timezone.utc).isoformat()
        self._agent_traces.append(
            {
                "agent_id": agent_id,
                "request_id": "",
                "user_id": user_id,
                "input_preview": input_preview[:300],
                "output_preview": output_preview[:300],
                "latency_ms": int(latency_ms),
                "error": error,
                "timestamp": metric["last_run"],
            }
        )
        if len(self._agent_traces) > 200:
            self._agent_traces = self._agent_traces[-200:]

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
        t_total_start = time.perf_counter()

        current_thread = thread_storage.load_active(user_id)
        archived_threads = thread_storage.load_archived(user_id)

        t0 = time.perf_counter()
        state_snapshot = await state_analyzer_agent.analyze(
            user_message=query,
            previous_thread=current_thread,
        )
        t_state = int((time.perf_counter() - t0) * 1000)
        state_debug = (
            state_analyzer_agent.last_debug
            if isinstance(getattr(state_analyzer_agent, "last_debug", None), dict)
            else {}
        )
        self._record_agent_metric(
            agent_id="state_analyzer",
            latency_ms=t_state,
            user_id=user_id,
            input_preview=query,
            output_preview=f"state={state_snapshot.nervous_state}; intent={state_snapshot.intent}",
            error=str(state_debug.get("error")) if state_debug.get("error") else None,
        )

        t0 = time.perf_counter()
        updated_thread = await thread_manager_agent.update(
            user_message=query,
            state_snapshot=state_snapshot,
            user_id=user_id,
            current_thread=current_thread,
            archived_threads=archived_threads,
        )
        t_thread = int((time.perf_counter() - t0) * 1000)
        self._record_agent_metric(
            agent_id="thread_manager",
            latency_ms=t_thread,
            user_id=user_id,
            input_preview=query,
            output_preview=f"thread={updated_thread.thread_id}; phase={updated_thread.phase}",
        )
        if updated_thread.relation_to_thread == "new_thread" and current_thread is not None:
            thread_storage.archive_thread(current_thread, reason="new_thread")
        thread_storage.save_active(updated_thread)

        t0 = time.perf_counter()
        memory_bundle = await memory_retrieval_agent.assemble(
            user_message=query,
            thread_state=updated_thread,
            user_id=user_id,
        )
        t_memory = int((time.perf_counter() - t0) * 1000)
        self._record_agent_metric(
            agent_id="memory_retrieval",
            latency_ms=t_memory,
            user_id=user_id,
            input_preview=query,
            output_preview=f"hits={len(memory_bundle.semantic_hits)}; has_knowledge={memory_bundle.has_relevant_knowledge}",
        )

        writer_contract = WriterContract(
            user_message=query,
            thread_state=updated_thread,
            memory_bundle=memory_bundle,
        )
        t0 = time.perf_counter()
        draft_answer = await writer_agent.write(writer_contract)
        t_writer = int((time.perf_counter() - t0) * 1000)
        writer_debug = writer_agent.last_debug if isinstance(writer_agent.last_debug, dict) else {}
        self._record_agent_metric(
            agent_id="writer",
            latency_ms=t_writer,
            user_id=user_id,
            input_preview=query,
            output_preview=draft_answer,
            error=str(writer_debug.get("error")) if writer_debug.get("error") else None,
        )

        t0 = time.perf_counter()
        validation_result = validator_agent.validate(draft_answer, writer_contract)
        t_validator = int((time.perf_counter() - t0) * 1000)
        self._record_agent_metric(
            agent_id="validator",
            latency_ms=t_validator,
            user_id=user_id,
            input_preview=query,
            output_preview=f"blocked={validation_result.is_blocked}; reason={validation_result.block_reason}",
            error=validation_result.block_reason if validation_result.is_blocked else None,
        )
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
        total_latency_ms = int((time.perf_counter() - t_total_start) * 1000)
        semantic_hits_detail = []
        for raw_hit in memory_bundle.semantic_hits:
            if hasattr(raw_hit, "to_dict"):
                hit = raw_hit.to_dict()  # type: ignore[assignment]
            elif isinstance(raw_hit, dict):
                hit = raw_hit
            else:
                hit = {
                    "chunk_id": "",
                    "source": "unknown",
                    "score": 0.0,
                    "content": str(raw_hit),
                }
            content_full = str(hit.get("content", "") or "")
            semantic_hits_detail.append(
                {
                    "chunk_id": str(hit.get("chunk_id", "")),
                    "source": str(hit.get("source", "unknown")),
                    "score": float(hit.get("score", 0.0) or 0.0),
                    "content_preview": content_full[:200],
                    "content_full": content_full,
                }
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
                "pipeline_version": "multiagent_v1",
                "total_latency_ms": total_latency_ms,
                "thread_manager_model": "heuristic",
                "nervous_state": state_snapshot.nervous_state,
                "intent": state_snapshot.intent,
                "safety_flag": state_snapshot.safety_flag,
                "confidence": state_snapshot.confidence,
                "has_relevant_knowledge": memory_bundle.has_relevant_knowledge,
                "context_turns": memory_bundle.context_turns,
                "semantic_hits_count": len(memory_bundle.semantic_hits),
                "semantic_hits_detail": semantic_hits_detail,
                "rag_query": getattr(memory_bundle, "rag_query", "") or "",
                "conversation_context": memory_bundle.conversation_context,
                "user_profile": {
                    "patterns": list(getattr(memory_bundle.user_profile, "patterns", []) or []),
                    "values": list(getattr(memory_bundle.user_profile, "values", []) or []),
                    "progress_notes": list(getattr(memory_bundle.user_profile, "progress_notes", []) or []),
                },
                "thread_id": updated_thread.thread_id,
                "phase": updated_thread.phase,
                "relation_to_thread": updated_thread.relation_to_thread,
                "continuity_score": updated_thread.continuity_score,
                "response_mode": updated_thread.response_mode,
                "writer_system_prompt": str(writer_debug.get("system_prompt", "") or ""),
                "writer_user_prompt": str(writer_debug.get("user_prompt", "") or ""),
                "writer_llm_response_raw": str(writer_debug.get("llm_response", "") or ""),
                "writer_api_mode": writer_debug.get("api_mode"),
                "writer_error": writer_debug.get("error"),
                "writer_fallback_used": bool(writer_debug.get("fallback_used", False)),
                "tokens_prompt": writer_debug.get("tokens_prompt"),
                "tokens_completion": writer_debug.get("tokens_completion"),
                "tokens_total": writer_debug.get("tokens_total"),
                "tokens_used": writer_debug.get("tokens_total"),
                "estimated_cost_usd": writer_debug.get("estimated_cost_usd"),
                "model_used": str(writer_debug.get("model") or config.LLM_MODEL),
                "model_temperature": writer_debug.get("temperature"),
                "model_max_tokens": writer_debug.get("max_tokens"),
                "state_analyzer_model": state_debug.get("model"),
                "state_analyzer_api_mode": state_debug.get("api_mode"),
                "state_analyzer_error": state_debug.get("error"),
                "state_analyzer_parse_error": state_debug.get("parse_error"),
                "state_analyzer_fallback_used": bool(
                    state_debug.get("error") or state_debug.get("parse_error")
                ),
                "validator_blocked": validation_result.is_blocked,
                "validator_block_reason": validation_result.block_reason,
                "validator_quality_flags": validation_result.quality_flags,
                "memory_written": {
                    "user_input": query[:200],
                    "bot_response": final_answer[:200],
                    "thread_id": updated_thread.thread_id,
                    "phase": updated_thread.phase,
                },
                "timings": {
                    "state_analyzer_ms": t_state,
                    "thread_manager_ms": t_thread,
                    "memory_retrieval_ms": t_memory,
                    "writer_ms": t_writer,
                    "validator_ms": t_validator,
                },
            },
        }

    def run_sync(self, *, query: str, user_id: str) -> dict:
        return asyncio.run(self.run(query=query, user_id=user_id))


orchestrator = MultiAgentOrchestrator()
