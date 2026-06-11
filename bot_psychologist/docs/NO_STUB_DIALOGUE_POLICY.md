# No Stub Dialogue Policy (Политика диалога без stub)

- status: current
- last_verified_prd: PRD-047.13-HF1
- source_of_truth: docs/PROJECT_STATE.md; docs/PRD_INDEX.md; /api/admin/runtime/effective
- active_now: true
- not_production_ready: true
- related_artifacts: TO_DO_LIST/logs/PRD-047.13-HF1; TO_DO_LIST/reports/PRD-047.13-HF1_IMPLEMENTATION_REPORT.md

## Active Now (Активно сейчас)
- Известные stale phrases обнаруживаются `stale_stub_detector`.
- Final answers со stale mechanism stubs не проходят `final_answer_acceptance_gate_v1`.
- Failed answers не закрывают unanswered questions и не становятся healthy context.

## Not Production Ready (Не готово к production)
- Эта policy — runtime acceptance gate, а не полное решение качества диалога.

## How To Test (Как тестировать)
- Запустите stale detector tests.
- Запустите gate tests с PRD-HF1 stale phrases.

## PRD-047.13-HF1 cleanup closure note (Заметка о закрытии cleanup PRD-047.13-HF1)
- Документ повторно проверен при закрытии cleanup; runtime behavior не менялся.
