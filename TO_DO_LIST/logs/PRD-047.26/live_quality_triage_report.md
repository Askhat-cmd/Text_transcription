# PRD-047.26 Live Quality Triage Report

- status: `passed_with_warning`
- executed_case_count: `12`
- passed_case_count: `4`
- warning_case_count: `8`
- blocked_case_count: `0`
- direct_answer_success_rate: `0.8333`
- overlay_false_positive_count: `8`
- overlay_missing_where_expected_count: `0`
- dialogue_act_error_count: `3`
- answer_obligation_error_count: `3`
- response_mode_error_count: `0`
- retrieval_query_error_count: `0`
- kb_payload_error_count: `0`
- writer_style_regression_count: `2`
- evaluator_false_pass_count: `2`
- trace_missing_evidence_count: `0`
- db_track_readiness: `not_ready`
- recommended_next_prd: `PRD-047.26-HF1 - Dialogue Act / Answer Obligation Repair v1`

## Case Distribution
- `Q26-001`: status=`warning` failure_classes=`overlay_shadow_noise`
- `Q26-002`: status=`warning` failure_classes=`dialogue_act_error, answer_obligation_error, overlay_shadow_noise`
- `Q26-003`: status=`warning` failure_classes=`overlay_shadow_noise`
- `Q26-004`: status=`warning` failure_classes=`dialogue_act_error, answer_obligation_error, overlay_shadow_noise`
- `Q26-005`: status=`ok` failure_classes=`no_issue_detected`
- `Q26-006`: status=`ok` failure_classes=`no_issue_detected`
- `Q26-007`: status=`warning` failure_classes=`dialogue_act_error, answer_obligation_error, overlay_shadow_noise, writer_style_regression, evaluator_false_pass`
- `Q26-008`: status=`ok` failure_classes=`no_issue_detected`
- `Q26-009`: status=`ok` failure_classes=`no_issue_detected`
- `Q26-010`: status=`warning` failure_classes=`overlay_shadow_noise`
- `Q26-011`: status=`warning` failure_classes=`overlay_shadow_noise, writer_style_regression, evaluator_false_pass`
- `Q26-012`: status=`warning` failure_classes=`overlay_shadow_noise`
