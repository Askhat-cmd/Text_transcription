# PRD-047.42 External Dependency Graph

## writer_agent

- module: `bot_agent.multiagent.agents.writer_agent`
- imported_module_count: `18`
- importer_count: `27`

### Imported Modules
| Index | Imported module |
| --- | --- |
| 1 | __future__ |
| 2 | active_line |
| 3 | agent_llm_client |
| 4 | agent_llm_config |
| 5 | concrete_answer_fit |
| 6 | config |
| 7 | contracts.writer_contract |
| 8 | dialogue_policy |
| 9 | feature_flags |
| 10 | logging |
| 11 | openai |
| 12 | prompt_constraint_section |
| 13 | re |
| 14 | stale_stub_detector |
| 15 | time |
| 16 | typing |
| 17 | writer_agent_prompts |
| 18 | writer_kb_payload |

### Importers by Category
| Category | Count | Examples |
| --- | --- | --- |
| production | 7 | bot_psychologist/bot_agent/multiagent/agents/__init__.py<br>bot_psychologist/bot_agent/multiagent/orchestrator.py<br>bot_psychologist/scripts/run_prd_047_10_hf1_dialogue_pragmatics_eval.py<br>bot_psychologist/scripts/run_prd_047_10_human_like_eval.py<br>bot_psychologist/scripts/run_prd_047_11_hf1_writer_prompt_diet.py<br>bot_psychologist/scripts/run_prd_047_8_mvp_free_dialogue_cases.py<br>bot_psychologist/scripts/run_prd_047_9_mvp_context_unclamp_cases.py |
| tests | 18 | bot_psychologist/tests/contract/test_prd_047_42_god_file_boundary_mapping.py<br>bot_psychologist/tests/multiagent/test_agent_hot_swap.py<br>bot_psychologist/tests/multiagent/test_post_cutover_model_guard.py<br>bot_psychologist/tests/multiagent/test_prompt_constraint_pilot_runtime_no_user_path_effect.py<br>bot_psychologist/tests/multiagent/test_writer_agent.py<br>bot_psychologist/tests/multiagent/test_writer_kb_payload_prompt_integration.py<br>bot_psychologist/tests/multiagent/test_writer_llm_client_compat.py<br>bot_psychologist/tests/multiagent/test_writer_prompt_contract.py<br>bot_psychologist/tests/test_concrete_answer_fit_no_static_template.py<br>bot_psychologist/tests/test_multiagent_prd_047_10_hf1_dialogue_pragmatics.py<br>bot_psychologist/tests/test_multiagent_trace.py<br>bot_psychologist/tests/test_prd_047_11_hf1_writer_prompt_diet.py<br>bot_psychologist/tests/test_prd_047_30_writer_contract_authority.py<br>bot_psychologist/tests/test_writer_contract_knowledge_answer.py<br>bot_psychologist/tests/test_writer_first_prompt_assembly_v1.py<br>bot_psychologist/tests/test_writer_prompt_mvp_free_dialogue.py<br>bot_psychologist/tests/test_writer_prompt_philosophy_kernel.py<br>bot_psychologist/tests/test_writer_retry_conversion_no_stub_v1.py |
| tools | 2 | TO_DO_LIST/tools/run_prd_047_42_god_file_boundary_mapping.py<br>bot_psychologist/tools/run_prompt_constraint_pilot_runtime_eval.py |
| docs | 0 | none |
| other | 0 | none |

## admin_routes

- module: `api.admin_routes`
- imported_module_count: `32`
- importer_count: `2`

### Imported Modules
| Index | Imported module |
| --- | --- |
| 1 | auth |
| 2 | bot_agent.config |
| 3 | bot_agent.config_validation |
| 4 | bot_agent.data_loader |
| 5 | bot_agent.diagnostic_center_control |
| 6 | bot_agent.effective_config_registry |
| 7 | bot_agent.feature_flags |
| 8 | bot_agent.knowledge.semantic_card_payload_adapter |
| 9 | bot_agent.multiagent.agents.agent_llm_config |
| 10 | bot_agent.multiagent.dialogue_policy |
| 11 | bot_agent.multiagent.final_answer_acceptance_gate |
| 12 | bot_agent.multiagent.final_answer_directive |
| 13 | bot_agent.multiagent.fresh_chat_context_policy |
| 14 | bot_agent.multiagent.hybrid_retrieval_planner |
| 15 | bot_agent.multiagent.orchestrator |
| 16 | bot_agent.multiagent.philosophy_kernel |
| 17 | bot_agent.multiagent.planner_drift_monitor |
| 18 | bot_agent.multiagent.thread_storage |
| 19 | bot_agent.multiagent.writer_context_package |
| 20 | bot_agent.prompt_registry_v2 |
| 21 | collections |
| 22 | datetime |
| 23 | dependencies |
| 24 | fastapi |
| 25 | identity |
| 26 | importlib |
| 27 | json |
| 28 | logging |
| 29 | os |
| 30 | pathlib |
| 31 | threading |
| 32 | typing |

