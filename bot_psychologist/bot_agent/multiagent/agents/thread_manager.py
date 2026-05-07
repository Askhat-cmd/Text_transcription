"""Thread Manager agent for NEO multi-agent runtime."""

from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime
from typing import Any, Optional

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


def _mode_and_goal_with_reason(phase: str, state_snapshot: StateSnapshot) -> tuple[str, str, str]:
    if state_snapshot.safety_flag:
        return "safe_override", "stabilize and reduce overload", "safety_override"
    if state_snapshot.intent == "contact":
        return "validate", "hold contact and avoid overload", "explicit_contact_validate"
    if state_snapshot.nervous_state in {"hyper", "hypo"}:
        return "regulate", "softly stabilize state", "nervous_regulate"
    if state_snapshot.intent == "solution":
        return "practice", "provide one realistic next step", "solution_practice"
    if phase == "explore":
        return "explore", "expand perspective", "phase_explore"
    if phase == "clarify":
        return "reflect", "clarify key point", "phase_clarify_reflect"
    return "validate", "keep safe contact", "fallback_validate"


def _mode_and_goal(phase: str, state_snapshot: StateSnapshot) -> tuple[str, str]:
    mode, goal, _reason = _mode_and_goal_with_reason(phase, state_snapshot)
    return mode, goal


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
                mode, goal, mode_reason = _mode_and_goal_with_reason(new_thread.phase, state_snapshot)
                self.last_debug = self._compose_diagnostics(
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
                mode, goal, mode_reason = _mode_and_goal_with_reason(patched.phase, state_snapshot)
                self.last_debug = self._compose_diagnostics(
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
                    mode, goal, mode_reason = _mode_and_goal_with_reason(restored.phase, state_snapshot)
                    self.last_debug = self._compose_diagnostics(
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
                )
                mode, goal, mode_reason = _mode_and_goal_with_reason(new_thread.phase, state_snapshot)
                self.last_debug = self._compose_diagnostics(
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
        )
        diag["continuity_raw"] = continuity_raw
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
    ) -> ThreadState:
        phase = "stabilize" if state_snapshot.safety_flag else "clarify"
        mode, goal = _mode_and_goal(phase, state_snapshot)
        return ThreadState(
            thread_id=f"tm_{uuid.uuid4().hex[:12]}",
            user_id=user_id,
            core_direction=user_message.strip()[:140] or "new_topic",
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
        mode, goal, mode_reason = _mode_and_goal_with_reason(phase, state_snapshot)
        turns_in_phase = phase_diag["turns_in_phase_after"]
        updated = ThreadState(
            thread_id=current_thread.thread_id,
            user_id=current_thread.user_id,
            core_direction=current_thread.core_direction,
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
        mode, goal = _mode_and_goal(best.final_phase, state_snapshot)
        return ThreadState(
            thread_id=best.thread_id,
            user_id=user_id,
            core_direction=best.core_direction,
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
        return ThreadState(
            thread_id=current_thread.thread_id,
            user_id=current_thread.user_id,
            core_direction=current_thread.core_direction,
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
        if phase.get("previous_phase") != phase.get("selected_phase"):
            flags.append("phase_transition")

        return flags

    def _compose_diagnostics(
        self,
        *,
        relation: dict[str, Any],
        phase: dict[str, Any],
        mode: dict[str, Any],
        loops: dict[str, Any],
        action: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "version": THREAD_DIAGNOSTICS_VERSION,
            "relation": relation,
            "phase": phase,
            "mode": mode,
            "loops": loops,
            "action": action,
            "summary_flags": self._build_summary_flags(
                relation=relation,
                phase=phase,
                mode=mode,
                loops=loops,
                action=action,
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
