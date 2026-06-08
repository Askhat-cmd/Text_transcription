# Hardcoded Reply Classification

## Executive Summary
- status: `blocker`
- hardcoded_candidates_total: `1501`
- active_user_facing_candidates: `131`
- blocker_stub_user_facing_count: `55`
- warning_needs_targeted_refactor_count: `41`
- allowed_safety_boundary_count: `16`
- allowed_minimal_boundary_count: `19`

## Top Risky Files
| Path | Count |
| --- | ---: |
| `bot_psychologist/bot_agent/multiagent/agents/writer_agent.py` | 49 |
| `bot_psychologist/bot_agent/multiagent/diagnostic_center.py` | 17 |
| `bot_psychologist/bot_agent/multiagent/active_line.py` | 11 |
| `bot_psychologist/bot_agent/multiagent/agents/validator_agent.py` | 4 |
| `bot_psychologist/bot_agent/onboarding_flow.py` | 3 |
| `bot_psychologist/bot_agent/prompt_registry_v2.py` | 2 |
| `bot_psychologist/bot_agent/path_builder.py` | 1 |
| `bot_psychologist/bot_agent/practices_recommender.py` | 1 |
| `bot_psychologist/bot_agent/prompt_system_base.md` | 1 |
| `bot_psychologist/bot_agent/multiagent/dialogue_act_resolver.py` | 1 |

