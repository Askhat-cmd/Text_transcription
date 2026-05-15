# Project State - Bot Psychologist / Neo MindBot

## Current Stage
Проект находится на стадии post-PRD-046.0.9-RUN1-HF3: устранён runtime blocker пустого registry table, добавлены row-isolation и safe delete-policy fallback для Chroma-check path, подтверждена admin consistency синхронизация Dashboard/Registry/Chroma (`247/247`) перед переходом к human review.

## Current Runtime Architecture
Активный user-path:
User message -> State Analyzer -> Thread Manager -> Memory Retrieval -> Context Assembly -> Diagnostic Card -> Writer Move Compliance -> Writer -> Validator/Trace -> Memory Update.

Runtime работает без cascade legacy режима и опирается на управляемый pipeline с диагностическим trace, где Writer не является единственным диагностическим узлом.

## Current Knowledge Base State
Knowledge Base governance слой внедрен: chunk_type/allowed_use/safety_flags остаются deterministic authority. Текущее production-состояние: `247` governed blocks для `123__кузница_духа`; Chroma collection также `247` блоков, source set = только `123__кузница_духа`. Источник `КУЗНИЦА ДУХА` трактуется как internal lens library, не как user-facing цитатник.

## Current Context / Memory State
Context Assembly реализован и стабилизирован. Async turn LLM summary additive слой прошел HF1 acceptance-calibration: eval-case coverage расширена, validator safety guards усилены, processor evidence pending->ready подтверждён. Для длинных turns используется `llm_abstractive_v1` при `ready+valid+hash-match`, иначе deterministic fallback `deterministic_extractive_v1`. Raw dialogue history сохраняется полностью, summary-поля остаются добавочным слоем и не подменяют первичные turn records.

## Current LLM Enrichment State
Offline LLM enrichment pipeline внедрен и откалиброван, затем применен controlled overlay cycle:
- RUN1 показал blocker по unknown lens.
- HF2 закрыл unknown lens и quote/invariant риски.
- HF3 закрыл low_resource avoid_when hard-fail.
Текущее состояние: advisory enrichment metadata записана в `metadata.llm_enrichment` для 60 блоков батча APPLY1 без мутации governance authority полей.
Новый post-reprocess baseline (`247` block ids) построен в `PRD-046.0.9`; в `PRD-046.0.9-RUN1` выполнен реальный enrichment run: `items_completed=247`, `validation_errors_count=0`, `review_queue_items_count=87`, `provider_status=called`.
В `PRD-046.0.9-RUN1-HF1` dashboard получает enrichment/review состояние из артефактов RUN1 через единый endpoint `/api/dashboard/` и показывает явные warning/error причины вместо немых пустых карточек.
В `PRD-046.0.9-RUN1-HF2` endpoint/Frontend дополнительно откалиброваны под runtime acceptance: поддерживаются `/api/dashboard` и `/api/dashboard/`, production-block card опирается на focus-source (`247`), registry total показывается отдельно, а при API/payload проблемах отображается явная ошибка.
В `PRD-046.0.9-RUN1-HF3` registry endpoint стал row-isolated (одна плохая строка больше не роняет весь список), frontend реестра получил явные loading/error/empty состояния, а consistency gate подтвердил browser-visible состояние без reindex/apply.

## Current Admin Source Hygiene State
Delete policy в реестре стала явной и согласованной между backend/frontend:
- `Защищено` только для focus source `123__кузница_духа`;
- `Удалить` для безопасных zero-block источников;
- `Очистить тестовый` для test-like `<=1` блока только при safety-gates;
- snapshot registry создаётся перед фактическим delete-мутированием.
Production focus source и Chroma production count остаются неизменны.

## Current Writer KB Snippet State
Root cause mid-word KB snippet clipping подтверждён в `knowledge_policy._sanitize_preview` (жёсткий char-cut). В HF2 внедрена boundary-aware truncation логика (sentence/word boundary + ellipsis `…`) без изменения governance authority и без изменения production block text.

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
- Controlled apply workflow для validated review decisions (`PRD-046.0.7.1`) требует решений только по fresh review queue post-reprocess real-enrichment цикла.

## Not Implemented Yet
- Controlled application of validated review decisions to KB metadata (`PRD-046.0.7.1`).
- Diagnostic Center v1 (deferred until KB/retrieval/context readiness confirmed).

## Known Risks
- Без регулярной обработки pending turn summaries возможен возврат к deterministic fallback чаще, чем ожидается.
- В окружениях с нестабильной кодировкой входа возможны искажения текстовых сигналов; safety-guards должны сохраняться conservative.
- Premature Diagnostic Center launch создаст ложную уверенность в диагностике при неготовом context-quality слое.
- Overlay apply без отдельного controlled PRD нарушит release discipline.
- Старый review queue (`PRD-046.0.7`) устарел после смены block boundaries и не может применяться напрямую.
- Операции reindex остаются чувствительными к локальной стабильности Chroma SQLite; обязательны backup/manifest + recovery шаги.

## Next Planned PRDs
1. PRD-046.0.9.1 - Human Review Decisions for Post-Reprocess Enrichment v1.
2. PRD-046.0.7.1 - Controlled Review Decision Apply v1 (только для решений, привязанных к новым block ids).
3. Diagnostic Center rollout PRD (deferred, after gates).

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
- Date: 2026-05-15
- Source cycle: PRD-046.0.9-RUN1-HF3
