# _call_llm Variable Dependency Graph

## Cluster Summary

| cluster | lines | assigned vars | downstream scope | dominant dependencies |
| --- | --- | --- | --- | --- |
| client_and_ctx_default_seeding | 141-254 | 2 | provider_dispatch_input, writer_prompt_input | contract, self |
| knowledge_practice_kernel_inputs | 255-303 | 12 | local_only, writer_prompt_input | bool, ctx, dict, do_not_ask_definition, isinstance, item, knowledge_answer, knowledge_answer_first, list, practice_allowed, practice_gate, str |
| dialogue_policy_and_context_budget | 304-332 | 8 | local_only, writer_prompt_input | context_budget_chars, context_budget_for_profile, ctx, dialogue_policy_payload, dialogue_profile, dict, format_conversation_context_for_writer_with_meta, int, isinstance, normalize_dialogue_profile, str |
| request_detectors_and_mvp_override_block | 333-406 | 14 | local_only, writer_prompt_input | application_request, bool, constraint_resolution, detect_application_request, detect_direct_concrete_request, detect_examples_request, detect_expansion_request, detect_explicit_answer_need, detect_numbered_list_request, detect_practice_overview_request, detect_sarcasm_or_negative_feedback, detect_summary_request, dialogue_policy_payload, dict, direct_concrete_request, examples_requested, expansion_requested, explicit_answer_need, isinstance, item, list, numbered_list_requested, practice_overview_requested, sarcasm_or_negative_feedback, str, summary_request, user_message |
| writer_kb_payload_and_trace_capture | 407-453 | 2 | local_only, writer_prompt_input | bool, ctx, dict, format_writer_kb_payload_for_prompt, isinstance, list, str, writer_kb_payload_fallback_reason |
| writer_user_template_render_core | 454-611 | 1 | provider_dispatch_input | WRITER_USER_TEMPLATE, bool, constraint_resolution, context_meta, ctx, dialogue_profile, do_not_ask_definition, external_surveillance_frame_ban, float, formatted_context, freedom_hard_boundaries, human_like_answer_policy, int, item, knowledge_answer, knowledge_answer_first, known_concept_clarification_ban, list, mvp_override_block, overruled_constraints, philosophy_kernel, practice_allowed, practice_ban_instruction, repair_user_dissatisfaction, selected_lenses, self, str, writer_freedom_contract, writer_kb_payload_text |
| writer_user_template_render_runtime_tail | 612-842 | 0 | none | none |
| prompt_constraint_append_and_debug_bookkeeping | 843-891 | 3 | local_only, writer_prompt_input | dict, format_prompt_constraint_section_v1, isinstance, list, prompt_constraint_decision, str |
| runtime_settings_and_system_prompt_selection | 892-901 | 4 | local_only, provider_dispatch_input, response_parse_input | DIALOGUE_PROFILE_MVP_FREE, WRITER_SYSTEM, WRITER_SYSTEM_MVP_FREE_DIALOGUE, ctx, dialogue_profile, normalize_dialogue_profile, self, time |
| provider_dispatch | 902-912 | 1 | response_parse_input | client, create_agent_completion, runtime_settings, system_prompt, user_prompt |
| response_unpack_cost_and_return | 913-938 | 6 | response_parse_input | int, result, self, start_ts, time, tokens_completion, tokens_prompt |

## Full Local Variable Inventory

