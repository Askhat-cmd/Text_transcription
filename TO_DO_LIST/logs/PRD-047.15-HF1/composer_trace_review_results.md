# PRD-047.15-HF1 Composer Trace Review Results

- cases_total: `40`
- automated_expected_match_count: `33`
- automated_expected_match_rate: `0.825`
- false_positive_rag_count: `1`
- false_negative_rag_count: `6`
- weak_query_count: `0`
- summary_external_kb_leak_count: `0`
- literal_short_reply_query_count: `0`
- no_stub_violations_count: `0`
- llm_candidate_cases_count: `8`
- noisy_chunk_risk_count: `1`
- needs_more_context_fields_count: `9`

| Case | Group | Action | Query source | Expected | Computed | Flags |
| --- | --- | --- | --- | --- | --- | --- |
| SF01 | short_contextual_followup | query_kb | last_assistant_offer | inherit_concept_query | inherit_concept_query | good_fit |
| SF02 | short_contextual_followup | query_kb | last_assistant_offer | query_practice_context | inherit_concept_query | good_fit |
| SF03 | short_contextual_followup | suppress_rag | last_assistant_offer | suppress_short_support | suppress_rag | good_fit |
| SF04 | short_contextual_followup | suppress_rag | current_user_message | warning_needs_hybrid_or_more_context | suppress_rag | false_negative_rag, needs_hybrid_llm, needs_more_context_fields |
| SF05 | short_contextual_followup | trace_only | mixed_context | warning_needs_hybrid_or_more_context | trace_only | false_negative_rag, needs_hybrid_llm, needs_more_context_fields |
| SF06 | short_contextual_followup | trace_only | mixed_context | use_current_context_only | trace_only | good_fit, needs_more_context_fields |
| SF07 | short_contextual_followup | query_kb | last_assistant_offer | inherit_concept_query | inherit_concept_query | good_fit |
| SF08 | short_contextual_followup | trace_only | mixed_context | warning_needs_hybrid_or_more_context | trace_only | false_negative_rag, needs_hybrid_llm, needs_more_context_fields |
| SF09 | short_contextual_followup | suppress_rag | last_assistant_offer | suppress_short_support | suppress_rag | good_fit |
| SF10 | short_contextual_followup | query_kb | last_assistant_offer | use_current_context_only | inherit_concept_query | false_positive_rag |
| SM01 | summary_request | use_current_context_only | summary_request | use_current_context_only | use_current_context_only | good_fit |
| SM02 | summary_request | use_current_context_only | summary_request | use_current_context_only | use_current_context_only | good_fit |
| SM03 | summary_request | use_current_context_only | summary_request | use_current_context_only | use_current_context_only | good_fit |
| SM04 | summary_request | use_current_context_only | summary_request | use_current_context_only | use_current_context_only | good_fit |
| SM05 | summary_request | use_current_context_only | summary_request | use_current_context_only | use_current_context_only | good_fit |
| SM06 | summary_request | use_current_context_only | summary_request | use_current_context_only | use_current_context_only | good_fit |
| KQ01 | knowledge_question | query_kb | current_user_message | query_kb | query_kb | good_fit |
| KQ02 | knowledge_question | query_kb | current_user_message | query_kb | query_kb | good_fit |
| KQ03 | knowledge_question | query_kb | current_user_message | query_kb | query_kb | good_fit |
| KQ04 | knowledge_question | query_kb | current_user_message | query_kb | query_kb | good_fit |
| KQ05 | knowledge_question | query_kb | current_user_message | query_kb | query_kb | good_fit |
| KQ06 | knowledge_question | query_kb | current_user_message | query_kb | query_kb | good_fit |
| KQ07 | knowledge_question | query_kb | current_user_message | query_kb | query_kb | good_fit |
| KQ08 | knowledge_question | query_kb | current_user_message | query_kb | query_kb | good_fit |
| MX01 | mixed_context | query_kb | mixed_context | mixed_query_or_hybrid_needed | query_kb | good_fit, noisy_chunk_risk, needs_hybrid_llm |
| MX02 | mixed_context | suppress_rag | current_user_message | mixed_query_or_hybrid_needed | suppress_rag | false_negative_rag, needs_hybrid_llm, needs_more_context_fields |
| MX03 | mixed_context | trace_only | mixed_context | query_kb_and_memory_or_hybrid | trace_only | false_negative_rag, needs_hybrid_llm, needs_more_context_fields |
| MX04 | mixed_context | query_kb | current_user_message | query_kb | query_kb | good_fit |
| MX05 | mixed_context | query_kb | current_user_message | query_practice_context | query_practice_context | good_fit |
| MX06 | mixed_context | use_current_context_only | summary_request | query_kb_and_memory_or_hybrid | use_current_context_only | false_negative_rag, needs_hybrid_llm, needs_more_context_fields |
| MX07 | mixed_context | query_kb | current_user_message | query_kb_and_memory_or_hybrid | query_kb | good_fit, needs_hybrid_llm |
| MX08 | mixed_context | query_kb | current_user_message | query_kb | query_kb | good_fit |
| NS01 | noise_suppression | suppress_rag | current_user_message | suppress_rag | suppress_rag | good_fit |
| NS02 | noise_suppression | suppress_rag | current_user_message | suppress_rag | suppress_rag | good_fit |
| NS03 | noise_suppression | suppress_rag | current_user_message | suppress_rag | suppress_rag | good_fit |
| NS04 | noise_suppression | suppress_rag | answer_obligation | suppress_rag | suppress_rag | good_fit |
| NS05 | noise_suppression | suppress_rag | answer_obligation | suppress_rag | suppress_rag | good_fit |
| NS06 | noise_suppression | suppress_rag | answer_obligation | suppress_rag | suppress_rag | good_fit |
| NS07 | noise_suppression | trace_only | current_user_message | trace_only | trace_only | good_fit, needs_more_context_fields |
| NS08 | noise_suppression | trace_only | current_user_message | trace_only | trace_only | good_fit, needs_more_context_fields |
