# Real Live Acceptance Protocol (Протокол real live acceptance)

- status: current
- last_verified_prd: PRD-047.13-HF1
- source_of_truth: docs/PROJECT_STATE.md; docs/PRD_INDEX.md; /api/admin/runtime/effective
- active_now: true
- not_production_ready: true
- related_artifacts: TO_DO_LIST/logs/PRD-047.13-HF1; TO_DO_LIST/reports/PRD-047.13-HF1_IMPLEMENTATION_REPORT.md

## Active Now (Активно сейчас)
- Live acceptance должен вызывать работающий backend и экспортировать real turn traces.
- Mocked/dry cases не принимаются как live proof.
- Failed live/browser/architecture gates не должны отмечаться как passed.

## Not Production Ready (Не готово к production)
- Успешные локальные live cycles не означают production readiness.

## How To Test (Как тестировать)
- Запустите сервисы по `запуск проека.txt`.
- Запустите `python scripts/run_prd_047_12_hf1_acceptance.py --live --browser`.

## PRD-047.13-HF1 cleanup closure note (Заметка о закрытии cleanup PRD-047.13-HF1)
- Документ повторно проверен при закрытии cleanup; runtime behavior не менялся.
