# PRD-047.42 admin_routes Boundary Map

- file: `bot_psychologist/api/admin_routes.py`
- total_loc: `2144`
- mapped_loc: `1994`
- exact_cover: `False`

## Responsibility Sections
| Section | Lines | LOC | legacy_compat | Proposed future module | Responsibility |
| --- | --- | --- | --- | --- | --- |
| runtime_compat_helpers | 91-173 | 83 | yes | admin_runtime_compat.py | Admin runtime compatibility and deprecated-surface helpers for multiagent-only truth exposure. |
| router_bootstrap_and_admin_constants | 178-233 | 56 | no | admin_surface_bootstrap.py | Auth dependency, router registration, schema versions, and admin surface constants. |
| status_prompt_thread_and_prd_status_helpers | 235-665 | 431 | no | admin_surface_helpers.py | Status snapshots, prompt-stack builders, thread listings, agent-prompt reflection, and historical PRD artifact status loaders. |
| runtime_effective_payload_builder | 668-956 | 289 | yes | admin_runtime_effective_payload.py | Assembles the canonical runtime/effective admin payload across flags, dialogue policy, planner, trace, semantic cards, and compat metadata. |
| diagnostics_effective_payload_builder | 959-982 | 24 | no | admin_diagnostics_payload.py | Builds compact diagnostics payload for dedicated admin diagnostics surface. |
| schema_and_import_validation | 985-1132 | 148 | no | admin_config_schema.py | Builds admin config schema v10.4 and validates import/export payload normalization. |
| config_status_runtime_and_trace_routes | 1148-1432 | 285 | yes | admin_config_routes.py | Config CRUD, runtime status/effective endpoints, diagnostics endpoints, and deprecated admin trace routes. |
| prompt_history_import_export_routes | 1447-1705 | 259 | no | admin_prompt_routes.py | Prompt CRUD, prompt-stack v2 editing, history, and import/export endpoints. |
| agent_orchestrator_and_overview_routes | 1716-1905 | 190 | yes | admin_agent_ops_routes.py | Agent status/toggles/metrics, orchestrator config, traces, and overview endpoints. |
| thread_agent_llm_reset_and_identity_routes | 1916-2144 | 229 | no | admin_misc_routes.py | Thread cleanup, per-agent prompt/LLM config endpoints, full reset, and user identity admin route. |

