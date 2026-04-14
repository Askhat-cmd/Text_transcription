# PRD-060: `answer_adaptive.py` Modularization (Wave 46)

## Context
The post-LLM full-path block (semantic concepts, path recommendation, feedback prompt, working-state update, token/session metrics, turn persistence, summary persistence) remained inline.

## Scope (Wave 46)
Extract post-LLM full-path artifact preparation into response helper.

## Objectives
1. Remove broad post-LLM orchestration block from `answer_adaptive.py`.
2. Preserve metadata/token/session and persistence behavior.
3. Keep compatibility with current full-path success response builder.

## Technical Design
Add helper in `adaptive_runtime/response_utils.py`:
- `_prepare_full_path_post_llm_artifacts(...)`

Update `answer_adaptive.py`:
- replace inline post-LLM preparation block with helper call and returned artifacts map.

## Test Plan
Targeted:
- `tests/integration/test_adaptive_stream_contract.py`
- `tests/integration/test_runtime_validation_receives_query_v1031.py`
- `tests/integration/test_pipeline_without_sd.py`
- `tests/regression/test_streaming_sd_runtime_disabled_contract.py`
- `tests/test_sse_payload.py`

Full:
- `pytest -q tests --maxfail=1`
