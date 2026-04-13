# PRD-022: `answer_adaptive.py` Modularization (Wave 8)

## Context
`answer_adaptive.py` still had duplicated finalization logic for `debug_trace` across multiple branches (fast-path success, full success, partial/no-blocks, LLM error, exception path).

## Scope (Wave 8)
Extract repeated trace-finalization/memory-snapshot logic into shared helpers in `adaptive_runtime/trace_helpers.py` and wire them into all major branches.

## Objectives
1. Reduce orchestration duplication.
2. Preserve trace schema and payload contract.
3. Keep behavior identical for legacy stripping rules per branch.

## Technical Design
Add helpers:
- `_apply_trace_memory_snapshot(...)`
- `_finalize_trace_payload(...)`

Apply in `answer_adaptive.py` for:
- fast-path success branch
- full-path success branch
- partial/no-blocks return branch
- LLM-error return branch
- exception return branch

## Tasks
1. Add shared trace finalization helpers.
2. Integrate helpers in fast/full success branches.
3. Integrate helpers in partial/error branches.
4. Verify legacy strip semantics per branch remain unchanged.
5. Run targeted tests.
6. Run full suite.

## Test Plan
Targeted:
- `tests/integration/test_adaptive_stream_contract.py`
- `tests/integration/test_runtime_validation_receives_query_v1031.py`
- `tests/integration/test_pipeline_without_sd.py`
- `tests/regression/test_streaming_sd_runtime_disabled_contract.py`
- `tests/test_sse_payload.py`

Full:
- `pytest -q tests`