## Blocker Candidates
| Path | Line | Symbol | Type | Reason | Recommended action |
| --- | ---: | --- | --- | --- | --- |
| `bot_psychologist/bot_agent/onboarding_flow.py` | 125 | `build_first_turn_instruction` | `knowledge_explanation` | static explanation/interpretation can become repeated user-facing answer | `remove_in_targeted_prd` |
| `bot_psychologist/bot_agent/onboarding_flow.py` | 135 | `build_mixed_query_instruction` | `knowledge_explanation` | static explanation/interpretation can become repeated user-facing answer | `remove_in_targeted_prd` |
| `bot_psychologist/bot_agent/onboarding_flow.py` | 157 | `build_informational_guardrail_instruction` | `knowledge_explanation` | static explanation/interpretation can become repeated user-facing answer | `remove_in_targeted_prd` |
| `bot_psychologist/bot_agent/path_builder.py` | 496 | `_determine_key_focus` | `knowledge_explanation` | static explanation/interpretation can become repeated user-facing answer | `remove_in_targeted_prd` |
| `bot_psychologist/bot_agent/practices_recommender.py` | 249 | `get_practice_details` | `knowledge_explanation` | static explanation/interpretation can become repeated user-facing answer | `remove_in_targeted_prd` |
| `bot_psychologist/bot_agent/prompt_registry_v2.py` | 98 | `_build_style_policy` | `knowledge_explanation` | static explanation/interpretation can become repeated user-facing answer | `remove_in_targeted_prd` |
| `bot_psychologist/bot_agent/prompt_registry_v2.py` | 115 | `_build_style_policy` | `knowledge_explanation` | static explanation/interpretation can become repeated user-facing answer | `remove_in_targeted_prd` |
| `bot_psychologist/bot_agent/prompt_system_base.md` | 18 | `<text>` | `knowledge_explanation` | static explanation/interpretation can become repeated user-facing answer | `remove_in_targeted_prd` |
| `bot_psychologist/bot_agent/multiagent/active_line.py` | 150 | `_build_active_line_text` | `knowledge_explanation` | static explanation/interpretation can become repeated user-facing answer | `remove_in_targeted_prd` |
| `bot_psychologist/bot_agent/multiagent/active_line.py` | 174 | `_build_next_move` | `knowledge_explanation` | static explanation/interpretation can become repeated user-facing answer | `remove_in_targeted_prd` |
| `bot_psychologist/bot_agent/multiagent/active_line.py` | 136 | `_build_active_line_text` | `knowledge_explanation` | static explanation/interpretation can become repeated user-facing answer | `remove_in_targeted_prd` |
| `bot_psychologist/bot_agent/multiagent/active_line.py` | 145 | `_build_active_line_text` | `knowledge_explanation` | static explanation/interpretation can become repeated user-facing answer | `remove_in_targeted_prd` |
| `bot_psychologist/bot_agent/multiagent/active_line.py` | 147 | `_build_active_line_text` | `knowledge_explanation` | static explanation/interpretation can become repeated user-facing answer | `remove_in_targeted_prd` |
| `bot_psychologist/bot_agent/multiagent/active_line.py` | 155 | `_build_next_move` | `knowledge_explanation` | static explanation/interpretation can become repeated user-facing answer | `remove_in_targeted_prd` |
| `bot_psychologist/bot_agent/multiagent/active_line.py` | 163 | `_build_next_move` | `knowledge_explanation` | static explanation/interpretation can become repeated user-facing answer | `remove_in_targeted_prd` |
| `bot_psychologist/bot_agent/multiagent/active_line.py` | 165 | `_build_next_move` | `knowledge_explanation` | static explanation/interpretation can become repeated user-facing answer | `remove_in_targeted_prd` |
| `bot_psychologist/bot_agent/multiagent/active_line.py` | 167 | `_build_next_move` | `knowledge_explanation` | static explanation/interpretation can become repeated user-facing answer | `remove_in_targeted_prd` |
| `bot_psychologist/bot_agent/multiagent/active_line.py` | 171 | `_build_next_move` | `knowledge_explanation` | static explanation/interpretation can become repeated user-facing answer | `remove_in_targeted_prd` |
| `bot_psychologist/bot_agent/multiagent/active_line.py` | 173 | `_build_next_move` | `knowledge_explanation` | static explanation/interpretation can become repeated user-facing answer | `remove_in_targeted_prd` |
| `bot_psychologist/bot_agent/multiagent/dialogue_act_resolver.py` | 51 | `<module>` | `repair` | static repair answer can replace Writer instead of retry/contract signal | `convert_to_writer_retry` |
| `bot_psychologist/bot_agent/multiagent/dialogue_policy.py` | 40 | `<module>` | `knowledge_explanation` | static explanation/interpretation can become repeated user-facing answer | `remove_in_targeted_prd` |
| `bot_psychologist/bot_agent/multiagent/dialogue_pragmatics.py` | 50 | `<module>` | `repair` | static repair answer can replace Writer instead of retry/contract signal | `convert_to_writer_retry` |
| `bot_psychologist/bot_agent/multiagent/final_answer_directive.py` | 27 | `<module>` | `knowledge_explanation` | static explanation/interpretation can become repeated user-facing answer | `remove_in_targeted_prd` |
| `bot_psychologist/bot_agent/multiagent/response_planner.py` | 152 | `<module>` | `repair` | static repair answer can replace Writer instead of retry/contract signal | `convert_to_writer_retry` |
| `bot_psychologist/bot_agent/multiagent/agents/writer_agent.py` | 1324 | `_enforce_answer_compliance` | `repair` | static repair answer can replace Writer instead of retry/contract signal | `convert_to_writer_retry` |
| `bot_psychologist/bot_agent/multiagent/agents/writer_agent.py` | 1403 | `_enforce_answer_compliance` | `knowledge_explanation` | static explanation/interpretation can become repeated user-facing answer | `remove_in_targeted_prd` |
| `bot_psychologist/bot_agent/multiagent/agents/writer_agent.py` | 1450 | `_enforce_answer_compliance` | `knowledge_explanation` | static explanation/interpretation can become repeated user-facing answer | `remove_in_targeted_prd` |
| `bot_psychologist/bot_agent/multiagent/agents/writer_agent.py` | 1538 | `_enforce_mvp_free_dialogue_compliance` | `repair` | static repair answer can replace Writer instead of retry/contract signal | `convert_to_writer_retry` |
| `bot_psychologist/bot_agent/multiagent/agents/writer_agent.py` | 1592 | `_enforce_mvp_free_dialogue_compliance` | `repair` | static repair answer can replace Writer instead of retry/contract signal | `convert_to_writer_retry` |
| `bot_psychologist/bot_agent/multiagent/agents/writer_agent.py` | 1601 | `_enforce_mvp_free_dialogue_compliance` | `knowledge_explanation` | static explanation/interpretation can become repeated user-facing answer | `remove_in_targeted_prd` |
| `bot_psychologist/bot_agent/multiagent/agents/writer_agent.py` | 1667 | `_enforce_mvp_free_dialogue_compliance` | `repair` | static repair answer can replace Writer instead of retry/contract signal | `convert_to_writer_retry` |
| `bot_psychologist/bot_agent/multiagent/agents/writer_agent.py` | 1679 | `_enforce_mvp_free_dialogue_compliance` | `knowledge_explanation` | static explanation/interpretation can become repeated user-facing answer | `remove_in_targeted_prd` |
| `bot_psychologist/bot_agent/multiagent/agents/writer_agent.py` | 1715 | `_enforce_mvp_free_dialogue_compliance` | `knowledge_explanation` | static explanation/interpretation can become repeated user-facing answer | `remove_in_targeted_prd` |
| `bot_psychologist/bot_agent/multiagent/agents/writer_agent.py` | 1168 | `_enforce_answer_compliance` | `knowledge_explanation` | static explanation/interpretation can become repeated user-facing answer | `remove_in_targeted_prd` |
| `bot_psychologist/bot_agent/multiagent/agents/writer_agent.py` | 1184 | `_enforce_answer_compliance` | `repair` | static repair answer can replace Writer instead of retry/contract signal | `convert_to_writer_retry` |
| `bot_psychologist/bot_agent/multiagent/agents/writer_agent.py` | 1218 | `_enforce_answer_compliance` | `knowledge_explanation` | static explanation/interpretation can become repeated user-facing answer | `remove_in_targeted_prd` |
| `bot_psychologist/bot_agent/multiagent/agents/writer_agent.py` | 1330 | `_enforce_answer_compliance` | `knowledge_explanation` | static explanation/interpretation can become repeated user-facing answer | `remove_in_targeted_prd` |
| `bot_psychologist/bot_agent/multiagent/agents/writer_agent.py` | 1337 | `_enforce_answer_compliance` | `knowledge_explanation` | static explanation/interpretation can become repeated user-facing answer | `remove_in_targeted_prd` |
| `bot_psychologist/bot_agent/multiagent/agents/writer_agent.py` | 1343 | `_enforce_answer_compliance` | `knowledge_explanation` | static explanation/interpretation can become repeated user-facing answer | `remove_in_targeted_prd` |
| `bot_psychologist/bot_agent/multiagent/agents/writer_agent.py` | 1383 | `_enforce_answer_compliance` | `knowledge_explanation` | static explanation/interpretation can become repeated user-facing answer | `remove_in_targeted_prd` |

