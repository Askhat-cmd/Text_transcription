# Rule Coverage Log

- PRD: `PRD-047.42-APPLY-20`
- case_count: `17`
- covered_rule_count: `22`
- uncovered_rule_count: `53`

| rule | lines | condition | cases where condition fired |
| --- | --- | --- | --- |
| R01 | 584-585 | not text | empty_text_passthrough |
| R02 | 707-711 | 'greeting_answered_with_mechanism_explanation' in gate_failed_checks and _contains_any(lowered_user, ('здравств', 'привет', 'добрый день', 'добрый вечер')) | greeting_gate_feedback_repair |
| R03 | 767-773 | answer_obligation == 'close_gently' and (has_question or has_unsolicited_practice or _contains_any(lowered_text, ('если хочешь', 'если захочешь', 'давай продолжим', 'следующий шаг'))) | close_gently_obligation |
| R04 | 786-816 | answer_obligation == 'provide_one_bounded_practice' | bounded_practice_be_strong |
| R05 | 796-814 | '?' in text or len(text.strip()) > 900 or practice_multistep or (not practice_step_present) or (not practice_anchor_present) | bounded_practice_be_strong |
| R06 | 803-809 | 'будь сильным' in lowered_user | bounded_practice_be_strong |
| R07 | 818-824 | literal_markdown_echo | literal_markdown_echo |
| R08 | 821-824 | normalized_response != normalized_requested | literal_markdown_echo |
| R09 | 826-834 | answer_obligation == 'acknowledge_style_preference_then_answer' and ('расскажи больше' in lowered_text or len(text) < 140) | none |
| R10 | 829-834 | concept_question | none |
| R11 | 836-845 | answer_obligation == 'repair_and_answer_last_question' and ('сейчас полезнее прямое объяснение механизма' in lowered_text or len(text) < 180) | repair_last_question_neurostalking |
| R12 | 840-845 | 'нейросталкинг' in target.lower() | repair_last_question_neurostalking |
| R13 | 847-862 | answer_obligation == 'answer_last_offer' and (any((marker in lowered_text for marker in ('подтверди', 'если хочешь', 'могу так сделать'))) or any((marker in lowered_text for marker in ('предлагаю такой план', 'хотите,... | none |
| R14 | 857-862 | any((color in offer_repair_context for color in ('красн', 'оранж', 'зелен'))) | none |
| R15 | 864-872 | answer_obligation in {'answer_knowledge_question', 'answer_direct_question'} and ('сейчас полезнее прямое объяснение механизма' in lowered_text or len(text) < 140) | low_resource_short_contact, thanks_close_no_more_steps, safety_priority_question_strip, clarify_one_point_insert_question, user_repair_signal_retry, known_concept_neurostalking_repair, question_policy_none_known_concept, template_leakage_practice_forbidden, active_line_revoicing_trim, tail_known_concept_self_realization |
| R16 | 867-872 | concept_question | safety_priority_question_strip, known_concept_neurostalking_repair, question_policy_none_known_concept |
| R17 | 874-911 | dialogue_profile == DIALOGUE_PROFILE_MVP_FREE | mvp_free_branch_handoff |
| R18 | 914-918 | not practice_allowed and (not should_answer_directly) and (is_greeting or has_unsolicited_practice) | none |
| R19 | 921-923 | _contains_any(lowered_user, _LOW_RESOURCE_NO_PRACTICE_MARKERS) | low_resource_short_contact |
| R20 | 922-923 | has_unsolicited_practice or len(text) > 280 or '?' in text | low_resource_short_contact |
| R21 | 925-929 | active_line_intent == 'thanks_close' and (has_unsolicited_practice or _contains_any(lowered_text, ('шаг', 'давай сделаем', 'предложу еще'))) | thanks_close_no_more_steps |
| R22 | 931-932 | planner_safety_priority and has_question | none |
| R23 | 934-935 | planner_next_move == 'give_short_support' or planner_answer_shape == 'short_support' | none |
| R24 | 937-938 | planner_next_move == 'give_short_support' and (len(text) > 260 or has_question or has_unsolicited_practice) | none |
| R25 | 940-941 | planner_next_move == 'stabilize_safety' and (len(text) > 320 or has_question) | none |
| R26 | 943-947 | planner_next_move == 'stabilize_safety' and _contains_any(lowered_text, ('механизм', 'прогнозирован', 'контрол', 'паттерн', 'драйвер', 'до начала действия')) | none |
| R27 | 949-954 | planner_next_move == 'close_gently' and (has_question or has_unsolicited_practice or _contains_any(lowered_text, ('новый шаг', 'давай продолжим', 'в следующий раз разберем'))) | none |
| R28 | 956-960 | planner_next_move == 'give_short_support' and _contains_any(lowered_text, ('механизм', 'теория', 'стратегия', 'прогнозирован', 'контрол', 'паттерн')) | none |
| R29 | 962-970 | planner_next_move == 'clarify_one_point' | clarify_one_point_insert_question |
| R30 | 964-965 | question_count == 0 | clarify_one_point_insert_question |
| R31 | 966-968 | question_count > 1 | none |
| R32 | 969-970 | len(text) > 320 | none |
| R33 | 972-977 | user_repair_signal | user_repair_signal_retry |
| R34 | 981-999 | should_answer_directly and (asks_define_known_term or has_external_surveillance_frame) | none |
| R35 | 982-987 | 'самореализац' in lowered_user and ('коррелир' in lowered_user or 'связан' in lowered_user) | none |
| R36 | 988-993 | concept == 'нейросталкинг' | none |
| R37 | 994-999 | concept == 'самореализация' | none |
| R38 | 1001-1026 | planner_question_policy == 'none' and has_question | none |
| R39 | 1002-1008 | planner_next_move == 'give_direct_step' or planner_answer_shape == 'one_step' | none |
| R40 | 1009-1010 | planner_next_move == 'give_short_support' or planner_answer_shape == 'short_support' | none |
| R41 | 1011-1012 | planner_next_move == 'stabilize_safety' or planner_answer_shape == 'safety_grounding' | none |
| R42 | 1013-1025 | planner_next_move == 'answer_known_concept' | none |
| R43 | 1014-1019 | 'самореализац' in lowered_user and 'нейросталкинг' in lowered_user | none |
| R44 | 1020-1025 | 'нейросталкинг' in lowered_user | none |
| R45 | 1027-1043 | planner_question_policy == 'none' and _contains_any(lowered_text, ('что именно', 'почему', 'как ты', 'можешь ли', 'хочешь')) | none |
| R46 | 1030-1036 | planner_next_move == 'give_direct_step' or planner_answer_shape == 'one_step' | none |
| R47 | 1037-1038 | planner_next_move == 'give_short_support' | none |
| R48 | 1039-1040 | planner_next_move == 'stabilize_safety' | none |
| R49 | 1041-1042 | planner_next_move == 'close_gently' | none |
| R50 | 1044-1057 | planner_question_policy == 'none' | none |
| R51 | 1045-1051 | planner_next_move == 'give_direct_step' or planner_answer_shape == 'one_step' | none |
| R52 | 1052-1057 | planner_next_move == 'deepen_mechanism' or planner_answer_shape == 'mechanism_explanation' | none |
| R53 | 1059-1066 | planner_next_move == 'repair_misalignment' | none |
| R54 | 1061-1066 | has_question or has_repair_forbidden or len(text) > 480 | none |
| R55 | 1068-1071 | planner_practice_policy == 'forbidden' and has_unsolicited_practice | template_leakage_practice_forbidden |
| R56 | 1073-1082 | (planner_next_move == 'deepen_mechanism' or user_mechanism_request) and (planner_question_policy == 'none' or user_requests_no_question) and (len(text) > 700 or has_question or has_unsolicited_practice or user_request... | none |
| R57 | 1084-1090 | planner_answer_shape == 'one_step' or planner_next_move == 'give_direct_step' | none |
| R58 | 1092-1131 | planner_answer_shape == 'one_step' or user_step_request or active_line_intent == 'ask_for_direct_step' | none |
| R59 | 1094-1097 | list_like | none |
| R60 | 1096-1097 | first_item | none |
| R61 | 1099-1105 | len(sentence_parts) > 2 | none |
| R62 | 1106-1123 | planner_question_policy == 'none' and _contains_any(lowered_text, ('хочешь', 'хочется', 'можешь', 'уточни', 'попробу', 'какой', 'что выбрать')) | none |
| R63 | 1125-1131 | not has_step_marker | none |
| R64 | 1133-1152 | active_line_practice_suppression and (not active_line_should_offer_practice) and has_unsolicited_practice | none |
| R65 | 1134-1135 | planner_next_move == 'stabilize_safety' or planner_answer_shape == 'safety_grounding' | none |
| R66 | 1136-1141 | active_line_intent == 'correction_of_bot' or active_line_repair_mode | none |
| R67 | 1142-1147 | active_line_intent == 'understand_mechanism' | none |
| R68 | 1154-1169 | not active_line_revoicing_allowed and starts_with_mechanical_revoicing(text) | none |
| R69 | 1155-1160 | active_line_intent == 'correction_of_bot' or active_line_repair_mode | none |
| R70 | 1161-1166 | active_line_intent == 'understand_mechanism' | none |
| R71 | 1168-1169 | len(parts) == 2 and parts[1].strip() | none |
| R72 | 1171-1189 | planner_next_move == 'answer_known_concept' and planner_practice_policy == 'forbidden' | tail_known_concept_self_realization |
| R73 | 1172-1177 | 'самореализац' in lowered_user and 'нейросталкинг' in lowered_user | none |
| R74 | 1178-1183 | 'нейросталкинг' in lowered_user | none |
| R75 | 1184-1189 | 'самореализац' in lowered_user | tail_known_concept_self_realization |

## НЕПОКРЫТЫЕ ПРАВИЛА

- `R09` `826-834`: requires a more specific compound contract/text state than the current deterministic case set
- `R10` `829-834`: needs exact concept-oriented user message and matching planner obligation
- `R13` `847-862`: needs last-offer memory state plus exact repeated-offer wording
- `R14` `857-862`: needs last-offer memory state plus exact repeated-offer wording
- `R18` `914-918`: needs practice markers plus matching policy state
- `R22` `931-932`: requires a more specific compound contract/text state than the current deterministic case set
- `R23` `934-935`: requires a more specific compound contract/text state than the current deterministic case set
- `R24` `937-938`: needs practice markers plus matching policy state
- `R25` `940-941`: needs safety-priority planner profile with exact long/question shape
- `R26` `943-947`: needs safety-priority planner profile with exact long/question shape
- `R27` `949-954`: needs practice markers plus matching policy state
- `R28` `956-960`: requires a more specific compound contract/text state than the current deterministic case set
- `R31` `966-968`: requires a more specific compound contract/text state than the current deterministic case set
- `R32` `969-970`: requires a more specific compound contract/text state than the current deterministic case set
- `R34` `981-999`: requires a more specific compound contract/text state than the current deterministic case set
- `R35` `982-987`: needs dedicated self-realization concept fixture
- `R36` `988-993`: needs exact concept-oriented user message and matching planner obligation
- `R37` `994-999`: needs dedicated self-realization concept fixture
- `R38` `1001-1026`: requires a more specific compound contract/text state than the current deterministic case set
- `R39` `1002-1008`: needs exact one-step planner state and text shape to reach this nested branch
- `R40` `1009-1010`: requires a more specific compound contract/text state than the current deterministic case set
- `R41` `1011-1012`: needs safety-priority planner profile with exact long/question shape
- `R42` `1013-1025`: needs exact concept-oriented user message and matching planner obligation
- `R43` `1014-1019`: needs dedicated self-realization concept fixture
- `R44` `1020-1025`: needs exact concept-oriented user message and matching planner obligation
- `R45` `1027-1043`: requires a more specific compound contract/text state than the current deterministic case set
- `R46` `1030-1036`: needs exact one-step planner state and text shape to reach this nested branch
- `R47` `1037-1038`: requires a more specific compound contract/text state than the current deterministic case set
- `R48` `1039-1040`: needs safety-priority planner profile with exact long/question shape
- `R49` `1041-1042`: requires a more specific compound contract/text state than the current deterministic case set
- `R50` `1044-1057`: requires a more specific compound contract/text state than the current deterministic case set
- `R51` `1045-1051`: needs exact one-step planner state and text shape to reach this nested branch
- `R52` `1052-1057`: requires a more specific compound contract/text state than the current deterministic case set
- `R53` `1059-1066`: requires a more specific compound contract/text state than the current deterministic case set
- `R54` `1061-1066`: requires a more specific compound contract/text state than the current deterministic case set
- `R56` `1073-1082`: needs practice markers plus matching policy state
- `R57` `1084-1090`: needs exact one-step planner state and text shape to reach this nested branch
- `R58` `1092-1131`: needs exact one-step planner state and text shape to reach this nested branch
- `R59` `1094-1097`: requires a more specific compound contract/text state than the current deterministic case set
- `R60` `1096-1097`: requires a more specific compound contract/text state than the current deterministic case set
- `R61` `1099-1105`: requires a more specific compound contract/text state than the current deterministic case set
- `R62` `1106-1123`: requires a more specific compound contract/text state than the current deterministic case set
- `R63` `1125-1131`: requires a more specific compound contract/text state than the current deterministic case set
- `R64` `1133-1152`: needs last-offer memory state plus exact repeated-offer wording
- `R65` `1134-1135`: needs safety-priority planner profile with exact long/question shape
- `R66` `1136-1141`: requires a more specific compound contract/text state than the current deterministic case set
- `R67` `1142-1147`: requires a more specific compound contract/text state than the current deterministic case set
- `R68` `1154-1169`: needs mechanical revoicing output plus active-line settings
- `R69` `1155-1160`: requires a more specific compound contract/text state than the current deterministic case set
- `R70` `1161-1166`: requires a more specific compound contract/text state than the current deterministic case set
- `R71` `1168-1169`: requires a more specific compound contract/text state than the current deterministic case set
- `R73` `1172-1177`: needs dedicated self-realization concept fixture
- `R74` `1178-1183`: needs exact concept-oriented user message and matching planner obligation
