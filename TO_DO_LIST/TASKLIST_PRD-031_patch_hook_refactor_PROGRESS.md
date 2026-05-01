# TASKLIST PRD-031 patch — hook refactor (progress)

## Контекст
- PRD: `TO_DO_LIST/PRD-031-patch-hook-refactor.md`
- Цель: декомпозировать `useAgents` на 4 специализированных хука без изменения backend-контрактов.

## План
- [x] Прочитать PRD и сверить текущую реализацию `web_ui`.
- [x] Создать 4 новых хука:
  - [x] `useAgentStatus.ts`
  - [x] `useOrchestrator.ts`
  - [x] `useThreads.ts`
  - [x] `useAgentPrompts.ts`
- [x] Переключить компоненты на новые хуки:
  - [x] `AgentsTab.tsx`
  - [x] `OrchestratorTab.tsx`
  - [x] `ThreadsTab.tsx`
  - [x] `AgentPromptEditorPanel.tsx`
- [x] Удалить `useAgents.ts`.
- [x] Заменить тесты:
  - [x] удалить `useAgents.test.ts`
  - [x] добавить 4 теста по новым хукам
- [x] Прогоны:
  - [x] `npm run lint` (`tsc --noEmit`)
  - [x] `npm run test -- --run src/hooks/useAgentStatus.test.ts src/hooks/useOrchestrator.test.ts src/hooks/useThreads.test.ts src/hooks/useAgentPrompts.test.ts`

## Definition of done
- [x] В проекте нет импортов `useAgents`.
- [x] Все 4 таба работают через специализированные хуки.
- [x] TypeScript и unit tests зелёные.

## Фактические прогоны
- `npm run lint` → OK
- `npm run test -- --run src/hooks/useAgentStatus.test.ts src/hooks/useOrchestrator.test.ts src/hooks/useThreads.test.ts src/hooks/useAgentPrompts.test.ts` → 8 passed
- `rg "useAgents" bot_psychologist/web_ui/src -n` → NO_MATCH
