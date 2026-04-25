# TASKLIST PRD-017 - Thread Manager Agent

Start date: 2026-04-25  
PRD: `PRD-017-Thread-Manager-Agent.md`  
Scope: `bot_psychologist/bot_agent/multiagent/`

## 1. Implementation plan
- [x] Read PRD and lock scope for this wave.
- [x] Create `multiagent` package and contracts folder.
- [x] Implement contracts:
  - [x] `StateSnapshot`
  - [x] `ThreadState`
  - [x] `ArchivedThread`
  - [x] `MemoryBundle`
  - [x] `WriterContract`
- [x] Implement `thread_storage.py` with active/archive persistence.
- [x] Implement `agents/thread_manager.py` with safety fallback.
- [x] Add `agents/thread_manager_prompts.py` scaffold.
- [x] Add minimal `orchestrator.py`.
- [x] Add feature flags:
  - [x] `MULTIAGENT_ENABLED`
  - [x] `THREAD_MANAGER_MODEL`
  - [x] `THREAD_STORAGE_DIR`
- [x] Add guarded integration in `answer_adaptive.py` (flag-off behavior preserved).

## 2. Tests
- [x] `tests/multiagent/test_thread_state_contracts.py`
- [x] `tests/multiagent/test_thread_storage.py`
- [x] `tests/multiagent/test_thread_manager.py`
- [x] Feature flags regression:
  - [x] `tests/test_feature_flags.py`
  - [x] `tests/config/test_feature_flags_baseline.py`
- [x] Smoke on existing adaptive path:
  - [x] `tests/test_mode_handlers.py`

## 3. Checks
- [x] `py_compile` for all new/changed files.
- [x] Multiagent branch is guarded by `MULTIAGENT_ENABLED`.
- [x] Classic runtime path remains default and unchanged when flag is disabled.
- [x] New tests are green in local venv.

## 4. Test run result
- `pytest tests/multiagent tests/test_feature_flags.py tests/config/test_feature_flags_baseline.py -q`
  - Result: `19 passed`
- `pytest tests/test_mode_handlers.py -q`
  - Result: `1 passed`

## 5. Progress log
- 2026-04-25: PRD read, tasklist created, implementation started.
- 2026-04-25: Contracts, storage, Thread Manager, orchestrator, feature flags, guarded adaptive integration completed.
- 2026-04-25: Target tests passed; tasklist updated.

