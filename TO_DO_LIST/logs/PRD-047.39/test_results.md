# PRD-047.39 Test Results

Date: 2026-07-02
Status: `passed_with_warning`

## Compile
Command:

```powershell
& 'bot_psychologist\.venv\Scripts\python.exe' -m py_compile tools/run_prd_047_39_architecture_inventory.py
```

Result: `PASS`

## Runner Unit / Contract Baseline Before Hygiene
Command:

```powershell
$env:PYTHONPATH='bot_psychologist'; & 'bot_psychologist\.venv\Scripts\python.exe' -m pytest bot_psychologist/tests/test_prd_047_39_architecture_inventory.py bot_psychologist/tests/contract/test_no_legacy.py -q
```

Result: `6 passed in 0.04s`

## Preservation Subset 1 Before Hygiene
Command:

```powershell
$env:PYTHONPATH='bot_psychologist'; & 'bot_psychologist\.venv\Scripts\python.exe' -m pytest bot_psychologist/tests/test_prd_047_34_latest_turn_authority.py bot_psychologist/tests/test_prd_047_36_hf6_boundary_trace_contract.py bot_psychologist/tests/test_prd_047_36_hf6_no_internal_db_trace_integrity.py bot_psychologist/tests/test_prd_047_36_hf6_no_practice_trace_integrity.py -q
```

Result: `14 passed in 0.69s`

## Preservation Subset 2 Before Hygiene
Command:

```powershell
$env:PYTHONPATH='bot_psychologist'; & 'bot_psychologist\.venv\Scripts\python.exe' -m pytest bot_psychologist/tests/test_prd_047_36_hf5_selected_knowledge_admission_contract.py bot_psychologist/tests/test_prd_047_36_hf5_direct_concept_followup_kb_visibility.py bot_psychologist/tests/test_prd_047_27_hf1_semantic_cards_runtime_visibility.py bot_psychologist/tests/api/test_prd_047_36_hf4_trace_persistence_every_turn.py bot_psychologist/tests/api/test_multiagent_trace_storage_consistency.py bot_psychologist/tests/test_final_answer_acceptance_gate_v1.py -q
```

Result: `20 passed in 4.06s`

## Runner Unit / Contract After Hygiene
Result: `6 passed in 0.04s`

## Preservation Subset 1 After Hygiene
Result: `14 passed in 0.76s`

## Preservation Subset 2 After Hygiene
Result: `20 passed in 4.35s`

## Regression Discovery
Command:

```powershell
$env:PYTHONPATH='bot_psychologist'; & 'bot_psychologist\.venv\Scripts\python.exe' -m pytest bot_psychologist/tests/regression --collect-only -q
```

Result: `19 tests collected in 3.42s`; retired `test_no_sd_required_by_response_flow.py` is not collected.

## Warning
Full `bot_psychologist/tests/regression -q` timed out after 124s in this environment. The deterministic preservation subsets before/after hygiene are identical and passing.
