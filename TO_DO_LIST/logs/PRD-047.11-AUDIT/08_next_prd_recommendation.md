# Next PRD Recommendation

- recommended_prd: `PRD-047.11-HF1`
- rationale: Приоритетный failure-кластер находится в truthfulness runtime/evaluator слое (`bad_phrase=15`, `cases_failed=14`), поэтому следующий PRD должен чинить acceptance gate truthfulness, stale phrase suppression и advisory prompt pressure. Web Chat readability остаётся отдельным warning, но не является главным подтверждённым failure.
