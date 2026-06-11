# Writer Freedom Contract (Контракт свободы Writer)

## Scope (Область)
`Writer Freedom Contract v1` — guided-freedom policy для Writer.

Версия:
- `writer_freedom_contract_v1`

## Required Fields (Обязательные поля)
- `enabled`
- `freedom_level`
- `mode_hint`
- `mode_is_hint_not_cage`
- `question_limit`
- `practice_requires_gate`
- `practice_allowed`
- `hard_boundaries`
- `must_follow_exact_mode`

## Contract Semantics (Семантика contract)
- Response mode — guidance, а не strict cage.
- Один main move на answer.
- Practice требует explicit gate/safety need.
- Hard boundaries обязательны (`no_diagnosis`, `no_spiritual_authority`, `no_raw_kb_quote_dumping`, `no_unsolicited_practice`).

## Prompt Integration (Интеграция в prompt)
- Prompt block renderer: `render_writer_freedom_contract_prompt_block(...)`.
- Writer prompt включает compact freedom block вместо verbose contract dump.
- Micro-guidance в Writer prompt:
  - speak from lens, not about lens
  - avoid exposing internal lens names unless useful
  - avoid bureaucratic phrasing on personal tone
  - warm direct style for vulnerable user messages

## Runtime / Trace / Admin (Runtime, trace и admin)
- Propagated через `WriterContract` prompt context.
- Trace включает `debug.writer_freedom_contract.prompt_block_chars`.
- Admin runtime effective экспонирует read-only freedom contract state.

## Interaction With Active Line (Взаимодействие с Active Line)
- Writer freedom остаётся guided, но continuity constraints приходят из `active_line` signals.
- `active_line_should_offer_practice=false` подавляет unsolicited action-step behavior.
- `active_line_revoicing_allowed=false` подавляет mechanical question revoicing openers.
- `active_line_repair_mode` приоритизирует acknowledgement + return to mechanism на correction turns.
- Это сохраняет semantics `mode_is_hint_not_cage` при enforcement continuity-quality boundaries.

## Interaction With Response Planner (Взаимодействие с Response Planner)
- `response_planner` даёт compact per-turn move shape, depth и policy hints.
- Freedom contract остаётся style/governance frame; planner — turn-level move selector.
- Compliance сохраняет hard limits при сохранённой freedom:
  - `question_policy=none` подавляет follow-up question behavior.
  - `practice_policy=forbidden` подавляет unsolicited practice steps.
  - `revoicing_policy=suppressed` блокирует mechanical revoicing openers.
  - `answer_shape=one_step` enforce один executable step вместо reflective filler.
  - `next_move=repair_misalignment` enforce короткое repair acknowledgement без reopening loops.
- Writer остаётся non-scripted: planner — deterministic guidance, а не rigid text templating.

## PRD-047.5-HF1 Compliance Tightening (Ужесточение compliance PRD-047.5-HF1)
- Добавлен targeted compliance repair для cases, выявленных strict evaluator:
  - safety-adjacent outputs (`stabilize_safety`) принудительно уводятся от mechanism-language drift;
  - `question_policy=none` избегает latent question invites в final text;
  - `answer_known_concept` + `practice_policy=forbidden` избегает unsolicited practice framing.
- Compliance остаётся trace-visible и deterministic; hidden runner-side fallback не вводился.
- Writer freedom остаётся active, но final-answer policy obedience теперь строже для acceptance-critical planner shapes.

## PRD-047.6 Observability Guard Boundary (Граница observability guard PRD-047.6)
- Runtime drift guard вне Writer generation path.
- Writer freedom остаётся intact, когда answer complies с:
  - planner `answer_shape`
  - planner `question_policy`
  - planner `practice_policy`
  - safety policy boundaries
- Drift guard производит только warning/critical diagnostics:
  - trace/debug/admin visibility;
  - replay artifact evidence.
- Drift guard не блокирует и не заменяет user-visible final answer.

## PRD-047.9 Unified Adaptive Policy Alignment (Согласование Unified Adaptive Policy PRD-047.9)
- `mvp_free_dialogue` остаётся developer-local preset в одном runtime path.
- В MVP profile explicit user request для explanation/overview/examples имеет более высокую practical authority, чем advisory planner/diagnostic constraints, при сохранении mandatory minimal safety baseline.
- Writer prompt теперь получает explicit block `MVP FREE DIALOGUE OVERRIDES` и context diagnostics (`context_budget_chars`, truncation flags, preserved recent turns counters).
- Context assembly recency-preserving: latest turns сохраняются первыми в profile budget; old-prefix clipping (`[:2000]`) удалён из writer prompt path.

## PRD-047.10 Update (2026-06-01) (Обновление PRD-047.10)
- В `mvp_free_dialogue` writer freedom калибруется через unified `dialogue_policy.human_like_answer_policy`.
- Legacy hard-style constraints представлены в `constraint_resolution.overruled_constraints` как audit metadata, когда explicit user request или human-like policy требуют richer response shape.
- Minimal safety и hard boundaries остаются mandatory.
