# Project State - Bot Psychologist / Neo MindBot

## Current Stage
Проект находится на стадии post-PRD-046.0.7-HF2 hygiene blocker fix: SD активный фильтр в BotDB API/UI отключён, source hygiene apply выполнен в guarded режиме, readiness gate переведён в `ready` для clean reprocess из единственного active source.

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
- Clean source reprocess planning from single active source (`PRD-046.0.8`).
- Controlled apply workflow для validated review decisions (`PRD-046.0.7.1`) отложен после clean-reprocess chain.

## Not Implemented Yet
- Clean source reprocess from single active source (`PRD-046.0.8`).
- Controlled application of validated review decisions to KB metadata (`PRD-046.0.7.1`).
- Diagnostic Center v1 (deferred until KB/retrieval/context readiness confirmed).

## Known Risks
- Без регулярной обработки pending turn summaries возможен возврат к deterministic fallback чаще, чем ожидается.
- В окружениях с нестабильной кодировкой входа возможны искажения текстовых сигналов; safety-guards должны сохраняться conservative.
- Premature Diagnostic Center launch создаст ложную уверенность в диагностике при неготовом context-quality слое.
- Overlay apply без отдельного controlled PRD нарушит release discipline.
- Clean reprocess остаётся high-risk операцией и требует строгого выполнения preflight/checkpoint дисциплины в `PRD-046.0.8`.

## Next Planned PRDs
1. PRD-046.0.8 - Clean Source Reprocess from Single Active Source v1.
2. PRD-046.0.8.1 - Chroma Reindex + KB Quality Re-Audit after Reprocess.
3. PRD-046.0.7.1 - Controlled Review Decision Apply v1.
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
- Source cycle: PRD-046.0.7-HF2
