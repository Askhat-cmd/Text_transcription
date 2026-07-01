# PRD-047.36-HF5 Implementation Report

Date: 2026-07-01
Status: `accepted_with_warning`

## Scope delivered
- Repaired the generic selected-knowledge admission contract for direct concept follow-ups inside the current pipeline.
- Preserved greeting/contact suppression, `no_internal_db`, public hidden-competence boundaries, and semantic-card advisory-only status.
- Added targeted HF5 tests, a reproducible live smoke runner, and root-cause/report artifacts.

## Functional result
- Contextual concept follow-ups with already selected knowledge are now promoted to a minimal Writer-visible package when no hard blocker applies.
- Writer grounding visibility now distinguishes `direct_concept_followup` from generic `no_clear_retrieval_need`.
- Existing `memory_bundle.knowledge_rag_hits` can be reused in a bounded way when selected knowledge should flow but the gate would otherwise leave payload empty.
- Payload ordering now lets one selected semantic card lead the minimal concept-follow-up package instead of being crowded out by ordering alone.

## Main files changed
- `bot_psychologist/bot_agent/multiagent/contextual_retrieval_query_composer.py`
- `bot_psychologist/bot_agent/multiagent/writer_context_package.py`
- `bot_psychologist/tests/test_prd_047_36_hf5_selected_knowledge_admission_contract.py`
- `bot_psychologist/tests/test_prd_047_36_hf5_direct_concept_followup_kb_visibility.py`
- `bot_psychologist/tools/run_prd_047_36_hf5_direct_concept_followup_kb_visibility.py`

## Acceptance summary
- Chat 12 failure class repaired: `PASS`
- greeting/contact preservation: `PASS`
- `no_internal_db` preservation: `PASS`
- semantic cards remain advisory-only / Writer-can-ignore: `PASS`
- public internal-language leak observed: `NO`

## Why status is accepted_with_warning
HF5 itself passed targeted tests, preservation subsets, frontend subset, lint, build, and live smoke. The only remaining warning is outside HF5 scope:
- full `python -m pytest tests -q` still stops on the historical unrelated `_build_llm_prompts` import blocker

