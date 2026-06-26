# PRD-047.35 Product Simplicity Audit

Status: `passed_with_warning`

## Goal

Keep the product path simple for ordinary users: answer from competence, not about internal storage.

## Simplifications delivered

- public answers no longer need DB/chunk/system language to sound informed
- internal knowledge is framed as hidden competence inside the existing Writer path
- ordinary explanation guidance is reduced to:
  - one mechanism
  - what it protects
  - at most one next move or question
- direct owner/debug-like source questions remain allowed without becoming the main product path

## Noise reduced in the current pipeline

- `writer_context_package.py` now carries a compact `hidden_knowledge_competence_v1` decision instead of relying on implicit behavior
- `runtime_trace_summary.py` exposes the same state so owner review can see the rule without leaking it to the end user
- `legacy_advisory_sanitizer.py` now repeats the anti-internals / Wake-depth rule to Writer in a compact form
- `response_planner.py` now explicitly avoids base/chunk/semantic-card wording in ordinary branches
- Writer system prompt now states that internal knowledge is hidden competence, not a conversation topic

## Scope discipline kept

- canonical runtime stayed `multiagent_adapter`
- no new route
- no new agent
- no broad KB default for ordinary support/contact turns
- no DB/Chroma/source mutation

## Honest warnings

- panic scenario turn 1 is still too generic and over-crisis-shaped for a third-person helper question
- one creative deepening answer still expanded into `adaptive_current_pipeline` length instead of staying compact
- close/thanks behavior after explicit continuation still sometimes carries extra mechanism recap

## Conclusion

The product got simpler in the right place: public answers speak from competence instead of talking about internal machinery. The remaining debt is live answer polish, not architecture or retrieval authority.
