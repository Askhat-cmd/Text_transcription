# PRD-047.31-HF1 Live Smoke Report

## Restart Proof
- Killed stale backend listener: `PID 21816`
- Killed stale frontend listener: `PID 15884`
- Restarted backend via `bot_psychologist/tools/start_pilot_web_chat_backend.ps1`
- Restarted frontend via `npm run dev` in `bot_psychologist/web_ui`
- Healthy after restart:
  - `http://127.0.0.1:8001/api/v1/health` -> `healthy`
  - `http://localhost:3000` -> `200`
- Active listeners after restart:
  - backend `:8001` -> `PID 23096` (parent `23144`)
  - frontend `:3000` -> `PID 24596`

## Mandatory Scenario
- Case: `CHAT2-EXPLICIT-PRACTICE-001`
- Session: `prd04731-main`
- Result: `passed`
- Final answer shape:
  - one contextual practice about anger/non-reactivity in the boss/lying thread
  - includes a pause/label/breathing step plus neutral follow-up wording
  - does not contain `открой задачу`, `первый минимальный фрагмент`, or `5 минут`
- Key live trace facts:
  - `relation_to_thread=continue`
  - `relation_reason=explicit_practice_request_continuation`
  - `answer_obligation=provide_one_bounded_practice`
  - `writer_grounding_visibility.reason=explicit_practice_request_narrow_grounding`
  - `allowed_grounding_types=["practice"]`
  - `practice_request_runtime_note=Detected explicit practice request. Forced contextual practice answer. KB remains optional/narrow.`

## Additional Smoke Cases
- `A-SUPPORT-NO-PRACTICE-2` -> `passed`
  - user asked for support/presence, not practice
  - answer stayed support-oriented
  - `answer_obligation=answer_concrete_situation`
  - `writer_grounding_visibility.reason=non_kb_emotional_support_turn`
  - `explicit_practice_request=false`
- `B-NO-PRACTICE-REQUEST-2` -> `passed_with_warning`
  - user explicitly blocked practice and asked for explanation
  - answer stayed explanation-first, not exercise-first
  - `practice_blocked_by_user_request=true`
  - `explicit_practice_request=false`
  - `writer_grounding_visibility.reason=repair_turn`
  - warning: wording is still verbose and should be cleaned in the next PRD
- `C-DIRECT-KB-SOURCE-2` -> `passed`
  - direct source/KB path preserved
  - answer explicitly referenced the internal-base framing
  - `writer_grounding_visibility.reason=direct_source_request`
  - `direct_kb_question=true`

## Overall
- Live smoke status: `passed_with_warning`
- Honest warning:
  - support/explanation paths can still be too long or mechanism-heavy
  - this does not block the explicit-practice hotfix acceptance
