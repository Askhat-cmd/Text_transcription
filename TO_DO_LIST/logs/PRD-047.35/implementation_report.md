# PRD-047.35 Implementation Report

Status: `passed_with_warning`  
Main implementation commit: `897e73f`

## Scope delivered

PRD-047.35 kept the canonical current pipeline and changed how knowledge is expressed in public user mode. Internal KB/semantic-card evidence now stays a Writer-only competence lens instead of becoming a user-facing topic, while ordinary answers are biased toward Wake-style depth principles without copying Wake style.

## Code changes

### Hidden knowledge competence

- `writer_context_package.py`
  - added `hidden_knowledge_competence_v1`
  - classifies:
    - `public_user_mode`
    - `owner_debug_question_detected`
    - `user_facing_db_language_suppressed`
    - `knowledge_used_as_hidden_lens`
    - `raw_kb_dump_allowed`
    - `reason`
  - forwards this state into `runtime_truth_trace_v1`
  - strengthened grounding note language so Writer uses internal knowledge as competence, not as a report about storage

- `runtime_trace_summary.py`
  - exposes `hidden_knowledge_competence_v1` in compact trace summary
  - adds a fallback builder so the trace stays informative even when older payload shapes are encountered

### Writer directive / prompt shaping

- `final_answer_directive.py`
  - added owner-debug-like DB/source detection
  - tightened compact profile notes so ordinary answers favor one mechanism, what it protects, and one next move
  - strengthened no-internal-db and safety profile wording

- `contracts/writer_contract.py`
  - passes hidden-competence state into Writer prompt context

- `agents/writer_agent_prompts.py`
  - added explicit public-user-mode rule:
    - no "в базе", "по чанкам", `semantic card`, internal-system language
    - use hidden competence instead
    - use Wake only as depth reference, not a style template

### Legacy/noise cleanup

- `legacy_advisory_sanitizer.py`
  - injects compact anti-internals / Wake-depth reminders into the Writer-visible summary
  - exposes hidden-competence and wake-depth reference notes in the sanitized final-directive JSON

- `response_planner.py`
  - ordinary planner branches now explicitly avoid base/chunk/semantic-card wording
  - mechanism branch now asks for the protective function, not just mechanism naming

## Tests and tooling

- added:
  - `tests/test_prd_047_35_hidden_knowledge_competence.py`
  - `tests/test_prd_047_35_public_user_mode.py`
  - `tests/test_prd_047_35_wake_depth_reference_behavior.py`
  - `tools/run_prd_047_35_owner_smoke.py`

## Acceptance summary

- both Wake reference files were read before implementation
- task list was created before coding
- `hidden_knowledge_competence_v1` is visible in runtime trace
- public user mode suppresses DB/chunk/internal-system language
- direct owner/debug-like questions still work without becoming raw storage reports
- latest-turn authority from PRD-047.34 remained preserved
- ordinary answers now bias toward one mechanism + protective function + one next move

## Honest warning that remains

- `python -m pytest tests -q` is still blocked by the historical unrelated import error:
  - `ImportError: cannot import name '_build_llm_prompts' from 'bot_agent.answer_adaptive'`
- live owner smoke stayed clean on internal-language leakage, but not perfect on shape:
  - panic helper turn 1 was too crisis-generic for the actual question
  - one deep explanation turn stayed too long
  - one close/thanks turn still carried extra recap instead of stopping cleanly
