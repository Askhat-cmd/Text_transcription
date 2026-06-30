# Live Smoke Report

## Runtime Checks
- `GET http://127.0.0.1:8001/api/v1/health` -> `healthy`
- `GET http://localhost:3000` -> `200`
- `GET http://localhost:3000/chat` -> `200`

## Scope Note
- This HF1 smoke verified live service availability and the repaired delivery surfaces.
- A full owner multi-turn replay was not rerun inside this HF1 microcycle; the next recommended step is to rerun the frozen readiness gate on top of the repaired pipeline.
