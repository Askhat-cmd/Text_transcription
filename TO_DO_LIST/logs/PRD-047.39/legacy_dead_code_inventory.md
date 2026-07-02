# PRD-047.39 Legacy Dead-Code Inventory

| Component | Kind | Import graph status | Active refs | Test refs | Docs/log refs | Classification |
| --- | --- | --- | --- | --- | --- | --- |
| answer_basic | retired_pipeline | referenced_by_test_only | 0 | 12 | 0 | dead_confirmed |
| answer_sag_aware | retired_pipeline | referenced_by_test_only | 0 | 4 | 0 | dead_confirmed |
| answer_graph_powered | retired_pipeline | referenced_by_test_only | 0 | 4 | 0 | dead_confirmed |
| sd_classifier | retired_sd_module | referenced_by_test_only | 0 | 49 | 0 | dead_confirmed |
| user_level_adapter | retired_level_module | referenced_by_active_path | 7 | 22 | 1 | unclear_needs_trace |
| prompt_sd_green | retired_prompt | referenced_by_test_only | 0 | 3 | 0 | dead_confirmed |
| prompt_sd_blue | retired_prompt | referenced_by_test_only | 0 | 3 | 0 | dead_confirmed |
| prompt_sd_red | retired_prompt | referenced_by_test_only | 0 | 3 | 0 | dead_confirmed |
| prompt_sd_orange | retired_prompt | referenced_by_test_only | 0 | 3 | 0 | dead_confirmed |
| prompt_sd_yellow | retired_prompt | referenced_by_test_only | 0 | 3 | 0 | dead_confirmed |
| prompt_sd_purple | retired_prompt | referenced_by_test_only | 0 | 3 | 0 | dead_confirmed |
| prompt_system_level_beginner | retired_prompt | referenced_by_test_only | 0 | 5 | 0 | dead_confirmed |
| prompt_system_level_intermediate | retired_prompt | referenced_by_test_only | 0 | 5 | 0 | dead_confirmed |
| prompt_system_level_advanced | retired_prompt | referenced_by_test_only | 0 | 5 | 0 | dead_confirmed |

## Evidence Notes
- `dead_confirmed` here means no active runtime-path reference was found by git-grep.
- This PRD does not delete any active runtime modules; removal candidates move to PRD-047.40.
