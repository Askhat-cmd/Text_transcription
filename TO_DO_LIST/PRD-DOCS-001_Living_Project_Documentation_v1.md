# PRD-DOCS-001 — Living Project Documentation v1

## 0. Назначение PRD

Создать в репозитории верхнеуровневый слой “живой” проектной документации, который позволит быстро понять текущее состояние Bot Psychologist / Neo MindBot без чтения десятков PRD, reports и logs.

Этот PRD **не меняет runtime**. Он создаёт навигационный слой над уже накопленным `TO_DO_LIST`.

---

## 1. Контекст

В проекте уже выполнено много последовательных PRD:

- multiagent runtime;
- State Analyzer calibration;
- Thread Manager diagnostics;
- Context Assembly и deterministic turn micro-summary;
- Diagnostic Card contract;
- Writer Move Compliance;
- Knowledge Governance;
- Chroma/API retrieval restore;
- Offline LLM KB enrichment pipeline;
- real LLM enrichment calibration chain.

`TO_DO_LIST`, `reports` и `logs` остаются главным рабочим архивом операций. Но сейчас их уже недостаточно как единой карты состояния: чтобы понять “где бот сейчас”, нужно читать слишком много разрозненных файлов.

Также после `PRD-046.0.5-RUN1-HF3` появился важный переходный момент:

```text
KB enrichment real batch:
- hard validation passed;
- production candidate ready;
- promotion still requires separate apply PRD.
```

Перед следующим apply/reindex и дальнейшими слоями полезно зафиксировать архитектурную карту, дорожную карту и правила обновления документации.

---

## 2. Цель

Создать папку `docs/` с компактной живой документацией:

```text
docs/
  PROJECT_STATE.md
  ARCHITECTURE_OVERVIEW.md
  ROADMAP.md
  DECISIONS.md
  PRD_INDEX.md
```

Документация должна отвечать на вопросы:

- в какой стадии разработки находится бот;
- какая архитектура сейчас актуальна;
- какие PRD завершены;
- что stable / experimental / in progress;
- какие риски известны;
- какой следующий этап;
- что нельзя делать преждевременно;
- какие архитектурные решения уже приняты и не должны случайно нарушаться.

---

## 3. Главный принцип

```text
TO_DO_LIST = операционный архив деталей.
docs/ = верхнеуровневая карта состояния проекта.
```

Не превращать `docs/` в огромную энциклопедию. Документы должны быть читаемыми, поддерживаемыми и полезными для:

- владельца проекта;
- архитектурного агента;
- IDE-агента;
- будущего нового чата;
- быстрой проверки текущей стадии.

---

## 4. Scope

### 4.1 Workstream A — Report hygiene / текущий хвост HF3

Перед созданием общей документации IDE-агент должен проверить и при необходимости поправить отчётные артефакты последнего PRD `PRD-046.0.5-RUN1-HF3`.

Минимально:

1. Проверить:
   - `TO_DO_LIST/reports/PRD-046.0.5-RUN1-HF3_IMPLEMENTATION_REPORT.md`
   - `TO_DO_LIST/reports/PRD-046.0.5-RUN1-HF3_CALIBRATION_REPORT.md`
   - `TO_DO_LIST/reports/PRD-046.0.5-RUN1-HF3_OVERLAY_READINESS_REPORT.md`
   - `TO_DO_LIST/reports/PRD-046.0.5-RUN1-HF3_REAL_LLM_ENRICHMENT_REPORT.md`
   - `TO_DO_LIST/reports/PRD-046.0.5-RUN1-HF3_NEXT_PRD_RECOMMENDATION.md`

2. Убедиться, что в этих файлах нет:
   - PowerShell interpolation artifacts вида `$(@{...})`;
   - `System.Object[]`;
   - `filled_after_commit`;
   - `filled_after_push`;
   - пустых отчётов;
   - невалидной рекомендации следующего PRD.

3. Если такие дефекты есть — исправить только отчётные `.md` файлы, не меняя runtime и enrichment data.

Ожидаемая содержательная фиксация:

```text
PRD-046.0.5-RUN1-HF3:
- hard validation passed: 60/60;
- validation_failed: 0;
- hard_validation_failed: 0;
- production_candidate_ready: true;
- promotion_allowed: false;
- promotion reason: requires_separate_apply_prd;
- next technical KB step after documentation: PRD-046.0.5-APPLY1 — Apply Real LLM Enrichment Overlay + Chroma Refresh v1.
```

