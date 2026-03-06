
# PRD v2.2: Bug Fixes + Admin UI Redesign *(исправленная редакция)*

## 1. Контекст и цели

**Версия:** v2.2 (замена PRD v2.1 — все слабые места устранены)
**Репозиторий:** `Askhat-cmd/Text_transcription`
**Базовая ветка:** `main` (коммит `99e759d`)
**Зависимости:** PRD v2.0.1 полностью реализован и работает

### Три задачи:

1. **Bug fix B1** — температура остаётся заблокированной при смене модели на non-reasoning
2. **Bug fix B2** — `reset_prompt_override` пишет `null` в JSON вместо удаления ключа
3. **UI Redesign** — Admin Panel получает новую цветовую схему

### ⚠️ Первый шаг — создать ветку:

```bash
git checkout main && git pull
git checkout -b feature/v2.2-admin-ui
```

Все изменения вносить только в эту ветку. После выполнения всех тасков — PR в `main`.

***

## 2. Факты о текущем коде

**Файлы для изменения:**


| Файл | SHA (текущий) | Что меняем |
| :-- | :-- | :-- |
| `bot_psychologist/bot_agent/runtime_config.py` | — | Bug fix B2 |
| `bot_psychologist/web_ui/src/components/admin/AdminPanel.tsx` | `29f6817` | Bug fix B1 + UI |
| `bot_psychologist/web_ui/src/components/admin/ConfigGroupPanel.tsx` | `dfa093c` | Bug fix B1 + UI |
| `bot_psychologist/web_ui/src/components/admin/PromptEditorPanel.tsx` | `9ab36c1` | UI |
| `bot_psychologist/web_ui/src/components/admin/HistoryPanel.tsx` | `c397865` | UI |
| `bot_psychologist/web_ui/src/constants/adminColors.ts` | *(новый файл)* | UI — константы цветов |
| `bot_psychologist/tests/test_runtime_config.py` | *(новый файл)* | Тесты B2 |

**Ключевые факты:**

**Факт 1.** `AdminPanel.tsx`, ~строка 47:

```typescript
const currentLLMModel =
  (configData?.groups?.llm?.params?.LLM_MODEL?.value as string) ?? '';
```

Читает **сохранённое значение с сервера**, не черновик из UI.

**Факт 2.** `ConfigGroupPanel.tsx`, ~строка 33:

```typescript
const isTemperatureBlocked =
  key === 'LLM_TEMPERATURE' && isReasoningModel(currentLLMModel);
```

Получает `currentLLMModel` как prop из AdminPanel — то есть сохранённое, не черновик.

**Факт 3.** Когда пользователь меняет `LLM_MODEL` в дропдауне, `drafts['LLM_MODEL']` обновляется мгновенно, но `currentLLMModel` из родителя остаётся старым — температура заблокирована несправедливо.

**Факт 4.** `runtime_config.py`, метод `reset_prompt_override`:

```python
data.setdefault("prompts", {})[name] = None  # пишет null в JSON
```

**Факт 5.** `AdminPanel.tsx` использует `bg-gray-50` / `bg-white` — всё монохромное.

**Факт 6.** `PromptEditorPanel.tsx`, строка 48-55 (точное расположение):

```tsx
<div className="flex justify-between items-center mb-3">
  <h3 className="font-semibold text-gray-800 text-sm">Промты</h3>
  <button onClick={onResetAll} ...>↩ Все к дефолту</button>
</div>
```

Кнопка «Сохранить» — строка ~103, класс `bg-blue-600`.
Кнопка «Показать оригинал» — строка ~93, класс `border-gray-300 text-gray-600`.

***

## 3. Визуальная схема нового интерфейса

