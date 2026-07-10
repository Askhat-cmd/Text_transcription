# _call_llm Boundary Map

- PRD: `PRD-047.42-APPLY-6`
- Target: `bot_psychologist/bot_agent/multiagent/agents/writer_agent.py::WriterAgent._call_llm`
- Method line span: `135-938` (804 LOC)
- Real provider call: line `902` via `create_agent_completion(...)`
- Rule of this PRD: mapping only, no production-code movement

| cluster | lines | loc | writes last_debug | responsibility | future extraction note |
| --- | --- | --- | --- | --- | --- |
| client_and_ctx_default_seeding | 141-254 | 114 | no | Gets the client, builds `ctx = contract.to_prompt_context()`, and seeds a large default surface with `ctx.setdefault(...)` so prompt rendering never sees missing keys. | Read-only in this PRD. Future cut candidate only after defaults are grouped into smaller helper families. |
| knowledge_practice_kernel_inputs | 255-303 | 49 | no | Extracts knowledge/practice guards, philosophy kernel, freedom contract, and list-like helper payloads from `ctx` into local normalized structures. | Good early helper candidates: pure dict/list normalization helpers with explicit parameters. |
| dialogue_policy_and_context_budget | 304-332 | 29 | no | Builds `dialogue_policy_payload`, human-like/constraint payloads, normalizes profile, resolves context budget, and formats conversation context with metadata. | Likely safe next-stage helper cluster if split away from later prompt rendering. |
| request_detectors_and_mvp_override_block | 333-406 | 74 | no | Derives request-shape booleans from policy plus lexical detectors, computes `rich_user_request`, and constructs the MVP override text block. | Mixed but still helper-friendly: detector booleans are pure, MVP override block is formatting-only. |
| writer_kb_payload_and_trace_capture | 407-453 | 47 | yes | Formats `writer_kb_payload_text`, normalizes fallback reason, and copies several payload/trace structures into `self.last_debug` before prompt assembly. | Not pure as-is because it mutates `self.last_debug`; could move behind a stateful helper or return a debug patch dict. |
| writer_user_template_render_core | 454-611 | 158 | no | First half of `WRITER_USER_TEMPLATE.format(...)`: core thread state, governance, context budget, KB payload, philosophy kernel, freedom contract, and final-answer directive wiring. | Too large for one cut; split by template responsibility groups before moving. |
| writer_user_template_render_runtime_tail | 612-842 | 231 | no | Second half of `WRITER_USER_TEMPLATE.format(...)`: fresh-chat policy, writer-context package, active line, planner, pragmatics, retrieval, human-like policy, shape profile, and constraint-resolution fields. | Likely later extraction target after core render arguments are grouped into named builder helpers. |
| prompt_constraint_append_and_debug_bookkeeping | 843-891 | 49 | yes | Builds the optional prompt-constraint section, appends it to `user_prompt`, and records prompt/context/policy diagnostics in `self.last_debug`. | State-coupled cluster; candidate for a helper returning `(user_prompt, debug_patch)`. |
| runtime_settings_and_system_prompt_selection | 892-901 | 10 | yes | Starts timing, re-normalizes dialogue profile, resolves runtime settings, chooses the system prompt, and stores the final prompt mode in debug. | Small, isolated, and a strong early candidate for APPLY-7 after mapping review. |
| provider_dispatch | 902-912 | 11 | no | Single provider call through `create_agent_completion(...)` using the assembled prompts and runtime settings. | Keep separate. Explicitly deferred by this PRD and the previous recommendation. |
| response_unpack_cost_and_return | 913-938 | 26 | yes | Unpacks `AgentLLMResult`, estimates cost, computes duration, patches `self.last_debug`, and returns `llm_response`. | Provider-response parsing should be a later dedicated slice, not merged with prompt preparation. |

## Immediate Apply-7 Reading

- Safest early extraction edge is not the provider call itself; it is the small pre-dispatch runtime block at `892-901` plus selected pure detector/default-formatting helpers earlier in the method.
- The largest single concentration of responsibility remains `WRITER_USER_TEMPLATE.format(...)` at `454-842`; this block should be decomposed by argument-family builders, not by one giant move.
- The first clearly state-coupled preparation cluster begins at `407-453`, where prompt preparation starts writing directly into `self.last_debug`.
