# PRD-047.34 Latest Turn Authority Audit

Status: completed  
Implementation commit: `39ff982`

## Audited files

- `bot_psychologist/bot_agent/multiagent/dialogue_act_resolver.py`
- `bot_psychologist/bot_agent/multiagent/unanswered_question_tracker.py`
- `bot_psychologist/bot_agent/multiagent/final_answer_directive.py`
- `bot_psychologist/bot_agent/multiagent/dialogue_policy.py`
- `bot_psychologist/bot_agent/multiagent/dialogue_pragmatics.py`
- `bot_psychologist/bot_agent/multiagent/response_planner.py`
- `bot_psychologist/bot_agent/multiagent/runtime_trace_summary.py`
- `bot_psychologist/bot_agent/multiagent/writer_context_package.py`
- `bot_psychologist/bot_agent/multiagent/contracts/writer_contract.py`
- `bot_psychologist/bot_agent/multiagent/agents/writer_agent_prompts.py`

## Before repair

- `dialogue_act_resolver.py` could leave support/contact shifts under weak `unknown` semantics.
- `answer_obligation_resolver.py` still had stale-thread continuation defaults for repair/unknown-like states.
- `final_answer_directive.py` did not explicitly encode:
  - `current_user_request`
  - `must_answer_source`
  - `previous_must_answer_demoted`
  - `previous_must_answer`
  - `explicit_continue_previous_detected`
  - `answer_target`
  - `writer_contact_mode`
- `runtime_trace_summary.py` did not expose a compact latest-turn authority block.
- Writer prompt/contract surfaces could not clearly distinguish:
  - latest-turn answer target
  - explicit continuation exception
  - demoted previous open loop
  - free human contact mode

## Authority assignment after repair

### Who assigns `must_answer`

- `final_answer_directive.py` now assigns the effective answer target.
- Default rule: latest non-empty user turn wins.
- Exceptions:
  - `safety`
  - `direct_source`
  - `explicit_practice`
  - `explicit_continue_previous`

### Who can preserve stale previous state

- Only the explicit continuation path may keep the previous open loop active.
- Previous question/offer state still stays trace-visible as `previous_must_answer`, but it is demoted to context-only when the latest turn changes contact mode, tone, or request type.

### What happens on `dialogue_act=unknown`

- Unknown-like states no longer automatically imply `continue_thread`.
- Current-turn human support/repair/contact shifts now resolve to `answer_latest_turn`.

### What happens on `continue_thread`

- Continuity is still allowed, but only when explicit continuation is detected.
- That detection is compact and principle-based, not a new phrase-engine.

### Where answer-shape now comes from

- `final_answer_directive.py` selects `answer_shape_profile`.
- `free_writer_contact` is available when the latest turn changes the desired human contact mode and is not a technical/direct-source/practice request.

### How the previous open loop reaches Writer now

- It stays visible via `previous_must_answer` and runtime trace as context.
- It no longer acts as the primary command unless `answer_target=previous_open_loop`.

## Additional live-path finding

- Latest-turn authority alone was not enough.
- `writer_agent.py` still contained post-LLM canned one-step rewrites and legacy advisory prompt fragments that could reintroduce micro-step pressure on `free_writer_contact + no_practice` turns.
- PRD-047.34 therefore also required:
  - prompt placeholder wiring fix
  - no-practice phrase broadening in `latest_turn_constraints.py`
  - canned one-step suppression in Writer compliance
  - legacy advisory sanitization so `target_micro_shift` / active-line hints do not leak `микро-шаг` advice when practice is forbidden

## Final architectural result

- Latest user turn is now the default answer authority inside the canonical current pipeline.
- Previous open loop remains context, not command, unless explicitly continued.
- Writer receives this rule through existing directive/contract/prompt/trace surfaces.
- No new route, no new agent, no DB mutation, and no semantic-card expansion were added.
