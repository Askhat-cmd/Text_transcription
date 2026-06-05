"""Thread Manager agent for NEO multi-agent runtime."""

from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime
from typing import Any, Optional

from ..creator_live_behavior_guard import (
    REQUEST_TYPE_EXAMPLE,
    REQUEST_TYPE_EXPLAIN,
    REQUEST_TYPE_PRACTICE,
    REQUEST_TYPE_SAFETY,
    detect_request_type_v1,
)
from ..contracts.state_snapshot import StateSnapshot
from ..contracts.thread_state import ArchivedThread, ThreadState
from .agent_llm_config import get_model_for_agent


logger = logging.getLogger(__name__)

_RETURN_MARKERS = (
    "return to",
    "go back",
    "continue that",
    "same topic",
    "вернемся",
    "вернёмся",
    "вернуться",
    "к прошлой теме",
)
_RESOLUTION_MARKERS = (
    "resolved",
    "understood",
    "thanks",
    "done",
    "clear",
    "понял",
    "поняла",
    "спасибо",
    "разобрался",
    "разобралась",
)
_BRANCH_MARKERS = (
    "also",
    "and another",
    "what if",
    "by the way",
    "next question",
    "еще",
    "ещё",
    "а еще",
    "а ещё",
    "кстати",
)
_NEW_THREAD_THRESHOLD = 0.20
THREAD_DIAGNOSTICS_VERSION = "thread_diagnostics_v1"
_FOLLOWUP_CONTINUE_MARKERS = (
    "ты права",
    "ты прав",
    "вы правы",
    "я понимаю",
    "об этом",
    "про это",
    "по этому поводу",
    "но как мне",
    "как мне не",
    # Legacy mojibake-safe markers (for old persisted test payloads/texts).
    "С‚С‹ РїСЂР°РІР°",
    "РІС‹ РїСЂР°РІС‹",
    "СЏ РїРѕРЅРёРјР°СЋ",
    "РѕР± СЌС‚РѕРј",
    "РїСЂРѕ СЌС‚Рѕ",
    "РїРѕ СЌС‚РѕРјСѓ РїРѕРІРѕРґСѓ",
    "РЅРѕ РєР°Рє РјРЅРµ",
    "РєР°Рє РјРЅРµ РЅРµ",
    "that makes sense",
    "you are right",
    "about it",
)
_LOW_RESOURCE_CONTINUE_MARKERS = (
    "\u0441\u0438\u043b \u043d\u0435\u0442",
    "\u0441\u0438\u043b \u043f\u043e\u0447\u0442\u0438 \u043d\u0435\u0442",
    "\u043f\u043e\u0447\u0442\u0438 \u043d\u0435\u0442 \u0441\u0438\u043b",
    "\u0431\u0435\u0437 \u0441\u0438\u043b",
    "\u043e\u0442\u0432\u0435\u0447\u0430\u0442\u044c \u0442\u044f\u0436\u0435\u043b\u043e",
    "\u0433\u043e\u0432\u043e\u0440\u0438\u0442\u044c \u0442\u044f\u0436\u0435\u043b\u043e",
    "\u0434\u0430\u0436\u0435 \u043e\u0442\u0432\u0435\u0447\u0430\u0442\u044c",
    "\u0441\u043e\u0432\u0441\u0435\u043c \u043f\u0440\u043e\u0441\u0442\u043e\u0435",
    "\u0447\u0442\u043e-\u0442\u043e \u043f\u0440\u043e\u0441\u0442\u043e\u0435",
    "\u0447\u0442\u043e \u0442\u043e \u043f\u0440\u043e\u0441\u0442\u043e\u0435",
    "\u043d\u0430 \u0441\u0435\u0439\u0447\u0430\u0441",
    "\u043d\u0435 \u0434\u0430\u0432\u0438",
    "\u0431\u0435\u0437 \u0434\u0430\u0432\u043b\u0435\u043d\u0438\u044f",
    "\u043d\u0435 \u0432\u044b\u0432\u043e\u0436\u0443",
    "no energy left",
    "almost no energy",
    "hard to answer",
    "hard to even reply",
    "even replying is hard",
    "something simple",
    "something very simple",
    "right now",
    "no pressure",
    "don't push",
)
_RECURRENCE_CONTINUITY_MARKERS = (
    "\u0441\u043d\u043e\u0432\u0430",
    "\u043e\u043f\u044f\u0442\u044c",
    "\u0432\u0441\u0435 \u0435\u0449\u0435",
    "\u0432\u0441\u0451 \u0435\u0449\u0451",
    "\u043f\u043e-\u043f\u0440\u0435\u0436\u043d\u0435\u043c\u0443",
    "\u043a\u0430\u043a \u0442\u043e\u0433\u0434\u0430",
    "\u0442\u043e \u0436\u0435 \u0441\u0430\u043c\u043e\u0435",
    "\u0442\u0430 \u0436\u0435 \u0438\u0441\u0442\u043e\u0440\u0438\u044f",
    "again",
    "still",
    "same thing",
)
_SEMANTIC_CONTINUITY_STOPWORDS = {
    "\u0441\u0435\u0439\u0447\u0430\u0441",
    "\u0445\u043e\u0447\u0443",
    "\u043a\u0430\u043a",
    "\u044d\u0442\u043e",
    "\u0442\u043e\u0436\u0435",
    "\u043e\u043f\u044f\u0442\u044c",
    "\u0441\u043d\u043e\u0432\u0430",
    "\u0435\u0449\u0451",
    "\u0435\u0449\u0435",
    "want",
    "again",
    "still",
}
_SEMANTIC_CONTINUITY_THEME_MARKERS = (
    "\u043e\u0442\u043b\u043e\u0436",      # отложить / откладывать
    "\u043f\u0435\u0440\u0435\u043f\u0438\u0441",  # переписывать
    "\u0447\u0435\u0440\u043d\u043e\u0432\u0438\u043a",
    "\u043f\u0443\u0431\u043b\u0438",      # публикация / публиковать
    "postpone",
    "draft",
    "publish",
    "delay",
    "avoid",
)


def _normalize_tokens(text: str) -> set[str]:
    # Unicode-safe tokenization: works for English, Russian and legacy mojibake text.
    tokens = re.findall(r"[^\W_]+", text.lower(), flags=re.UNICODE)
    return {t for t in tokens if len(t) > 2}


def _continuity_score(message: str, core_direction: str) -> float:
    current = _normalize_tokens(message)
    core = _normalize_tokens(core_direction)
    if not current or not core:
        return 0.0
    union = len(current | core)
    if union == 0:
        return 0.0
    return round(len(current & core) / union, 4)


def _recurrence_marker_hit(message: str) -> bool:
    lowered = (message or "").lower()
    return any(marker in lowered for marker in _RECURRENCE_CONTINUITY_MARKERS)


