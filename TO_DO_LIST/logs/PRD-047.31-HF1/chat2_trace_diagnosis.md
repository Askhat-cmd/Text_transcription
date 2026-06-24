# PRD-047.31-HF1 Chat2 Trace Diagnosis

Date: 2026-06-24
Status: pre_code_diagnosis_completed
Primary evidence: `TO_DO_LIST/context/ЧАТ_С_БОТОМ2.txt`

## Exact Failing Latest User Request

The critical latest user turn is:

`дай мне какую нибудь практику. Чтобы я мог выработать в себе навык не быть реактивным`

This is an explicit practice request, not a generic support turn and not a direct KB/source request.

## Actual Bot Reply

The bot answered:

`Сделай один шаг прямо сейчас: открой задачу и выполни первый минимальный фрагмент в течение 5 минут.`

This is generic productivity advice. It does not answer the current thread about anger, boss, lying, and non-reactivity.

## Recent Concrete Thread That Should Have Been Inherited

Immediately before the practice request, the active thread was:

- resistance in unpleasant interactions
- anger during conversation
- seeing obvious lying
- the other person is the user's boss
- the user wants to not be reactive

The assistant had already been discussing anger, impulse, pause, clarifying question, and role-risk context. So the practice request should have inherited this exact thread.

## Thread / Intent / Phase Actually Used

From the trace:

- `State Analyzer`
  - `nervous_state=window`
  - `intent=explore`
  - `safety_flag=false`
- `Thread Manager`
  - `phase=clarify`
  - `relation=new_thread`
  - `continuity=100%`
  - `NEW THREAD`

The damaging part is `relation=new_thread`. The latest practice request was treated as a new thread instead of a continuation of the active anger/boss/lying discussion.

## Stale Must Answer

From `FINAL ANSWER DIRECTIVE`:

- `answer_obligation=continue_thread`
- `must_answer="А если на меня накатывает гнев во время разговора, когда я вижу что мне нагло врут, но это мой начальник!"`
- `answer_shape=structured_explanation`

This confirms a stale `must_answer`: the directive still targeted the previous anger question instead of the newest explicit request for a practice.

## Dialogue / Writer Signals That Help Explain the Failure

- `DIALOGUE ACT RESOLUTION`
  - `dialogue_act=unknown`
  - `confidence=0.4`
- `ANSWER OBLIGATION`
  - `answer_obligation=continue_thread`
  - `answer_shape=structured_explanation`
- `DIALOGUE PRAGMATICS`
  - `is_contextual_followup=false`
  - `inherited_user_intent=give_example`
  - `should_answer_directly=false`
  - `reason=none`

So the system did not promote the latest turn as:

- explicit practice request
- contextual follow-up
- one contextual practice answer

## Grounding Visibility Behavior

From the directive and prompt canvas:

- `grounding_visibility.kb_visible_to_writer=false`
- `grounding_visibility.semantic_cards_visible_to_writer=false`
- `grounding_visibility.reason=direct_one_step_no_kb_needed`
- `retrieval_action=suppress_rag`
- `retrieval_need=none`

This means PRD-047.30 itself was not rolled back. Broad KB stayed hidden. The problem is that the system also failed to allow narrow practice/dialogue-move support for the explicit practice request.

## KB / Semantic / Practice Visibility

- broad KB was not Writer-visible
- semantic cards stayed `trace_only`
- `Writer KB Payload` had `chunks 0`
- the trace suggests no narrow contextual practice grounding path was activated

So the failure is not "too much KB". It is "latest practice request was not given a narrow contextual practice path".

## Checks That Failed or Stayed Too Weak

- explicit practice request detection did not become authoritative
- stale `must_answer` was not overridden by the latest user message
- thread continuation was lost despite immediate conversational continuity
- writer grounding visibility stayed in a generic no-KB/no-practice-support mode
- acceptance feedback only reported `answer_too_generic_for_concrete_situation`
  - this was too weak to force a rewrite toward one contextual practice

## Why The Final Answer Was Irrelevant

The system combined several weak signals:

1. the latest practice request was treated as a `new_thread`
2. the directive kept the old `must_answer`
3. the turn was not classified as explicit practice request
4. no narrow contextual practice grounding path became available
5. the final answer gate noticed genericity, but not the more specific failure:
   - the user explicitly asked for a practice tied to the current anger/boss/lying thread

## Hotfix Direction Confirmed By Evidence

The minimal correct fix is:

- detect explicit practice request on the latest user turn
- override stale `must_answer` with the latest practice request
- preserve continuation with the immediate anger/boss/lying thread
- allow one narrow contextual practice answer shape
- reject generic productivity practice in this thread

This matches PRD-047.31-HF1 scope and does not require rolling back PRD-047.30.
