# PRD-047.36-HF4 Trace Persistence Coverage Report

Date: 2026-07-01

## Fresh 5-turn chat before backend restart
- `delivered_turn_numbers = [1, 2, 3, 4, 5]`
- `saved_history_turn_numbers = [1, 2, 3, 4, 5]`
- `stored_debug_turn_indices = [1, 2, 3, 4, 5]`
- `available_turn_indices = [1, 2, 3, 4, 5]`
- `trace_endpoint_turns_ok = [1, 2, 3, 4, 5]`
- `trace_unavailable_count = 0`
- `requested_turn_missing_count = 0`

## Fresh new chat after backend restart
- `delivered_turn_numbers = [1, 2]`
- `saved_history_turn_numbers = [1, 2]`
- `stored_debug_turn_indices = [1, 2]`
- `available_turn_indices = [1, 2]`
- `trace_endpoint_turns_ok = [1, 2]`
- `trace_unavailable_count = 0`
- `requested_turn_missing_count = 0`

## Conclusion
- HF4 closed the incomplete-turn-set class for fresh delivered chats.