```
┌─────────────────────────────────────────────────────────────┐
│  HEADER  bg-gradient slate-900→slate-700         ~80px      │
│  ⚙️ Admin Config Panel    [🔑 API Key ____] [✓]            │
│  [↓ Экспорт] [↑ Импорт] [🗑 Полный сброс]                  │
├─────────────────────────────────────────────────────────────┤
│  TABS  bg-slate-800                              ~44px       │
│  [🤖 LLM] [🔍 Поиск] [🧠 Память] [🗄️ Хр-ще] [⚙️ RT]...  │
│         ^^^^активный: border-b-2 violet-400                  │
├─────────────────────────────────────────────────────────────┤
│  CONTENT AREA  bg-slate-100                                  │
│  ┌──────────────────────────────────────────────────────┐   │
│  │▌ border-l-4 violet   bg-white  shadow-md  rounded-xl │   │
│  │  [🤖 LLM]  "LLM настройки"        [Сохранить (2)] ↩ │   │
│  │  ─────────────────────────────────────────────────── │   │
│  │  LLM_MODEL    [dropdown gpt-4o-mini▼]       [✓] [↩] │   │
│  │  LLM_TEMP     [0.7_____________________]    [✓] [↩] │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

**Цветовая карта по группам:**


| Группа | Ключ | Полоса | Кнопки | Иконка-фон |
| :-- | :-- | :-- | :-- | :-- |
| LLM | `llm` | `border-l-violet-500` | `bg-violet-600` | `bg-violet-100 text-violet-700` |
| Поиск | `retrieval` | `border-l-blue-500` | `bg-blue-600` | `bg-blue-100 text-blue-700` |
| Память | `memory` | `border-l-emerald-500` | `bg-emerald-600` | `bg-emerald-100 text-emerald-700` |
| Хранилище | `storage` | `border-l-amber-500` | `bg-amber-500` | `bg-amber-100 text-amber-700` |
| Runtime | `runtime` | `border-l-slate-500` | `bg-slate-600` | `bg-slate-100 text-slate-700` |
| Промты | `prompts` | — (modal panel) | `bg-rose-600` | `from-rose-900 to-rose-700` |
| История | `history` | — (full panel) | — | `from-indigo-900 to-indigo-700` |


***

## 4. Bug Fix B1 — Температура реагирует на черновик модели

### Суть проблемы

Пользователь сохранил `gpt-5-mini`. Меняет на `gpt-4o-mini` в дропдауне — температура должна разблокироваться **мгновенно**, без нажатия «Сохранить». Сейчас `currentLLMModel` читается с сервера и не обновляется.

### ⚠️ Важно: Task B1.1 выполнять НЕ НУЖНО отдельно

Task UI.2 полностью переписывает `ConfigGroupPanel.tsx` и уже содержит фикс температуры. Если выполняется UI.2 — задачи B1.1 и B1.2 покрыты им полностью.

**Если UI Redesign не нужен** — выполнить только B1.1 и B1.2:

### Task B1.1 — `ConfigGroupPanel.tsx` (только если UI.2 не выполняется)

Убрать `currentLLMModel` из интерфейса `Props` (строка ~10):

```typescript
// БЫЛО:
interface Props {
  groupKey: string;
  group: ConfigGroup;
  onSave: (key: string, value: unknown) => Promise<void>;
  onReset: (key: string) => Promise<void>;
  isSaving: boolean;
  currentLLMModel: string;  // ← УДАЛИТЬ
}

// СТАЛО:
interface Props {
  groupKey: string;
  group: ConfigGroup;
  onSave: (key: string, value: unknown) => Promise<void>;
  onReset: (key: string) => Promise<void>;
  isSaving: boolean;
  // currentLLMModel убран — читаем из drafts['LLM_MODEL'] напрямую
}
```

В функции `renderInput` изменить `isTemperatureBlocked` (~строка 75):

```typescript
// БЫЛО:
const isTemperatureBlocked =
  key === 'LLM_TEMPERATURE' && isReasoningModel(currentLLMModel);

// СТАЛО:
const isTemperatureBlocked =
  key === 'LLM_TEMPERATURE' &&
  isReasoningModel(String(drafts['LLM_MODEL'] ?? ''));
```


### Task B1.2 — `AdminPanel.tsx` (только если UI.2 не выполняется)

Удалить строку `currentLLMModel` (~строка 47):

```typescript
// УДАЛИТЬ:
const currentLLMModel =
  (configData?.groups?.llm?.params?.LLM_MODEL?.value as string) ?? '';
```

Убрать prop из JSX `<ConfigGroupPanel>`:

```tsx
// БЫЛО:
<ConfigGroupPanel
  ...
  currentLLMModel={currentLLMModel}
/>

// СТАЛО:
<ConfigGroupPanel
  ...
  // currentLLMModel удалён
/>
```


***

## 5. Bug Fix B2 — Сброс промта удаляет ключ, не пишет null

### Task B2.1 — `runtime_config.py`

Найти метод `reset_prompt_override`, строку:

```python
data.setdefault("prompts", {})[name] = None
```

Заменить на:

```python
data.setdefault("prompts", {}).pop(name, None)
```

В методе `get_all_prompts` добавить защитный фильтр (обратная совместимость со старыми `null` в JSON):

```python
# БЫЛО:
override_text = overrides.get(name)
is_overridden = override_text is not None

# СТАЛО:
override_text = overrides.get(name)
# None может остаться от старых записей до фикса — игнорируем
if override_text is None:
    is_overridden = False
    override_text = None
else:
    is_overridden = True
```


***

## 6. UI Redesign — Новая цветовая схема

### Task UI.0 — Создать `adminColors.ts` *(новый файл)*

**Файл:** `bot_psychologist/web_ui/src/constants/adminColors.ts`

```typescript
// Все цветовые константы Admin Panel — единая точка правды
// Импортировать в AdminPanel.tsx и ConfigGroupPanel.tsx

export const GROUP_COLORS: Record<string, string> = {
  llm:       'violet',
  retrieval: 'blue',
  memory:    'emerald',
  storage:   'amber',
  runtime:   'slate',
};

