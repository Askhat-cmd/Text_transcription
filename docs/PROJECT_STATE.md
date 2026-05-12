# Project State - Bot Psychologist / Neo MindBot

## Current Stage
Проект находится на стадии post-PRD-046.0.8-HF2 candidate warning calibration: для единственного active source (`123__кузница_духа`) candidate повторно откалиброван без мутаций production (`all_blocks_merged/registry/chroma`), direct-practice/mixed-intent blockers закрыты, governance gate `passed`, `candidate_ready_for_apply=true`.

## Current Runtime Architecture
Активный user-path:
User message -> State Analyzer -> Thread Manager -> Memory Retrieval -> Context Assembly -> Diagnostic Card -> Writer Move Compliance -> Writer -> Validator/Trace -> Memory Update.

Runtime работает без cascade legacy режима и опирается на управляемый pipeline с диагностическим trace, где Writer не является единственным диагностическим узлом.

## Current Knowledge Base State
Knowledge Base governance слой внедрен: chunk_type/allowed_use/safety_flags ведут deterministic authority. Chroma/API retrieval восстановлены после governed reindex-chain, а RAG путь в bot runtime использует API retrieval вместо небезопасных fallback-контуров. Источник `КУЗНИЦА ДУХА` трактуется как internal lens library, не как user-facing цитатник.

## Current Context / Memory State
Context Assembly реализован и стабилизирован. Async turn LLM summary additive слой прошел HF1 acceptance-calibration: eval-case coverage расширена, validator safety guards усилены, processor evidence pending->ready подтверждён. Для длинных turns используется `llm_abstractive_v1` при `ready+valid+hash-match`, иначе deterministic fallback `deterministic_extractive_v1`. Raw dialogue history сохраняется полностью, summary-поля остаются добавочным слоем и не подменяют первичные turn records.

## Current LLM Enrichment State
Offline LLM enrichment pipeline внедрен и откалиброван, затем применен controlled overlay cycle:
- RUN1 показал blocker по unknown lens.
- HF2 закрыл unknown lens и quote/invariant риски.
- HF3 закрыл low_resource avoid_when hard-fail.
Текущее состояние: advisory enrichment metadata записана в `metadata.llm_enrichment` для 60 блоков батча APPLY1 без мутации governance authority полей.

## Stable Modules
- Multiagent runtime orchestration.
- State Analyzer routing/calibration (deterministic contract).
- Thread Manager diagnostics baseline.
- Context Assembly v1 deterministic path.
- Diagnostic Card + Writer Move Compliance contracts.
- Governance-first KB policy and redaction-safe trace.
- BotDB/Chroma retrieval restore path.
- Admin Review Workflow v1 (contracts + sanitizer + queue/decision validation CLI).
- BotDB source hygiene/readiness tools v1 (`source_hygiene_audit/apply`, `legacy_sd_usage_audit`, `reprocess_readiness_gate`).

## Experimental / In Progress Modules
- Controlled candidate apply + Chroma reindex подготовка (`PRD-046.0.8.1`).
- Controlled apply workflow для validated review decisions (`PRD-046.0.7.1`) отложен после clean-reprocess chain.

## Not Implemented Yet
- Controlled candidate apply + Chroma reindex + post-reprocess KB quality re-audit (`PRD-046.0.8.1`).
- Controlled application of validated review decisions to KB metadata (`PRD-046.0.7.1`).
- Diagnostic Center v1 (deferred until KB/retrieval/context readiness confirmed).

## Known Risks
- Без регулярной обработки pending turn summaries возможен возврат к deterministic fallback чаще, чем ожидается.
- В окружениях с нестабильной кодировкой входа возможны искажения текстовых сигналов; safety-guards должны сохраняться conservative.
- Premature Diagnostic Center launch создаст ложную уверенность в диагностике при неготовом context-quality слое.
- Overlay apply без отдельного controlled PRD нарушит release discipline.
- Переход к `PRD-046.0.8.1` требует строгого соблюдения no-mutation preflight discipline до controlled apply шага.

## Next Planned PRDs
1. PRD-046.0.8.1 - Controlled Candidate Apply + Chroma Reindex + KB Quality Re-Audit v1.
2. PRD-046.0.7.1 - Controlled Review Decision Apply v1.
3. Diagnostic Center rollout PRD (deferred, after gates).
4. Diagnostic Center rollout PRD (deferred, after gates).

## Do Not Do Yet
- Не включать Diagnostic Center до завершения async summary + retrieval eval шага.
- Не менять governance authority (`chunk_type/allowed_use/safety_flags`) через LLM overlay.
- Не превращать KB в direct-quote source для Writer.
- Не подменять deterministic governance решения LLM-логикой.

## Documentation Update Rule
1. PRD, меняющий stage/architecture, обязан обновить PROJECT_STATE.
2. PRD, меняющий последовательность работ, обязан обновить ROADMAP.
3. PRD с новым архитектурным решением обязан обновить DECISIONS.
4. Каждый новый PRD после push обязан обновить PRD_INDEX.
5. TO_DO_LIST остается детальным архивом, docs — краткая operational map.

## Last Updated
- Date: 2026-05-12
- Source cycle: PRD-046.0.8-HF2