## Warning Candidates
| Path | Line | Symbol | Type | Reason | Recommended action |
| --- | ---: | --- | --- | --- | --- |
| `bot_psychologist/bot_agent/output_validator.py` | 251 | `safe_fallback` | `unknown` | active runtime path may expose static user-facing text | `needs_architect_decision` |
| `bot_psychologist/bot_agent/multiagent/diagnostic_center.py` | 69 | `_resolve_current_need` | `unknown` | active runtime path may expose static user-facing text | `needs_architect_decision` |
| `bot_psychologist/bot_agent/multiagent/diagnostic_center.py` | 317 | `_build_confidence` | `unknown` | active runtime path may expose static user-facing text | `needs_architect_decision` |
| `bot_psychologist/bot_agent/multiagent/diagnostic_center.py` | 321 | `_build_user_state_summary` | `unknown` | active runtime path may expose static user-facing text | `needs_architect_decision` |
| `bot_psychologist/bot_agent/multiagent/diagnostic_center.py` | 337 | `_build_thread_line_summary` | `unknown` | active runtime path may expose static user-facing text | `needs_architect_decision` |
| `bot_psychologist/bot_agent/multiagent/diagnostic_center.py` | 96 | `_resolve_situation_label` | `unknown` | active runtime path may expose static user-facing text | `needs_architect_decision` |
| `bot_psychologist/bot_agent/multiagent/diagnostic_center.py` | 100 | `_resolve_situation_label` | `unknown` | active runtime path may expose static user-facing text | `needs_architect_decision` |
| `bot_psychologist/bot_agent/multiagent/diagnostic_center.py` | 107 | `_resolve_situation_label` | `unknown` | active runtime path may expose static user-facing text | `needs_architect_decision` |
| `bot_psychologist/bot_agent/multiagent/diagnostic_center.py` | 111 | `_resolve_situation_label` | `unknown` | active runtime path may expose static user-facing text | `needs_architect_decision` |
| `bot_psychologist/bot_agent/multiagent/diagnostic_center.py` | 173 | `_resolve_writer_move` | `unknown` | active runtime path may expose static user-facing text | `needs_architect_decision` |
| `bot_psychologist/bot_agent/multiagent/diagnostic_center.py` | 177 | `_resolve_writer_move` | `unknown` | active runtime path may expose static user-facing text | `needs_architect_decision` |
| `bot_psychologist/bot_agent/multiagent/diagnostic_center.py` | 311 | `_build_confidence` | `unknown` | active runtime path may expose static user-facing text | `needs_architect_decision` |
| `bot_psychologist/bot_agent/multiagent/diagnostic_center.py` | 315 | `_build_confidence` | `unknown` | active runtime path may expose static user-facing text | `needs_architect_decision` |
| `bot_psychologist/bot_agent/multiagent/diagnostic_center.py` | 330 | `_build_thread_line_summary` | `unknown` | active runtime path may expose static user-facing text | `needs_architect_decision` |
| `bot_psychologist/bot_agent/multiagent/diagnostic_center.py` | 332 | `_build_thread_line_summary` | `unknown` | active runtime path may expose static user-facing text | `needs_architect_decision` |
| `bot_psychologist/bot_agent/multiagent/diagnostic_center.py` | 334 | `_build_thread_line_summary` | `unknown` | active runtime path may expose static user-facing text | `needs_architect_decision` |
| `bot_psychologist/bot_agent/multiagent/diagnostic_center.py` | 336 | `_build_thread_line_summary` | `unknown` | active runtime path may expose static user-facing text | `needs_architect_decision` |
| `bot_psychologist/bot_agent/multiagent/diagnostic_center.py` | 160 | `_resolve_writer_move` | `unknown` | active runtime path may expose static user-facing text | `needs_architect_decision` |
| `bot_psychologist/bot_agent/multiagent/orchestrator.py` | 396 | `run` | `unknown` | active runtime path may expose static user-facing text | `needs_architect_decision` |
| `bot_psychologist/bot_agent/multiagent/agents/validator_agent.py` | 93 | `_check_safety` | `unknown` | active runtime path may expose static user-facing text | `needs_architect_decision` |
| `bot_psychologist/bot_agent/multiagent/agents/validator_agent.py` | 96 | `_check_safety` | `unknown` | active runtime path may expose static user-facing text | `needs_architect_decision` |
| `bot_psychologist/bot_agent/multiagent/agents/validator_agent.py` | 102 | `_check_safety` | `unknown` | active runtime path may expose static user-facing text | `needs_architect_decision` |
| `bot_psychologist/bot_agent/multiagent/agents/validator_agent.py` | 112 | `_check_contract` | `unknown` | active runtime path may expose static user-facing text | `needs_architect_decision` |
| `bot_psychologist/bot_agent/multiagent/agents/writer_agent.py` | 1780 | `_format_diagnostic_summary` | `direct_answer` | Writer compliance path returns static text; needs call-site review before removal | `convert_to_contract_signal` |
| `bot_psychologist/bot_agent/multiagent/agents/writer_agent.py` | 1098 | `_enforce_answer_compliance` | `direct_answer` | Writer compliance path returns static text; needs call-site review before removal | `convert_to_contract_signal` |
| `bot_psychologist/bot_agent/multiagent/agents/writer_agent.py` | 1409 | `_enforce_answer_compliance` | `direct_answer` | Writer compliance path returns static text; needs call-site review before removal | `convert_to_contract_signal` |
| `bot_psychologist/bot_agent/multiagent/agents/writer_agent.py` | 1578 | `_enforce_mvp_free_dialogue_compliance` | `direct_answer` | Writer compliance path returns static text; needs call-site review before removal | `convert_to_contract_signal` |
| `bot_psychologist/bot_agent/multiagent/agents/writer_agent.py` | 1582 | `_enforce_mvp_free_dialogue_compliance` | `direct_answer` | Writer compliance path returns static text; needs call-site review before removal | `convert_to_contract_signal` |
| `bot_psychologist/bot_agent/multiagent/agents/writer_agent.py` | 1773 | `_format_hits` | `direct_answer` | Writer compliance path returns static text; needs call-site review before removal | `convert_to_contract_signal` |
| `bot_psychologist/bot_agent/multiagent/agents/writer_agent.py` | 1812 | `_static_fallback` | `direct_answer` | Writer compliance path returns static text; needs call-site review before removal | `convert_to_contract_signal` |
| `bot_psychologist/bot_agent/multiagent/agents/writer_agent.py` | 1816 | `_static_fallback` | `direct_answer` | Writer compliance path returns static text; needs call-site review before removal | `convert_to_contract_signal` |
| `bot_psychologist/bot_agent/multiagent/agents/writer_agent.py` | 1824 | `_static_fallback` | `direct_answer` | Writer compliance path returns static text; needs call-site review before removal | `convert_to_contract_signal` |
| `bot_psychologist/bot_agent/multiagent/agents/writer_agent.py` | 1203 | `_enforce_answer_compliance` | `direct_answer` | Writer compliance path returns static text; needs call-site review before removal | `convert_to_contract_signal` |
| `bot_psychologist/bot_agent/multiagent/agents/writer_agent.py` | 1316 | `_enforce_answer_compliance` | `direct_answer` | Writer compliance path returns static text; needs call-site review before removal | `convert_to_contract_signal` |
| `bot_psychologist/bot_agent/multiagent/agents/writer_agent.py` | 1321 | `_enforce_answer_compliance` | `direct_answer` | Writer compliance path returns static text; needs call-site review before removal | `convert_to_contract_signal` |
| `bot_psychologist/bot_agent/multiagent/agents/writer_agent.py` | 1350 | `_enforce_answer_compliance` | `direct_answer` | Writer compliance path returns static text; needs call-site review before removal | `convert_to_contract_signal` |
| `bot_psychologist/bot_agent/multiagent/agents/writer_agent.py` | 1371 | `_enforce_answer_compliance` | `direct_answer` | Writer compliance path returns static text; needs call-site review before removal | `convert_to_contract_signal` |
| `bot_psychologist/bot_agent/multiagent/agents/writer_agent.py` | 1381 | `_enforce_answer_compliance` | `direct_answer` | Writer compliance path returns static text; needs call-site review before removal | `convert_to_contract_signal` |
| `bot_psychologist/bot_agent/multiagent/agents/writer_agent.py` | 1419 | `_enforce_answer_compliance` | `direct_answer` | Writer compliance path returns static text; needs call-site review before removal | `convert_to_contract_signal` |
| `bot_psychologist/bot_agent/multiagent/agents/writer_agent.py` | 1432 | `_enforce_answer_compliance` | `direct_answer` | Writer compliance path returns static text; needs call-site review before removal | `convert_to_contract_signal` |

