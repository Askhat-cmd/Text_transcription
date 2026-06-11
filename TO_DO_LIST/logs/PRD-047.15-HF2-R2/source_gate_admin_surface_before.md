# PRD-047.15-HF2-R2 Admin Surface Before

## Source proof bundle

- owner screenshots from `TO_DO_LIST/context/СКРИНЫ ВЕБ АДМИНКИ/`
- code grep in `web_ui/src/components/admin/AdminPanel.tsx`
- backend runtime payload builder in `api/admin_routes.py`

## Current primary surfaces

- top-level tabs:
  - `Overview`
  - `Agents`
  - `Orchestrator`
  - `Threads`
  - `Agent Prompts`
  - `Runtime`
  - `Diagnostic Center`
  - `Memory`

## Current duplicate / noisy surfaces

- `Advanced Controls` dropdown exposes:
  - `LLM`
  - `Retrieval`
  - `Diagnostics`
  - `Routing`
  - `Prompts`
  - `Compatibility`
- these overlap with already active top-level surfaces and create a second admin center

## Runtime tab problems before HF2-R2

- editable raw `runtime` config panel is shown before effective cards
- owner screenshot confirms visible active controls:
  - `mvp_free_dialogue` profile selector
  - `Knowledge Graph` checkbox
- no visible read-only Hybrid Retrieval Planner card

## HF2-R2 cleanup target

- keep Runtime as observability-first effective surface
- remove duplicate legacy/stale advanced sub-tabs from primary UI
- preserve `Compatibility` as the only read-only legacy lane
- move legacy runtime status explanations into Compatibility
- do not delete backend config; only hide/reframe stale controls in primary UI
