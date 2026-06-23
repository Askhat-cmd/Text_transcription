# PRD-047.28 No Production Mutation Plan

This PRD is experiment-only. The current web chat and manual runtime must stay on the existing `multiagent_adapter` path.

## Production Files That May Be Read

- `bot_psychologist/api/main.py`
- `bot_psychologist/api/routes/chat.py`
- `bot_psychologist/bot_agent/multiagent/runtime_adapter.py`
- `bot_psychologist/bot_agent/multiagent/orchestrator.py`
- `bot_psychologist/bot_agent/multiagent/agents/writer_agent.py`
- `bot_psychologist/bot_agent/multiagent/agents/writer_agent_prompts.py`
- `bot_psychologist/bot_agent/multiagent/writer_kb_payload.py`
- `bot_psychologist/bot_agent/multiagent/retrieval_query_builder.py`
- `bot_psychologist/bot_agent/multiagent/overlay_shadow_trace.py`
- `bot_psychologist/bot_agent/knowledge/semantic_card_*`

## Production Files That Must Not Be Mutated For This PRD

- `bot_psychologist/api/main.py`
- `bot_psychologist/api/routes/chat.py`
- `bot_psychologist/bot_agent/multiagent/runtime_adapter.py`
- `bot_psychologist/bot_agent/multiagent/orchestrator.py`
- `bot_psychologist/bot_agent/multiagent/agents/writer_agent.py`
- `bot_psychologist/bot_agent/multiagent/agents/writer_agent_prompts.py`
- `bot_psychologist/bot_agent/multiagent/writer_kb_payload.py`
- `bot_psychologist/bot_agent/multiagent/retrieval_query_builder.py`
- `bot_psychologist/bot_agent/multiagent/overlay_shadow_trace.py`
- `bot_psychologist/bot_agent/feature_flags.py`
- any DB / Chroma / registry / processed-block / admin UI runtime-default files

## Planned Experiment-Only Additions

- isolated experiment modules under a new PRD-047.28-specific package
- isolated runner CLI/tool for A/B/C experiment execution
- isolated tests for thin-spine behavior and artifact generation
- fixture case set under `TO_DO_LIST/fixtures/PRD-047.28/`
- evidence artifacts under `TO_DO_LIST/logs/PRD-047.28/`

## How No Production Mutation Will Be Preserved

- Variant A reuses the supported current runtime adapter instead of changing it.
- Variants B/C run only through a separate offline/CLI/eval path.
- No UI toggle, no admin toggle, and no permanent feature flag will be introduced.
- No DB/Chroma/retrieval-authority/overlay-apply mutation is allowed.
- Existing startup protocol remains the same; experiment code is opt-in and isolated.

## Proof Obligations After Implementation

- `git diff --stat` should show experiment/tests/docs/TO_DO_LIST artifacts only.
- `git diff -- bot_psychologist/api/main.py`
- `git diff -- bot_psychologist/api/routes/chat.py`
- `git diff -- bot_psychologist/bot_agent/multiagent/runtime_adapter.py`
- `git diff -- bot_psychologist/bot_agent/multiagent/orchestrator.py`
- targeted PRD-047.28 tests must pass
- relevant existing regression subset must pass
- final `no_mutation_proof.md` must confirm:
  - production runtime entrypoint unchanged
  - web/manual route not switched to thin spine
  - no DB/Chroma/registry mutation
  - no semantic-card expansion or overlay apply activation
  - no secrets/raw logs committed