## Allowed Safety / Minimal Boundaries
| Path | Line | Symbol | Type | Reason | Recommended action |
| --- | ---: | --- | --- | --- | --- |
| `bot_psychologist/bot_agent/output_validator.py` | 247 | `safe_fallback` | `safety_minimal` | safety/empty-answer boundary candidate; keep only with trace evidence | `document` |
| `bot_psychologist/bot_agent/prompt_registry_v2.py` | 123 | `_build_style_policy` | `safety_minimal` | safety/empty-answer boundary candidate; keep only with trace evidence | `document` |
| `bot_psychologist/bot_agent/multiagent/diagnostic_center_creator_live_pilot_acceptance.py` | 308 | `_simulate_answer` | `safety_minimal` | safety/empty-answer boundary candidate; keep only with trace evidence | `document` |
| `bot_psychologist/bot_agent/multiagent/diagnostic_center_provider_backed_limited_smoke_execution.py` | 375 | `_build_provider_call_prompt` | `safety_minimal` | safety/empty-answer boundary candidate; keep only with trace evidence | `document` |
| `bot_psychologist/bot_agent/multiagent/agents/writer_agent.py` | 1283 | `_enforce_answer_compliance` | `safety_minimal` | safety/empty-answer boundary candidate; keep only with trace evidence | `document` |
| `bot_psychologist/bot_agent/multiagent/agents/writer_agent.py` | 1298 | `_enforce_answer_compliance` | `safety_minimal` | safety/empty-answer boundary candidate; keep only with trace evidence | `document` |
| `bot_psychologist/bot_agent/multiagent/agents/writer_agent.py` | 1808 | `_static_fallback` | `safety_minimal` | safety/empty-answer boundary candidate; keep only with trace evidence | `document` |
| `bot_psychologist/bot_agent/multiagent/agents/writer_agent.py` | 1354 | `_enforce_answer_compliance` | `safety_minimal` | safety/empty-answer boundary candidate; keep only with trace evidence | `document` |
| `bot_psychologist/bot_agent/multiagent/agents/writer_agent.py` | 1375 | `_enforce_answer_compliance` | `safety_minimal` | safety/empty-answer boundary candidate; keep only with trace evidence | `document` |
| `bot_psychologist/bot_agent/multiagent/agents/writer_agent.py` | 1439 | `_enforce_answer_compliance` | `safety_minimal` | safety/empty-answer boundary candidate; keep only with trace evidence | `document` |
| `bot_psychologist/bot_agent/multiagent/agents/writer_agent.py` | 1459 | `_enforce_answer_compliance` | `safety_minimal` | safety/empty-answer boundary candidate; keep only with trace evidence | `document` |
| `bot_psychologist/bot_agent/multiagent/agents/writer_agent.py` | 1572 | `_enforce_mvp_free_dialogue_compliance` | `safety_minimal` | safety/empty-answer boundary candidate; keep only with trace evidence | `document` |
| `Bot_data_base/api/routes/registry.py` | 183 | `_safe_chroma_delete_source` | `safety_minimal` | safety/empty-answer boundary candidate; keep only with trace evidence | `document` |
| `Bot_data_base/api/routes/registry.py` | 209 | `_safe_chroma_delete_source` | `safety_minimal` | safety/empty-answer boundary candidate; keep only with trace evidence | `document` |
| `Bot_data_base/api/routes/registry.py` | 333 | `_resolve_delete_policy` | `safety_minimal` | safety/empty-answer boundary candidate; keep only with trace evidence | `document` |
| `Bot_data_base/api/routes/registry.py` | 357 | `_resolve_delete_policy` | `safety_minimal` | safety/empty-answer boundary candidate; keep only with trace evidence | `document` |

