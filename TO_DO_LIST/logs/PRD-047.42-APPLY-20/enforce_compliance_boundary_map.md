# _enforce_answer_compliance Boundary Map

- PRD: `PRD-047.42-APPLY-20`
- target: `WriterAgent._enforce_answer_compliance(self, response_text: str, contract: WriterContract) -> str`
- method lines: `582-1191` (`610` LOC)
- rule_count: `75`

## Section A. Prelude locals / detector intake

| local | lines | source | read by rules |
| --- | --- | --- | --- |
| text | 583-583 | str-normalized value | R01, R05, R09, R11, R13, R15, R20, R24, R25, R32, R54, R56, R68 |
| ctx | 587-587 | contract.to_prompt_context() | none |
| user_message | 588-588 | ctx.get(...) | none |
| lowered_user | 589-589 | user_message.lower() | R02, R06, R19, R35, R43, R44, R73, R74, R75 |
| literal_markdown_echo | 590-590 | _extract_literal_markdown_echo_request(user_message) | R07 |
| dialogue_profile | 591-591 | ctx.get(...) | R17 |
| expansion_requested | 592-592 | ctx.get(...) | none |
| repair_and_expand_requested | 593-595 | ctx.get(...) | none |
| knowledge_answer | 596-596 | ctx.get(...) | none |
| practice_gate | 597-597 | ctx.get(...) | none |
| practice_allowed | 598-598 | bool-derived flag | R18 |
| should_answer_directly | 599-599 | bool-derived flag | R18, R34 |
| is_greeting | 600-600 | bool-derived flag | R18 |
| concept | 601-601 | str-normalized value | R36, R37 |
| active_line | 602-602 | ctx.get(...) | none |
| active_line_intent | 603-603 | str-normalized value | R21, R58, R66, R67, R69, R70 |
| active_line_repair_mode | 604-604 | str-normalized value | R66, R69 |
| active_line_revoicing_allowed | 605-605 | bool-derived flag | R68 |
| active_line_should_offer_practice | 606-606 | bool-derived flag | R64 |
| active_line_practice_suppression | 607-607 | bool-derived flag | R64 |
| response_planner | 608-608 | ctx.get(...) | none |
| planner_next_move | 609-609 | str-normalized value | R23, R24, R25, R26, R27, R28, R29, R39, R40, R41, R42, R46, R47, R48, R49, R51, R52, R53, R56, R57, R65, R72 |
| planner_answer_shape | 610-610 | str-normalized value | R23, R39, R40, R41, R46, R51, R52, R57, R58, R65 |
| planner_question_policy | 611-611 | str-normalized value | R38, R45, R50, R56, R62 |
| planner_practice_policy | 612-612 | str-normalized value | R55, R72 |
| planner_safety_priority | 613-613 | bool-derived flag | R22 |
| dialogue_policy_payload | 614-614 | ctx.get(...) | none |
| dialogue_pragmatics_payload | 615-619 | ctx.get(...) | none |
| explicit_answer_need | 620-622 | detector/helper call | none |
| direct_concrete_request | 623-625 | detector/helper call | none |
| summary_request | 626-628 | detector/helper call | none |
| sarcasm_or_negative_feedback | 629-631 | detector/helper call | none |
| application_request | 632-634 | detector/helper call | none |
| human_like_answer_policy | 635-639 | dict-normalization | none |
| constraint_resolution | 640-644 | dict-normalization | none |
| practice_overview_requested | 645-649 | bool-derived flag | none |
| pragmatics_contextual_followup | 650-652 | bool-derived flag | none |
| pragmatics_offer_type | 653-655 | str-normalized value | none |
| pragmatics_should_not_reconfirm | 656-658 | bool-derived flag | none |
| pragmatics_repair_dissatisfaction | 659-661 | bool-derived flag | none |
| lowered_text | 662-662 | text.lower() | R03, R09, R11, R13, R15, R21, R26, R27, R28, R45, R62 |
| final_answer_directive | 686-690 | ctx.get(...) | none |
| writer_contact_mode | 691-695 | ctx.get(...) | none |
| gate_feedback | 697-701 | dict-normalization | none |
| gate_failed_checks | 702-706 | {str(item) for item in list(gate_feedback.get('failed_che... | R02 |
| answer_obligation | 724-728 | ctx.get(...) | R03, R04, R09, R11, R13, R15 |
| last_direct_question | 729-729 | ctx.get(...) | none |
| last_offer_summary | 730-730 | ctx.get(...) | R13 |
| offer_repair_context | 731-731 | f'{last_offer_summary} {last_direct_question}'.lower() | R13, R14 |
| concept_question | 732-732 | 'нейросталкинг' in lowered_user | R10, R16 |
| has_unsolicited_practice | 734-734 | any(...) detector | R03, R18, R20, R21, R24, R27, R55, R56, R64 |
| has_question | 735-735 | '?' in text | R03, R22, R24, R25, R27, R38, R54, R56 |
| asks_define_known_term | 736-736 | any(...) detector | R34 |
| has_external_surveillance_frame | 737-737 | any(...) detector | R34 |
| user_requests_no_question | 738-740 | _contains_any(...) | R56 |
| user_requests_no_practice | 741-751 | _contains_any(...) | R56 |
| user_repair_signal | 752-754 | _contains_any(...) | R33 |
| user_step_request | 755-757 | _contains_any(...) | R58 |
| canned_step_disallowed | 761-765 | bool-derived flag | none |
| user_mechanism_request | 774-776 | _contains_any(...) | R56 |
| answer_fit | 777-783 | evaluate_concrete_answer_fit(...) | none |

## Section B. Numbered rule cascade

| rule | lines | condition | action on text / branch result | early return | locals read |
| --- | --- | --- | --- | --- | --- |
| R01 | 584-585 | not text | return text | yes | text |
| R02 | 707-711 | 'greeting_answered_with_mechanism_explanation' in gate_failed_checks and _contains_any(lowered_user, ('здравств', 'привет', 'добрый день', 'добрый вечер')) | return self._repair_greeting_without_mechanism_lecture(user_message=user_message) | yes | gate_failed_checks, lowered_user |
| R03 | 767-773 | answer_obligation == 'close_gently' and (has_question or has_unsolicited_practice or _contains_any(lowered_text, ('если хочешь', 'если захочешь', 'давай продолжим', 'следующий шаг'))) | return self._build_gentle_close_reply() | yes | answer_obligation, has_question, has_unsolicited_practice, lowered_text |
| R04 | 786-816 | answer_obligation == 'provide_one_bounded_practice' | return self._strip_optional_followup_invitation(text) or text | yes | answer_obligation |
| R05 | 796-814 | '?' in text or len(text.strip()) > 900 or practice_multistep or (not practice_step_present) or (not practice_anchor_present) | return self._defer_no_stub_repair(signal='bounded_practice_repair', text=text, must_answer=user_message) | yes | practice_multistep, text, practice_step_present, practice_anchor_present |
| R06 | 803-809 | 'будь сильным' in lowered_user | return 'Одна короткая практика: в момент, когда включается «Будь сильным», заметь, где тело напрягается, и тихо назови про себя: «сейчас я снова держусь чере... | yes | lowered_user |
| R07 | 818-824 | literal_markdown_echo | return normalized_requested | yes | literal_markdown_echo |
| R08 | 821-824 | normalized_response != normalized_requested | return normalized_requested | yes | normalized_response, normalized_requested |
| R09 | 826-834 | answer_obligation == 'acknowledge_style_preference_then_answer' and ('расскажи больше' in lowered_text or len(text) < 140) | return self._defer_no_stub_repair(signal='style_preference_direct_answer_repair', text=text, must_answer='known_concept_question') | yes | answer_obligation, lowered_text, text |
| R10 | 829-834 | concept_question | return self._defer_no_stub_repair(signal='style_preference_direct_answer_repair', text=text, must_answer='known_concept_question') | yes | concept_question |
| R11 | 836-845 | answer_obligation == 'repair_and_answer_last_question' and ('сейчас полезнее прямое объяснение механизма' in lowered_text or len(text) < 180) | return self._defer_no_stub_repair(signal='repair_answer_last_question_repair', text=text, must_answer=target) | yes | answer_obligation, lowered_text, text |
| R12 | 840-845 | 'нейросталкинг' in target.lower() | return self._defer_no_stub_repair(signal='repair_answer_last_question_repair', text=text, must_answer=target) | yes | target |
| R13 | 847-862 | answer_obligation == 'answer_last_offer' and (any((marker in lowered_text for marker in ('подтверди', 'если хочешь', 'могу так сделать'))) or any((marker in lowered_text for marker in ('предлагаю такой план', 'хотите,... | return self._defer_no_stub_repair(signal='answer_last_offer_repair', text=text, must_answer=last_offer_summary or last_direct_question or 'last_assistant_off... | yes | answer_obligation, lowered_text, text, last_offer_summary, offer_repair_context |
| R14 | 857-862 | any((color in offer_repair_context for color in ('красн', 'оранж', 'зелен'))) | return self._defer_no_stub_repair(signal='answer_last_offer_repair', text=text, must_answer=last_offer_summary or last_direct_question or 'last_assistant_off... | yes | offer_repair_context |
| R15 | 864-872 | answer_obligation in {'answer_knowledge_question', 'answer_direct_question'} and ('сейчас полезнее прямое объяснение механизма' in lowered_text or len(text) < 140) | return self._defer_no_stub_repair(signal='knowledge_direct_answer_repair', text=text, must_answer='known_concept_question') | yes | answer_obligation, lowered_text, text |
| R16 | 867-872 | concept_question | return self._defer_no_stub_repair(signal='knowledge_direct_answer_repair', text=text, must_answer='known_concept_question') | yes | concept_question |
| R17 | 874-911 | dialogue_profile == DIALOGUE_PROFILE_MVP_FREE | return self._enforce_mvp_free_dialogue_compliance(text=text, user_message=user_message, lowered_text=lowered_text, lowered_user=lowered_user, concept=concept... | yes | dialogue_profile |
| R18 | 914-918 | not practice_allowed and (not should_answer_directly) and (is_greeting or has_unsolicited_practice) | return 'Привет. Рад знакомству. Можем спокойно начать: принеси любой вопрос или тему, которую хочешь разобрать.' | yes | practice_allowed, should_answer_directly, is_greeting, has_unsolicited_practice |
| R19 | 921-923 | _contains_any(lowered_user, _LOW_RESOURCE_NO_PRACTICE_MARKERS) | return 'Я рядом. Сейчас не нужно ничего разбирать. Можно просто немного снизить внутреннее давление.' | yes | lowered_user |
| R20 | 922-923 | has_unsolicited_practice or len(text) > 280 or '?' in text | return 'Я рядом. Сейчас не нужно ничего разбирать. Можно просто немного снизить внутреннее давление.' | yes | has_unsolicited_practice, text |
| R21 | 925-929 | active_line_intent == 'thanks_close' and (has_unsolicited_practice or _contains_any(lowered_text, ('шаг', 'давай сделаем', 'предложу еще'))) | return 'Пожалуйста. Рад, что стало чуть яснее.' | yes | active_line_intent, has_unsolicited_practice, lowered_text |
| R22 | 931-932 | planner_safety_priority and has_question | return 'Я рядом. Сейчас важнее чуть стабилизироваться и снизить внутреннюю перегрузку.' | yes | planner_safety_priority, has_question |
| R23 | 934-935 | planner_next_move == 'give_short_support' or planner_answer_shape == 'short_support' | return 'Я рядом. Сейчас не нужно ничего разбирать. Можно просто немного снизить внутреннее давление.' | yes | planner_next_move, planner_answer_shape |
| R24 | 937-938 | planner_next_move == 'give_short_support' and (len(text) > 260 or has_question or has_unsolicited_practice) | return 'Я рядом. Сейчас не нужно всё разбирать. Можно просто немного снизить внутреннее давление.' | yes | planner_next_move, has_question, has_unsolicited_practice, text |
| R25 | 940-941 | planner_next_move == 'stabilize_safety' and (len(text) > 320 or has_question) | return 'Я рядом. Сейчас важнее короткая опора здесь-и-сейчас, без перегруза.' | yes | planner_next_move, has_question, text |
| R26 | 943-947 | planner_next_move == 'stabilize_safety' and _contains_any(lowered_text, ('механизм', 'прогнозирован', 'контрол', 'паттерн', 'драйвер', 'до начала действия')) | return 'Я рядом. Сейчас важнее чуть стабилизироваться и снизить внутреннюю перегрузку. Без разбора, только опора здесь-и-сейчас.' | yes | planner_next_move, lowered_text |
| R27 | 949-954 | planner_next_move == 'close_gently' and (has_question or has_unsolicited_practice or _contains_any(lowered_text, ('новый шаг', 'давай продолжим', 'в следующий раз разберем'))) | return 'Пожалуйста. Рад, что стало чуть яснее.' | yes | planner_next_move, has_question, has_unsolicited_practice, lowered_text |
| R28 | 956-960 | planner_next_move == 'give_short_support' and _contains_any(lowered_text, ('механизм', 'теория', 'стратегия', 'прогнозирован', 'контрол', 'паттерн')) | return 'Я рядом. Сейчас не нужно ничего разбирать. Можно просто немного снизить внутреннее давление.' | yes | planner_next_move, lowered_text |
| R29 | 962-970 | planner_next_move == 'clarify_one_point' | return 'Если выбрать один узел прямо сейчас, что больше всего сжимает тебя в этой ситуации?' | yes | planner_next_move |
| R30 | 964-965 | question_count == 0 | return 'Если выбрать один узел прямо сейчас, что больше всего сжимает тебя в этой ситуации?' | yes | question_count |
| R31 | 966-968 | question_count > 1 | return (first + '?').strip() | yes | question_count |
| R32 | 969-970 | len(text) > 320 | return 'Похоже, это сильно выматывает. Если взять один конкретный эпизод, где это ощущается острее всего?' | yes | text |
| R33 | 972-977 | user_repair_signal | return self._defer_no_stub_repair(signal='user_repair_signal', text=text, must_answer=user_message) | yes | user_repair_signal |
| R34 | 981-999 | should_answer_directly and (asks_define_known_term or has_external_surveillance_frame) | return self._defer_no_stub_repair(signal='known_concept_correlation_repair', text=text, must_answer=user_message) | yes | should_answer_directly, asks_define_known_term, has_external_surveillance_frame |
| R35 | 982-987 | 'самореализац' in lowered_user and ('коррелир' in lowered_user or 'связан' in lowered_user) | return self._defer_no_stub_repair(signal='known_concept_correlation_repair', text=text, must_answer=user_message) | yes | lowered_user |
| R36 | 988-993 | concept == 'нейросталкинг' | return self._defer_no_stub_repair(signal='known_concept_neurostalking_repair', text=text, must_answer=user_message) | yes | concept |
| R37 | 994-999 | concept == 'самореализация' | return self._defer_no_stub_repair(signal='known_concept_self_realization_repair', text=text, must_answer=user_message) | yes | concept |
| R38 | 1001-1026 | planner_question_policy == 'none' and has_question | return re.sub('\\s*\\?+\\s*', '. ', text).strip() | yes | has_question, planner_question_policy |
| R39 | 1002-1008 | planner_next_move == 'give_direct_step' or planner_answer_shape == 'one_step' | return self._resolve_one_step_or_no_practice_fallback(text=text, user_message=user_message, lowered_user=lowered_user, canned_step_disallowed=canned_step_dis... | yes | planner_next_move, planner_answer_shape |
| R40 | 1009-1010 | planner_next_move == 'give_short_support' or planner_answer_shape == 'short_support' | return 'Я рядом. Сейчас не нужно ничего разбирать. Можно просто немного снизить внутреннее давление.' | yes | planner_next_move, planner_answer_shape |
| R41 | 1011-1012 | planner_next_move == 'stabilize_safety' or planner_answer_shape == 'safety_grounding' | return 'Я рядом. Сейчас важнее чуть стабилизироваться и снизить внутреннюю перегрузку. Без разбора, только опора здесь-и-сейчас.' | yes | planner_next_move, planner_answer_shape |
| R42 | 1013-1025 | planner_next_move == 'answer_known_concept' | return self._defer_no_stub_repair(signal='known_concept_correlation_repair', text=text, must_answer=user_message) | yes | planner_next_move |
| R43 | 1014-1019 | 'самореализац' in lowered_user and 'нейросталкинг' in lowered_user | return self._defer_no_stub_repair(signal='known_concept_correlation_repair', text=text, must_answer=user_message) | yes | lowered_user |
| R44 | 1020-1025 | 'нейросталкинг' in lowered_user | return self._defer_no_stub_repair(signal='known_concept_neurostalking_repair', text=text, must_answer=user_message) | yes | lowered_user |
| R45 | 1027-1043 | planner_question_policy == 'none' and _contains_any(lowered_text, ('что именно', 'почему', 'как ты', 'можешь ли', 'хочешь')) | return 'Я рядом. Продолжим спокойно и без лишней нагрузки.' | yes | planner_question_policy, lowered_text |
| R46 | 1030-1036 | planner_next_move == 'give_direct_step' or planner_answer_shape == 'one_step' | return self._resolve_one_step_or_no_practice_fallback(text=text, user_message=user_message, lowered_user=lowered_user, canned_step_disallowed=canned_step_dis... | yes | planner_next_move, planner_answer_shape |
| R47 | 1037-1038 | planner_next_move == 'give_short_support' | return 'Я рядом. Сейчас не нужно ничего разбирать. Можно просто немного снизить внутреннее давление.' | yes | planner_next_move |
| R48 | 1039-1040 | planner_next_move == 'stabilize_safety' | return 'Я рядом. Сейчас важнее чуть стабилизироваться и снизить внутреннюю перегрузку. Без разбора, только опора здесь-и-сейчас.' | yes | planner_next_move |
| R49 | 1041-1042 | planner_next_move == 'close_gently' | return 'Пожалуйста. Рад, что стало чуть яснее.' | yes | planner_next_move |
| R50 | 1044-1057 | planner_question_policy == 'none' | return self._resolve_one_step_or_no_practice_fallback(text=text, user_message=user_message, lowered_user=lowered_user, canned_step_disallowed=canned_step_dis... | yes | planner_question_policy |
| R51 | 1045-1051 | planner_next_move == 'give_direct_step' or planner_answer_shape == 'one_step' | return self._resolve_one_step_or_no_practice_fallback(text=text, user_message=user_message, lowered_user=lowered_user, canned_step_disallowed=canned_step_dis... | yes | planner_next_move, planner_answer_shape |
| R52 | 1052-1057 | planner_next_move == 'deepen_mechanism' or planner_answer_shape == 'mechanism_explanation' | return self._defer_no_stub_repair(signal='mechanism_explanation_repair', text=text, must_answer=user_message) | yes | planner_next_move, planner_answer_shape |
| R53 | 1059-1066 | planner_next_move == 'repair_misalignment' | return self._defer_no_stub_repair(signal='repair_misalignment', text=text, must_answer=user_message) | yes | planner_next_move |
| R54 | 1061-1066 | has_question or has_repair_forbidden or len(text) > 480 | return self._defer_no_stub_repair(signal='repair_misalignment', text=text, must_answer=user_message) | yes | has_question, has_repair_forbidden, text |
| R55 | 1068-1071 | planner_practice_policy == 'forbidden' and has_unsolicited_practice | return self._strip_optional_followup_invitation(text) or text | yes | has_unsolicited_practice, planner_practice_policy |
| R56 | 1073-1082 | (planner_next_move == 'deepen_mechanism' or user_mechanism_request) and (planner_question_policy == 'none' or user_requests_no_question) and (len(text) > 700 or has_question or has_unsolicited_practice or user_request... | return self._defer_no_stub_repair(signal='mechanism_explanation_repair', text=text, must_answer=user_message) | yes | user_mechanism_request, user_requests_no_question, has_question, has_unsolicited_practice, user_requests_no_practice, planner_next_move, planner_question_policy, text |
| R57 | 1084-1090 | planner_answer_shape == 'one_step' or planner_next_move == 'give_direct_step' | return self._resolve_one_step_or_no_practice_fallback(text=text, user_message=user_message, lowered_user=lowered_user, canned_step_disallowed=canned_step_dis... | yes | planner_answer_shape, planner_next_move |
| R58 | 1092-1131 | planner_answer_shape == 'one_step' or user_step_request or active_line_intent == 'ask_for_direct_step' | return self._resolve_one_step_or_no_practice_fallback(text=text, user_message=user_message, lowered_user=lowered_user, canned_step_disallowed=canned_step_dis... | yes | user_step_request, planner_answer_shape, active_line_intent |
| R59 | 1094-1097 | list_like | return first_item.group(1).strip() | yes | list_like |
| R60 | 1096-1097 | first_item | return first_item.group(1).strip() | yes | first_item |
| R61 | 1099-1105 | len(sentence_parts) > 2 | return self._resolve_one_step_or_no_practice_fallback(text=text, user_message=user_message, lowered_user=lowered_user, canned_step_disallowed=canned_step_dis... | yes | sentence_parts |
| R62 | 1106-1123 | planner_question_policy == 'none' and _contains_any(lowered_text, ('хочешь', 'хочется', 'можешь', 'уточни', 'попробу', 'какой', 'что выбрать')) | return self._resolve_one_step_or_no_practice_fallback(text=text, user_message=user_message, lowered_user=lowered_user, canned_step_disallowed=canned_step_dis... | yes | planner_question_policy, lowered_text |
| R63 | 1125-1131 | not has_step_marker | return self._resolve_one_step_or_no_practice_fallback(text=text, user_message=user_message, lowered_user=lowered_user, canned_step_disallowed=canned_step_dis... | yes | has_step_marker |
| R64 | 1133-1152 | active_line_practice_suppression and (not active_line_should_offer_practice) and has_unsolicited_practice | return self._defer_no_stub_repair(signal='practice_suppression_meaning_repair', text=text, must_answer=user_message) | yes | active_line_practice_suppression, has_unsolicited_practice, active_line_should_offer_practice |
| R65 | 1134-1135 | planner_next_move == 'stabilize_safety' or planner_answer_shape == 'safety_grounding' | return 'Я рядом. Сейчас важнее чуть стабилизироваться и снизить внутреннюю перегрузку. Без разбора, только опора здесь-и-сейчас.' | yes | planner_next_move, planner_answer_shape |
| R66 | 1136-1141 | active_line_intent == 'correction_of_bot' or active_line_repair_mode | return self._defer_no_stub_repair(signal='active_line_correction_repair', text=text, must_answer=user_message) | yes | active_line_repair_mode, active_line_intent |
| R67 | 1142-1147 | active_line_intent == 'understand_mechanism' | return self._defer_no_stub_repair(signal='active_line_mechanism_repair', text=text, must_answer=user_message) | yes | active_line_intent |
| R68 | 1154-1169 | not active_line_revoicing_allowed and starts_with_mechanical_revoicing(text) | return self._defer_no_stub_repair(signal='active_line_revoicing_correction_repair', text=text, must_answer=user_message) | yes | active_line_revoicing_allowed, text |
| R69 | 1155-1160 | active_line_intent == 'correction_of_bot' or active_line_repair_mode | return self._defer_no_stub_repair(signal='active_line_revoicing_correction_repair', text=text, must_answer=user_message) | yes | active_line_repair_mode, active_line_intent |
| R70 | 1161-1166 | active_line_intent == 'understand_mechanism' | return self._defer_no_stub_repair(signal='active_line_revoicing_mechanism_repair', text=text, must_answer=user_message) | yes | active_line_intent |
| R71 | 1168-1169 | len(parts) == 2 and parts[1].strip() | return parts[1].strip() | yes | parts |
| R72 | 1171-1189 | planner_next_move == 'answer_known_concept' and planner_practice_policy == 'forbidden' | return self._defer_no_stub_repair(signal='known_concept_correlation_repair', text=text, must_answer=user_message) | yes | planner_next_move, planner_practice_policy |
| R73 | 1172-1177 | 'самореализац' in lowered_user and 'нейросталкинг' in lowered_user | return self._defer_no_stub_repair(signal='known_concept_correlation_repair', text=text, must_answer=user_message) | yes | lowered_user |
| R74 | 1178-1183 | 'нейросталкинг' in lowered_user | return self._defer_no_stub_repair(signal='known_concept_neurostalking_repair', text=text, must_answer=user_message) | yes | lowered_user |
| R75 | 1184-1189 | 'самореализац' in lowered_user | return self._defer_no_stub_repair(signal='known_concept_self_realization_repair', text=text, must_answer=user_message) | yes | lowered_user |

## Section C. Proposed continuous cluster families

| cluster family | lines | rule range | why this is a coherent future slice |
| --- | --- | --- | --- |
| intake_and_obligation_prelude | 583-785 | R01-R03 | All ctx extraction, detector booleans, answer-fit evaluation, and early greeting gate live here. This must stay ahead of every repair family because later rules read these normalized locals. |
| obligation_specific_repairs_before_profile_split | 786-872 | R04-R16 | Continuous sequence of obligation-bound repairs (`bounded_practice`, literal markdown, answer_last_offer, direct knowledge answers) that all run before dialogue-profile dispatch. |
| mvp_free_branch_handoff | 874-911 | R17 | Single early-return handoff into `_enforce_mvp_free_dialogue_compliance`. Keep isolated until the parent method is smaller; it is a branch boundary, not a simple helper. |
| non_mvp_contact_support_and_clarify_rules | 913-970 | R18-R32 | Compact contact/safety/clarification rules with many literal returns. These are mostly order-sensitive but continuous and can become a later `text -> text` family. |
| known_concept_and_question_policy_cascade | 972-1067 | R33-R54 | Repairs for known concepts, question-policy stripping, and misalignment recovery. This is the first large semantic cluster after the MVP split. |
| practice_step_and_active_line_tail | 1068-1190 | R55-R75 | Late tail: template leakage, direct-step fallback, active-line suppression, mechanical revoicing, and known-concept tail repairs. Good candidate for several continuous sub-slices later. |

## Section D. External dependencies

| dependency | module source | kind | used by rules |
| --- | --- | --- | --- |
| normalize_dialogue_profile | dialogue_policy | function | none |
| detect_expansion_request | dialogue_policy | function | none |
| detect_repair_and_expand_request | dialogue_policy | function | none |
| detect_explicit_answer_need | dialogue_policy | function | none |
| detect_direct_concrete_request | dialogue_policy | function | none |
| detect_summary_request | dialogue_policy | function | none |
| detect_sarcasm_or_negative_feedback | dialogue_policy | function | none |
| detect_application_request | dialogue_policy | function | none |
| evaluate_concrete_answer_fit | concrete_answer_fit | function | none |
| _contains_any | writer_agent_constants | function | R02, R03, R04, R19, R21, R26, R27, R28, R45, R53, R58, R62 |
| _extract_literal_markdown_echo_request | writer_agent_constants | function | none |
| starts_with_mechanical_revoicing | active_line | function | R68 |
| DIALOGUE_PROFILE_MVP_FREE | dialogue_policy | constant | R17 |
| _PRACTICE_MARKERS | writer_agent | constant | none |
| _KNOWN_CONCEPT_CLARIFICATION_MARKERS | writer_agent | constant | none |
| _EXTERNAL_SURVEILLANCE_MARKERS | writer_agent | constant | none |
| _LOW_RESOURCE_NO_PRACTICE_MARKERS | writer_agent | constant | R19 |
| re | stdlib | module | R04, R38, R58, R59, R68 |