---

## 5. Требуемые документы

### 5.1 `docs/PROJECT_STATE.md`

Главный документ “где проект сейчас”.

Обязательные разделы:

```text
# Project State — Bot Psychologist / Neo MindBot

## Current Stage
## Current Runtime Architecture
## Current Knowledge Base State
## Current Context / Memory State
## Current LLM Enrichment State
## Stable Modules
## Experimental / In Progress Modules
## Not Implemented Yet
## Known Risks
## Next Planned PRDs
## Do Not Do Yet
## Last Updated
```

Нужно отразить:

- проект использует multiagent-only runtime;
- active pipeline:
  ```text
  User message
  → State Analyzer
  → Thread Manager
  → Memory Retrieval
  → Context Assembly
  → Diagnostic Card
  → Writer Move Compliance
  → Writer
  → Validator / Trace
  → Memory Update
  ```
- Context Assembly есть, но turn micro-summary пока deterministic/extractive;
- Async Turn LLM Summary Store запланирован, но ещё не внедрён;
- Diagnostic Center v1 ещё не стартует;
- Knowledge Base governance готов;
- Chroma/API retrieval восстановлен;
- real LLM enrichment batch стал production candidate после HF3, но ещё не applied;
- enriched overlay не должен быть promoted без отдельного apply PRD;
- `КУЗНИЦА ДУХА` используется как внутренняя линза, не как цитатник;
- `Neo MindBot КОНСПЕКТ` — internal architecture/style material, не обычный user-facing knowledge source.

---

### 5.2 `docs/ARCHITECTURE_OVERVIEW.md`

Понятное описание текущей архитектуры.

Обязательные разделы:

```text
# Architecture Overview

## High-Level Flow
## State Analyzer
## Thread Manager
## Memory Retrieval
## Context Assembly
## Diagnostic Card
## Writer Move Compliance
## Writer
## Validator / Quality Trace
## Knowledge Base / RAG
## Memory Update
## Planned: Async Turn LLM Summary
## Planned: Diagnostic Center
```

Нужно описать простым техническим языком:

- за что отвечает каждый слой;
- какие данные он получает;
- что отдаёт дальше;
- какие trace/debug поля важны;
- где находится Knowledge Base / RAG;
- что делает governance policy;
- почему Writer не должен быть всей диагностической системой;
- почему Diagnostic Center пока не включён.

Добавить схему:

```text
User Message
  ↓
State Analyzer
  ↓
Thread Manager
  ↓
Memory Retrieval
  ↓
Context Assembly
  ↓
Diagnostic Card
  ↓
Writer Move Compliance
  ↓
Writer
  ↓
Validator / Quality Trace
  ↓
Memory Update
```

---

### 5.3 `docs/ROADMAP.md`

Живая дорожная карта.

Обязательные разделы:

```text
# Roadmap

## Done
## Current / In Progress
## Next
## Later
## Deferred / Not Yet
## Roadmap Rules
```

Нужно отразить текущий порядок:

```text
DONE:
- PRD-045.x runtime quality/multiagent/context/diagnostic-card foundation
- PRD-046.0.x knowledge governance and Chroma/API retrieval restore
- PRD-046.0.5 pipeline + real LLM enrichment calibration up to production candidate

CURRENT:
- documentation consolidation

NEXT:
- PRD-046.0.5-APPLY1 — Apply Real LLM Enrichment Overlay + Chroma Refresh v1
- PRD-045.6.3 — Async Turn LLM Summary Store v1
- PRD-046.0.6 — Knowledge Retrieval Eval Set v1
- PRD-046.0.7 — Admin Review Workflow v1

LATER:
- Diagnostic Center v1
- Planner-lite
- production hardening
```

Важно: Async Turn LLM Summary должен появиться **до активного усиления runtime через enriched KB и до Diagnostic Center**, чтобы knowledge context не вытеснил живой recent dialogue context.

---

### 5.4 `docs/DECISIONS.md`

Журнал архитектурных решений в простом ADR-style формате.

Пример структуры:

```text
# Architecture Decisions

## ADR-001 — Multiagent-only runtime
Status: accepted
Context:
Decision:
Consequences:

## ADR-002 — Writer is not the whole diagnostic system
...

## ADR-003 — Knowledge Base is an internal lens library, not a quote source
...

## ADR-004 — Governance/safety are deterministic authority; LLM enrichment is advisory
...

## ADR-005 — Raw dialogue history is preserved; summaries are additive
...

## ADR-006 — Turn LLM summaries must be async with deterministic fallback
...

## ADR-007 — Diagnostic Center waits for governed KB, retrieval quality and context quality
...
```

