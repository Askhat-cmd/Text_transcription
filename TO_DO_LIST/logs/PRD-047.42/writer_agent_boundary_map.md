# PRD-047.42 writer_agent Boundary Map

- file: `bot_psychologist/bot_agent/multiagent/agents/writer_agent.py`
- total_loc: `2188`
- mapped_loc: `2132`
- exact_cover: `False`

## Responsibility Sections
| Section | Lines | LOC | legacy_compat | Proposed future module | Responsibility |
| --- | --- | --- | --- | --- | --- |
| module_constants_and_detectors | 45-169 | 125 | no | writer_agent_constants.py | Static runtime defaults, lexical detectors, and tiny coercion helpers used by later Writer paths. |
| runtime_settings_and_write_lifecycle | 172-297 | 126 | no | writer_agent_runtime.py | Agent identity, runtime setting resolution, and top-level write/fallback lifecycle orchestration. |
| prompt_context_default_injection | 299-418 | 120 | no | writer_prompt_defaults.py | Mass default injection into prompt context before template rendering; protects prompt assembly from missing fields. |
| prompt_policy_overrides_and_context_budgeting | 419-617 | 199 | yes | writer_prompt_policy.py | Transforms policy flags, dialogue profile, knowledge/practice gates, and context budget rules into Writer-visible prompt inputs and debug metadata. |
| prompt_render_and_llm_io | 618-1102 | 485 | no | writer_llm_dispatch.py | Renders the actual Writer user prompt, dispatches to the model client, and records token/cost/debug metadata. |
| compliance_intake_and_obligation_resolution | 1104-1307 | 204 | no | writer_answer_compliance_core.py | Normalizes post-LLM answer, reconstructs per-turn constraints, and prepares compliance/evaluator state. |
| bounded_practice_and_direct_answer_repairs | 1308-1433 | 126 | no | writer_answer_compliance_repairs.py | Repairs bounded-practice, literal-markdown, direct-answer, and answer-obligation-specific misalignment before profile-specific branches. |
| safe_guided_compliance_branch | 1435-1712 | 278 | yes | writer_answer_compliance_safe_guided.py | Non-MVP compliance branch for greeting, support, safety, no-question, known-concept, and practice-suppression sanitization. |
| mvp_free_dialogue_branch | 1714-1936 | 223 | no | writer_answer_compliance_mvp.py | MVP-free-dialogue-specific compliance and retry-defer logic for contextual follow-ups, summary, sarcasm, expansion, and practice suppression. |
| fallbacks_debug_client_and_name_continuity | 1938-2183 | 246 | yes | writer_agent_fallbacks.py | Static fallback builders, retry signaling, client acquisition, language detection, and name continuity helpers. |

## AST Anchors
| Node type | Name | Lines | Owner class |
| --- | --- | --- | --- |
| FunctionDef | _extract_literal_markdown_echo_request | 137-150 |  |
| FunctionDef | _to_int | 153-157 |  |
| FunctionDef | _to_float | 160-164 |  |
| FunctionDef | _contains_any | 167-169 |  |
| ClassDef | WriterAgent | 172-2183 |  |
| method | __init__ | 175-178 | WriterAgent |
| method | _resolve_model | 180-181 | WriterAgent |
| method | _resolve_runtime_settings | 183-204 | WriterAgent |
| method | write | 206-297 | WriterAgent |
| method | _call_llm | 299-1102 | WriterAgent |
| method | _enforce_answer_compliance | 1104-1712 | WriterAgent |
| method | _enforce_mvp_free_dialogue_compliance | 1714-1936 | WriterAgent |
| method | _repair_greeting_without_mechanism_lecture | 1938-1947 | WriterAgent |
| method | _build_gentle_close_reply | 1950-1951 | WriterAgent |
| method | _build_no_practice_fallback_text | 1954-1962 | WriterAgent |
| method | _resolve_one_step_or_no_practice_fallback | 1964-1987 | WriterAgent |
| method | _set_final_answer_shape_debug | 1989-1990 | WriterAgent |
| method | _defer_no_stub_repair | 1992-2014 | WriterAgent |
| method | _strip_optional_followup_invitation | 2017-2023 | WriterAgent |
| method | _get_client | 2025-2037 | WriterAgent |
| method | _detect_language | 2040-2042 | WriterAgent |
| method | _format_hits | 2045-2048 | WriterAgent |
| method | _format_diagnostic_summary | 2051-2059 | WriterAgent |
| method | _estimate_cost | 2061-2069 | WriterAgent |
| method | _static_fallback | 2072-2141 | WriterAgent |
| method | _apply_name_continuity | 2143-2150 | WriterAgent |
| method | _extract_user_name | 2152-2176 | WriterAgent |
| method | _normalize_name | 2179-2183 | WriterAgent |
