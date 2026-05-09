# Architecture Decisions

## ADR-001 - Multiagent-only runtime
Status: accepted
Context: cascade/legacy path создавал размытые контракты и непредсказуемую диагностику.
Decision: runtime работает через multiagent-only orchestration с явным разделением ролей.
Consequences: выше контролируемость trace и проще quality gating.

## ADR-002 - Writer is not the whole diagnostic system
Status: accepted
Context: попытка возложить диагностику целиком на Writer ухудшает воспроизводимость.
Decision: диагностика распределяется между State Analyzer, Thread Manager, Diagnostic Card и compliance.
Consequences: Writer получает структурированный контекст, а не принимает системные решения в одиночку.

## ADR-003 - Context Assembly over "everything-in-prompt"
Status: accepted
Context: прямое включение всей истории/источников в prompt увеличивает шум и риск drift.
Decision: Context Assembly формирует ограниченный управляемый context package.
Consequences: выше predictability, ниже риск неконтролируемых ссылок и цитирования.

## ADR-004 - Knowledge Base is an internal lens library, not a quote source
Status: accepted
Context: внутренние книги и материалы не должны становиться user-facing цитатником.
Decision: KB используется как internal lens/practice metadata library.
Consequences: Writer не цитирует `КУЗНИЦУ ДУХА` напрямую пользователю.

## ADR-005 - Deterministic governance is authority; LLM enrichment is advisory
Status: accepted
Context: LLM может предложить полезные summaries/lenses, но допускает нестабильность формулировок.
Decision: `chunk_type/allowed_use/safety_flags` остаются deterministic authority.
Consequences: enrichment повышает качество retrieval-context, не разрушая safety contracts.

## ADR-006 - Raw history preserved; summaries are additive
Status: accepted
Context: компрессия истории без сохранения raw turns снижает дебаг и доверие к trace.
Decision: raw dialogue history сохраняется полностью, summary-слои добавочные.
Consequences: можно улучшать summaries без потери первичных данных.

## ADR-007 - Turn LLM summary must be async with deterministic fallback
Status: accepted
Context: синхронная summary-генерация может блокировать response path и деградировать UX.
Decision: planned async turn summary with deterministic fallback.
Consequences: улучшение semantic continuity без риска потери ответа при сбоях LLM.

## ADR-008 - Diagnostic Center deferred until readiness gates pass
Status: accepted
Context: преждевременный запуск Diagnostic Center при неготовом KB/context даст ложную уверенность.
Decision: запуск только после APPLY1, retrieval eval и context-quality прогресса.
Consequences: более надежный и интерпретируемый диагностический слой.