## Allowed Minimal Boundaries
| Path | Line | Symbol | Type | Reason | Recommended action |
| --- | ---: | --- | --- | --- | --- |
| `bot_psychologist/bot_agent/multiagent/agents/writer_agent.py` | 48 | `<module>` | `minimal_contact` | short contact/close acknowledgement without conceptual interpretation | `document` |
| `bot_psychologist/bot_agent/multiagent/agents/writer_agent.py` | 1266 | `_enforce_answer_compliance` | `minimal_contact` | short contact/close acknowledgement without conceptual interpretation | `document` |
| `bot_psychologist/bot_agent/multiagent/agents/writer_agent.py` | 1280 | `_enforce_answer_compliance` | `minimal_contact` | short contact/close acknowledgement without conceptual interpretation | `document` |
| `bot_psychologist/bot_agent/multiagent/agents/writer_agent.py` | 1286 | `_enforce_answer_compliance` | `minimal_contact` | short contact/close acknowledgement without conceptual interpretation | `document` |
| `bot_psychologist/bot_agent/multiagent/agents/writer_agent.py` | 1289 | `_enforce_answer_compliance` | `minimal_contact` | short contact/close acknowledgement without conceptual interpretation | `document` |
| `bot_psychologist/bot_agent/multiagent/agents/writer_agent.py` | 1292 | `_enforce_answer_compliance` | `minimal_contact` | short contact/close acknowledgement without conceptual interpretation | `document` |
| `bot_psychologist/bot_agent/multiagent/agents/writer_agent.py` | 1305 | `_enforce_answer_compliance` | `minimal_contact` | short contact/close acknowledgement without conceptual interpretation | `document` |
| `bot_psychologist/bot_agent/multiagent/agents/writer_agent.py` | 1311 | `_enforce_answer_compliance` | `minimal_contact` | short contact/close acknowledgement without conceptual interpretation | `document` |
| `bot_psychologist/bot_agent/multiagent/agents/writer_agent.py` | 1378 | `_enforce_answer_compliance` | `minimal_contact` | short contact/close acknowledgement without conceptual interpretation | `document` |
| `bot_psychologist/bot_agent/multiagent/agents/writer_agent.py` | 1810 | `_static_fallback` | `minimal_contact` | short contact/close acknowledgement without conceptual interpretation | `document` |
| `bot_psychologist/bot_agent/multiagent/agents/writer_agent.py` | 1814 | `_static_fallback` | `minimal_contact` | short contact/close acknowledgement without conceptual interpretation | `document` |
| `bot_psychologist/bot_agent/multiagent/agents/writer_agent.py` | 1820 | `_static_fallback` | `minimal_contact` | short contact/close acknowledgement without conceptual interpretation | `document` |
| `bot_psychologist/bot_agent/multiagent/agents/writer_agent.py` | 1826 | `_static_fallback` | `minimal_contact` | short contact/close acknowledgement without conceptual interpretation | `document` |
| `bot_psychologist/bot_agent/multiagent/agents/writer_agent.py` | 1828 | `_static_fallback` | `minimal_contact` | short contact/close acknowledgement without conceptual interpretation | `document` |
| `bot_psychologist/bot_agent/multiagent/agents/writer_agent.py` | 1274 | `_enforce_answer_compliance` | `minimal_contact` | short contact/close acknowledgement without conceptual interpretation | `document` |
| `bot_psychologist/bot_agent/multiagent/agents/writer_agent.py` | 1352 | `_enforce_answer_compliance` | `minimal_contact` | short contact/close acknowledgement without conceptual interpretation | `document` |
| `bot_psychologist/bot_agent/multiagent/agents/writer_agent.py` | 1373 | `_enforce_answer_compliance` | `minimal_contact` | short contact/close acknowledgement without conceptual interpretation | `document` |
| `bot_psychologist/bot_agent/multiagent/agents/writer_agent.py` | 1377 | `_enforce_answer_compliance` | `minimal_contact` | short contact/close acknowledgement without conceptual interpretation | `document` |
| `bot_psychologist/bot_agent/multiagent/agents/writer_agent.py` | 1819 | `_static_fallback` | `minimal_contact` | short contact/close acknowledgement without conceptual interpretation | `document` |

## Next PRD Recommendation
`PRD-047.14-HF1.2 - Hardcoded Reply Removal / Writer Retry Conversion v1`