| name | assignment lines | cluster | depends_on | downstream scope | sample later uses |
| --- | --- | --- | --- | --- | --- |
| client | 141-141 | client_and_ctx_default_seeding | self | provider_dispatch_input | 142, 903 |
| ctx | 145-145 | client_and_ctx_default_seeding | contract | writer_prompt_input | 146, 147, 148, 149, 150, 151, 152, 153 |
| knowledge_answer | 255-259 | knowledge_practice_kernel_inputs | isinstance, dict, ctx | writer_prompt_input | 265, 266, 513, 519, 512, 514 |
| practice_gate | 260-264 | knowledge_practice_kernel_inputs | isinstance, dict, ctx | local_only | 267 |
| knowledge_answer_first | 265-265 | knowledge_practice_kernel_inputs | bool, knowledge_answer | writer_prompt_input | 280, 515 |
| do_not_ask_definition | 266-266 | knowledge_practice_kernel_inputs | bool, knowledge_answer | writer_prompt_input | 275, 516 |
| practice_allowed | 267-267 | knowledge_practice_kernel_inputs | bool, practice_gate | writer_prompt_input | 270, 517 |
| practice_ban_instruction | 268-272 | knowledge_practice_kernel_inputs | practice_allowed, str, ctx | writer_prompt_input | 521 |
| known_concept_clarification_ban | 273-277 | knowledge_practice_kernel_inputs | do_not_ask_definition | writer_prompt_input | 522 |
| external_surveillance_frame_ban | 278-282 | knowledge_practice_kernel_inputs | knowledge_answer_first | writer_prompt_input | 523 |
| philosophy_kernel | 283-287 | knowledge_practice_kernel_inputs | isinstance, dict, ctx | writer_prompt_input | 525, 530 |
| writer_freedom_contract | 288-292 | knowledge_practice_kernel_inputs | isinstance, dict, ctx | writer_prompt_input | 542, 545, 547 |
| selected_lenses | 293-297 | knowledge_practice_kernel_inputs | str, item, list, ctx | writer_prompt_input | 533 |
| freedom_hard_boundaries | 298-302 | knowledge_practice_kernel_inputs | str, item, list, ctx | writer_prompt_input | 551 |
| dialogue_policy_payload | 304-308 | dialogue_policy_and_context_budget | isinstance, dict, ctx | local_only | 321, 311, 310, 316, 315, 324, 335, 334 |
| human_like_answer_policy | 309-313 | dialogue_policy_and_context_budget | isinstance, dict, dialogue_policy_payload | writer_prompt_input | 875, 774, 777, 799, 802, 805, 817, 772 |
| constraint_resolution | 314-318 | dialogue_policy_and_context_budget | isinstance, dict, dialogue_policy_payload | writer_prompt_input | 374, 832, 835, 839 |
| user_message | 319-319 | dialogue_policy_and_context_budget | str, ctx | local_only | 340, 343, 346, 349, 352, 355, 358, 361 |
| dialogue_profile | 320-322 | dialogue_policy_and_context_budget | normalize_dialogue_profile, dialogue_policy_payload, ctx | writer_prompt_input | 901, 390, 329, 893, 894, 897, 325, 324 |
| context_budget_chars | 323-326 | dialogue_policy_and_context_budget | int, context_budget_for_profile, dialogue_profile, dialogue_policy_payload | local_only | 330 |
| context_meta | 327-331 | dialogue_policy_and_context_budget | format_conversation_context_for_writer_with_meta, dialogue_profile, context_budget_chars, str, ctx | writer_prompt_input | 867, 866, 869, 872, 499, 501, 502, 500 |
| formatted_context | 327-331 | dialogue_policy_and_context_budget | format_conversation_context_for_writer_with_meta, dialogue_profile, context_budget_chars, str, ctx | writer_prompt_input | 498 |
| mvp_overrides_payload | 333-337 | request_detectors_and_mvp_override_block | isinstance, dict, dialogue_policy_payload | local_only | 398, 394, 395, 396, 397 |
| practice_overview_requested | 338-340 | request_detectors_and_mvp_override_block | bool, detect_practice_overview_request, user_message, dialogue_policy_payload | local_only | 378, 397 |
| examples_requested | 341-343 | request_detectors_and_mvp_override_block | bool, detect_examples_request, user_message, dialogue_policy_payload | local_only | 379 |
| numbered_list_requested | 344-346 | request_detectors_and_mvp_override_block | bool, detect_numbered_list_request, user_message, dialogue_policy_payload | local_only | 380 |
| expansion_requested | 347-349 | request_detectors_and_mvp_override_block | bool, detect_expansion_request, user_message, dialogue_policy_payload | local_only | 381 |
| explicit_answer_need | 350-352 | request_detectors_and_mvp_override_block | bool, detect_explicit_answer_need, user_message, dialogue_policy_payload | local_only | 382, 877, 400 |
| direct_concrete_request | 353-355 | request_detectors_and_mvp_override_block | bool, detect_direct_concrete_request, user_message, dialogue_policy_payload | local_only | 383, 401 |
| summary_request | 356-358 | request_detectors_and_mvp_override_block | bool, detect_summary_request, user_message, dialogue_policy_payload | local_only | 384, 402 |
| sarcasm_or_negative_feedback | 359-361 | request_detectors_and_mvp_override_block | bool, detect_sarcasm_or_negative_feedback, user_message, dialogue_policy_payload | local_only | 385, 879, 370, 403 |
| application_request | 362-364 | request_detectors_and_mvp_override_block | bool, detect_application_request, user_message, dialogue_policy_payload | local_only | 386 |
| repair_user_dissatisfaction | 365-371 | request_detectors_and_mvp_override_block | bool, sarcasm_or_negative_feedback, dict, dialogue_policy_payload | writer_prompt_input | 878, 794 |
| overruled_constraints | 372-376 | request_detectors_and_mvp_override_block | str, item, list, constraint_resolution | writer_prompt_input | 880, 837 |
| rich_user_request | 377-388 | request_detectors_and_mvp_override_block | practice_overview_requested, examples_requested, numbered_list_requested, expansion_requested, explicit_answer_need, direct_concrete_request, summary_request, sarcasm_or_negative_feedback, application_request, bool, dialogue_policy_payload | local_only | 399 |
| mvp_override_block | 389-389 | request_detectors_and_mvp_override_block | literal_or_direct_ctx_only | writer_prompt_input | 841 |
| writer_kb_payload_fallback_reason | 407-414 | writer_kb_payload_and_trace_capture | str, ctx, bool | local_only | 415, 424 |
| writer_kb_payload_text | 417-425 | writer_kb_payload_and_trace_capture | format_writer_kb_payload_for_prompt, writer_kb_payload_fallback_reason, list, isinstance, dict, ctx | writer_prompt_input | 511 |
| user_prompt | 454-842 | writer_user_template_render_core | WRITER_USER_TEMPLATE, formatted_context, writer_kb_payload_text, practice_ban_instruction, known_concept_clarification_ban, external_surveillance_frame_ban, mvp_override_block, ctx, str, float, int, dialogue_profile, self, selected_lenses, freedom_hard_boundaries, overruled_constraints, knowledge_answer_first, do_not_ask_definition, practice_allowed, bool, context_meta, knowledge_answer, philosophy_kernel, writer_freedom_contract, item, human_like_answer_policy, repair_user_dissatisfaction, constraint_resolution, list | provider_dispatch_input | 861, 860, 907 |
| prompt_section | 843-847 | prompt_constraint_append_and_debug_bookkeeping | prompt_constraint_decision, format_prompt_constraint_section_v1 | writer_prompt_input | 859, 863, 865, 860 |
| activation_mode | 848-852 | prompt_constraint_append_and_debug_bookkeeping | isinstance, prompt_constraint_decision, dict, str | local_only | 862 |
| blocked_reasons | 853-858 | prompt_constraint_append_and_debug_bookkeeping | list, isinstance, prompt_constraint_decision, dict | local_only | 864 |
| start_ts | 892-892 | runtime_settings_and_system_prompt_selection | time | response_parse_input | 920 |
| dialogue_profile | 893-893 | runtime_settings_and_system_prompt_selection | normalize_dialogue_profile, ctx | local_only | 901, 894, 897 |
| runtime_settings | 894-894 | runtime_settings_and_system_prompt_selection | self, dialogue_profile | provider_dispatch_input | 923, 925, 926, 927, 904, 909, 910, 911 |
| system_prompt | 895-899 | runtime_settings_and_system_prompt_selection | WRITER_SYSTEM_MVP_FREE_DIALOGUE, WRITER_SYSTEM, dialogue_profile, DIALOGUE_PROFILE_MVP_FREE | provider_dispatch_input | 900, 906 |
| result | 902-912 | provider_dispatch | create_agent_completion, client, runtime_settings, system_prompt, user_prompt | response_parse_input | 913, 915, 916, 917, 924 |
| llm_response | 913-913 | response_unpack_cost_and_return | result | response_parse_input | 938, 928 |
| tokens_completion | 914-918 | response_unpack_cost_and_return | result | response_parse_input | 919, 930 |
| tokens_prompt | 914-918 | response_unpack_cost_and_return | result | response_parse_input | 919, 929 |
| tokens_total | 914-918 | response_unpack_cost_and_return | result | response_parse_input | 931 |
| estimated_cost | 919-919 | response_unpack_cost_and_return | self, tokens_prompt, tokens_completion | response_parse_input | 932 |
| duration_ms | 920-920 | response_unpack_cost_and_return | int, start_ts, time | response_parse_input | 933 |

## Notes

- `writer_prompt_input` means the variable feeds `WRITER_USER_TEMPLATE.format(...)` directly or indirectly.
- `provider_dispatch_input` means the variable survives until the `create_agent_completion(...)` call at lines `902-912`.
- Variables inside `407-453`, `843-891`, and `913-938` are the most obviously coupled to `self.last_debug` and therefore poor pure-function candidates without returning explicit debug patches.