## AST Anchors
| Node type | Name | Lines | Owner class |
| --- | --- | --- | --- |
| FunctionDef | _env_flags_snapshot | 91-92 |  |
| FunctionDef | _is_truthy_env | 95-97 |  |
| FunctionDef | _compute_env_pipeline_mode | 100-103 |  |
| FunctionDef | _compute_active_runtime | 106-108 |  |
| FunctionDef | _runtime_entrypoint | 111-112 |  |
| FunctionDef | _deprecated_runtime_warnings | 115-119 |  |
| FunctionDef | _legacy_status_payload | 122-130 |  |
| FunctionDef | _compatibility_runtime_payload | 133-155 |  |
| FunctionDef | _runtime_agents_contract_payload | 158-165 |  |
| FunctionDef | _thread_manager_llm_meta | 168-173 |  |
| FunctionDef | require_dev_key | 178-185 |  |
| FunctionDef | _filter_operational_flags | 235-240 |  |
| FunctionDef | _status_snapshot | 243-252 |  |
| FunctionDef | _prompt_stack_v2_sections_baseline | 255-270 |  |
| FunctionDef | _prompt_history_metadata | 273-284 |  |
| FunctionDef | _build_prompt_stack_v2_meta | 287-321 |  |
| FunctionDef | _build_prompt_stack_v2_detail | 324-361 |  |
| FunctionDef | _group_feature_flags | 364-386 |  |
| FunctionDef | _compute_agent_metrics | 389-415 |  |
| FunctionDef | _get_thread_storage_dir | 418-422 |  |
| FunctionDef | _list_active_threads | 425-450 |  |
| FunctionDef | _list_archived_threads | 453-476 |  |
| FunctionDef | _get_agent_prompts_raw | 479-494 |  |
| FunctionDef | _group_param_value | 497-503 |  |
| FunctionDef | _load_prd_047_2_quality_calibration_status | 506-536 |  |
| FunctionDef | _load_prd_047_3_active_line_calibration_status | 539-569 |  |
| FunctionDef | _load_prd_047_4_response_planner_calibration_status | 572-602 |  |
| FunctionDef | _load_prd_047_6_planner_drift_replay_status | 605-626 |  |
| FunctionDef | _load_prd_047_7_guided_live_testing_status | 629-665 |  |
| FunctionDef | _build_runtime_effective_payload | 668-956 |  |
| FunctionDef | _build_diagnostics_effective_payload | 959-982 |  |
| FunctionDef | _build_config_schema_v104 | 985-1069 |  |
| FunctionDef | _validate_import_overrides_payload | 1072-1132 |  |
| AsyncFunctionDef | admin_get_config | 1148-1153 |  |
| AsyncFunctionDef | admin_get_config_schema | 1164-1194 |  |
| AsyncFunctionDef | admin_get_config_schema_v104 | 1205-1206 |  |
| AsyncFunctionDef | admin_set_config | 1225-1265 |  |
| AsyncFunctionDef | admin_reset_config_param | 1276-1281 |  |
| AsyncFunctionDef | admin_reset_all_config | 1292-1295 |  |
| AsyncFunctionDef | admin_status | 1306-1314 |  |
| AsyncFunctionDef | admin_runtime_effective | 1325-1326 |  |
| AsyncFunctionDef | admin_diagnostic_center_effective | 1337-1338 |  |
| AsyncFunctionDef | admin_diagnostic_center_control_update | 1349-1353 |  |
| AsyncFunctionDef | admin_diagnostic_center_control_reset | 1364-1365 |  |
| AsyncFunctionDef | admin_diagnostics_effective | 1376-1377 |  |
| AsyncFunctionDef | admin_trace_last | 1388-1393 |  |
| AsyncFunctionDef | admin_trace_recent | 1404-1412 |  |
| AsyncFunctionDef | admin_reload_data | 1423-1432 |  |
| AsyncFunctionDef | admin_get_prompts | 1447-1452 |  |
| AsyncFunctionDef | admin_get_prompts_stack_v2 | 1463-1464 |  |
| AsyncFunctionDef | admin_get_prompts_stack_v2_usage | 1475-1480 |  |
| AsyncFunctionDef | admin_get_prompt | 1491-1501 |  |
| AsyncFunctionDef | admin_get_prompt_stack_v2 | 1512-1513 |  |
| AsyncFunctionDef | admin_set_prompt | 1524-1539 |  |
| AsyncFunctionDef | admin_set_prompt_stack_v2 | 1550-1563 |  |
| AsyncFunctionDef | admin_reset_prompt | 1582-1589 |  |
| AsyncFunctionDef | admin_reset_prompt_stack_v2 | 1600-1609 |  |
| AsyncFunctionDef | admin_reset_all_prompts | 1616-1619 |  |
| AsyncFunctionDef | admin_get_history | 1630-1635 |  |
| AsyncFunctionDef | admin_export_overrides | 1650-1663 |  |
| AsyncFunctionDef | admin_import_overrides | 1674-1705 |  |
| AsyncFunctionDef | admin_agents_status | 1716-1728 |  |
| AsyncFunctionDef | admin_agents_toggle | 1735-1741 |  |
| AsyncFunctionDef | admin_agents_record_metric | 1748-1759 |  |
| AsyncFunctionDef | admin_orchestrator_get_config | 1770-1792 |  |
| AsyncFunctionDef | admin_orchestrator_patch_config | 1799-1820 |  |
| AsyncFunctionDef | admin_agents_traces | 1831-1843 |  |
| AsyncFunctionDef | admin_overview | 1850-1885 |  |
| AsyncFunctionDef | admin_agents_traces_record | 1892-1905 |  |
| AsyncFunctionDef | admin_threads_list | 1916-1929 |  |
| AsyncFunctionDef | admin_threads_delete | 1936-1941 |  |
| AsyncFunctionDef | admin_agent_prompts_get | 1952-1973 |  |
| AsyncFunctionDef | admin_agent_prompts_update | 1980-1997 |  |
| AsyncFunctionDef | admin_agent_prompts_reset | 2004-2011 |  |
| AsyncFunctionDef | admin_get_agents_llm_config | 2017-2025 |  |
| AsyncFunctionDef | admin_patch_agent_llm_config | 2032-2059 |  |
| AsyncFunctionDef | admin_reset_agent_llm_config | 2066-2083 |  |
| AsyncFunctionDef | admin_reset_everything | 2093-2096 |  |
| AsyncFunctionDef | _admin_user_identity_payload | 2098-2129 |  |
| AsyncFunctionDef | admin_get_user_identity | 2140-2144 |  |
