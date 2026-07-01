# PRD-047.36-HF4 Live Smoke Report

Date: 2026-07-01
Verdict: `PASS`

## Runtime health
- Frontend: `200`
- Backend health after restart: `200 healthy`

## Scenario summary
- Scenario A fresh 5-turn chat: `PASS`
- Scenario B reload same fresh 5-turn chat: `PASS`
- Scenario C old session after restart with precise expired reason: `PASS`
- Scenario D new chat after restart: `PASS`
- Scenario E reload same new post-restart chat: `PASS`

## Honest bounded note
- Full `python -m pytest tests/test_final_answer_acceptance_gate_v1.py tests/multiagent/test_writer_agent.py -q` still fails on old unrelated `test_semantic_hits_limit_to_two`.
