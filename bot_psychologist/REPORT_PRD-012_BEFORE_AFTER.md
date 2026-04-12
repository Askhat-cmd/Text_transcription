# PRD-012 Before and After Report

Date: 2026-04-12
Scope: `bot_psychologist/`

## Before

- Trace payload mixed active fields with outdated compatibility fields.
- Web trace surface showed mixed terminology and extra operator noise.
- Admin routing controls exposed non-active runtime toggles.
- Runtime config editable map included outdated routing and prompt keys.
- README and docs still described inactive architecture branches.

## After

- API trace contract is unified as `trace_contract_version = "v2"`.
- Trace read path sanitizes old fields before UI/debug exposure.
- Web trace status bar uses fixed Neo chip set:
  `MODE`, `STATE`, `RULE`, `CHUNKS`, `HITS`, `TOKENS`, `LLM`, `WARN`.
- LLM canvas remains developer-only and collapsed by default.
- Admin routing tab and config payloads expose only active Neo controls.
- Runtime config editable surface no longer includes outdated routing/prompt keys.
- Retrieval evaluation scripts no longer pass removed routing arguments.
- README and core docs are rewritten to Neo-only runtime guidance.

## Validation Evidence

### Automated

- Backend/UI/inventory/regression suite:

```powershell
pytest tests/contract tests/ui tests/inventory tests/regression/test_no_sd_runtime_metadata_fields.py tests/regression/test_trace_reflects_real_execution_only.py tests/regression/test_streaming_sd_runtime_disabled_contract.py tests/test_llm_payload_endpoint.py tests/test_sse_payload.py -q
```

- Frontend quality checks:

```powershell
cd web_ui
npm run lint
npm run build
```

### Static checks

- Docs and sample config cleanup check:

```powershell
rg -n -i "sd_|\bsd\b|user_level_adapter|decision_gate|prompt_sd_|DISABLE_SD_RUNTIME|DISABLE_USER_LEVEL_ADAPTER|ENABLE_FAST_SD_DETECTOR|PROMPT_MODE_OVERRIDES_SD|PROMPT_SD_OVERRIDES_BASE" README.md docs .env.example
```

Result: no matches.

## Residual Items

- Commit and push are intentionally pending user confirmation.
