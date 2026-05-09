# Project State - Bot Psychologist / Neo MindBot

## Current Stage
Проект находится на стадии controlled stabilization перед production-применением LLM-enriched Knowledge Base overlay. Основной runtime уже переведен на multiagent-only архитектуру, а KB-enrichment pipeline прошел цепочку real-calibration до production-candidate качества. После `PRD-046.0.5-RUN1-HF3` hard-gate метрики для enrichment-batch пройдены, но promotion остается policy-controlled и требует отдельного apply PRD.

## Current Runtime Architecture
Активный user-path:
User message -> State Analyzer -> Thread Manager -> Memory Retrieval -> Context Assembly -> Diagnostic Card -> Writer Move Compliance -> Writer -> Validator/Trace -> Memory Update.

Runtime работает без cascade legacy режима и опирается на управляемый pipeline с диагностическим trace, где Writer не является единственным диагностическим узлом.

## Current Knowledge Base State
Knowledge Base governance слой внедрен: chunk_type/allowed_use/safety_flags ведут deterministic authority. Chroma/API retrieval восстановлены после governed reindex-chain, а RAG путь в bot runtime использует API retrieval вместо небезопасных fallback-контуров. Источник `КУЗНИЦА ДУХА` трактуется как internal lens library, не как user-facing цитатник.

## Current Context / Memory State
Context Assembly реализован и стабилизирован. Turn micro-summary пока deterministic/extractive и не усиливает semantic continuity на уровне LLM-summary. Raw dialogue history сохраняется полностью, summary-поля рассматриваются как добавочный слой и не подменяют первичные turn records.

## Current LLM Enrichment State
Offline LLM enrichment pipeline внедрен и откалиброван:
- RUN1 показал blocker по unknown lens.
- HF2 закрыл unknown lens и quote/invariant риски.
- HF3 закрыл low_resource avoid_when hard-fail.
Текущее состояние: production_candidate_ready=true на controlled batch, promotion_allowed=false по policy (`requires_separate_apply_prd`).

## Stable Modules
- Multiagent runtime orchestration.
- State Analyzer routing/calibration (deterministic contract).
- Thread Manager diagnostics baseline.
- Context Assembly v1 deterministic path.
- Diagnostic Card + Writer Move Compliance contracts.
- Governance-first KB policy and redaction-safe trace.
- BotDB/Chroma retrieval restore path.

## Experimental / In Progress Modules
- LLM-enriched overlay apply path (готов как кандидат, но еще не применен).
- Расширенные soft-review workflows для enrichment (manual review queue).

## Not Implemented Yet
- Async Turn LLM Summary Store (planned PRD-045.6.3).
- Retrieval Eval program v1 (planned PRD-046.0.6).
- Admin Review workflow for enrichment gating (planned PRD-046.0.7).
- Diagnostic Center v1 (deferred until KB/retrieval/context readiness confirmed).

## Known Risks
- Без async turn summary enriched KB может начать доминировать над живой линией диалога.
- Premature Diagnostic Center launch создаст ложную уверенность в диагностике при неготовом context-quality слое.
- Overlay apply без отдельного controlled PRD нарушит release discipline.

## Next Planned PRDs
1. PRD-046.0.5-APPLY1 - Apply Real LLM Enrichment Overlay + Chroma Refresh v1.
2. PRD-045.6.3 - Async Turn LLM Summary Store v1.
3. PRD-046.0.6 - Knowledge Retrieval Eval Set v1.
4. PRD-046.0.7 - Admin Review Workflow v1.

## Do Not Do Yet
- Не включать Diagnostic Center до завершения APPLY1 + context-quality шага.
- Не промоутить overlay напрямую в production blocks вне apply PRD.
- Не превращать KB в direct-quote source для Writer.
- Не подменять deterministic governance решения LLM-логикой.

## Documentation Update Rule
1. PRD, меняющий stage/architecture, обязан обновить PROJECT_STATE.
2. PRD, меняющий последовательность работ, обязан обновить ROADMAP.
3. PRD с новым архитектурным решением обязан обновить DECISIONS.
4. Каждый новый PRD после push обязан обновить PRD_INDEX.
5. TO_DO_LIST остается детальным архивом, docs — краткая operational map.

## Last Updated
- Date: 2026-05-09
- Source cycle: PRD-DOCS-001
