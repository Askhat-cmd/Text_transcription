# TASKLIST PRD-019 - Memory + Retrieval Agent

Start date: 2026-04-25  
PRD: `PRD-019-Memory-Retrieval-Agent.md`  
Scope: `bot_psychologist/bot_agent/multiagent/`

## 1. Implementation plan
- [x] Read PRD and lock scope.
- [x] Expand `contracts/memory_bundle.py` with `SemanticHit`, `UserProfile`, extended `MemoryBundle`.
- [x] Add `agents/memory_retrieval_config.py`.
- [x] Add `agents/memory_retrieval.py` (deterministic, no LLM calls).
- [x] Export `memory_retrieval_agent` in `agents/__init__.py`.
- [x] Integrate `memory_retrieval_agent.assemble()` in `orchestrator.py`.
- [x] Add async scaffold call `memory_retrieval_agent.update(...)` in orchestrator run flow.
- [x] Add string defaults in `feature_flags.py`:
  - [x] `MEMORY_RAG_N_RESULTS`
  - [x] `MEMORY_RAG_MIN_SCORE`
  - [x] `MEMORY_CONV_TURNS_DEFAULT`

## 2. Tests
- [x] Add fixtures: `tests/multiagent/fixtures/memory_retrieval_fixtures.json`.
- [x] Add tests: `tests/multiagent/test_memory_retrieval.py`.
- [x] Cover n_turns policy resolution (stabilize/integrate/new_thread/default).
- [x] Cover RAG query builder behavior and max length.
- [x] Cover score filtering/sorting and compat `retrieved_chunks`.
- [x] Cover graceful degradation on source failures.
- [x] Cover orchestrator integration and debug fields.

## 3. Regression checks
- [x] Existing PRD-017 tests remain green.
- [x] Existing PRD-018 tests remain green.
- [x] `memory_retrieval.py` has no OpenAI imports/calls.
- [x] No imports from `adaptive_runtime` in new MRA module.
- [x] `contracts/state_snapshot.py` untouched.
- [x] `contracts/thread_state.py` untouched.

## 4. Execution checks
- [x] `py_compile` for changed files.
- [x] `pytest tests/multiagent -q`
- [x] `pytest tests/test_feature_flags.py tests/config/test_feature_flags_baseline.py -q`

## 5. Progress log
- 2026-04-25: PRD reviewed, tasklist created, implementation started.
- 2026-04-25: Added MRA contracts/config/agent/orchestrator integration and feature-flag defaults.
- 2026-04-25: Added fixtures and full `test_memory_retrieval.py` suite.
- 2026-04-25: Fixed MR-26/MR-27 import path in tests (`importlib.import_module("bot_agent.multiagent.orchestrator")`).
- 2026-04-25: Validation complete: `pytest tests/multiagent -q` => 75 passed; feature-flags tests => 4 passed.
