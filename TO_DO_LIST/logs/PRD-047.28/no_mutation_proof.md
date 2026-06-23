# PRD-047.28 No Mutation Proof

- status: `pre_push_verified_post_push_pending`
- prd: `PRD-047.28`
- runtime_result: `BLOCKED`

## Scope Boundary

- Production runtime entrypoint was not changed.
- Web chat/manual production route was not switched to thin spine.
- DB/Chroma/registry were not mutated.
- Semantic cards were not expanded.
- Overlay apply was not enabled.
- Existing config defaults were not changed.
- Experiment files stay isolated under `bot_psychologist/bot_agent/experiments`, `bot_psychologist/tools`, `bot_psychologist/tests`, `TO_DO_LIST/fixtures/PRD-047.28`, and `TO_DO_LIST/logs/PRD-047.28`.

## Key Production Diff Check

Command:

```powershell
git diff -- bot_psychologist\api\main.py bot_psychologist\api\routes\chat.py bot_psychologist\bot_agent\multiagent\runtime_adapter.py bot_psychologist\bot_agent\multiagent\orchestrator.py bot_psychologist\bot_agent\multiagent\agents\writer_agent.py bot_psychologist\bot_agent\multiagent\writer_kb_payload.py bot_psychologist\bot_agent\multiagent\retrieval_query_builder.py bot_psychologist\bot_agent\multiagent\overlay_shadow_trace.py
```

Result:

```text
no diff output
```

Interpretation:

- Canonical API/runtime entrypoints and current production retrieval/Writer/overlay files remain untouched in this PRD branch state.

## Git Working Tree Snapshot Before Main Commit

Command:

```powershell
git status --short
```

Observed state:

```text
 D TO_DO_LIST/PRD-047.27-HF2_TASK_LIST.md
 ?? TO_DO_LIST/PRD-047.28_TASK_LIST.md
 ?? TO_DO_LIST/PRD-047.28_Thin_Spine_Live_Prompt_Experiment_RU.md
 ?? TO_DO_LIST/fixtures/
 ?? TO_DO_LIST/logs/PRD-047.28/
 ?? bot_psychologist/bot_agent/experiments/
 ?? bot_psychologist/tests/test_prd_047_28_case_loader.py
 ?? bot_psychologist/tests/test_prd_047_28_live_turn_note.py
 ?? bot_psychologist/tests/test_prd_047_28_runner_mock_mode.py
 ?? bot_psychologist/tests/test_prd_047_28_thin_context_and_safety.py
 ?? bot_psychologist/tools/prd_047_28_thin_spine_experiment.py
```

Notes:

- The tracked deletion of `TO_DO_LIST/PRD-047.27-HF2_TASK_LIST.md` pre-existed in the worktree and is not part of the thin-spine production runtime.
- All new PRD-047.28 code paths are isolated experiment/tests/docs/task artifacts.

## Diff Stat Snapshot Before Staging

Command:

```powershell
git diff --stat
```

Observed output:

```text
TO_DO_LIST/PRD-047.27-HF2_TASK_LIST.md | 38 ----------------------------------
1 file changed, 38 deletions(-)
```

Interpretation:

- `git diff --stat` only reports tracked-file changes before staging; the experiment additions were still untracked at this proof point.
- No tracked production runtime file diff appeared in this snapshot.

## Test Evidence

Targeted PRD tests:

```powershell
.venv\Scripts\python.exe -m pytest tests\test_prd_047_28_case_loader.py tests\test_prd_047_28_live_turn_note.py tests\test_prd_047_28_thin_context_and_safety.py tests\test_prd_047_28_runner_mock_mode.py -q
```

Result:

```text
8 passed in 0.40s
```

Relevant regression subset:

```powershell
.venv\Scripts\python.exe -m pytest tests\test_retrieval_query_builder_current_turn_focus.py tests\multiagent\test_writer_kb_payload.py tests\multiagent\test_overlay_shadow_trace.py -q
```

Result:

```text
20 passed in 0.37s
```

Full suite attempt:

```powershell
$env:TEMP='c:\My_practice\Text_transcription\bot_psychologist\.tmp_pytest'; $env:TMP=$env:TEMP; .venv\Scripts\python.exe -m pytest tests -q
```

Result:

```text
blocked during collection: ImportError in tests/regression/test_no_sd_required_by_response_flow.py
missing symbol: _build_llm_prompts from bot_agent.answer_adaptive
```

Interpretation:

- The full suite is not green for an existing unrelated regression/import issue outside PRD-047.28 scope.

## Live Experiment Evidence

Command:

```powershell
.venv\Scripts\python.exe tools\prd_047_28_thin_spine_experiment.py --variant all --include-kb --include-live-turn-note
```

Result:

```text
final_status=BLOCKED
case_count=10
variant_count=3
live_llm_available=true
rows=30
```

Additional note:

- The rerun after runner refactor completed without the earlier `Event loop is closed` teardown noise.

## Pending Post-Push Verification

- implementation_commit: `PENDING_MAIN_COMMIT`
- metadata_commit: `PENDING_METADATA_COMMIT`
- `HEAD == origin/main`: pending
- clean working tree after metadata micro-push: pending
