# PRD-047.15-HF2-R2 Validation Commands

## Backend

```text
cd bot_psychologist
python -m pytest tests/test_hybrid_retrieval_admin_runtime_contract.py tests/test_multiagent_trace.py tests/test_debug_metrics_and_export.py tests/api/test_multiagent_trace_contract.py
python -m pytest tests/test_debug_metrics_and_export.py
```

## Frontend

```text
cd bot_psychologist/web_ui
npm run test -- --run src/components/chat/MultiAgentTraceWidget.test.ts src/components/admin/AdminPanel.test.ts
npm run build
```

## Acceptance Runner

```text
cd C:\My_practice\Text_transcription
python bot_psychologist/scripts/run_prd_047_15_hf2_r2_hybrid_retrieval_visibility.py --mode all
```

## Status

- backend pytest: passed
- frontend vitest: passed
- frontend build: passed
- runner direct/live/browser: passed
