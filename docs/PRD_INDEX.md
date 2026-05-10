# PRD Index

| PRD | Название | Статус | Commit | Что изменилось | Отчёт |
| --- | --- | --- | --- | --- | --- |
| PRD-045.0..045.7.1 | Runtime quality foundation chain | done | historical | multiagent/runtime diagnostics/context/writer contracts | see TO_DO_LIST/reports |
| PRD-046.0 | KB preparation governance v1 | done | historical | governance baseline for chunks | see report |
| PRD-046.0.1 | Admin upload governance adapter | done | historical | ingestion governance wiring | see report |
| PRD-046.0.2 | Structure-aware chunking boundary governance | done | historical | governed chunking boundaries | see report |
| PRD-046.0.2.1 | Boundary calibration precision guard | done | historical | calibration of allowed-use precision | see report |
| PRD-046.0.3 | Runtime governance filtering retrieval policy | done | historical | retrieval policy constraints | see report |
| PRD-046.0.3-HF1 | LLM client/BotDB health guard | done | historical | live runtime restore guards | see report |
| PRD-046.0.3.1 | Debug redaction safe trace guard | done | historical | removed unsafe debug content leaks | see report |
| PRD-046.0.4 | Real source KB quality audit | done | historical | KB quality audit baseline | see report |
| PRD-046.0.4.1 | Chroma recovery index consistency gate | done | historical | governed gate before reindex | see report |
| PRD-046.0.4.2 | Source reprocess governance backfill | done | historical | governed backfill for source blocks | see report |
| PRD-046.0.4.2.1 | Practice classification precision | done | historical | reduced manual review noise | see report |
| PRD-046.0.4.3 | Chroma reindex from governed blocks | done | historical | restored `/api/query` from governed index | see report |
| PRD-046.0.5 | Offline LLM summary/lens enrichment | done | historical | offline enrichment pipeline + contracts | see report |
| PRD-046.0.5-HF1 | Prompt/validator calibration | done | historical | anti-quote and validator calibration | see report |
| PRD-046.0.5-RUN1 | Real LLM enrichment batch run | done | historical | first real batch, blocker discovery | see report |
| PRD-046.0.5-RUN1-HF2 | Lens/validator real calibration | done | af63952 | unknown lens blocker removed, gate still failed on low-resource rule | TO_DO_LIST/reports/PRD-046.0.5-RUN1-HF2_IMPLEMENTATION_REPORT.md |
| PRD-046.0.5-RUN1-HF3 | Low-resource avoid_when calibration | done | c42a12c | hard validation 0/60 fails, production-candidate-ready | TO_DO_LIST/reports/PRD-046.0.5-RUN1-HF3_IMPLEMENTATION_REPORT.md |
| PRD-046.0.5-APPLY1 | Apply real enrichment overlay + Chroma refresh | done | 1ee5f12 | applied advisory llm_enrichment metadata (60 blocks), reindex 229 blocks, API/bot retrieval enrichment smoke | TO_DO_LIST/reports/PRD-046.0.5-APPLY1_IMPLEMENTATION_REPORT.md |
| PRD-045.6.3 | Async Turn LLM Summary Store v1 | done | 2340bbc | async turn summary contract/service/processor + context assembly selection with deterministic fallback | TO_DO_LIST/reports/PRD-045.6.3_IMPLEMENTATION_REPORT.md |
| PRD-045.6.3-HF1 | Turn Summary Eval/Validator/Processor Evidence Calibration | done | 2469aee | eval dataset >=5, stronger validator guards, real pending->ready processor evidence | TO_DO_LIST/reports/PRD-045.6.3-HF1_IMPLEMENTATION_REPORT.md |
| PRD-DOCS-001 | Living project documentation v1 | done | 8912bb2 | create docs layer + report hygiene | TO_DO_LIST/reports/PRD-DOCS-001_IMPLEMENTATION_REPORT.md |
| PRD-046.0.6 | Knowledge Retrieval Eval Set v1 | done | b5e115f | deterministic retrieval eval dataset/runner, scorecard and weak-case queue; safety gap on internal_only exposure detected | TO_DO_LIST/reports/PRD-046.0.6_IMPLEMENTATION_REPORT.md |
| PRD-046.0.6-HF1 | Retrieval Governance Safety Fix v1 | done | 64ec628 | API-side retrieval policy suppresses internal_only in non-safety top-k; eval gate closed (`internal_only_unsafe_exposure_count=0`) | TO_DO_LIST/reports/PRD-046.0.6-HF1_IMPLEMENTATION_REPORT.md |
| PRD-046.0.7 | Admin Review Workflow v1 | done | 4b24388 | review contracts/sanitizer + CLI queue builder/decision validator + sanitized review artifacts with no-mutation proof | TO_DO_LIST/reports/PRD-046.0.7_IMPLEMENTATION_REPORT.md |

## Documentation Update Rule
1. Каждый новый PRD после push обновляет `docs/PRD_INDEX.md`.
2. Если изменился project stage — обновляется `docs/PROJECT_STATE.md`.
3. Если изменилась последовательность шагов — обновляется `docs/ROADMAP.md`.
4. Если принято новое архитектурное решение — обновляется `docs/DECISIONS.md`.
5. `TO_DO_LIST` хранит полный архив logs/reports, `docs/` хранит сжатую карту текущего состояния.

