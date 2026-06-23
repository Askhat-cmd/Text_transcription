# PRD-047.29 Source Gate Runtime Map

Date: 2026-06-23
PRD: `PRD-047.29_Current_Pipeline_Simplification_Targets_Layer_Noise_Reduction_RU.md`
Status: source_gate_completed_before_code

## Read Inputs

- `TO_DO_LIST/PRD-047.29_Current_Pipeline_Simplification_Targets_Layer_Noise_Reduction_RU.md`
- `TO_DO_LIST/PRD-047.28_Thin_Spine_Live_Prompt_Experiment_RU.md`
- `TO_DO_LIST/PRD-047.28_TASK_LIST.md`
- `TO_DO_LIST/logs/PRD-047.28/implementation_report.md`
- `TO_DO_LIST/logs/PRD-047.28/thin_spine_comparative_report.md`
- `TO_DO_LIST/logs/PRD-047.28/variant_outputs.jsonl`
- `TO_DO_LIST/logs/PRD-047.28/no_mutation_proof.md`
- `TO_DO_LIST/logs/PRD-047.28/next_prd_recommendation.md`
- `TO_DO_LIST/PRD-047.27-HF2_TASK_LIST.md`
- `запуск проека.txt`

## Runtime Map

- Final directive / answer obligation:
  - `bot_psychologist/bot_agent/multiagent/answer_obligation_resolver.py`
  - `bot_psychologist/bot_agent/multiagent/final_answer_directive.py`
  - assembled in `bot_psychologist/bot_agent/multiagent/orchestrator.py`
- `must_answer` assembly:
  - `_must_answer_current_turn(...)` in `bot_psychologist/bot_agent/multiagent/final_answer_directive.py`
  - fallback source can still pull old `unanswered_question_state`
- Writer current-turn constraints entrypoint:
  - `WriterContract.to_prompt_context()` in `bot_psychologist/bot_agent/multiagent/contracts/writer_contract.py`
  - writer-visible directive sanitization in `bot_psychologist/bot_agent/multiagent/legacy_advisory_sanitizer.py`
- Practice suggestion / bounded practice sources:
  - obligation path in `answer_obligation_resolver.py`
  - planner/directive path in `final_answer_directive.py`
  - writer-visible practice wording rewrite in `legacy_advisory_sanitizer.py`
  - writer prompt/runtime compliance in `bot_psychologist/bot_agent/multiagent/agents/writer_agent.py`
- Breathing / grounding suggestion risk zone:
  - not from one dedicated router; can leak through writer prompt freedom plus practice-compatible planner/advisory blocks
  - needs latest-turn hard-stop signal at directive/writer-contract level
- Writer-visible KB / semantic cards boundary:
  - `bot_psychologist/bot_agent/multiagent/writer_context_package.py`
  - semantic-card selection starts in `bot_psychologist/bot_agent/knowledge/semantic_card_payload_adapter.py`
  - writer KB payload is assembled in `bot_psychologist/bot_agent/multiagent/writer_kb_payload.py`
- Web/API debug trace assembly:
  - raw debug payload built in `bot_psychologist/bot_agent/multiagent/orchestrator.py`
  - API surface built in `bot_psychologist/api/debug_routes.py`
  - typed response surface in `bot_psychologist/api/models.py`

## Largest Trace Blocks

- `final_answer_directive`
- `dialogue_policy`
- `retrieval_decision`
- `writer_kb_payload_trace`
- `semantic_hits_detail`
- `live_turn_evidence`
- `overlay_shadow`
- `contextual_retrieval_query_composer`

These are useful for deep debug, but too large for quick pilot inspection. A compact top-level summary is justified.

## Active Compatibility / Fallback Noise

- legacy advisory summary is still built even when final answer directive already exists
- writer-visible directive JSON is sanitized and compacted separately from raw directive
- old unanswered-question state can still influence `must_answer`
- retrieval / semantic-card / KB traces remain visible even when the latest user turn explicitly forbids internal DB grounding
- overlay trace remains present as diagnostics even though overlay apply must stay off in this PRD

## Safe-To-Change Files For This PRD

- `bot_psychologist/bot_agent/multiagent/final_answer_directive.py`
- `bot_psychologist/bot_agent/multiagent/contracts/writer_contract.py`
- `bot_psychologist/bot_agent/multiagent/writer_context_package.py`
- `bot_psychologist/bot_agent/multiagent/orchestrator.py`
- `bot_psychologist/bot_agent/multiagent/legacy_advisory_sanitizer.py`
- `bot_psychologist/api/debug_routes.py`
- `bot_psychologist/api/models.py`
- targeted tests under `bot_psychologist/tests/`
- new fixture/evidence files under `TO_DO_LIST/`

## Do-Not-Change Scope For This PRD

- live Web Chat entrypoint must remain `multiagent_adapter`
- do not connect thin spine to live runtime
- do not add a new LLM agent
- do not add new feature flags for this repair
- do not rewrite DB / Chroma / registry / chunk governance
- do not enable overlay apply
- do not physically remove Diagnostic Center / semantic cards / overlay systems
- do not attempt unrelated full-suite repair beyond honest blocker reporting

## Owner-Restored File

- `TO_DO_LIST/PRD-047.27-HF2_TASK_LIST.md`
- `restored_by_owner=true`
- include in push, no rewrite