Обязательные решения для фиксации:

- отказ от cascade runtime в пользу multiagent-only;
- Writer не должен сам выполнять всю диагностику;
- Context Assembly собирает управляемый context package вместо “всё в prompt”;
- Knowledge Base — библиотека линз/практик, не цитатник;
- `КУЗНИЦА ДУХА` не цитируется напрямую пользователю;
- LLM enrichment не заменяет deterministic governance/safety;
- raw history always preserved;
- turn LLM summaries должны быть async + fallback;
- enriched KB не должна вытеснять живой recent context;
- Diagnostic Center не стартует до KB/retrieval/context readiness.

---

### 5.5 `docs/PRD_INDEX.md`

Индекс PRD.

Формат таблицы:

```markdown
| PRD | Название | Статус | Commit | Что изменило | Отчёт |
| --- | --- | --- | --- | --- | --- |
```

Не нужно идеально восстанавливать каждый commit для старых PRD, если это потребует большого ручного расследования. Но нужно зафиксировать основные этапы:

- `PRD-045.0`–`PRD-045.7.1`;
- `PRD-046.0`–`PRD-046.0.5`;
- `PRD-046.0.5-HF1`;
- `PRD-046.0.5-RUN1`;
- `PRD-046.0.5-RUN1-HF2`;
- `PRD-046.0.5-RUN1-HF3`;
- этот `PRD-DOCS-001`.

Для PRD, где commit точно известен из reports, указать commit short hash. Для старых PRD допустимо `see report` или `historical`.

Также добавить правило:

```text
Каждый новый PRD обязан по возможности обновлять:
- docs/PRD_INDEX.md всегда;
- docs/PROJECT_STATE.md, если изменился статус проекта;
- docs/ROADMAP.md, если изменилась дорожная карта;
- docs/DECISIONS.md, если принято архитектурное решение.
```

---

## 6. Documentation update policy

Создать раздел в `docs/PROJECT_STATE.md` или отдельный блок в `docs/PRD_INDEX.md`:

```text
Documentation update rule:
1. Любой PRD, который меняет архитектурный статус, должен обновлять docs/PROJECT_STATE.md.
2. Любой PRD, который меняет последовательность работ, должен обновлять docs/ROADMAP.md.
3. Любой PRD, который принимает новое архитектурное решение, должен обновлять docs/DECISIONS.md.
4. Любой PRD после merge/push должен добавлять/обновлять строку в docs/PRD_INDEX.md.
5. TO_DO_LIST остаётся архивом полных reports/logs; docs/ — краткая карта.
```

---

## 7. Non-goals

В этом PRD запрещено:

- менять runtime behavior;
- менять Writer;
- менять State Analyzer;
- менять Thread Manager;
- менять DiagnosticCard;
- менять Memory Retrieval;
- менять Context Assembly;
- менять Knowledge Base pipeline;
- применять LLM enrichment overlay к production blocks;
- делать Chroma reindex;
- запускать Diagnostic Center;
- внедрять Async Turn LLM Summary;
- менять Web UI;
- удалять или переписывать `TO_DO_LIST`.

---

## 8. Acceptance Criteria

PRD считается выполненным, если:

1. Создана папка `docs/`.
2. Созданы файлы:
   - `docs/PROJECT_STATE.md`
   - `docs/ARCHITECTURE_OVERVIEW.md`
   - `docs/ROADMAP.md`
   - `docs/DECISIONS.md`
   - `docs/PRD_INDEX.md`
3. Документы читаемые, не пустые, не являются dump’ом всех PRD.
4. В `PROJECT_STATE.md` отражено:
   - current stage;
   - active runtime pipeline;
   - KB governance / Chroma / LLM enrichment status;
   - Async Turn LLM Summary planned;
   - Diagnostic Center deferred.
5. В `ROADMAP.md` есть актуальная последовательность:
   - docs;
   - enrichment overlay apply;
   - async turn summary;
   - retrieval eval;
   - admin review;
   - diagnostic center.
