# Admin Configurability Audit

required runtime fields:
- writer_first_prompt_assembly_enabled: `present`
- final_answer_directive_enabled: `present`
- legacy_blocks_visible_to_writer: `missing`
- legacy_blocks_source_signals_only: `missing`
- diagnostic_center_role: `present`
- planner_role: `present`
- active_line_role: `present`

screenshot proof:
- admin_runtime_effective.png: `missing`
- admin_prompts_writer.png: `missing`
- admin_diagnostic_center.png: `missing`

Notes:
- `admin_effective_payload.json` confirms `profile=mvp_free_dialogue`, `final_answer_directive_enabled=true`, `writer_first_prompt_assembly_enabled=true`.
- Screenshot proof is absent because the local environment did not have Playwright available for browser automation.
- The audit therefore remains `warning`, not `passed`, even though the runtime payload itself is reachable.
