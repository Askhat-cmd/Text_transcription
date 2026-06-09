# PRD-047.15-HF1 Composer Calibration Cases

- cases_total: `40`

| Case | Group | User message | Expected category | Expected actions |
| --- | --- | --- | --- | --- |
| SF01 | short_contextual_followup | Да | inherit_concept_query | query_kb |
| SF02 | short_contextual_followup | Да, хорошо | query_practice_context | query_kb |
| SF03 | short_contextual_followup | Давай | suppress_short_support | suppress_rag |
| SF04 | short_contextual_followup | Покажи | warning_needs_hybrid_or_more_context | query_kb |
| SF05 | short_contextual_followup | Продолжай | warning_needs_hybrid_or_more_context | query_kb |
| SF06 | short_contextual_followup | Можно | use_current_context_only | use_current_context_only, trace_only |
| SF07 | short_contextual_followup | Ок | inherit_concept_query | query_kb |
| SF08 | short_contextual_followup | Хорошо, дальше | warning_needs_hybrid_or_more_context | query_kb |
| SF09 | short_contextual_followup | Да | suppress_short_support | suppress_rag |
| SF10 | short_contextual_followup | Да, хорошо | use_current_context_only | use_current_context_only |
| SM01 | summary_request | Подведи краткий итог нашей беседы. | use_current_context_only | use_current_context_only |
| SM02 | summary_request | Сделай резюме. | use_current_context_only | use_current_context_only |
| SM03 | summary_request | К чему мы пришли? | use_current_context_only | use_current_context_only |
| SM04 | summary_request | Что мы поняли? | use_current_context_only | use_current_context_only |
| SM05 | summary_request | Дай summary. | use_current_context_only | use_current_context_only |
| SM06 | summary_request | Собери всё вместе. | use_current_context_only | use_current_context_only |
| KQ01 | knowledge_question | Что такое нейросталкинг? | query_kb | query_kb |
| KQ02 | knowledge_question | Объясни Кузницу Духа простыми словами. | query_kb | query_kb |
| KQ03 | knowledge_question | Что значит автоматизм? | query_kb | query_kb |
| KQ04 | knowledge_question | Как работает защитный механизм? | query_kb | query_kb |
| KQ05 | knowledge_question | Чем отличается наблюдение от контроля? | query_kb | query_kb |
| KQ06 | knowledge_question | Расскажи про самореализацию. | query_kb | query_kb |
| KQ07 | knowledge_question | Как работает нейросталкинг в живом диалоге? | query_kb | query_kb |
| KQ08 | knowledge_question | Что значит внутренняя наблюдательность? | query_kb | query_kb |
| MX01 | mixed_context | Подведи итог и свяжи это с нейросталкингом. | mixed_query_or_hybrid_needed | query_kb, query_kb_and_memory |
| MX02 | mixed_context | Покажи это через Кузницу. | mixed_query_or_hybrid_needed | query_kb |
| MX03 | mixed_context | Да, но на моём примере. | query_kb_and_memory_or_hybrid | query_kb_and_memory |
| MX04 | mixed_context | А как это связано с автоматизмом? | query_kb | query_kb |
| MX05 | mixed_context | Теперь дай практику по этому. | query_practice_context | query_kb |
| MX06 | mixed_context | Суммируй и дай практику по нейросталкингу. | query_kb_and_memory_or_hybrid | query_kb_and_memory, query_kb |
| MX07 | mixed_context | Объясни коротко, но с примером из нашей беседы. | query_kb_and_memory_or_hybrid | query_kb_and_memory, query_kb |
| MX08 | mixed_context | Что из этого относится к защитному механизму? | query_kb | query_kb |
| NS01 | noise_suppression | Привет. | suppress_rag | suppress_rag |
| NS02 | noise_suppression | Спасибо. | suppress_rag | suppress_rag |
| NS03 | noise_suppression | Пока. | suppress_rag | suppress_rag |
| NS04 | noise_suppression | Просто поддержи. | suppress_rag | suppress_rag |
| NS05 | noise_suppression | Что сделать прямо сейчас? | suppress_rag | suppress_rag |
| NS06 | noise_suppression | Один шаг. | suppress_rag | suppress_rag |
| NS07 | noise_suppression | Не надо теории. | trace_only | trace_only, suppress_rag |
| NS08 | noise_suppression | Скажи коротко. | trace_only | trace_only, suppress_rag |
