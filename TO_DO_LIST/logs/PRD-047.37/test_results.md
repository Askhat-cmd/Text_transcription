# PRD-047.37 Test Results

Date: 2026-07-02
Status: `passed_with_warnings`

## Environment Notes
- Python used: `bot_psychologist/.venv/Scripts/python.exe`
- Required layout note: preservation pytest subsets pass when run from repository root with `PYTHONPATH=bot_psychologist`.
- Initial pytest attempts without the correct import layout failed with `ModuleNotFoundError` for `bot_psychologist` / `bot_agent`; rerun with `PYTHONPATH=bot_psychologist` passed.

## Python Preservation Checks

### HF6 boundary trace preservation
Command:

```powershell
$env:PYTHONPATH='bot_psychologist'; & 'bot_psychologist\.venv\Scripts\python.exe' -m pytest bot_psychologist/tests/test_prd_047_36_hf6_boundary_trace_contract.py bot_psychologist/tests/test_prd_047_36_hf6_no_internal_db_trace_integrity.py bot_psychologist/tests/test_prd_047_36_hf6_no_practice_trace_integrity.py -q
```

Result:

```text
6 passed in 0.66s
```

### HF5 selected-knowledge admission preservation
Command:

```powershell
$env:PYTHONPATH='bot_psychologist'; & 'bot_psychologist\.venv\Scripts\python.exe' -m pytest bot_psychologist/tests/test_prd_047_36_hf5_selected_knowledge_admission_contract.py bot_psychologist/tests/test_prd_047_36_hf5_direct_concept_followup_kb_visibility.py -q
```

Result:

```text
5 passed in 0.33s
```

### HF4 trace persistence preservation
Command:

```powershell
$env:PYTHONPATH='bot_psychologist'; & 'bot_psychologist\.venv\Scripts\python.exe' -m pytest bot_psychologist/tests/api/test_prd_047_36_hf4_trace_persistence_every_turn.py bot_psychologist/tests/api/test_multiagent_trace_storage_consistency.py -q
```

Result:

```text
5 passed in 3.93s
```

## Frontend Checks

### Typecheck / lint
Command:

```powershell
npm run lint
```

Working directory:

```text
bot_psychologist/web_ui
```

Result:

```text
PASS
tsc --noEmit
```

### Production build
Command:

```powershell
npm run build
```

Working directory:

```text
bot_psychologist/web_ui
```

Result:

```text
PASS
vite built successfully
```

Warnings:

```text
Browserslist/caniuse-lite data is 6 months old.
adminConfig.service.ts is both dynamically and statically imported, so dynamic import will not move it into another chunk.
Some chunks are larger than 500 kB after minification.
```

These warnings are pre-existing build hygiene warnings and not PRD-047.37 blockers.

## Optional Sanity Script
No `bot_psychologist/tools/run_prd_047_37_freeze_sanity_check.py` script was created, so no `py_compile` command was applicable. See `sanity_check_report.md`.

## Full Pytest
Full `python -m pytest tests -q` was not rerun for this documentation/freeze PRD. The known historical unrelated `_build_llm_prompts` full-suite blocker remains recorded as backlog.
