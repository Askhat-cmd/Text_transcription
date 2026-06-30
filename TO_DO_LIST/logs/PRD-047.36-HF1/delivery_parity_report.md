# Delivery Parity Report

## Repair
- SSE `done` payload now carries `turn_number`.
- Backend debug trace and history response now expose the same turn identity.
- Frontend bot messages store `turnNumber` from delivery metadata instead of relying on local positional reconstruction.

## Outcome
- `user_message -> API answer -> visible bubble -> saved history -> reload` now shares the same explicit turn key.
- This closes the bounded parity gap that previously let visible benign turns vanish from reloaded history.
