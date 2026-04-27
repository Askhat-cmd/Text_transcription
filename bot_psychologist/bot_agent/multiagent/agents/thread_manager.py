"""Thread Manager agent for NEO multi-agent runtime."""

from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime
from typing import Optional

from ..contracts.state_snapshot import StateSnapshot
from ..contracts.thread_state import ArchivedThread, ThreadState


logger = logging.getLogger(__name__)

_RETURN_MARKERS = (
    "return to",
    "go back",
    "continue that",
    "same topic",
    "\u0432\u0435\u0440\u043d\u0435\u043c\u0441\u044f",
    "\u0432\u0435\u0440\u043d\u0451\u043c\u0441\u044f",
    "\u0432\u0435\u0440\u043d\u0443\u0442\u044c\u0441\u044f",
    "\u043a \u043f\u0440\u043e\u0448\u043b\u043e\u0439 \u0442\u0435\u043c\u0435",
)
_RESOLUTION_MARKERS = (
    "resolved",
    "understood",
    "thanks",
    "done",
    "clear",
    "\u043f\u043e\u043d\u044f\u043b",
    "\u043f\u043e\u043d\u044f\u043b\u0430",
    "\u0441\u043f\u0430\u0441\u0438\u0431\u043e",
    "\u0440\u0430\u0437\u043e\u0431\u0440\u0430\u043b\u0441\u044f",
    "\u0440\u0430\u0437\u043e\u0431\u0440\u0430\u043b\u0430\u0441\u044c",
)
_BRANCH_MARKERS = (
    "also",
    "and another",
    "what if",
    "by the way",
    "next question",
    "\u0435\u0449\u0435",
    "\u0435\u0449\u0451",
    "\u0430 \u0435\u0449\u0435",
    "\u0430 \u0435\u0449\u0451",
    "\u043a\u0441\u0442\u0430\u0442\u0438",
)
_NEW_THREAD_THRESHOLD = 0.20
_FOLLOWUP_CONTINUE_MARKERS = (
    "\u0442\u044b \u043f\u0440\u0430\u0432\u0430",
    "\u0442\u044b \u043f\u0440\u0430\u0432",
    "\u0432\u044b \u043f\u0440\u0430\u0432\u044b",
    "\u044f \u043f\u043e\u043d\u0438\u043c\u0430\u044e",
    "\u043e\u0431 \u044d\u0442\u043e\u043c",
    "\u043f\u0440\u043e \u044d\u0442\u043e",
    "\u043f\u043e \u044d\u0442\u043e\u043c\u0443 \u043f\u043e\u0432\u043e\u0434\u0443",
    "\u043d\u043e \u043a\u0430\u043a \u043c\u043d\u0435",
    "\u043a\u0430\u043a \u043c\u043d\u0435 \u043d\u0435",
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


def _mode_and_goal(phase: str, state_snapshot: StateSnapshot) -> tuple[str, str]:
    if state_snapshot.safety_flag:
        return "safe_override", "stabilize and reduce overload"
    if state_snapshot.intent == "contact":
        return "validate", "hold contact and avoid overload"
    if state_snapshot.nervous_state in {"hyper", "hypo"}:
        return "regulate", "softly stabilize state"
    if phase == "explore" and state_snapshot.intent == "solution":
        return "practice", "provide one realistic next step"
    if phase == "explore":
        return "explore", "expand perspective"
    if phase == "clarify":
        return "reflect", "clarify key point"
    return "validate", "keep safe contact"


class ThreadManagerAgent:
    """Builds and updates thread state per user turn."""

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
                return self._new_thread(
                    user_message=user_message,
                    state_snapshot=state_snapshot,
                    now=now,
                    user_id=user_id,
                )

            if state_snapshot.safety_flag:
                return self._safety_patch(
                    current_thread=current_thread,
                    state_snapshot=state_snapshot,
                    now=now,
                )

            relation, continuity = self._resolve_relation(
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
                    return restored

            if relation == "new_thread":
                return self._new_thread(
                    user_message=user_message,
                    state_snapshot=state_snapshot,
                    now=now,
                    user_id=user_id,
                    relation="new_thread",
                )

            return self._continue_thread(
                user_message=user_message,
                state_snapshot=state_snapshot,
                current_thread=current_thread,
                relation=relation,
                continuity=continuity,
                now=now,
            )
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.error("[THREAD_MANAGER] update failed: %s", exc, exc_info=True)
            return self._safe_fallback(
                user_message=user_message,
                state_snapshot=state_snapshot,
                current_thread=current_thread,
                user_id=user_id,
            )

    def _resolve_relation(
        self,
        *,
        user_message: str,
        current_thread: ThreadState,
        archived_threads: list[ArchivedThread],
    ) -> tuple[str, float]:
        lowered = user_message.lower()
        continuity = _continuity_score(user_message, current_thread.core_direction)

        if archived_threads and any(marker in lowered for marker in _RETURN_MARKERS):
            return "return_to_old", continuity
        if any(marker in lowered for marker in _FOLLOWUP_CONTINUE_MARKERS):
            return "continue", max(continuity, 0.25)
        if continuity < _NEW_THREAD_THRESHOLD:
            return "new_thread", continuity
        if any(marker in lowered for marker in _BRANCH_MARKERS):
            return "branch", continuity
        return "continue", continuity

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
        if state_snapshot.safety_flag:
            return "stabilize"
        if continuity > 0.85 and relation == "continue":
            return current_phase
        if current_phase == "stabilize" and state_snapshot.nervous_state == "window":
            return "clarify"
        if current_phase == "clarify" and relation == "continue" and turns_in_phase >= 2:
            return "explore"
        if current_phase == "explore" and closed_loops_count >= 2:
            return "integrate"
        if current_phase == "integrate" and relation in {"branch", "new_thread"}:
            return "clarify"
        return current_phase

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
        open_loops = list(current_thread.open_loops)
        closed_loops = list(current_thread.closed_loops)
        lowered = user_message.lower()

        if relation == "branch" and user_message.strip():
            open_loops.append(user_message.strip()[:220])

        if any(marker in lowered for marker in _RESOLUTION_MARKERS) and open_loops:
            closed_loops.append(open_loops.pop(0))

        phase = self._resolve_phase(
            state_snapshot=state_snapshot,
            current_phase=current_thread.phase,
            relation=relation,
            turns_in_phase=current_thread.turns_in_phase,
            closed_loops_count=len(closed_loops),
            continuity=continuity,
        )
        mode, goal = _mode_and_goal(phase, state_snapshot)
        turns_in_phase = current_thread.turns_in_phase + 1 if phase == current_thread.phase else 1
        return ThreadState(
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
            return self._new_thread(
                user_message=user_message,
                state_snapshot=state_snapshot,
                now=now,
                user_id=user_id,
            )
        return ThreadState(
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


thread_manager_agent = ThreadManagerAgent()