export const ACCENT_CLASSES = {
  violet: {
    border:   'border-l-violet-500',
    icon:     'bg-violet-100 text-violet-700',
    saveBtn:  'bg-violet-600 hover:bg-violet-700 text-white',
    checkBtn: 'bg-violet-600 hover:bg-violet-700 text-white',
    badge:    'bg-violet-100 text-violet-700',
    override: 'border-violet-300 bg-violet-50',
    ring:     'focus:ring-violet-300',
  },
  blue: {
    border:   'border-l-blue-500',
    icon:     'bg-blue-100 text-blue-700',
    saveBtn:  'bg-blue-600 hover:bg-blue-700 text-white',
    checkBtn: 'bg-blue-600 hover:bg-blue-700 text-white',
    badge:    'bg-blue-100 text-blue-700',
    override: 'border-blue-300 bg-blue-50',
    ring:     'focus:ring-blue-300',
  },
  emerald: {
    border:   'border-l-emerald-500',
    icon:     'bg-emerald-100 text-emerald-700',
    saveBtn:  'bg-emerald-600 hover:bg-emerald-700 text-white',
    checkBtn: 'bg-emerald-600 hover:bg-emerald-700 text-white',
    badge:    'bg-emerald-100 text-emerald-700',
    override: 'border-emerald-300 bg-emerald-50',
    ring:     'focus:ring-emerald-300',
  },
  amber: {
    border:   'border-l-amber-500',
    icon:     'bg-amber-100 text-amber-700',
    saveBtn:  'bg-amber-500 hover:bg-amber-600 text-white',
    checkBtn: 'bg-amber-500 hover:bg-amber-600 text-white',
    badge:    'bg-amber-100 text-amber-700',
    override: 'border-amber-300 bg-amber-50',
    ring:     'focus:ring-amber-300',
  },
  slate: {
    border:   'border-l-slate-500',
    icon:     'bg-slate-100 text-slate-700',
    saveBtn:  'bg-slate-600 hover:bg-slate-700 text-white',
    checkBtn: 'bg-slate-600 hover:bg-slate-700 text-white',
    badge:    'bg-slate-100 text-slate-700',
    override: 'border-slate-300 bg-slate-50',
    ring:     'focus:ring-slate-300',
  },
} as const;

export type AccentKey = keyof typeof ACCENT_CLASSES;
```


***

### Task UI.1 — `AdminPanel.tsx` (header + tabs + layout)

Полный новый вариант файла. Ключевые изменения:

- Импорт `GROUP_COLORS` из `../../constants/adminColors`
- Удалена переменная `currentLLMModel` (фикс B1)
- Тёмный header `slate-900→slate-700`
- Тёмная таб-панель `slate-800`
- Передаётся `accentColor` в `ConfigGroupPanel`

```tsx
// components/admin/AdminPanel.tsx
import React, { useState, useEffect, useRef } from 'react';
import { useAdminConfig } from '../../hooks/useAdminConfig';
import { ConfigGroupPanel } from './ConfigGroupPanel';
import { PromptEditorPanel } from './PromptEditorPanel';
import { HistoryPanel } from './HistoryPanel';
import { GROUP_COLORS } from '../../constants/adminColors';
import type { HistoryEntry } from '../../types/admin.types';

type Tab = 'llm' | 'retrieval' | 'memory' | 'storage' | 'runtime' | 'prompts' | 'history';

const TABS: { key: Tab; label: string; hoverColor: string }[] = [
  { key: 'llm',       label: '🤖 LLM',       hoverColor: 'hover:bg-violet-500/20' },
  { key: 'retrieval', label: '🔍 Поиск',      hoverColor: 'hover:bg-blue-500/20'   },
  { key: 'memory',    label: '🧠 Память',     hoverColor: 'hover:bg-emerald-500/20'},
  { key: 'storage',   label: '🗄️ Хранилище', hoverColor: 'hover:bg-amber-500/20'  },
  { key: 'runtime',   label: '⚙️ Runtime',    hoverColor: 'hover:bg-slate-500/20'  },
  { key: 'prompts',   label: '📝 Промты',     hoverColor: 'hover:bg-rose-500/20'   },
  { key: 'history',   label: '🕐 История',    hoverColor: 'hover:bg-indigo-500/20' },
];

