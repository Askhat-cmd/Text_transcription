# PRD-047.40 user_level_adapter Trace

- verdict: `active`
- post_status: `200`
- trace_status: `200`
- metadata_has_user_level: `False`
- metadata_has_user_level_adapter_applied: `False`
- trace_has_user_level: `False`
- trace_has_user_level_adapter_applied: `False`
- latest_turn_constraints: `none`
- session_id: `prd-047-40-user-level-b9f64edb13`
- answer_preview: `Осознанность — это способность внимать настоящему моменту: замечать свои мысли, чувства и ощущения без немедленных оценок или действий. Главный механизм — неповреждённое наблюдение (видеть мысль как событие, а не как факт о себе), которое м`

## Active Runtime Hits

- `bot_psychologist/api/debug_routes.py:45` - `"user_level_adapter_applied",`
- `bot_psychologist/api/routes/common.py:230` - `"user_level_adapter_applied",`
- `bot_psychologist/api/routes/common.py:240` - `"user_level_adapter_applied",`
- `bot_psychologist/bot_agent/response/response_generator.py:115` - `user_level_adapter=None,`
- `bot_psychologist/bot_agent/response/response_generator.py:130` - `_ = user_level_adapter  # compatibility: accepted but intentionally ignored in Neo runtime`
- `bot_psychologist/bot_agent/response/response_generator.py:215` - `user_level_adapter=None,`
- `bot_psychologist/bot_agent/response/response_generator.py:224` - `_ = user_level_adapter  # compatibility: accepted but intentionally ignored in Neo runtime`

## Test Hits

- `bot_psychologist/tests/api/test_multiagent_metadata_contract.py:50` - `"user_level_adapter_applied": True,`
- `bot_psychologist/tests/api/test_multiagent_metadata_contract.py:66` - `"user_level_adapter_applied",`
- `bot_psychologist/tests/contract/test_dead_code_removed.py:54` - `def test_user_level_adapter_verdict_is_recorded_as_active() -> None:`
- `bot_psychologist/tests/contract/test_dead_code_removed.py:55` - `report_path = WORKSPACE_ROOT / "TO_DO_LIST" / "logs" / "PRD-047.40" / "user_level_adapter_trace.md"`
- `bot_psychologist/tests/contract/test_dead_code_removed.py:56` - `assert report_path.exists(), "user_level_adapter trace report is missing"`
- `bot_psychologist/tests/contract/test_live_metadata_contract_after_purge.py:38` - `"user_level_adapter_applied": False,`
- `bot_psychologist/tests/contract/test_live_metadata_contract_after_purge.py:72` - `"user_level_adapter_applied",`
- `bot_psychologist/tests/integration/test_pipeline_without_level_adapter.py:30` - `"user_level_adapter_applied": False,`
- `bot_psychologist/tests/integration/test_pipeline_without_level_adapter.py:60` - `assert "user_level_adapter_applied" not in body["metadata"]`
- `bot_psychologist/tests/inventory/test_no_active_legacy_trace_metadata_keys.py:39` - `"user_level_adapter_applied",`
- `bot_psychologist/tests/inventory/test_streaming_runtime_divergence_inventory.py:34` - `assert "user_level_adapter_applied" in text`
- `bot_psychologist/tests/regression/_retired/retired_no_sd_required_by_response_flow.py:39` - `user_level_adapter=None,`
- `bot_psychologist/tests/regression/test_no_user_level_runtime_metadata.py:69` - `"user_level_adapter_applied": False,`
- `bot_psychologist/tests/regression/test_no_user_level_runtime_metadata.py:73` - `"user_level_adapter_applied": False,`
- `bot_psychologist/tests/regression/test_no_user_level_runtime_metadata.py:106` - `assert "user_level_adapter_applied" not in metadata`
- `bot_psychologist/tests/regression/test_no_user_level_runtime_metadata.py:115` - `assert "user_level_adapter_applied" not in trace`
- `bot_psychologist/tests/test_path_builder.py:62` - `user_level_adapter=object(),`
- `bot_psychologist/tests/test_response_generator.py:55` - `user_level_adapter=object(),  # backward-compatible arg; ignored in Neo runtime`
- `bot_psychologist/tests/unit/test_user_level_adapter_removed.py:12` - `def test_user_level_adapter_not_used_in_adaptive_runtime() -> None:`