def _strip_semantic_noise(tokens: set[str]) -> set[str]:
    cleaned = {token for token in tokens if token not in _SEMANTIC_CONTINUITY_STOPWORDS}
    recurrence_tokens = {
        token
        for marker in _RECURRENCE_CONTINUITY_MARKERS
        for token in _normalize_tokens(marker)
    }
    return cleaned - recurrence_tokens


def _semantic_frame_sources(current_thread: ThreadState) -> dict[str, str]:
    active_frame = current_thread.active_frame if isinstance(current_thread.active_frame, dict) else {}
    open_loops = " ".join(str(item or "") for item in list(current_thread.open_loops or []))
    active_values = " ".join(str(item or "") for item in active_frame.values())
    return {
        "core_direction": str(current_thread.core_direction or ""),
        "pattern_core": str(current_thread.pattern_core or ""),
        "open_loops": open_loops,
        "active_frame": active_values,
    }


def _active_frame_continuity_signal(
    *,
    user_message: str,
    current_thread: ThreadState,
    resolution_marker_hit: bool,
) -> tuple[bool, dict[str, Any]]:
    recurrence_hit = _recurrence_marker_hit(user_message)
    sources = _semantic_frame_sources(current_thread)
    frame_text = " ".join(str(text or "") for text in sources.values()).lower()
    message_lower = (user_message or "").lower()
    source_tokens = {
        name: _strip_semantic_noise(_normalize_tokens(text))
        for name, text in sources.items()
    }
    semantic_frame_tokens: set[str] = set()
    matched_sources: list[str] = []
    message_tokens = _strip_semantic_noise(_normalize_tokens(user_message))

    for name, tokens in source_tokens.items():
        semantic_frame_tokens.update(tokens)
        if message_tokens.intersection(tokens):
            matched_sources.append(name)

    overlap = len(message_tokens.intersection(semantic_frame_tokens))
    message_theme_hit = any(marker in message_lower for marker in _SEMANTIC_CONTINUITY_THEME_MARKERS)
    frame_theme_hit = any(marker in frame_text for marker in _SEMANTIC_CONTINUITY_THEME_MARKERS)

    hit_reason = ""
    should_continue = False
    if recurrence_hit and not resolution_marker_hit and overlap >= 1:
        should_continue = True
        hit_reason = "recurrence_marker_plus_frame_overlap"
    elif recurrence_hit and not resolution_marker_hit and message_theme_hit and frame_theme_hit:
        should_continue = True
        hit_reason = "recurrence_marker_plus_theme_alignment"

    diag = {
        "recurrence_marker_hit": recurrence_hit,
        "semantic_frame_token_overlap": overlap,
        "semantic_frame_token_count": len(semantic_frame_tokens),
        "message_token_count": len(message_tokens),
        "matched_sources": matched_sources,
        "message_theme_hit": message_theme_hit,
        "frame_theme_hit": frame_theme_hit,
        "hit_reason": hit_reason,
    }
    return should_continue, diag


def _mode_and_goal_with_reason(
    phase: str,
    state_snapshot: StateSnapshot,
    *,
    user_message: str = "",
) -> tuple[str, str, str]:
    request_type = detect_request_type_v1(user_message)
    explicit_practice_request = request_type == REQUEST_TYPE_PRACTICE
    explicit_safety_request = request_type == REQUEST_TYPE_SAFETY
    example_or_explain_request = request_type in {REQUEST_TYPE_EXAMPLE, REQUEST_TYPE_EXPLAIN}

    if state_snapshot.safety_flag:
        return "safe_override", "stabilize and reduce overload", "safety_override"
    if state_snapshot.intent == "contact":
        return "validate", "hold contact and avoid overload", "explicit_contact_validate"
    if (
        example_or_explain_request
        and not explicit_practice_request
        and not explicit_safety_request
        and state_snapshot.nervous_state in {"hyper", "hypo"}
    ):
        return "reflect", "give contextual example or explanation", "example_explain_deescalate"
    if state_snapshot.nervous_state in {"hyper", "hypo"}:
        return "regulate", "softly stabilize state", "nervous_regulate"
    if state_snapshot.intent == "solution":
        return "practice", "provide one realistic next step", "solution_practice"
    if phase == "explore":
        return "explore", "expand perspective", "phase_explore"
    if phase == "clarify":
        return "reflect", "clarify key point", "phase_clarify_reflect"
    return "validate", "keep safe contact", "fallback_validate"


def _mode_and_goal(
    phase: str,
    state_snapshot: StateSnapshot,
    *,
    user_message: str = "",
) -> tuple[str, str]:
    mode, goal, _reason = _mode_and_goal_with_reason(
        phase,
        state_snapshot,
        user_message=user_message,
    )
    return mode, goal


def _derive_pattern_core_v1(
    *,
    user_message: str,
    state_snapshot: StateSnapshot,
    previous_core: str = "",
) -> str:
    previous = str(previous_core or "").strip()
    if previous:
        return previous[:220]
    if state_snapshot.intent == "contact" and state_snapshot.nervous_state == "hypo":
        return "low-resource support / short support without pressure"
    if state_snapshot.intent == "solution":
        return "request for concrete next step / actionable micro-step"
    if state_snapshot.intent == "clarify":
        return "clarifying inner pattern / focused clarification"
    if state_snapshot.intent == "vent":
        return "emotional venting / expression of strong emotion"
    fallback = " ".join((user_message or "").strip().split())
    return fallback[:120] or "conversation_support_pattern"


def _build_active_frame_v1(
    *,
    state_snapshot: StateSnapshot,
    relation: str,
    response_mode: str,
    phase: str,
) -> dict[str, str]:
    if state_snapshot.safety_flag:
        current_need = "immediate safety and stabilization"
    elif state_snapshot.intent == "contact" and state_snapshot.nervous_state == "hypo":
        current_need = "short support without pressure"
    elif state_snapshot.intent == "contact":
        current_need = "warm contact and validation"
    elif state_snapshot.intent == "solution":
        current_need = "one concrete next step"
    elif state_snapshot.intent == "clarify":
        current_need = "gentle clarification"
    elif state_snapshot.intent == "vent":
        current_need = "emotional validation"
    else:
        current_need = "explore perspective carefully"

    if state_snapshot.safety_flag:
        last_supportive_move = "safety override"
    elif relation == "new_thread":
        last_supportive_move = "started contact and matched response mode"
    elif relation == "branch":
        last_supportive_move = "acknowledged branch while preserving thread"
    elif relation == "return_to_old":
        last_supportive_move = "restored previous thread continuity"
    elif (
        relation == "continue"
        and state_snapshot.intent == "contact"
        and state_snapshot.nervous_state == "hypo"
        and phase == "clarify"
    ):
        last_supportive_move = "held low-resource thread and avoided exploration"
    elif relation == "continue":
        last_supportive_move = "continued current thread without restarting"
    else:
        last_supportive_move = "maintained thread continuity"

    if state_snapshot.safety_flag:
        next_direction = "prioritize safety"
    elif state_snapshot.nervous_state == "hypo" and state_snapshot.intent == "contact":
        next_direction = "keep answer short and low pressure"
    elif state_snapshot.nervous_state == "hyper":
        next_direction = "stabilize before analysis"
    elif state_snapshot.intent == "solution" or response_mode == "practice":
        next_direction = "offer one executable micro-step"
    elif state_snapshot.intent == "clarify":
        next_direction = "reflect one key point and ask at most one question"
    else:
        next_direction = "expand carefully without strong interpretation"

    return {
        "current_need": current_need,
        "last_supportive_move": last_supportive_move,
        "next_recommended_direction": next_direction,
    }