export const AdminPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<Tab>('llm');
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [apiKey, setApiKey] = useState<string>(
    () => localStorage.getItem('devApiKey') || ''
  );
  const [showApiKey, setShowApiKey] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const {
    configData, prompts, selectedPrompt,
    isLoading, isSaving, error, successMessage,
    clearError, loadConfig, loadPrompts, loadPromptDetail,
    saveConfigParam, resetConfigParam, resetAllConfig,
    savePrompt, resetPrompt, resetAllPrompts,
    exportOverrides, importOverrides,
  } = useAdminConfig();

  useEffect(() => {
    if (apiKey) localStorage.setItem('devApiKey', apiKey);
  }, [apiKey]);

  useEffect(() => { loadConfig(); loadPrompts(); }, []);

  useEffect(() => {
    if (activeTab !== 'history') return;
    import('../../services/adminConfig.service').then(({ adminConfigService }) => {
      adminConfigService.getHistory().then((data) => setHistory(data.history));
    });
  }, [activeTab]);

  const handleResetConfigParam = async (key: string) => {
    if (key === '__all__') await resetAllConfig();
    else await resetConfigParam(key);
  };

  const handleImportFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    await importOverrides(file);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  return (
    <div className="min-h-screen bg-slate-100">

      {/* ── Header: тёмный градиент ── */}
      <div className="bg-gradient-to-r from-slate-900 to-slate-700 px-6 py-4 shadow-lg">
        <div className="max-w-6xl mx-auto">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h1 className="text-xl font-bold text-white tracking-tight">
                ⚙️ Admin Config Panel
              </h1>
              <p className="text-sm text-slate-400 mt-0.5">
                Горячее управление параметрами без рестарта сервера
              </p>
            </div>

            {/* API Key */}
            <div className="flex items-center gap-2">
              <div className="relative">
                <input
                  type={showApiKey ? 'text' : 'password'}
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder="dev-key-001"
                  className="w-48 px-3 py-1.5 bg-slate-800 border border-slate-600 rounded
                             text-sm text-slate-200 placeholder-slate-500
                             focus:outline-none focus:ring-2 focus:ring-violet-400"
                />
                <button
                  onClick={() => setShowApiKey(!showApiKey)}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-xs text-slate-500 hover:text-slate-300"
                >
                  {showApiKey ? '🙈' : '👁️'}
                </button>
              </div>
              <span className={`text-xs px-2 py-1 rounded font-medium ${
                apiKey
                  ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                  : 'bg-red-500/20 text-red-400 border border-red-500/30'
              }`}>
                {apiKey ? '✓' : '✕'}
              </span>
            </div>
          </div>

          {/* Кнопки действий */}
          <div className="flex items-center gap-2">
            <button
              onClick={exportOverrides}
              className="px-3 py-1.5 border border-slate-500 rounded text-sm text-slate-300
                         hover:bg-slate-600 transition-colors"
            >
              ↓ Экспорт
            </button>
            <label className="px-3 py-1.5 border border-slate-500 rounded text-sm text-slate-300
                               hover:bg-slate-600 transition-colors cursor-pointer">
              ↑ Импорт
              <input
                ref={fileInputRef}
                type="file"
                accept=".json"
                className="hidden"
                onChange={handleImportFile}
              />
            </label>
            <button
              onClick={async () => {
                if (!window.confirm('Полный сброс: удалить ВСЕ overrides (конфиг + промты)?')) return;
                const { adminConfigService } = await import('../../services/adminConfig.service');
                await adminConfigService.resetAll();
                await loadConfig();
                await loadPrompts();
              }}
              className="px-3 py-1.5 border border-red-500/40 rounded text-sm text-red-400
                         hover:bg-red-500/20 transition-colors"
            >
              🗑 Полный сброс
            </button>
          </div>
        </div>
      </div>

      {/* ── Tabs: тёмная полоса ── */}
      <div className="bg-slate-800 px-6 shadow-md">
        <div className="max-w-6xl mx-auto flex gap-1">
          {TABS.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`px-4 py-3 text-sm font-medium border-b-2 transition-all ${
                activeTab === tab.key
                  ? 'border-violet-400 text-white bg-white/5'
                  : `border-transparent text-slate-400 ${tab.hoverColor} hover:text-white`
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* ── Notifications ── */}
      <div className="max-w-6xl mx-auto px-6 pt-3">
        {error && (
          <div className="flex items-center justify-between px-4 py-3
                          bg-red-50 border border-red-200 rounded-lg text-sm text-red-700 mb-3">
            <span>⚠ {error}</span>
            <button onClick={clearError} className="text-red-400 hover:text-red-600">✕</button>
          </div>
        )}
        {successMessage && (
          <div className="px-4 py-3 bg-emerald-50 border border-emerald-200
                          rounded-lg text-sm text-emerald-700 mb-3">
            ✓ {successMessage}
          </div>
        )}
      </div>

      {/* ── Main content ── */}
      <div className="max-w-6xl mx-auto px-6 pb-10">
        {isLoading && (
          <div className="text-center text-slate-400 py-12 text-sm">Загрузка...</div>
        )}

        {!isLoading && configData && (
          <>
            {(['llm', 'retrieval', 'memory', 'storage', 'runtime'] as const)
              .includes(activeTab as any) && (
              <div className="mt-4 space-y-4">
                {Object.entries(configData.groups)
                  .filter(([groupKey]) => groupKey === activeTab)
                  .map(([groupKey, group]) => (
                    <ConfigGroupPanel
                      key={groupKey}
                      groupKey={groupKey}
                      group={group}
                      onSave={saveConfigParam}
                      onReset={handleResetConfigParam}
                      isSaving={isSaving}
                      accentColor={GROUP_COLORS[groupKey] ?? 'blue'}
                    />
                  ))}
              </div>
            )}

            {activeTab === 'prompts' && (
              <div className="mt-4 bg-white rounded-xl border border-slate-200
                              p-5 shadow-md h-[70vh]">
                <PromptEditorPanel
                  prompts={prompts}
                  selectedPrompt={selectedPrompt}
                  onSelect={loadPromptDetail}
                  onSave={savePrompt}
                  onReset={resetPrompt}
                  onResetAll={resetAllPrompts}
                  isSaving={isSaving}
                />
              </div>
            )}

            {activeTab === 'history' && (
              <div className="mt-4">
                <HistoryPanel history={history} />
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};
```


***

### Task UI.2 — `ConfigGroupPanel.tsx` *(включает фикс B1)*

> ⚠️ Этот таск уже содержит Bug Fix B1 (температура). Если выполнен UI.2 — таски B1.1 и B1.2 пропустить.

Полный новый вариант файла:

```tsx
// components/admin/ConfigGroupPanel.tsx
import React, { useState, useEffect } from 'react';
import type { ConfigGroup } from '../../types/admin.types';
import { ACCENT_CLASSES, type AccentKey } from '../../constants/adminColors';

interface Props {
  groupKey: string;
  group: ConfigGroup;
  onSave: (key: string, value: unknown) => Promise<void>;
  onReset: (key: string) => Promise<void>;
  isSaving: boolean;
  accentColor?: string; // 'violet' | 'blue' | 'emerald' | 'amber' | 'slate'
  // ✅ currentLLMModel УДАЛЁН — читаем из drafts['LLM_MODEL'] напрямую
}

const REASONING_PREFIXES = ['gpt-5', 'o1', 'o3', 'o4'];
const isReasoningModel = (model: string): boolean =>
  REASONING_PREFIXES.some((p) => model.startsWith(p));

export const ConfigGroupPanel: React.FC<Props> = ({
  groupKey: _groupKey,
  group,
  onSave,
  onReset,
  isSaving,
  accentColor = 'blue',
}) => {
  const [drafts, setDrafts] = useState<Record<string, unknown>>({});
  const [dirtyKeys, setDirtyKeys] = useState<Set<string>>(new Set());

  const accentKey: AccentKey =
    accentColor in ACCENT_CLASSES ? (accentColor as AccentKey) : 'blue';
  const accent = ACCENT_CLASSES[accentKey];

  useEffect(() => {
    const init: Record<string, unknown> = {};
    Object.entries(group.params).forEach(([key, param]) => {
      init[key] = param.value;
    });
    setDrafts(init);
    setDirtyKeys(new Set());
  }, [group]);

  const handleChange = (key: string, value: unknown) => {
    setDrafts((prev) => ({ ...prev, [key]: value }));
    setDirtyKeys((prev) => new Set(prev).add(key));
  };

  const handleSave = async (key: string) => {
    await onSave(key, drafts[key]);
    setDirtyKeys((prev) => {
      const next = new Set(prev);
      next.delete(key);
      return next;
    });
  };

  const handleSaveAll = async () => {
    for (const key of Array.from(dirtyKeys)) {
      await onSave(key, drafts[key]);
    }
    setDirtyKeys(new Set());
  };

  const renderInput = (key: string, param: ConfigGroup['params'][string]) => {
    const draft = drafts[key];

    // ✅ ФИКС B1: читаем из локального drafts, не из внешнего prop
    const isTemperatureBlocked =
      key === 'LLM_TEMPERATURE' &&
      isReasoningModel(String(drafts['LLM_MODEL'] ?? ''));

    const baseClass =
      'w-full px-3 py-1.5 rounded border text-sm focus:outline-none focus:ring-2 focus:ring-offset-0 ' +
      (param.is_overridden && !dirtyKeys.has(key)
        ? `${accent.override} ${accent.ring}`
        : `border-gray-200 bg-white ${accent.ring}`);

    if (isTemperatureBlocked) {
      return (
        <div className="flex items-center gap-2">
          <input
            className={`${baseClass} opacity-40 cursor-not-allowed`}
            value={String(draft)}
            disabled
          />
          <span className="text-xs text-gray-400 italic whitespace-nowrap">
            н/п для reasoning-модели
          </span>
        </div>
      );
    }

    if (param.type === 'bool') {
      return (
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={Boolean(draft)}
            onChange={(e) => handleChange(key, e.target.checked)}
            className="w-4 h-4 rounded"
          />
          <span className="text-sm text-gray-600">
            {Boolean(draft) ? 'Включено' : 'Выключено'}
          </span>
        </label>
      );
    }

    if (param.type === 'select' && param.options) {
      return (
        <select
          className={baseClass}
          value={String(draft)}
          onChange={(e) => handleChange(key, e.target.value)}
        >
          {param.options.map((opt) => (
            <option key={opt} value={opt}>{opt}</option>
          ))}
        </select>
      );
    }

    if (param.type === 'int' || param.type === 'float') {
      return (
        <div className="flex items-center gap-2">
          <input
            type="number"
            className={baseClass}
            value={String(draft)}
            min={param.min}
            max={param.max}
            step={param.type === 'float' ? 0.05 : 1}
            onChange={(e) =>
              handleChange(
                key,
                param.type === 'float'
                  ? parseFloat(e.target.value)
                  : parseInt(e.target.value, 10)
              )
            }
          />
          <span className="text-xs text-gray-400 whitespace-nowrap">
            [{param.min} – {param.max}]
          </span>
        </div>
      );
    }

    return (
      <input
        type="text"
        className={baseClass}
        value={String(draft)}
        onChange={(e) => handleChange(key, e.target.value)}
      />
    );
  };

  return (
    <div className={`bg-white rounded-xl border-l-4 ${accent.border} shadow-md overflow-hidden`}>
      {/* Заголовок карточки */}
      <div className="flex justify-between items-center px-5 py-4 border-b border-gray-100">
        <div className="flex items-center gap-3">
          <span className={`text-lg px-2 py-1 rounded-lg ${accent.icon}`}>
            {group.label.split(' ')[0]}
          </span>
          <h3 className="font-semibold text-gray-800 text-base">
            {group.label.split(' ').slice(1).join(' ')}
          </h3>
        </div>
        <div className="flex gap-2">
          {dirtyKeys.size > 0 && (
            <button
              onClick={handleSaveAll}
              disabled={isSaving}
              className={`px-3 py-1 rounded text-sm font-medium
                         ${accent.saveBtn} disabled:opacity-50 transition-colors`}
            >
              Сохранить все ({dirtyKeys.size})
            </button>
          )}
          <button
            onClick={() => onReset('__all__')}
            disabled={isSaving}
            className="px-3 py-1 bg-gray-100 text-gray-500 rounded text-sm
                       hover:bg-gray-200 disabled:opacity-50 transition-colors"
          >
            ↩ Сбросить группу
          </button>
        </div>
      </div>

      {/* Параметры */}
      <div className="px-5 py-4 space-y-5">
        {Object.entries(group.params).map(([key, param]) => (
          <div key={key} className="grid grid-cols-[1fr_auto] gap-x-3 items-start">
            <div>
              <div className="flex items-center gap-2 mb-1.5">
                <label className="text-sm font-medium text-gray-700">
                  {param.label}
                </label>
                {param.is_overridden && !dirtyKeys.has(key) && (
                  <span className="px-1.5 py-0.5 bg-amber-100 text-amber-700
                                   rounded text-xs font-medium">
                    override
                  </span>
                )}
                {dirtyKeys.has(key) && (
                  <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${accent.badge}`}>
                    изменено
                  </span>
                )}
              </div>
              {renderInput(key, param)}
              {param.note && (
                <p className="text-xs text-gray-400 mt-1 italic">{param.note}</p>
              )}
              {param.is_overridden && (
                <p className="text-xs text-gray-400 mt-0.5">
                  Дефолт: <span className="font-mono">{String(param.default)}</span>
                </p>
              )}
            </div>
            <div className="flex flex-col gap-1 pt-6">
              {dirtyKeys.has(key) && (
                <button
                  onClick={() => handleSave(key)}
                  disabled={isSaving}
                  className={`px-2 py-1 rounded text-xs
                             ${accent.checkBtn} disabled:opacity-50 transition-colors`}
                >
                  ✓
                </button>
              )}
              {param.is_overridden && (
                <button
                  onClick={() => onReset(key)}
                  disabled={isSaving}
                  title="Сбросить к дефолту"
                  className="px-2 py-1 bg-gray-100 text-gray-500 rounded text-xs
                             hover:bg-gray-200 disabled:opacity-50 transition-colors"
                >
                  ↩
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
```


***

### Task UI.3 — `HistoryPanel.tsx`

Полный новый вариант:

```tsx
// components/admin/HistoryPanel.tsx
import React from 'react';
import type { HistoryEntry } from '../../types/admin.types';

interface Props { history: HistoryEntry[]; }

const TYPE_STYLES: Record<string, { label: string; cls: string }> = {
  config:       { label: 'config изменён', cls: 'bg-violet-100 text-violet-700' },
  config_reset: { label: 'config сброшен', cls: 'bg-gray-100   text-gray-600'   },
  prompt:       { label: 'промт изменён',  cls: 'bg-rose-100   text-rose-700'   },
  prompt_reset: { label: 'промт сброшен',  cls: 'bg-gray-100   text-gray-600'   },
};

export const HistoryPanel: React.FC<Props> = ({ history }) => {
  const sorted = [...history].reverse();

  return (
    <div className="bg-white rounded-xl shadow-md overflow-hidden border border-gray-100">
      {/* Шапка — indigo-градиент */}
      <div className="bg-gradient-to-r from-indigo-900 to-indigo-700 px-5 py-3">
        <h3 className="text-white font-semibold text-sm">🕐 История изменений</h3>
        <p className="text-indigo-300 text-xs mt-0.5">последние {history.length} записей</p>
      </div>

      {sorted.length === 0 ? (
        <div className="text-center text-gray-400 py-12 text-sm">
          История пуста — изменений ещё не было
        </div>
      ) : (
        <div className="divide-y divide-gray-50">
          {sorted.map((entry, i) => {
            const style = TYPE_STYLES[entry.type] ?? {
              label: entry.type,
              cls: 'bg-gray-100 text-gray-600',
            };
            const ts = new Date(entry.timestamp).toLocaleString('ru-RU', {
              day: '2-digit', month: '2-digit', year: 'numeric',
              hour: '2-digit', minute: '2-digit', second: '2-digit',
            });
            return (
              <div
                key={i}
                className="flex items-start justify-between px-5 py-3.5
                           hover:bg-slate-50 transition-colors"
              >
                <div className="flex items-start gap-3">
                  <span className={`mt-0.5 px-2 py-0.5 rounded text-xs font-medium
                                   whitespace-nowrap ${style.cls}`}>
                    {style.label}
                  </span>
                  <div>
                    <p className="text-sm font-mono font-medium text-gray-800">
                      {entry.key}
                    </p>
                    <p className="text-xs text-gray-500 mt-0.5">
                      <span className="text-red-500 font-mono">{String(entry.old)}</span>
                      <span className="mx-1.5 text-gray-400">→</span>
                      <span className="text-emerald-600 font-mono">{String(entry.new)}</span>
                    </p>
                  </div>
                </div>
                <span className="text-xs text-gray-400 whitespace-nowrap ml-4 mt-0.5">
                  {ts}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
```


***

### Task UI.4 — `PromptEditorPanel.tsx` *(точечные изменения)*

**Файл:** `bot_psychologist/web_ui/src/components/admin/PromptEditorPanel.tsx`
**SHA текущего файла:** `9ab36c1d8b58d495c963eecf97958b7f45f8e0f1`

**Изменение 1.** Строки 48-55 — заменить шапку левой панели:

```tsx
// БЫЛО (строки 48-55):
<div className="flex justify-between items-center mb-3">
  <h3 className="font-semibold text-gray-800 text-sm">Промты</h3>
  <button
    onClick={onResetAll}
    disabled={isSaving}
    className="text-xs text-gray-500 hover:text-red-500 disabled:opacity-50"
  >
    ↩ Все к дефолту
  </button>
</div>

// СТАЛО:
<div className="bg-gradient-to-r from-rose-900 to-rose-700 px-4 py-3
                rounded-t-lg flex items-center justify-between mb-3 -mx-0">
  <h3 className="text-white font-semibold text-sm">📝 Промты</h3>
  <button
    onClick={onResetAll}
    disabled={isSaving}
    className="text-xs text-rose-300 hover:text-white transition-colors disabled:opacity-50"
  >
    ⟲ Все к дефолту
  </button>
</div>
```

**Изменение 2.** Строка ~93 — кнопка «Показать оригинал»:

```tsx
// БЫЛО:
className={`px-3 py-1.5 rounded text-sm border transition-colors ${
  showDiff
    ? 'bg-gray-800 text-white border-gray-800'
    : 'border-gray-300 text-gray-600 hover:bg-gray-50'
}`}

// СТАЛО:
className={`px-3 py-1.5 rounded text-sm border transition-colors ${
  showDiff
    ? 'bg-rose-800 text-white border-rose-800'
    : 'border-rose-200 text-rose-600 hover:bg-rose-50'
}`}
```

**Изменение 3.** Строка ~103 — кнопка «Сохранить»:

```tsx
// БЫЛО:
className="px-3 py-1.5 bg-blue-600 text-white rounded text-sm
           hover:bg-blue-700 disabled:opacity-50"

// СТАЛО:
className="px-3 py-1.5 bg-rose-600 text-white rounded text-sm
           hover:bg-rose-700 disabled:opacity-50"
```

**Изменение 4.** Активный промт в списке — строка ~68, заменить `blue` на `rose`:

```tsx
// БЫЛО:
'bg-blue-50 border border-blue-200 text-blue-800'

// СТАЛО:
'bg-rose-50 border border-rose-200 text-rose-800'
```


***

## 7. Task V.3 — Автотесты для Bug Fix B2

**Новый файл:** `bot_psychologist/tests/test_runtime_config_reset.py`

```python
"""
Тесты для метода reset_prompt_override в runtime_config.py
Запуск: pytest bot_psychologist/tests/test_runtime_config_reset.py -v
"""
import json
import os
import tempfile
import pytest

# Импорт адаптируется к структуре проекта — уточнить путь если нужно
from bot_psychologist.bot_agent.runtime_config import RuntimeConfig


@pytest.fixture
def temp_override_file():
    """Временный файл override для тестов."""
    with tempfile.NamedTemporaryFile(
        mode='w', suffix='.json', delete=False
    ) as f:
        json.dump({"prompts": {"prompt_sd_green": "custom text"}}, f)
        yield f.name
    os.unlink(f.name)


def test_reset_removes_key_not_writes_null(temp_override_file):
    """После reset_prompt_override ключ должен быть удалён, не null."""
    config = RuntimeConfig(override_path=temp_override_file)
    config.reset_prompt_override("prompt_sd_green")

    with open(temp_override_file) as f:
        data = json.load(f)

    assert "prompt_sd_green" not in data.get("prompts", {}), \
        "Ключ должен быть удалён, а не установлен в null"


def test_reset_nonexistent_key_is_safe(temp_override_file):
    """Сброс несуществующего ключа не должен вызывать ошибку."""
    config = RuntimeConfig(override_path=temp_override_file)
    config.reset_prompt_override("nonexistent_key")  # не должно бросить исключение


def test_get_all_prompts_ignores_null_values(temp_override_file):
    """get_all_prompts должен игнорировать null-значения из старых записей."""
    # Симулируем старый JSON с null
    with open(temp_override_file, 'w') as f:
        json.dump({"prompts": {"prompt_sd_green": None}}, f)

    config = RuntimeConfig(override_path=temp_override_file)
    all_prompts = config.get_all_prompts()

    for p in all_prompts:
        assert p.get('is_overridden') is not True or p.get('text') is not None, \
            "Промт с null не должен помечаться как override"


def test_is_reasoning_model():
    """Проверка функции isReasoningModel для всех граничных случаев."""
    REASONING_PREFIXES = ['gpt-5', 'o1', 'o3', 'o4']

    def is_reasoning(model: str) -> bool:
        return any(model.startswith(p) for p in REASONING_PREFIXES)

    assert is_reasoning('gpt-5-mini') is True
    assert is_reasoning('o1-preview') is True
    assert is_reasoning('o3-mini') is True
    assert is_reasoning('gpt-4o-mini') is False
    assert is_reasoning('gpt-4-turbo') is False
    assert is_reasoning('') is False
```


***

## 8. Пошаговый план выполнения

```
Шаг 0  →  git checkout -b feature/v2.2-admin-ui

Шаг 1  →  Task B2.1   runtime_config.py: pop() вместо None + фильтр в get_all_prompts
Шаг 2  →  Task V.3    Создать test_runtime_config_reset.py
           Проверка:   pytest bot_psychologist/tests/test_runtime_config_reset.py -v (4 passed)

Шаг 3  →  Task UI.0   Создать src/constants/adminColors.ts
Шаг 4  →  Task UI.2   Полностью переписать ConfigGroupPanel.tsx
           ⚠️ Содержит Bug Fix B1 — B1.1 и B1.2 НЕ выполнять отдельно
Шаг 5  →  Task UI.1   Полностью переписать AdminPanel.tsx
Шаг 6  →  Task UI.3   Полностью переписать HistoryPanel.tsx
Шаг 7  →  Task UI.4   Точечно изменить PromptEditorPanel.tsx (4 замены)

Шаг 8  →  Task V.1    npx tsc --noEmit  →  0 errors
Шаг 9  →  Task V.2    Визуальная проверка: открыть /admin, все 7 вкладок

Шаг 10 →  git push origin feature/v2.2-admin-ui
           Создать PR в main
```


***

## 9. Definition of Done

**Bug Fixes:**

- [ ] Смена модели на `gpt-4o-mini` в дропдауне **мгновенно** разблокирует температуру (без сохранения)
- [ ] Смена на `gpt-5-mini` **мгновенно** блокирует температуру
- [ ] После `reset_prompt_override` в `admin_overrides.json` нет ключей со значением `null`
- [ ] `pytest test_runtime_config_reset.py` — **4 passed, 0 failed**

**UI Redesign:**

- [ ] Header — тёмный градиент `slate-900 → slate-700`
- [ ] Таб-бар тёмный `slate-800`, активный таб с `violet-400`-подчёркиванием
- [ ] Карточка LLM — фиолетовая полоса + фиолетовые кнопки
- [ ] Карточка Поиск — синяя полоса + синие кнопки
- [ ] Карточка Память — зелёная полоса + зелёные кнопки
- [ ] Карточка Хранилище — янтарная полоса + янтарные кнопки
- [ ] Карточка Runtime — серая полоса + серые кнопки
- [ ] История — indigo-шапка, красный для старого значения, зелёный для нового
- [ ] Промты — rose-шапка, rose-кнопки, rose-активный элемент в списке

**Качество:**

- [ ] `npx tsc --noEmit` — **0 errors**
- [ ] Цветовые константы только в `src/constants/adminColors.ts`
- [ ] PR создан в ветку `feature/v2.2-admin-ui`, не напрямую в `main`

