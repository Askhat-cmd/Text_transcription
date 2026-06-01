from __future__ import annotations

from dataclasses import dataclass, field

from bot_agent.multiagent.live_turn_evidence import LIVE_TURN_EVIDENCE_VERSION, build_live_turn_evidence_v1


@dataclass
class _DummyMemory:
    conversation_context: str = "USER: привет\nASSISTANT: привет"
    semantic_hits: list = field(default_factory=list)


@dataclass
class _DummyState:
    nervous_state: str = "window"
    intent: str = "contact"
    safety_flag: bool = False


@dataclass
class _DummyThread:
    thread_id: str = "t-1"
    phase: str = "clarify"
    relation_to_thread: str = "continue"
    response_mode: str = "reflect"


@dataclass
class _DummyValidation:
    is_blocked: bool = False
    block_reason: str = ""
    quality_flags: list[str] = field(default_factory=list)


class _DummyContract:
    def to_prompt_context(self) -> dict:
        return {
            "response_mode": "reflect",
            "response_goal": "support",
            "must_avoid": [],
            "dialogue_profile": "mvp_free_dialogue",
            "retrieval_action": "recent_context_only",
            "dialogue_pragmatics_short_type": "affirmation",
        }


def test_build_live_turn_evidence_v1_has_required_sections() -> None:
    payload = build_live_turn_evidence_v1(
        query="да",
        user_id="u1",
        session_id="s1",
        turn_index=2,
        orchestrator_result={"answer": "Ответ"},
        writer_contract=_DummyContract(),
        writer_debug={"system_prompt": "sys", "user_prompt": "usr", "model": "gpt-5-mini"},
        memory_bundle=_DummyMemory(),
        state_snapshot=_DummyState(),
        thread_state=_DummyThread(),
        thread_debug={},
        diagnostic_card=None,
        active_line_state={},
        response_planner_state={},
        dialogue_policy={},
        dialogue_pragmatics={},
        contextual_retrieval_decision={},
        validation_result=_DummyValidation(),
    )

    assert payload["version"] == LIVE_TURN_EVIDENCE_VERSION
    assert payload["turn_identity"]["user_id"] == "u1"
    assert payload["writer"]["prompt_canvas"]["system_prompt_sha256"].startswith("sha256:")
    assert "writer_debug" in payload["writer"]
    assert payload["validator"]["is_blocked"] is False
