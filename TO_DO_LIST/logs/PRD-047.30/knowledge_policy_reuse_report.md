# PRD-047.30 Knowledge Policy Reuse Report

Date: 2026-06-24
Status: completed

## Conclusion

`knowledge_policy.py` remains the canonical governance gate for chunk safety and eligibility. PRD-047.30 did not bypass it, replace it, or duplicate its safety decisions in a new subsystem.

## Where `apply_knowledge_policy_v1` Runs

- `bot_psychologist/bot_agent/multiagent/agents/memory_retrieval.py:294`
  - filtered retrieval hits are passed through `apply_knowledge_policy_v1(filtered_hits)`
  - the result becomes `policy_decisions` plus `knowledge_policy_trace`
  - the trace is stored into `MemoryBundle.knowledge_policy_trace`

## What `knowledge_policy.py` Still Owns

- drop `do_not_use`
- keep `internal_only` out of Writer-visible grounding
- preserve diagnostic-only vs writer-allowed distinctions
- carry safety/governance evidence into debug trace

## What PRD-047.30 Changed Instead

- `writer_context_package.py` now decides whether already-approved grounding should be visible to Writer on this specific turn
- this is an authority/packaging throttle, not a second governance filter
- when grounding is hidden, trace/debug evidence still keeps the underlying policy outcome visible

## Why This Matches PRD Scope

- governance stays in `knowledge_policy.py`
- Writer-visible throttling stays in `writer_context_package.py`
- prompt wording stays in `writer_contract.py` and `writer_agent_prompts.py`
- duplicate advisory compression stays in `legacy_advisory_sanitizer.py`

## Proof Points

- `tests/test_prd_047_30_writer_grounding_visibility.py::test_knowledge_policy_still_blocks_internal_only_and_do_not_use`
- live trace still exports `knowledge_policy_trace`
- `writer_grounding_visibility_v1` changes only visibility, not policy admission
