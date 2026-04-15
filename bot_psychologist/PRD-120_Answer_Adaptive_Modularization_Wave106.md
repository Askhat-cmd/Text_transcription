# PRD-120: `answer_adaptive.py` Modularization (Wave 106)

## Context
Facade still passed several monkeypatch-safe dependencies to runtime helpers using callback-style argument names (`*_fn`).
This wave standardizes those contracts to neutral names while preserving behavior.

## Scope (Wave 106)
Rename Stage-1/2/3 helper argument names for externally provided dependencies:
- `get_conversation_memory_fn` -> `get_conversation_memory`
- `classify_parallel_fn` -> `classify_parallel`
- `detect_routing_signals_fn` -> `detect_routing_signals`
- `should_use_fast_path_fn` -> `should_use_fast_path`
- `get_retriever_fn` -> `get_retriever`

## Objectives
1. Reduce callback-style naming noise in the facade/runtime contract.
2. Keep monkeypatch compatibility and runtime behavior unchanged.
3. Keep full test matrix green.

## Technical Design
Update files:
- `bot_agent/adaptive_runtime/runtime_misc_helpers.py`
- `bot_agent/adaptive_runtime/routing_stage_helpers.py`
- `bot_agent/adaptive_runtime/retrieval_stage_helpers.py`
- `bot_agent/answer_adaptive.py`

Changes are strictly naming-level contract cleanup (signatures + keyword arguments + internal calls), no logic changes.

## Test Plan
Targeted:
- `tests/unit/test_sd_runtime_disabled.py`
- `tests/integration/test_degraded_mode_without_retrieval.py`
- `tests/integration/test_runtime_validation_receives_query_v1031.py`
- `tests/test_retrieval_pipeline_simplified.py`
- `tests/e2e/test_degraded_retrieval_case.py`

Full:
- `pytest -q`
