"""Writer contract used by multi-agent orchestrator."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..context_assembly import format_context_for_writer
from ..writer_move_compliance import build_writer_move_instructions_v1
from .context_package import ContextAssemblyPackage
from .diagnostic_card import DiagnosticCard
from .memory_bundle import MemoryBundle
from .thread_state import ThreadState


@dataclass
class WriterContract:
    """Stable payload that Writer receives for one response generation."""

    user_message: str
    thread_state: ThreadState
    memory_bundle: MemoryBundle
    context_package: ContextAssemblyPackage | None = None
    diagnostic_card: DiagnosticCard | None = None
    knowledge_answer_guard: dict[str, Any] | None = None
    response_language: str | None = None

    def to_dict(self) -> dict:
        return {
            "user_message": self.user_message,
            "thread_state": self.thread_state.to_dict(),
            "memory_bundle": self.memory_bundle.to_dict(),
            "context_package": (
                self.context_package.to_dict() if self.context_package is not None else None
            ),
            "diagnostic_card": (
                self.diagnostic_card.to_dict() if self.diagnostic_card is not None else None
            ),
            "knowledge_answer_guard": (
                dict(self.knowledge_answer_guard) if isinstance(self.knowledge_answer_guard, dict) else None
            ),
            "response_language": self.response_language,
        }

    def to_prompt_context(self) -> dict:
        """Serialize context for Writer prompt templates."""
        if self.context_package is not None:
            conversation_context = format_context_for_writer(self.context_package)
            semantic_hits = [
                str(item.get("content", "") or "")
                for item in self.context_package.knowledge_rag_hits
                if str(item.get("content", "") or "").strip()
            ]
            if not semantic_hits:
                semantic_hits = [
                    str(item.get("content", "") or "")
                    for item in self.context_package.semantic_memory_hits
                    if str(item.get("content", "") or "").strip()
                ]
            context_assembly_trace = self.context_package.trace.to_dict()
        else:
            conversation_context = self.memory_bundle.conversation_context
            semantic_hits = [hit.content for hit in self.memory_bundle.semantic_hits[:2]]
            context_assembly_trace = {}

        diagnostic_card_payload = (
            self.diagnostic_card.to_dict() if self.diagnostic_card is not None else {}
        )
        diagnostic_summary = (
            {
                "present": True,
                "situation_label": self.diagnostic_card.situation_label,
                "current_need": self.diagnostic_card.current_need,
                "suggested_writer_move": self.diagnostic_card.suggested_writer_move,
                "confidence": float(self.diagnostic_card.confidence),
                "risk_flags": list(self.diagnostic_card.risk_flags),
            }
            if self.diagnostic_card is not None
            else {
                "present": False,
                "situation_label": "",
                "current_need": "",
                "suggested_writer_move": "",
                "confidence": 0.0,
                "risk_flags": [],
            }
        )
        writer_move_instructions = build_writer_move_instructions_v1(self.diagnostic_card)
        writer_move_summary = (
            f"move={writer_move_instructions.get('move')}; "
            f"max_sentences={writer_move_instructions.get('max_sentences')}; "
            f"max_questions={writer_move_instructions.get('max_questions')}; "
            f"style={writer_move_instructions.get('style')}"
        )
        knowledge_answer_guard = (
            dict(self.knowledge_answer_guard)
            if isinstance(self.knowledge_answer_guard, dict)
            else {}
        )
        knowledge_answer = (
            dict(knowledge_answer_guard.get("knowledge_answer", {}))
            if isinstance(knowledge_answer_guard.get("knowledge_answer"), dict)
            else {}
        )
        practice_gate = (
            dict(knowledge_answer_guard.get("practice_gate", {}))
            if isinstance(knowledge_answer_guard.get("practice_gate"), dict)
            else {}
        )

        return {
            "user_message": self.user_message,
            "phase": self.thread_state.phase,
            "response_mode": self.thread_state.response_mode,
            "response_goal": self.thread_state.response_goal,
            "must_avoid": self.thread_state.must_avoid,
            "ok_position": self.thread_state.ok_position,
            "openness": self.thread_state.openness,
            "open_loops": self.thread_state.open_loops,
            "closed_loops": self.thread_state.closed_loops,
            "core_direction": self.thread_state.core_direction,
            "pattern_core": self.thread_state.pattern_core,
            "active_frame": self.thread_state.active_frame,
            "nervous_state": self.thread_state.nervous_state,
            "safety_active": self.thread_state.safety_active,
            "conversation_context": conversation_context,
            "user_profile_patterns": self.memory_bundle.user_profile.patterns,
            "user_profile_values": self.memory_bundle.user_profile.values,
            "semantic_hits": semantic_hits[:2],
            "has_relevant_knowledge": self.memory_bundle.has_relevant_knowledge,
            "context_assembly_trace": context_assembly_trace,
            "context_package_summary": {
                "present": self.context_package is not None,
                "recent_full_count": (
                    len(self.context_package.recent_turns_full)
                    if self.context_package is not None
                    else 0
                ),
                "recent_summarized_count": (
                    len(self.context_package.recent_turns_summarized)
                    if self.context_package is not None
                    else 0
                ),
            },
            "diagnostic_card": diagnostic_card_payload,
            "diagnostic_card_summary": diagnostic_summary,
            "diagnostic_card_avoid_list": (
                list(self.diagnostic_card.avoid_list)
                if self.diagnostic_card is not None
                else []
            ),
            "diagnostic_card_risk_flags": (
                list(self.diagnostic_card.risk_flags)
                if self.diagnostic_card is not None
                else []
            ),
            "writer_move_instructions": writer_move_instructions,
            "writer_move_instruction_summary": writer_move_summary,
            "writer_move_must_do": list(writer_move_instructions.get("must_do", []) or []),
            "writer_move_must_not_do": list(writer_move_instructions.get("must_not_do", []) or []),
            "knowledge_answer_guard": knowledge_answer_guard,
            "knowledge_answer": knowledge_answer,
            "practice_gate": practice_gate,
        }