6. В `DECISIONS.md` есть минимум 7 ADR-style решений.
7. В `PRD_INDEX.md` есть таблица по основным PRD.
8. Исправлены явные report hygiene дефекты HF3, если они есть.
9. Нет runtime changes.
10. Нет секретов, raw full chunk text, `.env`, sqlite/db/cache, `.venv`, `node_modules`.
11. Созданы task list, implementation report и logs.
12. Сделан commit и push в `main`.
13. Implementation report обновлён после финального push с commit hash и push status.

---

## 9. Required artifacts

Создать:

```text
TO_DO_LIST/PRD-DOCS-001_TASK_LIST.md
TO_DO_LIST/reports/PRD-DOCS-001_IMPLEMENTATION_REPORT.md
TO_DO_LIST/reports/PRD-DOCS-001_DOCS_CHECK_REPORT.md
TO_DO_LIST/logs/PRD-DOCS-001/test_command_output.txt
TO_DO_LIST/logs/PRD-DOCS-001/sanitized_runtime_logs.txt
```

Опционально:

```text
TO_DO_LIST/logs/PRD-DOCS-001/docs_file_inventory.json
TO_DO_LIST/logs/PRD-DOCS-001/docs_link_check.json
```

---

## 10. Suggested checks

Так как runtime не меняется, runtime tests не обязательны. Но нужно выполнить documentation checks.

Минимальный набор:

```bash
git status --short
git diff --stat
python - <<'PY'
from pathlib import Path
required = [
    "docs/PROJECT_STATE.md",
    "docs/ARCHITECTURE_OVERVIEW.md",
    "docs/ROADMAP.md",
    "docs/DECISIONS.md",
    "docs/PRD_INDEX.md",
]
for path in required:
    p = Path(path)
    assert p.exists(), f"missing {path}"
    text = p.read_text(encoding="utf-8")
    assert len(text.strip()) > 500, f"too short {path}"
    assert "TODO TODO" not in text, f"placeholder in {path}"
print("docs checks passed")
PY
```

Также проверить отсутствие секретов:

```bash
grep -R "OPENAI_API_KEY\|api_key\|BEGIN PRIVATE KEY\|\\.env" docs TO_DO_LIST/reports/PRD-DOCS-001* || true
```

Если используется PowerShell — аналогичные команды допустимы.

---

## 11. Implementation report requirements

В `TO_DO_LIST/reports/PRD-DOCS-001_IMPLEMENTATION_REPORT.md` указать:

```text
## Status
- Implementation: done / partial / blocked
- Branch: main
- Runtime behavior changed: false
- Writer changed: false
- DiagnosticCard changed: false
- State Analyzer changed: false
- Thread Manager changed: false
- Knowledge pipeline changed: false
- Chroma reindex performed: false

## Files created/updated
...

## Docs Summary
- PROJECT_STATE created/updated: yes/no
- ARCHITECTURE_OVERVIEW created/updated: yes/no
- ROADMAP created/updated: yes/no
- DECISIONS created/updated: yes/no
- PRD_INDEX created/updated: yes/no

## HF3 Report Hygiene
- checked: yes/no
- fixed: yes/no
- remaining issues: ...

## Checks
- docs check: passed/failed
- secret scan: passed/failed
- git diff stat captured: yes/no

## Next Recommendation
- PRD-046.0.5-APPLY1 — Apply Real LLM Enrichment Overlay + Chroma Refresh v1

## Commit / Push
- Commit hash: ...
- Push status: pushed to main
- Report sync: post-push sync committed
```

---

## 12. Next step after this PRD

Если `PRD-DOCS-001` выполнен успешно:

```text
PRD-046.0.5-APPLY1 — Apply Real LLM Enrichment Overlay + Chroma Refresh v1
```

Цель следующего KB PRD будет:

- применить production-candidate overlay к controlled enriched metadata;
- не менять deterministic governance authority;
- обновить governed blocks / enrichment overlay reference;
- безопасно пересобрать Chroma;
- проверить `/api/query`;
- проверить, что enriched summaries/lens/tags/use_when/avoid_when появляются в API metadata;
- затем перейти к Async Turn LLM Summary Store или Retrieval Eval, в зависимости от фактического результата.

---

## 13. Safety reminder

Документация не должна создавать впечатление, что:

- Diagnostic Center уже готов;
- enriched KB уже applied в production;
- Writer должен цитировать `КУЗНИЦУ`;
- LLM enrichment решает safety/governance;
- Async Turn LLM Summary уже работает.

Все planned слои должны быть явно помечены как planned/deferred, если они ещё не внедрены.
