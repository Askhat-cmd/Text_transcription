# PRD-047.17 Source Audit

- status: `passed`
- contains_prd_047_16_successor: `True`

## Git Status
- `?? Bot_data_base/knowledge_governance/offline_enrichment.py`
- `?? Bot_data_base/tests/test_mechanism_enrichment_anti_runtime_activation.py`
- `?? Bot_data_base/tests/test_mechanism_metadata_enrichment.py`
- `?? Bot_data_base/tests/test_run_mechanism_metadata_enrichment.py`
- `?? Bot_data_base/tools/run_mechanism_metadata_enrichment.py`
- `?? TO_DO_LIST/PRD-047.17_Offline_Summary_Lens_Use_When_Enrichment_over_Mechanism_Metadata_v1_RU.md`
- `?? TO_DO_LIST/PRD-047.17_TASK_LIST.md`
- `?? TO_DO_LIST/logs/PRD-047.17/`

## Previous Gaps To Close
- missing_mechanism_hints_count=28/54
- contraindications_present_ratio=0.0
- practice metadata gaps remain
- use_when / avoid_when still partly generic and not source-grounded

## Out Of Scope
- no live Writer/runtime activation
- no Chroma reindex
- no DB mutation
- no MemoryRetrievalAgent live behavior change
