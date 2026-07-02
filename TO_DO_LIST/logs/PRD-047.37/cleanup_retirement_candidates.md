# PRD-047.37 Cleanup / Retirement Candidates

Date: 2026-07-02
Status: `candidate_backlog_only`

No deletion is performed in PRD-047.37. Each item below requires a later cleanup PRD with evidence and rollback plan.

| Component / Path | Current Role | Why It May Be Redundant Or Noisy | Risk If Removed | Proof Needed Before Removal | Recommended Future PRD |
| --- | --- | --- | --- | --- | --- |
| Legacy fallback paths around static repair text | Compatibility / quarantine fallback residue | Can confuse Writer authorship and no-stub boundary | Removing active safety/minimal-contact fallback could break guarded cases | Active path inventory plus final-answer exposure proof | Cleanup Pass 1 - no-stub/fallback inventory |
| Shadow-only planner artifacts | Developer observability | Invalid/noisy JSON may look like production failure | Removing trace fields can hide useful debugging | Trace samples proving `production_answer_affected=false` and no active dependency | Cleanup Pass 1 - shadow planner trace hygiene |
| Duplicate trace labels in Web UI / debug payload | Owner/developer observability | Multiple labels for candidates/payload/boundaries increase confusion | UI regression or loss of exact trace proof | Screenshot/API contract proof before/after | Cleanup Pass 1 - trace label normalization |
| Old reports/log naming inconsistencies | Historical evidence archive | Harder source gates and transfer briefs | Renaming can break historical links and PRD references | Link map and redirect/manifest if files move | Docs/log hygiene PRD |
| Stale PRD drafts / old task lists | Historical project memory | Makes current stage hard to identify | Accidental deletion of evidence | Archive manifest and PRD index cross-check | Archive hygiene PRD |
| Compatibility code no longer used | Backward compatibility | Adds cognitive load and hidden branch risk | Could still support tests/admin/legacy sessions | Runtime import/call graph and coverage proof | Compatibility retirement PRD |
| Old UI trace projection remnants | Owner debug UI | Can render misleading counters or stale labels | Trace UI may lose important diagnostics | Owner/browser proof with sample traces | Web Trace projection cleanup PRD |
| Ignored local artifacts / logs / restart files | Local development residue | Can confuse git status and no-mutation proof | Deleting active local runtime files can disrupt running servers | `.gitignore` audit and path-by-path classification | Local artifact hygiene PRD |
| Exact strategic docs missing at root but present in context/archive | Documentation topology | Source gates ask for paths that are absent | Moving/copying private/context docs can expose unwanted material | Inventory of public vs private docs and owner approval for relocations | Strategic docs normalization PRD |
| Historical full-suite `_build_llm_prompts` blocker | Test debt | Prevents full pytest confidence | Fixing casually may reopen old prompt path | Reproduce/import graph audit and targeted migration plan | Historical test debt PRD |

## Retirement Discipline
Do not delete major runtime code in a freeze PRD. A future cleanup PRD must prove that a candidate is inactive or safely replaceable, include rollback steps, and preserve trace/debug visibility where it affects owner evidence.
