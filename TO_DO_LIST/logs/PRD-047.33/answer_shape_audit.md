# Answer Shape Audit - PRD-047.33

Date: 2026-06-25
Status: completed

## Scope
- `bot_psychologist/bot_agent/multiagent/dialogue_policy.py`
- `bot_psychologist/bot_agent/multiagent/final_answer_directive.py`
- `bot_psychologist/bot_agent/multiagent/contracts/writer_contract.py`
- `bot_psychologist/bot_agent/multiagent/agents/writer_agent_prompts.py`
- `bot_psychologist/bot_agent/multiagent/writer_context_package.py`
- `bot_psychologist/bot_agent/multiagent/runtime_trace_summary.py`
- `bot_psychologist/bot_agent/multiagent/orchestrator.py`
- `bot_psychologist/web_ui/src/components/chat/MultiAgentTraceWidget.tsx`

## Where answer shape is set today
- `dialogue_policy.py` sets global soft compactness defaults: `compact_support_answer`, `target_length_chars`, `preferred_shape`, `avoid_mechanism_heavy_default`, and human-like constraints such as list/question limits.
- `final_answer_directive.py` is the main answer-shape authority. It resolves `answer_obligation`, `answer_shape`, `depth`, `practice_policy`, latest-turn constraints, and now `answer_shape_profile`.
- `writer_contract.py` is the bridge layer that exposes final-directive shape hints to Writer prompt assembly.
- `writer_agent_prompts.py` is where shape guidance becomes plain-language Writer instructions. This is the highest-leverage place for reducing methodical defaults without adding a new runtime path.
- `runtime_trace_summary.py` exposes the selected profile and notes for owner review, but only reflects what the final directive actually carried.

## Current conflict points before calibration
- `dialogue_policy` could say "compact support" while `final_answer_directive` still inherited a more open `depth` or `structured_explanation` shape.
- ordinary direct/explanation turns had enough freedom to drift into the default teaching template: mechanism -> list/options -> explanation -> takeaway.
- Writer prompt already had human-like guidance, but it was not explicit enough about when long structured answers are allowed versus when compact direct answers are preferred.
- direct KB/source turns and no-internal-db turns needed to stay distinct; otherwise one compactness rule could accidentally flatten both.

## Why ordinary turns became too methodical
- ordinary explanation turns often arrived with no Writer-visible payload, so the remaining verbosity was coming from prompt/directive shape, not from KB pressure;
- `structured_explanation` and `medium/long` depth are safe defaults, but they encourage textbook answers when not balanced by a stronger compact shape hint;
- Writer had no explicit selected profile in the prompt, only general compactness signals, so it could still produce a well-formed but lecture-like answer.

## Minimal calibration chosen
- keep the canonical runtime intact; no new agent, no new route, no DB/Chroma mutation;
- tighten `target_length_chars` for compact support from `600_1400` to `450_1100`;
- add explicit soft `answer_shape_profile` selection in `final_answer_directive.py`;
- expose selected profile plus profile notes into Writer prompt assembly;
- sharpen prompt wording: ordinary support/explanation turns should sound like a human answer, not a teaching article;
- preserve special cases:
  - `bounded_practice` for explicit practice;
  - `no_internal_db_compact` for explicit no-internal-db;
  - `direct_kb_grounded_compact` for direct source/base questions;
  - `safety_grounding_compact` for safety-first turns.

## Live residual found during audit
- live case B (`Как преодолеть свое сопротивление?`) improved in length and tone after calibration, but trace still reports `selected_answer_shape_profile=adaptive_current_pipeline` instead of `ordinary_explanation_compact`.
- this does not look like KB interference: Writer payload is still `0`.
- practical implication: answer quality improved, but one shape-classification path is still not fully aligned with runtime truth for that ordinary direct-question case.

## Audit conclusion
- the remaining owner-pilot problem is not retrieval authority and not practice routing;
- the main lever is still prompt/directive answer-shape calibration inside the existing pipeline;
- PRD-047.33 implementation should be accepted as `passed_with_warning`: ordinary turns are materially improved, direct source/no-internal-db/practice paths stay preserved, and runtime truth remains honest, but one ordinary-explanation trace profile still needs a future narrow repair.