_RUNTIME_ACTIVE_FRAME_KEYS = {
    "active_concept",
    "dialogue_state",
    "last_assistant_offer",
    "last_direct_user_question",
    "dialogue_style_state",
}


def _merge_runtime_active_frame(
    *,
    semantic_frame: dict[str, str],
    previous_active_frame: dict[str, Any] | None,
) -> dict[str, Any]:
    merged: dict[str, Any] = dict(semantic_frame)
    previous = dict(previous_active_frame or {})
    for key in _RUNTIME_ACTIVE_FRAME_KEYS:
        if key in previous:
            merged[key] = previous[key]
    return merged


class ThreadManagerAgent:
    """Builds and updates thread state per user turn."""

    def __init__(self, model: Optional[str] = None, client: Optional[Any] = None) -> None:
        self._model = model or get_model_for_agent("thread_manager")
        self._client = client
        self.last_debug: dict[str, Any] = {}

    async def update(
        self,
        *,
        user_message: str,
        state_snapshot: StateSnapshot,
        user_id: str = "default",
        current_thread: Optional[ThreadState],
        archived_threads: list[ArchivedThread],
    ) -> ThreadState:
        try:
            now = datetime.utcnow()

            if current_thread is None:
                new_thread = self._new_thread(
                    user_message=user_message,
                    state_snapshot=state_snapshot,
                    now=now,
                    user_id=user_id,
                )
                relation_diag = self._relation_diag_no_current_thread(
                    user_message=user_message,
                    core_direction=new_thread.core_direction,
                    selected_relation="new_thread",
                    continuity=new_thread.continuity_score,
                )
                mode, goal, mode_reason = _mode_and_goal_with_reason(
                    new_thread.phase,
                    state_snapshot,
                    user_message=user_message,
                )
                self.last_debug = self._compose_diagnostics(
                    thread_state=new_thread,
                    relation=relation_diag,
                    phase={
                        "previous_phase": None,
                        "selected_phase": new_thread.phase,
                        "phase_reason": "safety_stabilize" if state_snapshot.safety_flag else "new_thread_default_clarify",
                        "turns_in_phase_before": 0,
                        "turns_in_phase_after": new_thread.turns_in_phase,
                        "closed_loops_count": len(new_thread.closed_loops),
                        "continuity_score": new_thread.continuity_score,
                    },
                    mode={
                        "selected_mode": mode,
                        "response_goal": goal,
                        "mode_reason": mode_reason,
                        "safety_flag": state_snapshot.safety_flag,
                        "intent": state_snapshot.intent,
                        "nervous_state": state_snapshot.nervous_state,
                        "phase": new_thread.phase,
                    },
                    loops={
                        "open_loops_before": 0,
                        "open_loops_after": len(new_thread.open_loops),
                        "closed_loops_before": 0,
                        "closed_loops_after": len(new_thread.closed_loops),
                        "open_loop_added": len(new_thread.open_loops) > 0,
                        "closed_loop_added": False,
                        "resolution_marker_hit": relation_diag["resolution_marker_hit"],
                    },
                    action={
                        "thread_action": "new_thread",
                        "previous_thread_id_present": False,
                        "selected_thread_id_present": bool(new_thread.thread_id),
                        "archived_previous_thread": False,
                        "restored_archived_thread": False,
                        "safety_patch_used": False,
                    },
                )
                return new_thread

            if state_snapshot.safety_flag:
                patched = self._safety_patch(
                    current_thread=current_thread,
                    state_snapshot=state_snapshot,
                    now=now,
                )
                continuity = _continuity_score(user_message, current_thread.core_direction)
                relation_diag = self._relation_diag_from_message(
                    user_message=user_message,
                    core_direction=current_thread.core_direction,
                    selected_relation="continue",
                    continuity=continuity,
                    relation_reason="safety_patch",
                    archived_threads_count=len(archived_threads),
                    current_thread_present=True,
                )
                mode, goal, mode_reason = _mode_and_goal_with_reason(
                    patched.phase,
                    state_snapshot,
                    user_message=user_message,
                )
                self.last_debug = self._compose_diagnostics(
                    thread_state=patched,
                    relation=relation_diag,
                    phase={
                        "previous_phase": current_thread.phase,
                        "selected_phase": patched.phase,
                        "phase_reason": "safety_stabilize",
                        "turns_in_phase_before": current_thread.turns_in_phase,
                        "turns_in_phase_after": patched.turns_in_phase,
                        "closed_loops_count": len(patched.closed_loops),
                        "continuity_score": patched.continuity_score,
                    },
                    mode={
                        "selected_mode": mode,
                        "response_goal": goal,
                        "mode_reason": mode_reason,
                        "safety_flag": state_snapshot.safety_flag,
                        "intent": state_snapshot.intent,
                        "nervous_state": state_snapshot.nervous_state,
                        "phase": patched.phase,
                    },
                    loops={
                        "open_loops_before": len(current_thread.open_loops),
                        "open_loops_after": len(patched.open_loops),
                        "closed_loops_before": len(current_thread.closed_loops),
                        "closed_loops_after": len(patched.closed_loops),
                        "open_loop_added": False,
                        "closed_loop_added": False,
                        "resolution_marker_hit": relation_diag["resolution_marker_hit"],
                    },
                    action={
                        "thread_action": "safety_patch",
                        "previous_thread_id_present": bool(current_thread.thread_id),
                        "selected_thread_id_present": bool(patched.thread_id),
                        "archived_previous_thread": False,
                        "restored_archived_thread": False,
                        "safety_patch_used": True,
                    },
                )
                return patched

            relation, continuity, relation_diag = self._resolve_relation_with_debug(
                user_message=user_message,
                current_thread=current_thread,
                archived_threads=archived_threads,
            )

            if relation == "return_to_old":
                restored = self._restore_archived(
                    user_message=user_message,
                    state_snapshot=state_snapshot,
                    user_id=user_id,
                    archived_threads=archived_threads,
                    now=now,
                )
                if restored is not None:
                    mode, goal, mode_reason = _mode_and_goal_with_reason(
                        restored.phase,
                        state_snapshot,
                        user_message=user_message,
                    )
                    self.last_debug = self._compose_diagnostics(
                        thread_state=restored,
                        relation=relation_diag,
                        phase={
                            "previous_phase": current_thread.phase,
                            "selected_phase": restored.phase,
                            "phase_reason": "keep_current_phase",
                            "turns_in_phase_before": current_thread.turns_in_phase,
                            "turns_in_phase_after": restored.turns_in_phase,
                            "closed_loops_count": len(restored.closed_loops),
                            "continuity_score": continuity,
                        },
                        mode={
                            "selected_mode": mode,
                            "response_goal": goal,
                            "mode_reason": mode_reason,
                            "safety_flag": state_snapshot.safety_flag,
                            "intent": state_snapshot.intent,
                            "nervous_state": state_snapshot.nervous_state,
                            "phase": restored.phase,
                        },
                        loops={
                            "open_loops_before": len(current_thread.open_loops),
                            "open_loops_after": len(restored.open_loops),
                            "closed_loops_before": len(current_thread.closed_loops),
                            "closed_loops_after": len(restored.closed_loops),
                            "open_loop_added": len(restored.open_loops) > len(current_thread.open_loops),
                            "closed_loop_added": len(restored.closed_loops) > len(current_thread.closed_loops),
                            "resolution_marker_hit": relation_diag["resolution_marker_hit"],
                        },
                        action={
                            "thread_action": "restore_archived_thread",
                            "previous_thread_id_present": bool(current_thread.thread_id),
                            "selected_thread_id_present": bool(restored.thread_id),
                            "archived_previous_thread": False,
                            "restored_archived_thread": True,
                            "safety_patch_used": False,
                        },
                    )
                    return restored

            if relation == "new_thread":
                new_thread = self._new_thread(
                    user_message=user_message,
                    state_snapshot=state_snapshot,
                    now=now,
                    user_id=user_id,
                    relation="new_thread",
                    previous_active_frame=current_thread.active_frame,
                )
                mode, goal, mode_reason = _mode_and_goal_with_reason(
                    new_thread.phase,
                    state_snapshot,
                    user_message=user_message,
                )
                self.last_debug = self._compose_diagnostics(
                    thread_state=new_thread,
                    relation=relation_diag,
                    phase={
                        "previous_phase": current_thread.phase,
                        "selected_phase": new_thread.phase,
                        "phase_reason": "new_thread_default_clarify",
                        "turns_in_phase_before": current_thread.turns_in_phase,
                        "turns_in_phase_after": new_thread.turns_in_phase,
                        "closed_loops_count": len(new_thread.closed_loops),
                        "continuity_score": continuity,
                    },
                    mode={
                        "selected_mode": mode,
                        "response_goal": goal,
                        "mode_reason": mode_reason,
                        "safety_flag": state_snapshot.safety_flag,
                        "intent": state_snapshot.intent,
                        "nervous_state": state_snapshot.nervous_state,
                        "phase": new_thread.phase,
                    },
                    loops={
                        "open_loops_before": len(current_thread.open_loops),
                        "open_loops_after": len(new_thread.open_loops),
                        "closed_loops_before": len(current_thread.closed_loops),
                        "closed_loops_after": len(new_thread.closed_loops),
                        "open_loop_added": len(new_thread.open_loops) > 0,
                        "closed_loop_added": False,
                        "resolution_marker_hit": relation_diag["resolution_marker_hit"],
                    },
                    action={
                        "thread_action": "new_thread",
                        "previous_thread_id_present": bool(current_thread.thread_id),
                        "selected_thread_id_present": bool(new_thread.thread_id),
                        "archived_previous_thread": True,
                        "restored_archived_thread": False,
                        "safety_patch_used": False,
                    },
                )
                return new_thread

            continued, phase_diag, mode_diag, loops_diag = self._continue_thread_with_debug(
                user_message=user_message,
                state_snapshot=state_snapshot,
                current_thread=current_thread,
                relation=relation,
                continuity=continuity,
                now=now,
            )
            action_name = "branch_thread" if relation == "branch" else "continue_thread"
            self.last_debug = self._compose_diagnostics(
                thread_state=continued,
                relation=relation_diag,
                phase=phase_diag,
                mode=mode_diag,
                loops=loops_diag,
                action={
                    "thread_action": action_name,
                    "previous_thread_id_present": bool(current_thread.thread_id),
                    "selected_thread_id_present": bool(continued.thread_id),
                    "archived_previous_thread": False,
                    "restored_archived_thread": False,
                    "safety_patch_used": False,
                },
            )
            return continued
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.error("[THREAD_MANAGER] update failed: %s", exc, exc_info=True)
            return self._safe_fallback(
                user_message=user_message,
                state_snapshot=state_snapshot,
                current_thread=current_thread,
                user_id=user_id,
            )

    def _relation_diag_from_message(
        self,
        *,
        user_message: str,
        core_direction: str,
        selected_relation: str,
        continuity: float,
        relation_reason: str,
        archived_threads_count: int,
        current_thread_present: bool,
        active_frame_semantic_continue_hit: bool = False,
        active_frame_semantic_continue_reason: str = "",
        semantic_frame_token_overlap: int = 0,
        semantic_frame_token_count: int = 0,
        semantic_frame_sources_checked: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        lowered = user_message.lower()
        message_tokens = _normalize_tokens(user_message)
        core_tokens = _normalize_tokens(core_direction)
        token_intersection_count = len(message_tokens & core_tokens)
        token_union_count = len(message_tokens | core_tokens)
        return {
            "selected_relation": selected_relation,
            "relation_reason": relation_reason,
            "continuity_score": continuity,
            "new_thread_threshold": _NEW_THREAD_THRESHOLD,
            "current_thread_present": current_thread_present,
            "archived_threads_count": archived_threads_count,
            "return_marker_hit": any(marker in lowered for marker in _RETURN_MARKERS),
            "followup_continue_marker_hit": any(marker in lowered for marker in _FOLLOWUP_CONTINUE_MARKERS),
            "low_resource_continue_marker_hit": any(marker in lowered for marker in _LOW_RESOURCE_CONTINUE_MARKERS),
            "branch_marker_hit": any(marker in lowered for marker in _BRANCH_MARKERS),
            "resolution_marker_hit": any(marker in lowered for marker in _RESOLUTION_MARKERS),
            "message_token_count": len(message_tokens),
            "core_token_count": len(core_tokens),
            "token_intersection_count": token_intersection_count,
            "token_union_count": token_union_count,
            "active_frame_semantic_continue_hit": active_frame_semantic_continue_hit,
            "active_frame_semantic_continue_reason": active_frame_semantic_continue_reason,
            "semantic_frame_token_overlap": semantic_frame_token_overlap,
            "semantic_frame_token_count": semantic_frame_token_count,
            "semantic_frame_sources_checked": list(semantic_frame_sources_checked or []),
        }

    def _relation_diag_no_current_thread(
        self,
        *,
        user_message: str,
        core_direction: str,
        selected_relation: str,
        continuity: float,
    ) -> dict[str, Any]:
        return self._relation_diag_from_message(
            user_message=user_message,
            core_direction=core_direction,
            selected_relation=selected_relation,
            continuity=continuity,
            relation_reason="no_current_thread",
            archived_threads_count=0,
            current_thread_present=False,
        )

    def _resolve_relation_with_debug(
        self,
        *,
        user_message: str,
        current_thread: ThreadState,
        archived_threads: list[ArchivedThread],
    ) -> tuple[str, float, dict[str, Any]]:
        continuity_raw = _continuity_score(user_message, current_thread.core_direction)
        relation = "continue"
        continuity = continuity_raw
        relation_reason = "continuity_continue"

        lowered = user_message.lower()
        return_marker_hit = any(marker in lowered for marker in _RETURN_MARKERS)
        followup_continue_marker_hit = any(marker in lowered for marker in _FOLLOWUP_CONTINUE_MARKERS)
        low_resource_continue_marker_hit = any(marker in lowered for marker in _LOW_RESOURCE_CONTINUE_MARKERS)
        branch_marker_hit = any(marker in lowered for marker in _BRANCH_MARKERS)
        resolution_marker_hit = any(marker in lowered for marker in _RESOLUTION_MARKERS)
        active_frame_hit, active_frame_diag = _active_frame_continuity_signal(
            user_message=user_message,
            current_thread=current_thread,
            resolution_marker_hit=resolution_marker_hit,
        )

        if archived_threads and return_marker_hit:
            relation = "return_to_old"
            relation_reason = "return_marker_with_archived_threads"
        elif followup_continue_marker_hit:
            relation = "continue"
            continuity = max(continuity_raw, 0.25)
            relation_reason = "followup_continue_marker"
        elif branch_marker_hit:
            relation = "branch"
            continuity = continuity_raw
            relation_reason = "branch_marker"
        elif low_resource_continue_marker_hit:
            relation = "continue"
            continuity = max(continuity_raw, 0.25)
            relation_reason = "low_resource_continuation_marker"
        elif active_frame_hit:
            relation = "continue"
            continuity = max(continuity_raw, 0.25)
            relation_reason = "active_frame_semantic_continuity"
        elif continuity_raw < _NEW_THREAD_THRESHOLD:
            relation = "new_thread"
            continuity = continuity_raw
            relation_reason = "continuity_below_threshold"

        diag = self._relation_diag_from_message(
            user_message=user_message,
            core_direction=current_thread.core_direction,
            selected_relation=relation,
            continuity=continuity,
            relation_reason=relation_reason,
            archived_threads_count=len(archived_threads),
            current_thread_present=True,
            active_frame_semantic_continue_hit=active_frame_hit,
            active_frame_semantic_continue_reason=str(active_frame_diag.get("hit_reason", "") or ""),
            semantic_frame_token_overlap=int(active_frame_diag.get("semantic_frame_token_overlap", 0) or 0),
            semantic_frame_token_count=int(active_frame_diag.get("semantic_frame_token_count", 0) or 0),
            semantic_frame_sources_checked=list(active_frame_diag.get("matched_sources", []) or []),
        )
        diag["continuity_raw"] = continuity_raw
        diag["recurrence_marker_hit"] = bool(active_frame_diag.get("recurrence_marker_hit", False))
        return relation, continuity, diag

    def _resolve_relation(
        self,
        *,
        user_message: str,
        current_thread: ThreadState,
        archived_threads: list[ArchivedThread],
    ) -> tuple[str, float]:
        relation, continuity, _debug = self._resolve_relation_with_debug(
            user_message=user_message,
            current_thread=current_thread,
            archived_threads=archived_threads,
        )
        return relation, continuity

    def _resolve_phase_with_debug(
        self,
        *,
        state_snapshot: StateSnapshot,
        current_phase: str,
        relation: str,
        turns_in_phase: int,
        closed_loops_count: int,
        continuity: float,
    ) -> tuple[str, dict[str, Any]]:
        if state_snapshot.safety_flag:
            selected_phase = "stabilize"
            phase_reason = "safety_stabilize"
        elif continuity > 0.85 and relation == "continue":
            selected_phase = current_phase
            phase_reason = "high_continuity_keep_phase"
        elif current_phase == "stabilize" and state_snapshot.nervous_state == "window":
            selected_phase = "clarify"
            phase_reason = "stabilize_to_clarify"
        elif (
            current_phase == "clarify"
            and relation == "continue"
            and (
                state_snapshot.nervous_state in {"hyper", "hypo"}
                or state_snapshot.intent == "contact"
            )
        ):
            selected_phase = "clarify"
            phase_reason = (
                "low_resource_hold_phase"
                if state_snapshot.nervous_state in {"hyper", "hypo"}
                else "contact_hold_phase"
            )
        elif current_phase == "clarify" and relation == "continue" and turns_in_phase >= 2:
            selected_phase = "explore"
            phase_reason = "clarify_to_explore"
        elif current_phase == "explore" and closed_loops_count >= 2:
            selected_phase = "integrate"
            phase_reason = "explore_to_integrate"
        elif current_phase == "integrate" and relation in {"branch", "new_thread"}:
            selected_phase = "clarify"
            phase_reason = "integrate_to_clarify_on_branch_or_new"
        else:
            selected_phase = current_phase
            phase_reason = "keep_current_phase"

        turns_in_phase_after = turns_in_phase + 1 if selected_phase == current_phase else 1
        return selected_phase, {
            "previous_phase": current_phase,
            "selected_phase": selected_phase,
            "phase_reason": phase_reason,
            "turns_in_phase_before": turns_in_phase,
            "turns_in_phase_after": turns_in_phase_after,
            "closed_loops_count": closed_loops_count,
            "continuity_score": continuity,
        }

    def _resolve_phase(
        self,
        *,
        state_snapshot: StateSnapshot,
        current_phase: str,
        relation: str,
        turns_in_phase: int,
        closed_loops_count: int,
        continuity: float,
    ) -> str:
        phase, _debug = self._resolve_phase_with_debug(
            state_snapshot=state_snapshot,
            current_phase=current_phase,
            relation=relation,
            turns_in_phase=turns_in_phase,
            closed_loops_count=closed_loops_count,
            continuity=continuity,
        )
        return phase

    def _new_thread(
        self,
        *,
        user_message: str,
        state_snapshot: StateSnapshot,
        now: datetime,
        user_id: str,
        relation: str = "new_thread",
        previous_active_frame: dict[str, Any] | None = None,
    ) -> ThreadState:
        phase = "stabilize" if state_snapshot.safety_flag else "clarify"
        mode, goal = _mode_and_goal(phase, state_snapshot, user_message=user_message)
        pattern_core = _derive_pattern_core_v1(
            user_message=user_message,
            state_snapshot=state_snapshot,
        )
        active_frame = _build_active_frame_v1(
            state_snapshot=state_snapshot,
            relation=relation,
            response_mode=mode,
            phase=phase,
        )
        active_frame = _merge_runtime_active_frame(
            semantic_frame=active_frame,
            previous_active_frame=previous_active_frame,
        )
        return ThreadState(
            thread_id=f"tm_{uuid.uuid4().hex[:12]}",
            user_id=user_id,
            core_direction=user_message.strip()[:140] or "new_topic",
            pattern_core=pattern_core,
            active_frame=active_frame,
            phase=phase,
            open_loops=[user_message.strip()[:200]] if "?" in user_message else [],
            closed_loops=[],
            nervous_state=state_snapshot.nervous_state,
            intent=state_snapshot.intent,
            openness=state_snapshot.openness,
            ok_position=state_snapshot.ok_position,
            relation_to_thread=relation,  # type: ignore[arg-type]
            response_goal=goal,
            response_mode=mode,  # type: ignore[arg-type]
            must_avoid=self._build_must_avoid(
                closed_loops=[],
                safety_flag=state_snapshot.safety_flag,
                phase=phase,
                ok_position=state_snapshot.ok_position,
                relation=relation,
            ),
            continuity_score=1.0 if relation == "new_thread" else 0.0,
            turns_in_phase=1,
            last_meaningful_shift="new_thread",
            safety_active=state_snapshot.safety_flag,
            created_at=now,
            updated_at=now,
        )

    def _continue_thread_with_debug(
        self,
        *,
        user_message: str,
        state_snapshot: StateSnapshot,
        current_thread: ThreadState,
        relation: str,
        continuity: float,
        now: datetime,
    ) -> tuple[ThreadState, dict[str, Any], dict[str, Any], dict[str, Any]]:
        open_loops = list(current_thread.open_loops)
        closed_loops = list(current_thread.closed_loops)
        open_before = len(open_loops)
        closed_before = len(closed_loops)
        lowered = user_message.lower()

        open_loop_added = False
        if relation == "branch" and user_message.strip():
            open_loops.append(user_message.strip()[:220])
            open_loop_added = True

        resolution_marker_hit = any(marker in lowered for marker in _RESOLUTION_MARKERS)
        closed_loop_added = False
        if resolution_marker_hit and open_loops:
            closed_loops.append(open_loops.pop(0))
            closed_loop_added = True

        phase, phase_diag = self._resolve_phase_with_debug(
            state_snapshot=state_snapshot,
            current_phase=current_thread.phase,
            relation=relation,
            turns_in_phase=current_thread.turns_in_phase,
            closed_loops_count=len(closed_loops),
            continuity=continuity,
        )
        mode, goal, mode_reason = _mode_and_goal_with_reason(
            phase,
            state_snapshot,
            user_message=user_message,
        )
        turns_in_phase = phase_diag["turns_in_phase_after"]
        pattern_core = _derive_pattern_core_v1(
            user_message=user_message,
            state_snapshot=state_snapshot,
            previous_core=current_thread.pattern_core,
        )
        active_frame = _build_active_frame_v1(
            state_snapshot=state_snapshot,
            relation=relation,
            response_mode=mode,
            phase=phase,
        )
        active_frame = _merge_runtime_active_frame(
            semantic_frame=active_frame,
            previous_active_frame=current_thread.active_frame,
        )
        updated = ThreadState(
            thread_id=current_thread.thread_id,
            user_id=current_thread.user_id,
            core_direction=current_thread.core_direction,
            pattern_core=pattern_core,
            active_frame=active_frame,
            phase=phase,  # type: ignore[arg-type]
            open_loops=open_loops,
            closed_loops=closed_loops,
            nervous_state=state_snapshot.nervous_state,
            intent=state_snapshot.intent,
            openness=state_snapshot.openness,
            ok_position=state_snapshot.ok_position,
            relation_to_thread=relation,  # type: ignore[arg-type]
            response_goal=goal,
            response_mode=mode,  # type: ignore[arg-type]
            must_avoid=self._build_must_avoid(
                closed_loops=closed_loops,
                safety_flag=state_snapshot.safety_flag,
                phase=phase,
                ok_position=state_snapshot.ok_position,
                relation=relation,
            ),
            continuity_score=continuity,
            turns_in_phase=turns_in_phase,
            last_meaningful_shift=relation if relation != "continue" else "",
            safety_active=state_snapshot.safety_flag,
            created_at=current_thread.created_at,
            updated_at=now,
        )
        mode_diag = {
            "selected_mode": mode,
            "response_goal": goal,
            "mode_reason": mode_reason,
            "safety_flag": state_snapshot.safety_flag,
            "intent": state_snapshot.intent,
            "nervous_state": state_snapshot.nervous_state,
            "phase": phase,
        }
        loops_diag = {
            "open_loops_before": open_before,
            "open_loops_after": len(open_loops),
            "closed_loops_before": closed_before,
            "closed_loops_after": len(closed_loops),
            "open_loop_added": open_loop_added,
            "closed_loop_added": closed_loop_added,
            "resolution_marker_hit": resolution_marker_hit,
        }
        return updated, phase_diag, mode_diag, loops_diag

    def _continue_thread(
        self,
        *,
        user_message: str,
        state_snapshot: StateSnapshot,
        current_thread: ThreadState,
        relation: str,
        continuity: float,
        now: datetime,
    ) -> ThreadState:
        updated, _phase_diag, _mode_diag, _loops_diag = self._continue_thread_with_debug(
            user_message=user_message,
            state_snapshot=state_snapshot,
            current_thread=current_thread,
            relation=relation,
            continuity=continuity,
            now=now,
        )
        return updated

    def _restore_archived(
        self,
        *,
        user_message: str,
        state_snapshot: StateSnapshot,
        user_id: str,
        archived_threads: list[ArchivedThread],
        now: datetime,
    ) -> Optional[ThreadState]:
        if not archived_threads:
            return None
        message_tokens = _normalize_tokens(user_message)
        best = max(
            archived_threads,
            key=lambda item: len(message_tokens & _normalize_tokens(item.core_direction)),
        )
        mode, goal = _mode_and_goal(
            best.final_phase,
            state_snapshot,
            user_message=user_message,
        )
        active_frame = _build_active_frame_v1(
            state_snapshot=state_snapshot,
            relation="return_to_old",
            response_mode=mode,
            phase=best.final_phase,
        )
        return ThreadState(
            thread_id=best.thread_id,
            user_id=user_id,
            core_direction=best.core_direction,
            pattern_core=best.pattern_core,
            active_frame=dict(best.active_frame) or active_frame,
            phase=best.final_phase,  # type: ignore[arg-type]
            open_loops=list(best.open_loops),
            closed_loops=list(best.closed_loops),
            nervous_state=state_snapshot.nervous_state,
            intent=state_snapshot.intent,
            openness=state_snapshot.openness,
            ok_position=state_snapshot.ok_position,
            relation_to_thread="return_to_old",
            response_goal=goal,
            response_mode=mode,  # type: ignore[arg-type]
            must_avoid=self._build_must_avoid(
                closed_loops=best.closed_loops,
                safety_flag=state_snapshot.safety_flag,
                phase=best.final_phase,
                ok_position=state_snapshot.ok_position,
                relation="return_to_old",
            ),
            continuity_score=0.9,
            turns_in_phase=1,
            last_meaningful_shift="return_to_old",
            safety_active=state_snapshot.safety_flag,
            created_at=now,
            updated_at=now,
        )

    def _safety_patch(
        self,
        *,
        current_thread: ThreadState,
        state_snapshot: StateSnapshot,
        now: datetime,
    ) -> ThreadState:
        active_frame = _build_active_frame_v1(
            state_snapshot=state_snapshot,
            relation="continue",
            response_mode="safe_override",
            phase="stabilize",
        )
        active_frame = _merge_runtime_active_frame(
            semantic_frame=active_frame,
            previous_active_frame=current_thread.active_frame,
        )
        return ThreadState(
            thread_id=current_thread.thread_id,
            user_id=current_thread.user_id,
            core_direction=current_thread.core_direction,
            pattern_core=current_thread.pattern_core,
            active_frame=active_frame,
            phase="stabilize",
            open_loops=list(current_thread.open_loops),
            closed_loops=list(current_thread.closed_loops),
            nervous_state=state_snapshot.nervous_state,
            intent=state_snapshot.intent,
            openness=state_snapshot.openness,
            ok_position=state_snapshot.ok_position,
            relation_to_thread="continue",
            response_goal="stabilize and reduce overload",
            response_mode="safe_override",
            must_avoid=self._build_must_avoid(
                closed_loops=current_thread.closed_loops,
                safety_flag=True,
                phase="stabilize",
                ok_position=state_snapshot.ok_position,
                relation="continue",
            ),
            continuity_score=current_thread.continuity_score,
            turns_in_phase=current_thread.turns_in_phase + 1,
            last_meaningful_shift="safety_override",
            safety_active=True,
            created_at=current_thread.created_at,
            updated_at=now,
        )

    def _build_summary_flags(
        self,
        *,
        relation: dict[str, Any],
        phase: dict[str, Any],
        mode: dict[str, Any],
        loops: dict[str, Any],
        action: dict[str, Any],
        semantic_frame: dict[str, Any],
    ) -> list[str]:
        flags: list[str] = []

        if relation.get("relation_reason") == "continuity_below_threshold":
            flags.append("low_continuity_new_thread")
        if relation.get("relation_reason") == "followup_continue_marker" and (
            float(relation.get("continuity_raw") or 0.0) < _NEW_THREAD_THRESHOLD
        ):
            flags.append("followup_marker_overrode_low_overlap")
        if relation.get("relation_reason") == "low_resource_continuation_marker":
            flags.append("low_resource_followup_continued")
            if float(relation.get("continuity_raw") or 0.0) < _NEW_THREAD_THRESHOLD:
                flags.append("low_resource_marker_overrode_low_overlap")
        if relation.get("relation_reason") == "active_frame_semantic_continuity":
            flags.append("active_frame_semantic_continuity")
            if float(relation.get("continuity_raw") or 0.0) < _NEW_THREAD_THRESHOLD:
                flags.append("semantic_guard_overrode_low_overlap")
        if relation.get("branch_marker_hit"):
            flags.append("branch_marker_hit")
        if relation.get("return_marker_hit"):
            flags.append("return_marker_hit")
        if relation.get("resolution_marker_hit") or loops.get("resolution_marker_hit"):
            flags.append("resolution_marker_hit")
        if action.get("safety_patch_used"):
            flags.append("safety_patch_used")
        if mode.get("mode_reason") == "solution_practice":
            flags.append("solution_practice_mode")
        if mode.get("mode_reason") == "explicit_contact_validate":
            flags.append("contact_validate_mode")
        if mode.get("mode_reason") == "nervous_regulate":
            flags.append("nervous_regulate_mode")
        if phase.get("phase_reason") == "low_resource_hold_phase":
            flags.append("low_resource_phase_hold")
        if phase.get("phase_reason") == "contact_hold_phase":
            flags.append("contact_phase_hold")
        if phase.get("previous_phase") != phase.get("selected_phase"):
            flags.append("phase_transition")
        if semantic_frame.get("pattern_core_present"):
            flags.append("pattern_core_present")
        if semantic_frame.get("active_frame_present"):
            flags.append("active_frame_present")
        if semantic_frame.get("current_need") == "short support without pressure":
            flags.append("low_resource_active_frame")
        if semantic_frame.get("current_need") == "one concrete next step":
            flags.append("solution_active_frame")

        return flags

    def _build_semantic_frame_diag(self, thread_state: ThreadState) -> dict[str, Any]:
        active_frame = thread_state.active_frame if isinstance(thread_state.active_frame, dict) else {}
        keys = [key for key in ("current_need", "last_supportive_move", "next_recommended_direction") if key in active_frame]
        return {
            "pattern_core_present": bool(str(thread_state.pattern_core or "").strip()),
            "active_frame_present": bool(active_frame),
            "active_frame_keys": keys,
            "current_need": str(active_frame.get("current_need", "") or ""),
            "next_recommended_direction": str(active_frame.get("next_recommended_direction", "") or ""),
        }

    def _compose_diagnostics(
        self,
        *,
        thread_state: ThreadState,
        relation: dict[str, Any],
        phase: dict[str, Any],
        mode: dict[str, Any],
        loops: dict[str, Any],
        action: dict[str, Any],
    ) -> dict[str, Any]:
        semantic_frame = self._build_semantic_frame_diag(thread_state)
        return {
            "version": THREAD_DIAGNOSTICS_VERSION,
            "relation": relation,
            "phase": phase,
            "mode": mode,
            "loops": loops,
            "action": action,
            "semantic_frame": semantic_frame,
            "summary_flags": self._build_summary_flags(
                relation=relation,
                phase=phase,
                mode=mode,
                loops=loops,
                action=action,
                semantic_frame=semantic_frame,
            ),
        }

    def _build_must_avoid(
        self,
        *,
        closed_loops: list[str],
        safety_flag: bool,
        phase: str,
        ok_position: str,
        relation: str,
    ) -> list[str]:
        must_avoid = list(closed_loops)
        if relation == "continue":
            must_avoid.append("open_new_topics_without_user_request")
        if phase == "stabilize":
            must_avoid.extend(["deep_analysis", "complex_practices"])
        if ok_position == "I-W-":
            must_avoid.append("rhetorical_questions")
        if safety_flag:
            must_avoid.extend(["analysis", "practices", "too_many_questions"])
        seen = set()
        result = []
        for item in must_avoid:
            if item not in seen:
                result.append(item)
                seen.add(item)
        return result

    def _safe_fallback(
        self,
        *,
        user_message: str,
        state_snapshot: StateSnapshot,
        current_thread: Optional[ThreadState],
        user_id: str,
    ) -> ThreadState:
        now = datetime.utcnow()
        if current_thread is None:
            fallback_thread = self._new_thread(
                user_message=user_message,
                state_snapshot=state_snapshot,
                now=now,
                user_id=user_id,
            )
            relation_diag = self._relation_diag_no_current_thread(
                user_message=user_message,
                core_direction=fallback_thread.core_direction,
                selected_relation="new_thread",
                continuity=fallback_thread.continuity_score,
            )
            relation_diag["relation_reason"] = "new_thread_fallback"
            self.last_debug = self._compose_diagnostics(
                thread_state=fallback_thread,
                relation=relation_diag,
                phase={
                    "previous_phase": None,
                    "selected_phase": fallback_thread.phase,
                    "phase_reason": "new_thread_default_clarify",
                    "turns_in_phase_before": 0,
                    "turns_in_phase_after": fallback_thread.turns_in_phase,
                    "closed_loops_count": len(fallback_thread.closed_loops),
                    "continuity_score": fallback_thread.continuity_score,
                },
                mode={
                    "selected_mode": fallback_thread.response_mode,
                    "response_goal": fallback_thread.response_goal,
                    "mode_reason": "fallback_validate",
                    "safety_flag": state_snapshot.safety_flag,
                    "intent": state_snapshot.intent,
                    "nervous_state": state_snapshot.nervous_state,
                    "phase": fallback_thread.phase,
                },
                loops={
                    "open_loops_before": 0,
                    "open_loops_after": len(fallback_thread.open_loops),
                    "closed_loops_before": 0,
                    "closed_loops_after": len(fallback_thread.closed_loops),
                    "open_loop_added": len(fallback_thread.open_loops) > 0,
                    "closed_loop_added": False,
                    "resolution_marker_hit": relation_diag["resolution_marker_hit"],
                },
                action={
                    "thread_action": "safe_fallback",
                    "previous_thread_id_present": False,
                    "selected_thread_id_present": bool(fallback_thread.thread_id),
                    "archived_previous_thread": False,
                    "restored_archived_thread": False,
                    "safety_patch_used": False,
                },
            )
            return fallback_thread

        fallback_thread = ThreadState(
            thread_id=current_thread.thread_id,
            user_id=current_thread.user_id,
            core_direction=current_thread.core_direction,
            pattern_core=_derive_pattern_core_v1(
                user_message=user_message,
                state_snapshot=state_snapshot,
                previous_core=current_thread.pattern_core,
            ),
            active_frame=_build_active_frame_v1(
                state_snapshot=state_snapshot,
                relation="continue",
                response_mode="safe_override" if state_snapshot.safety_flag else "reflect",
                phase="stabilize" if state_snapshot.safety_flag else current_thread.phase,
            ),
            phase="stabilize" if state_snapshot.safety_flag else current_thread.phase,
            open_loops=list(current_thread.open_loops),
            closed_loops=list(current_thread.closed_loops),
            nervous_state=state_snapshot.nervous_state,
            intent=state_snapshot.intent,
            openness=state_snapshot.openness,
            ok_position=state_snapshot.ok_position,
            relation_to_thread="continue",
            response_goal="maintain safe contact",
            response_mode="safe_override" if state_snapshot.safety_flag else "reflect",
            must_avoid=self._build_must_avoid(
                closed_loops=current_thread.closed_loops,
                safety_flag=state_snapshot.safety_flag,
                phase=current_thread.phase,
                ok_position=state_snapshot.ok_position,
                relation="continue",
            ),
            continuity_score=current_thread.continuity_score,
            turns_in_phase=current_thread.turns_in_phase + 1,
            last_meaningful_shift="fallback",
            safety_active=state_snapshot.safety_flag,
            created_at=current_thread.created_at,
            updated_at=now,
        )
        relation_diag = self._relation_diag_from_message(
            user_message=user_message,
            core_direction=current_thread.core_direction,
            selected_relation="continue",
            continuity=current_thread.continuity_score,
            relation_reason="new_thread_fallback",
            archived_threads_count=0,
            current_thread_present=True,
        )
        mode_reason = "safety_override" if state_snapshot.safety_flag else "fallback_validate"
        self.last_debug = self._compose_diagnostics(
            thread_state=fallback_thread,
            relation=relation_diag,
            phase={
                "previous_phase": current_thread.phase,
                "selected_phase": fallback_thread.phase,
                "phase_reason": "keep_current_phase",
                "turns_in_phase_before": current_thread.turns_in_phase,
                "turns_in_phase_after": fallback_thread.turns_in_phase,
                "closed_loops_count": len(fallback_thread.closed_loops),
                "continuity_score": fallback_thread.continuity_score,
            },
            mode={
                "selected_mode": fallback_thread.response_mode,
                "response_goal": fallback_thread.response_goal,
                "mode_reason": mode_reason,
                "safety_flag": state_snapshot.safety_flag,
                "intent": state_snapshot.intent,
                "nervous_state": state_snapshot.nervous_state,
                "phase": fallback_thread.phase,
            },
            loops={
                "open_loops_before": len(current_thread.open_loops),
                "open_loops_after": len(fallback_thread.open_loops),
                "closed_loops_before": len(current_thread.closed_loops),
                "closed_loops_after": len(fallback_thread.closed_loops),
                "open_loop_added": False,
                "closed_loop_added": False,
                "resolution_marker_hit": relation_diag["resolution_marker_hit"],
            },
            action={
                "thread_action": "safe_fallback",
                "previous_thread_id_present": bool(current_thread.thread_id),
                "selected_thread_id_present": bool(fallback_thread.thread_id),
                "archived_previous_thread": False,
                "restored_archived_thread": False,
                "safety_patch_used": False,
            },
        )
        return fallback_thread


thread_manager_agent = ThreadManagerAgent()
