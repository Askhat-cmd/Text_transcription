# PRD-047.31-HF1 Implementation Report

## Status
- `completed_main_push`

## Delivery Metadata
- main implementation commit: `13db9ce`
- main push target: `origin/main`

## Scope Delivered
- Repaired explicit practice-request detection in the latest-turn layer so generic requests like `Дай мне какую-нибудь практику...` route to `practice_request` even without `?`.
- Repaired stale `must_answer` carry-over by letting the explicit current practice request replace the previous unanswered concrete question.
- Preserved thread continuity for explicit practice follow-ups after a concrete anger/boss discussion, even when lexical overlap is low.
- Added narrow Writer grounding for explicit practice turns: only `practice`, `dialogue_move`, `anti_pattern`, and `safety` types may become Writer-visible; broad concept/mechanism chunks remain hidden by default.
- Added compact runtime trace note for explicit practice mode without exposing raw chunks.

## Code Changes
- `bot_psychologist/bot_agent/multiagent/dialogue_act_resolver.py`
  - Added generic explicit practice-request recognition.
- `bot_psychologist/bot_agent/multiagent/unanswered_question_tracker.py`
  - Treats `practice_request` as the current authoritative unanswered request.
- `bot_psychologist/bot_agent/multiagent/final_answer_directive.py`
  - Uses the latest explicit practice request as `must_answer`.
- `bot_psychologist/bot_agent/multiagent/agents/thread_manager.py`
  - Keeps explicit practice follow-ups in the current thread with `relation_reason=explicit_practice_request_continuation`.
- `bot_psychologist/bot_agent/multiagent/writer_context_package.py`
  - Added narrow practice-grounding allowlist and Writer payload filtering.
- `bot_psychologist/bot_agent/multiagent/runtime_trace_summary.py`
  - Added explicit practice-request runtime note for compact trace surfaces.

## Test Coverage Added/Updated
- `bot_psychologist/tests/test_prd_047_31_hf1_practice_request_authority.py`
  - explicit practice route
  - stale unanswered-question override
  - latest `must_answer`
  - generic productivity fallback rejection
  - thread continuation
- `bot_psychologist/tests/test_prd_047_30_writer_grounding_visibility.py`
  - narrow practice grounding allowlist
  - `no_internal_db` suppression still wins
- `bot_psychologist/tests/test_prd_047_30_runtime_trace_summary.py`
  - compact explicit-practice trace note

## Live Outcome
- After full backend/frontend restart, the `ЧАТ_С_БОТОМ2` scenario no longer returns the stale `открой задачу / 5 минут` fallback.
- Live trace now shows:
  - `relation_reason=explicit_practice_request_continuation`
  - `answer_obligation=provide_one_bounded_practice`
  - `writer_grounding_visibility_v1.reason=explicit_practice_request_narrow_grounding`
  - `allowed_grounding_types=["practice"]`
  - `practice_request_runtime_note=Detected explicit practice request. Forced contextual practice answer. KB remains optional/narrow.`

## Retirement Candidates Observed During HF1
- legacy generic productivity fallback phrase family around `открой задачу / 5 минут`
- residual support-turn verbosity that still leans too explanatory when the user only wants presence/support
- legacy `datetime.utcnow()` usage inside thread-manager path and tests
- hybrid planner `legacy_fallback_used` noise on this path even though answer quality is now repaired
