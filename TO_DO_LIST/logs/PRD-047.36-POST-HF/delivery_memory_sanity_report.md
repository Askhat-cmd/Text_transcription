# PRD-047.36-POST-HF Delivery / Memory Sanity Report

- verdict: `PASS_WITH_WARNING`
- reasons: `visible_chat_text_not_sampled_for_api_only_rows`

## G3
- writer_raw_vs_api_match: `True`
- api_vs_memory_match: `True`
- visible_chat_accessible: `False`
- visible_chat_vs_api_match: `None`
- acceptance_gate_status: `passed`
- must_quarantine_answer: `False`
- quarantine_explains_memory_gap: `False`
- blocker_reasons: `none`

## G5
- writer_raw_vs_api_match: `True`
- api_vs_memory_match: `True`
- visible_chat_accessible: `False`
- visible_chat_vs_api_match: `None`
- acceptance_gate_status: `passed`
- must_quarantine_answer: `False`
- quarantine_explains_memory_gap: `False`
- blocker_reasons: `none`

## G8
- writer_raw_vs_api_match: `True`
- api_vs_memory_match: `False`
- visible_chat_accessible: `False`
- visible_chat_vs_api_match: `None`
- acceptance_gate_status: `failed`
- must_quarantine_answer: `True`
- quarantine_explains_memory_gap: `False`
- blocker_reasons: `none`
