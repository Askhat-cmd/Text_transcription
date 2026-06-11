# PRD-047.15-HF2-R2 Admin Screenshots Manifest

## Found screenshots

- `image.png`
  - top-level Admin navigation
  - evidence:
    - primary tabs are active
    - `Advanced Controls` exists as a second navigation lane
- `image (4).png`
  - Agent Prompts screen
  - evidence:
    - top-level dedicated screen already exists for prompts
- `image (8).png`
  - `Advanced Controls -> LLM`
  - evidence:
    - duplicate control surface separate from main runtime/admin cards
- `image (10).png`
  - `Advanced Controls` dropdown
  - evidence:
    - sub-tabs `LLM / Retrieval / Diagnostics / Routing / Prompts / Compatibility`
- `image (14).png`
  - Runtime screen
  - evidence:
    - visible editable dialogue profile selector with `mvp_free_dialogue`
    - visible editable `Knowledge Graph` checkbox
    - no visible Hybrid Retrieval Planner block

## Controls classification

### Active primary UI

- Overview
- Agents
- Orchestrator
- Threads
- Agent Prompts
- Runtime
- Diagnostic Center
- Memory

### Advanced / legacy / duplicate UI

- `Advanced Controls -> LLM`
- `Advanced Controls -> Retrieval`
- `Advanced Controls -> Diagnostics`
- `Advanced Controls -> Routing`
- `Advanced Controls -> Prompts`
- `Advanced Controls -> Compatibility`

## HF2-R2 decisions from screenshot evidence + source proof

- hide duplicate sub-tabs `LLM / Retrieval / Diagnostics / Routing / Prompts` from primary admin UI
- keep `Compatibility` as the only read-only legacy surface
- stop presenting raw dialogue profile alias and raw knowledge-graph toggle as active Runtime controls
- add visible read-only Hybrid Retrieval Planner block into Runtime

## Elements that must not be mutated blindly

- backend runtime config keys
- diagnostic center control semantics
- retrieval planner logic
- writer authority
