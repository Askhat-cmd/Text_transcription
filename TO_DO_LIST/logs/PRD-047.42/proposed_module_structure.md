# PRD-047.42 Proposed Module Structure

- stage: mapping only, no code moved in this PRD.
- purpose: produce a future-safe split plan before any decomposition PRD mutates source files.

| Current file | Proposed module | Lines | Approx LOC | legacy_compat | Moved responsibility |
| --- | --- | --- | --- | --- | --- |
| writer_agent | writer_agent_constants.py | 45-169 | 125 | no | Static runtime defaults, lexical detectors, and tiny coercion helpers used by later Writer paths. |
| writer_agent | writer_agent_runtime.py | 172-297 | 126 | no | Agent identity, runtime setting resolution, and top-level write/fallback lifecycle orchestration. |
| writer_agent | writer_prompt_defaults.py | 299-418 | 120 | no | Mass default injection into prompt context before template rendering; protects prompt assembly from missing fields. |
| writer_agent | writer_prompt_policy.py | 419-617 | 199 | yes | Transforms policy flags, dialogue profile, knowledge/practice gates, and context budget rules into Writer-visible prompt inputs and debug metadata. |
| writer_agent | writer_llm_dispatch.py | 618-1102 | 485 | no | Renders the actual Writer user prompt, dispatches to the model client, and records token/cost/debug metadata. |
| writer_agent | writer_answer_compliance_core.py | 1104-1307 | 204 | no | Normalizes post-LLM answer, reconstructs per-turn constraints, and prepares compliance/evaluator state. |
| writer_agent | writer_answer_compliance_repairs.py | 1308-1433 | 126 | no | Repairs bounded-practice, literal-markdown, direct-answer, and answer-obligation-specific misalignment before profile-specific branches. |
| writer_agent | writer_answer_compliance_safe_guided.py | 1435-1712 | 278 | yes | Non-MVP compliance branch for greeting, support, safety, no-question, known-concept, and practice-suppression sanitization. |
| writer_agent | writer_answer_compliance_mvp.py | 1714-1936 | 223 | no | MVP-free-dialogue-specific compliance and retry-defer logic for contextual follow-ups, summary, sarcasm, expansion, and practice suppression. |
| writer_agent | writer_agent_fallbacks.py | 1938-2183 | 246 | yes | Static fallback builders, retry signaling, client acquisition, language detection, and name continuity helpers. |
| admin_routes | admin_runtime_compat.py | 91-173 | 83 | yes | Admin runtime compatibility and deprecated-surface helpers for multiagent-only truth exposure. |
| admin_routes | admin_surface_bootstrap.py | 178-233 | 56 | no | Auth dependency, router registration, schema versions, and admin surface constants. |
| admin_routes | admin_surface_helpers.py | 235-665 | 431 | no | Status snapshots, prompt-stack builders, thread listings, agent-prompt reflection, and historical PRD artifact status loaders. |
| admin_routes | admin_runtime_effective_payload.py | 668-956 | 289 | yes | Assembles the canonical runtime/effective admin payload across flags, dialogue policy, planner, trace, semantic cards, and compat metadata. |
| admin_routes | admin_diagnostics_payload.py | 959-982 | 24 | no | Builds compact diagnostics payload for dedicated admin diagnostics surface. |
| admin_routes | admin_config_schema.py | 985-1132 | 148 | no | Builds admin config schema v10.4 and validates import/export payload normalization. |
| admin_routes | admin_config_routes.py | 1148-1432 | 285 | yes | Config CRUD, runtime status/effective endpoints, diagnostics endpoints, and deprecated admin trace routes. |
| admin_routes | admin_prompt_routes.py | 1447-1705 | 259 | no | Prompt CRUD, prompt-stack v2 editing, history, and import/export endpoints. |
| admin_routes | admin_agent_ops_routes.py | 1716-1905 | 190 | yes | Agent status/toggles/metrics, orchestrator config, traces, and overview endpoints. |
| admin_routes | admin_misc_routes.py | 1916-2144 | 229 | no | Thread cleanup, per-agent prompt/LLM config endpoints, full reset, and user identity admin route. |
| writer_contract | writer_contract_model.py | 21-87 | 67 | no | Stable contract dataclass definition plus shallow serialization for tracing and transport. |
| writer_contract | writer_prompt_context_sources.py | 89-240 | 152 | no | Collects fresh-chat policy, writer context package, conversation/rag sources, and base governance dictionaries. |
| writer_contract | writer_prompt_context_grounding.py | 241-378 | 138 | no | Resolves semantic-hit budgets, writer grounding visibility, payload/trace toggles, and dialogue profile/directive inputs. |
| writer_contract | writer_prompt_context_legacy_bridge.py | 379-468 | 90 | yes | Builds legacy-source signal bundle and sanitizes it into Writer-visible advisory guidance. |
| writer_contract | writer_prompt_context_payload.py | 469-979 | 511 | yes | Exports the full prompt-context payload consumed by Writer, including governance traces, planner, directive, and retrieval metadata. |
