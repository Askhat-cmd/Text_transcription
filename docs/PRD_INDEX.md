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
| PRD-046.0.7-HF1 | BotDB Admin Source Hygiene / Legacy SD Decommission / Reprocess Readiness Gate | done | b7c630f | source hygiene audit/apply dry-run + SD decommission in admin/query + readiness gate (`not_ready` blocker surfaced) | TO_DO_LIST/reports/PRD-046.0.7-HF1_IMPLEMENTATION_REPORT.md |
| PRD-046.0.7-HF2 | Source Hygiene Blocker Fix v1 | done | 1760f88 | controlled archive apply completed; blocker `multiple_active_sources_without_allowlist` closed; readiness gate -> `ready` | TO_DO_LIST/reports/PRD-046.0.7-HF2_IMPLEMENTATION_REPORT.md |
| PRD-046.0.8 | Clean Source Reprocess from Single Active Source v1 | done | ac587d5 | staged candidate-only clean reprocess built (`247` blocks), no production mutation; gate=`candidate_needs_governance_calibration` | TO_DO_LIST/reports/PRD-046.0.8_IMPLEMENTATION_REPORT.md |
| PRD-046.0.8-HF1 | Candidate Governance / Practice Classification Calibration v1 | done | historical | deterministic practice taxonomy + governance gate v2; `direct_practice_misclassified_count=0`, `unsafe_practice_suggestion_count=0`; no production mutation | TO_DO_LIST/reports/PRD-046.0.8-HF1_IMPLEMENTATION_REPORT.md |
| PRD-046.0.8-HF2 | Remaining Candidate Governance Warning Calibration v1 | done | historical | mixed-intent warning calibration (`mixed_intent_unresolved_count=0`), governance gate v3 passed, `candidate_ready_for_apply=true`, no production mutation | TO_DO_LIST/reports/PRD-046.0.8-HF2_IMPLEMENTATION_REPORT.md |
| PRD-046.0.8.1 | Controlled Candidate Apply + Chroma Reindex + KB Quality Re-Audit v1 | done | a593507 | candidate applied to production (`229 -> 247`), registry synced, Chroma reindexed/recovered to `247`, post-apply quality/retrieval gates regenerated | TO_DO_LIST/reports/PRD-046.0.8.1_IMPLEMENTATION_REPORT.md |
| PRD-046.0.9 | Post-Reprocess LLM Enrichment + Review Queue Rebaseline v1 | done | 85b2d22 | rebuilt fresh enrichment/review baseline for current `247` block ids in candidate mode; no production apply and no Chroma reindex | TO_DO_LIST/reports/PRD-046.0.9_IMPLEMENTATION_REPORT.md |
| PRD-046.0.9-RUN1 | Real Provider Enrichment Run after Post-Reprocess Rebaseline v1 | done | e3f9e37 | rerun with provider key succeeded (`247/247`, `missing_real_provider_output_count=0`), real review queue rebuilt (`87` items), no production mutation and no Chroma reindex | TO_DO_LIST/reports/PRD-046.0.9-RUN1_IMPLEMENTATION_REPORT.md |
| PRD-046.0.9-RUN1-HF1 | BotDB Admin Dashboard Metrics Restore + Enrichment Review Visibility v1 | done | 0f1d8a5 | restored read-only `/api/dashboard/` contract, returned dashboard enrichment/review visibility, added explicit warning/error surfacing, no production mutation | TO_DO_LIST/reports/PRD-046.0.9-RUN1-HF1_IMPLEMENTATION_REPORT.md |
| PRD-046.0.9-RUN1-HF2 | Admin Runtime UI Fix + Source Delete Hygiene + Writer KB Snippet Boundary Audit v1 | done | f7447fd | runtime dashboard render contract fixed (cache busting + payload guard), registry delete policy aligned with UI/backend safety gates, boundary-aware KB snippet truncation for Writer | TO_DO_LIST/reports/PRD-046.0.9-RUN1-HF2_IMPLEMENTATION_REPORT.md |
| PRD-046.0.9-RUN1-HF3 | Registry Runtime Render Fix + Admin Data Consistency Gate v1 | done | f0b7078 | registry row-isolation + safe Chroma source-exists fallback + explicit registry loading/error/empty states; consistency gate passed (`247/247`, review `87`) | TO_DO_LIST/reports/PRD-046.0.9-RUN1-HF3_IMPLEMENTATION_REPORT.md |
| PRD-046.0.9.1 | Human Review Decisions for Post-Reprocess Enrichment v1 | done | 4331da8 | delivered fresh-queue review decisioning layer (manifest/workbench/template/validator/no-mutation/tests) without production mutation; detected queue/block-id alignment blocker (`87` missing in current `229` blocks snapshot) | TO_DO_LIST/reports/PRD-046.0.9.1_IMPLEMENTATION_REPORT.md |
| PRD-046.0.9.1-HF1 | Blocks Snapshot Alignment Audit / Restore v1 | done | 7115d62 | added alignment audit+restore tooling, restored blocks snapshot to `247` with backup proof, enabled strict `--require-aligned` gate, rerun achieved queue coverage `87/87` | TO_DO_LIST/reports/PRD-046.0.9.1-HF1_IMPLEMENTATION_REPORT.md |
| PRD-046.0.9.2 | Architect Semantic Review Pass v1 | done | cf409f1 | prepared sanitized architect review batches (`87` items, `8` files), created architect decisions template/overlay, added overlay validator with coverage/apply-ready flags, generated no-mutation proof (`ready_for_architect_review=true`, `apply_ready=false`) | TO_DO_LIST/reports/PRD-046.0.9.2_IMPLEMENTATION_REPORT.md |
| PRD-046.0.9.3 | Review Automation Policy / Auto-Decisions v1 | done | 9bbcfc1 | implemented conservative policy auto-decisions for all `87` aligned items, generated validated overlay (`coverage=100%`, `apply_ready=true`), updated official overlay, produced policy/no-mutation reports without production apply/reindex | TO_DO_LIST/reports/PRD-046.0.9.3_IMPLEMENTATION_REPORT.md |

## Documentation Update Rule
1. Каждый новый PRD после push обновляет `docs/PRD_INDEX.md`.
2. Если изменился project stage — обновляется `docs/PROJECT_STATE.md`.
3. Если изменилась последовательность шагов — обновляется `docs/ROADMAP.md`.
4. Если принято новое архитектурное решение — обновляется `docs/DECISIONS.md`.
5. `TO_DO_LIST` хранит полный архив logs/reports, `docs/` хранит сжатую карту текущего состояния.



