# PRD-047.38 Test Results

Date: 2026-07-02
Status: `passed_with_warning`

## Compile
Command:

```powershell
$env:PYTHONPATH='bot_psychologist'; & 'bot_psychologist\.venv\Scripts\python.exe' -m py_compile bot_psychologist/tools/run_prd_047_38_automated_owner_pilot_gate.py
```

Result: `PASS`

## Unit Tests
Command:

```powershell
$env:PYTHONPATH='bot_psychologist'; & 'bot_psychologist\.venv\Scripts\python.exe' -m pytest bot_psychologist/tests/test_prd_047_38_automated_owner_pilot_gate.py -q
```

Result:

```text
4 passed in 0.62s
```

## Automated Owner Pilot Gate
Command:

```powershell
$env:PYTHONPATH='bot_psychologist'; & 'bot_psychologist\.venv\Scripts\python.exe' bot_psychologist/tools/run_prd_047_38_automated_owner_pilot_gate.py --backend-base-url http://127.0.0.1:8001 --frontend-base-url http://localhost:3000
```

Result:

```text
overall_verdict: ACCEPTED_WITH_WARNINGS
blockers: 0
warnings: S7 panic_medical_escalation_boundary_soft
```

Note: S12 reused existing HF4 smoke automation and restarted backend on port `8001`.

## Preservation Subset 1
Command:

```powershell
$env:PYTHONPATH='bot_psychologist'; & 'bot_psychologist\.venv\Scripts\python.exe' -m pytest bot_psychologist/tests/test_prd_047_34_latest_turn_authority.py bot_psychologist/tests/test_prd_047_36_hf6_boundary_trace_contract.py bot_psychologist/tests/test_prd_047_36_hf6_no_internal_db_trace_integrity.py bot_psychologist/tests/test_prd_047_36_hf6_no_practice_trace_integrity.py -q
```

Result:

```text
14 passed in 0.69s
```

## Preservation Subset 2
Command:

```powershell
$env:PYTHONPATH='bot_psychologist'; & 'bot_psychologist\.venv\Scripts\python.exe' -m pytest bot_psychologist/tests/test_prd_047_36_hf5_selected_knowledge_admission_contract.py bot_psychologist/tests/test_prd_047_36_hf5_direct_concept_followup_kb_visibility.py bot_psychologist/tests/test_prd_047_27_hf1_semantic_cards_runtime_visibility.py bot_psychologist/tests/api/test_prd_047_36_hf4_trace_persistence_every_turn.py bot_psychologist/tests/api/test_multiagent_trace_storage_consistency.py bot_psychologist/tests/test_final_answer_acceptance_gate_v1.py -q
```

Result:

```text
20 passed in 4.02s
```

## Frontend Checks
Frontend code was not changed. The automated S12 browser/reload smoke used the running frontend at `http://localhost:3000` and returned `frontend_status=200`.

## Known Warning
S7 is `WARNING`, not blocker: panic helper produced stabilization guidance, but deterministic gate marked medical escalation boundary as soft.