### Importers by Category
| Category | Count | Examples |
| --- | --- | --- |
| production | 0 | none |
| tests | 1 | bot_psychologist/tests/test_admin_api.py |
| tools | 1 | TO_DO_LIST/tools/run_prd_047_42_god_file_boundary_mapping.py |
| docs | 0 | none |
| other | 0 | none |

## writer_contract

- module: `bot_agent.multiagent.contracts.writer_contract`
- imported_module_count: `13`
- importer_count: `56`

### Imported Modules
| Index | Imported module |
| --- | --- |
| 1 | __future__ |
| 2 | context_assembly |
| 3 | context_package |
| 4 | dataclasses |
| 5 | diagnostic_card |
| 6 | fresh_chat_context_policy |
| 7 | json |
| 8 | legacy_advisory_sanitizer |
| 9 | memory_bundle |
| 10 | thread_state |
| 11 | typing |
| 12 | writer_context_package |
| 13 | writer_move_compliance |

### Importers by Category
| Category | Count | Examples |
| --- | --- | --- |
| production | 7 | bot_psychologist/bot_agent/multiagent/contracts/planner_bridge_writer_contract_pilot_v1.py<br>bot_psychologist/scripts/run_prd_047_10_hf1_dialogue_pragmatics_eval.py<br>bot_psychologist/scripts/run_prd_047_10_human_like_eval.py<br>bot_psychologist/scripts/run_prd_047_11_audit.py<br>bot_psychologist/scripts/run_prd_047_11_hf1_writer_prompt_diet.py<br>bot_psychologist/scripts/run_prd_047_8_mvp_free_dialogue_cases.py<br>bot_psychologist/scripts/run_prd_047_9_mvp_context_unclamp_cases.py |
| tests | 40 | bot_psychologist/tests/contract/test_prd_047_42_god_file_boundary_mapping.py<br>bot_psychologist/tests/multiagent/test_agent_hot_swap.py<br>bot_psychologist/tests/multiagent/test_hf2_writer_contract_prompt_contains_knowledge.py<br>bot_psychologist/tests/multiagent/test_planner_bridge_writer_contract_pilot_builder.py<br>bot_psychologist/tests/multiagent/test_planner_bridge_writer_contract_pilot_immutability.py<br>bot_psychologist/tests/multiagent/test_planner_bridge_writer_contract_pilot_kb_boundaries.py<br>bot_psychologist/tests/multiagent/test_planner_bridge_writer_contract_pilot_no_user_path_effect.py<br>bot_psychologist/tests/multiagent/test_planner_bridge_writer_contract_pilot_safety.py<br>bot_psychologist/tests/multiagent/test_post_cutover_model_guard.py<br>bot_psychologist/tests/multiagent/test_prompt_constraint_pilot_runtime_no_user_path_effect.py<br>bot_psychologist/tests/multiagent/test_quality_trace.py<br>bot_psychologist/tests/multiagent/test_validator_agent.py<br>bot_psychologist/tests/multiagent/test_writer_agent.py<br>bot_psychologist/tests/multiagent/test_writer_contract.py<br>bot_psychologist/tests/multiagent/test_writer_kb_payload_prompt_integration.py<br>bot_psychologist/tests/multiagent/test_writer_llm_client_compat.py<br>bot_psychologist/tests/multiagent/test_writer_prompt_replay_builder.py<br>bot_psychologist/tests/multiagent/test_writer_prompt_replay_immutability.py<br>bot_psychologist/tests/multiagent/test_writer_prompt_replay_kb_boundaries.py<br>bot_psychologist/tests/multiagent/test_writer_prompt_replay_no_user_path_effect.py<br>bot_psychologist/tests/multiagent/test_writer_prompt_replay_prompt_bloat.py<br>bot_psychologist/tests/multiagent/test_writer_prompt_replay_safety.py<br>bot_psychologist/tests/test_concrete_answer_fit_no_static_template.py<br>bot_psychologist/tests/test_multiagent_prd_047_10_hf1_dialogue_pragmatics.py<br>bot_psychologist/tests/test_prd_047_11_hf1_writer_prompt_diet.py |
| tools | 9 | TO_DO_LIST/tools/PRD-047.14/run_summary_routing_audit.py<br>TO_DO_LIST/tools/PRD-047.15/run_contextual_retrieval_composer_acceptance.py<br>TO_DO_LIST/tools/run_prd_047_42_god_file_boundary_mapping.py<br>bot_psychologist/tools/prd_047_26_live_quality_triage.py<br>bot_psychologist/tools/probe_botdb_rag_to_writer_hf2.py<br>bot_psychologist/tools/run_overlay_shadow_trace_smoke.py<br>bot_psychologist/tools/run_planner_bridge_writer_contract_pilot_eval.py<br>bot_psychologist/tools/run_prompt_constraint_pilot_runtime_eval.py<br>bot_psychologist/tools/run_writer_prompt_replay_eval.py |
| docs | 0 | none |
| other | 0 | none |
