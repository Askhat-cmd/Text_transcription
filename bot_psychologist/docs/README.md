# Bot Psychologist Docs Index (Индекс документации Bot Psychologist)

- status: current
- last_verified_prd: PRD-047.13-HF1
- source_of_truth: docs/PROJECT_STATE.md; docs/PRD_INDEX.md; /api/admin/runtime/effective
- active_now: true
- not_production_ready: true
- related_artifacts: TO_DO_LIST/logs/PRD-047.13-HF1; TO_DO_LIST/reports/PRD-047.13-HF1_IMPLEMENTATION_REPORT.md
- verification_scope: cleanup-only inventory, documentation truth sync, no runtime behavior changes

Этот индекс разделяет актуальную runtime-документацию и исторические артефакты. Считайте файлы ниже текущей документационной поверхностью, пока более поздний PRD не обновит этот индекс.

## Current Sources Of Truth (Актуальные источники правды)

- `docs/PROJECT_STATE.md` — текущее состояние репозитория и статус PRD.
- `docs/PRD_INDEX.md` — индекс acceptance и implementation по PRD.
- `docs/ROADMAP.md` — текущий roadmap и направление следующего PRD.
- `bot_psychologist/docs/PROJECT_STATUS_CURRENT.md` — краткая сводка статуса bot runtime.
- `/api/admin/runtime/effective` — effective runtime policy и admin-visible configuration.

## Living Runtime Docs (Актуальная runtime-документация)

- `ARCHITECTURE_CURRENT.md` — границы текущей multiagent architecture.
- `UNIFIED_DIALOGUE_POLICY_V2.md` — unified dialogue policy v2 и порядок authority.
- `RUNTIME_PROFILES_AND_PRESETS.md` — поведение runtime profile и preset.
- `FINAL_ANSWER_ACCEPTANCE_GATE.md` — contract final answer acceptance gate.
- `NO_STUB_DIALOGUE_POLICY.md` — no-stub runtime policy.
- `REAL_LIVE_ACCEPTANCE_PROTOCOL.md` — протокол real live acceptance.
- `WEB_CHAT_MARKDOWN_RENDERING.md` — contract Web Chat markdown rendering.
- `DIAGNOSTIC_CENTER_BOUNDARY.md` — границы Diagnostic Center и лимиты observability.

## Admin And Observability Docs (Документация admin и observability)

- `ADMIN_RUNTIME_EFFECTIVE.md` — contract Admin Runtime effective payload.
- `ADMIN_PROMPTS_READINESS_MAP.md` — admin prompt readiness map.
- `DIAGNOSTIC_CENTER_ADMIN_CONTROL.md` — документация admin control Diagnostic Center.
- `RUNTIME_DRIFT_GUARD.md` — заметки observability-first drift guard.
- `LIVE_USER_TESTING_PROTOCOL.md` — протокол guided live testing.

## Historical Or Reference Docs (Исторические и справочные документы)

Исторические документы, migration notes, PRD-артефакты, старые generated reports и archived evidence — только для справки. Они не должны перекрывать living runtime docs или Admin Runtime effective payload.

## How To Test (Как тестировать)

- Запустите targeted backend regression из `TO_DO_LIST/logs/PRD-047.13-HF1/test_command_output.txt`.
- Запустите `npm run build` из `bot_psychologist/web_ui`.
- Проверьте текущую effective policy через `/api/admin/runtime/effective`.

## PRD-047.13 Cleanup Boundary (Граница cleanup PRD-047.13)

PRD-047.13-HF1 закрывает шум documentation и artifact cleanup после PRD-047.13. Он не меняет Writer, Orchestrator, Dialogue Act, RAG, Chroma retrieval, authority Diagnostic Center, Web Chat runtime behavior или safety policy.

Текущие флаги остаются developer-local:

- `mvp_free_dialogue`: только developer-local.
- `production_rollout`: false.
- `normal_user_activation`: false.

Рекомендуемая следующая задача:

- `PRD-047.14` — Live Dialogue Quality Polish / Human Reference Calibration v1.
