# DEV_TASKS.md — PRD v2.2 Bug Fixes + Admin UI Redesign

**PRD Version:** v2.2  
**Base Branch:** `main` (коммит `99e759d`)  
**Feature Branch:** `feature/v2.2-admin-ui`  
**Date Created:** 2026-03-06  
**Status:** Ready for implementation

---

## 📋 Implementation Plan Overview

PRD v2.2 решает **3 ключевые задачи**:

1. **Bug Fix B1** — температура заблокирована при смене модели на non-reasoning
2. **Bug Fix B2** — `reset_prompt_override` пишет `null` в JSON вместо удаления ключа
3. **UI Redesign** — новая цветовая схема Admin Panel (5 групп, 7 вкладок)

**Общий объём работ:**
- **10 атомарных задач** (2 bug fixes + 5 UI + 3 тесты/проверки)
- **7 файлов** создать/изменить
- **Ветка:** `feature/v2.2-admin-ui` → PR в `main`

---

## 🎯 Phase 0: Подготовка

### Task 0.1: Создать feature-ветку
**Priority:** P0 (must be first)  
**Files:** N/A (git)  
**Type:** GIT

**Steps:**
```bash
cd c:\My_practice\Text_transcription
git checkout main && git pull
git checkout -b feature/v2.2-admin-ui
```

**Verification:**
```bash
git branch --show-current  # → feature/v2.2-admin-ui
```

---

## 🐛 Phase 1: Bug Fixes

### Task B2.1: Исправить `reset_prompt_override` — удалять ключ, не писать `null`
**Priority:** P0  
**Files:** `bot_psychologist/bot_agent/runtime_config.py`  
**Type:** MODIFY

**Проблема:** Метод `reset_prompt_override` записывает `None` в JSON, что создаёт `null` значения.

**Steps:**

1. Найти метод `reset_prompt_override` (~строка 580)
2. Заменить:
   ```python
   # БЫЛО:
   data.setdefault("prompts", {})[name] = None
   
   # СТАЛО:
   data.setdefault("prompts", {}).pop(name, None)
   ```

3. В методе `get_all_prompts` (~строка 520) добавить защитный фильтр:
   ```python
   # БЫЛО:
   override_text = overrides.get(name)
   is_overridden = override_text is not None
   
   # СТАЛО:
   override_text = overrides.get(name)
   # None может остаться от старых записей до фикса — игнорируем
   if override_text is None:
       is_overridden = False
   else:
       is_overridden = True
   ```

**Verification:**
```python
cd bot_psychologist
python -c "
from bot_agent.runtime_config import RuntimeConfig
cfg = RuntimeConfig()
cfg.set_prompt_override('prompt_sd_green', 'test')
cfg.reset_prompt_override('prompt_sd_green')
data = cfg._load_overrides()
assert 'prompt_sd_green' not in data.get('prompts', {}), 'Ключ должен быть удалён'
print('✓ B2.1 PASSED')
"
```

---

### Task V.3: Создать автотесты для Bug Fix B2
**Priority:** P1  
**Files:** `bot_psychologist/tests/test_runtime_config_reset.py`  
**Type:** CREATE

**Steps:**
1. Создать файл с тестами из PRD Section 7
2. Запустить pytest

**Verification:**
```bash
cd bot_psychologist
python -m pytest tests/test_runtime_config_reset.py -v
# Ожидаем: 4 passed, 0 failed
```

---

## 🎨 Phase 2: UI Redesign

### Task UI.0: Создать `adminColors.ts` — цветовые константы
**Priority:** P0  
**Files:** `bot_psychologist/web_ui/src/constants/adminColors.ts`  
**Type:** CREATE

**Steps:**
1. Создать файл `src/constants/adminColors.ts`
2. Добавить экспорты:
   - `GROUP_COLORS` — маппинг групп на цвета
   - `ACCENT_CLASSES` — полные наборы классов для каждого цвета
   - `type AccentKey` — тип для ключей

**Verification:**
```bash
cd web_ui
npx tsc --noEmit
# Ожидаем: 0 errors
```

---

### Task UI.1: Переписать `AdminPanel.tsx` — header + tabs + layout
**Priority:** P0  
**Files:** `bot_psychologist/web_ui/src/components/admin/AdminPanel.tsx`  
**Type:** MODIFY (полная замена)

**Steps:**
1. Добавить импорт `GROUP_COLORS` из `../../constants/adminColors`
2. Удалить переменную `currentLLMModel` (фикс B1)
3. Заменить header на тёмный градиент `slate-900 → slate-700`
4. Заменить tabs на тёмные `slate-800` с `violet-400` подчёркиванием
5. Передать `accentColor` в `ConfigGroupPanel`

**Ключевые изменения:**
- Header: `bg-gradient-to-r from-slate-900 to-slate-700`
- Tabs: `bg-slate-800`, активный: `border-violet-400 text-white`
- Content area: `bg-slate-100`
- API key input: `bg-slate-800 border-slate-600 text-slate-200`

**Verification:**
```bash
cd web_ui
npx tsc --noEmit
# Ожидаем: 0 errors
```

---

### Task UI.2: Переписать `ConfigGroupPanel.tsx` — карточки с цветами
**Priority:** P0  
**Files:** `bot_psychologist/web_ui/src/components/admin/ConfigGroupPanel.tsx`  
**Type:** MODIFY (полная замена)

**⚠️ Важно:** Этот таск **уже содержит Bug Fix B1** (температура). Если выполняется UI.2 — таски B1.1 и B1.2 **НЕ выполнять отдельно**.

**Steps:**
1. Добавить импорт `ACCENT_CLASSES` из `../../constants/adminColors`
2. Удалить `currentLLMModel` из `Props`
3. Добавить prop `accentColor?: string`
4. Исправить `isTemperatureBlocked` — читать из `drafts['LLM_MODEL']` (фикс B1)
5. Применить цветовые классы из `ACCENT_CLASSES[accentKey]`

**Фикс B1 (температура):**
```typescript
// БЫЛО:
const isTemperatureBlocked =
  key === 'LLM_TEMPERATURE' && isReasoningModel(currentLLMModel);

// СТАЛО:
const isTemperatureBlocked =
  key === 'LLM_TEMPERATURE' &&
  isReasoningModel(String(drafts['LLM_MODEL'] ?? ''));
```

**Verification:**
```bash
cd web_ui
npx tsc --noEmit
# Ожидаем: 0 errors

# Ручная проверка:
# 1. Открыть /admin
# 2. Выбрать gpt-5-mini → температура заблокирована
# 3. Сменить на gpt-4o-mini в дропдауне → температура разблокирована МГНОВЕННО
```

---

### Task UI.3: Переписать `HistoryPanel.tsx` — indigo-шапка
**Priority:** P0  
**Files:** `bot_psychologist/web_ui/src/components/admin/HistoryPanel.tsx`  
**Type:** MODIFY (полная замена)

**Steps:**
1. Добавить градиентную шапку `from-indigo-900 to-indigo-700`
2. Изменить стили бейджей: `prompt` → `bg-rose-100`, `config` → `bg-violet-100`
3. Добавить форматирование даты с секундами
4. Добавить `border-l-4` для карточки

**Verification:**
```bash
cd web_ui
npx tsc --noEmit
# Ожидаем: 0 errors
```

---

### Task UI.4: Обновить `PromptEditorPanel.tsx` — rose-акценты
**Priority:** P0  
**Files:** `bot_psychologist/web_ui/src/components/admin/PromptEditorPanel.tsx`  
**Type:** MODIFY (точечные изменения)

**Steps:**

**Изменение 1 (строки 48-55):** Заменить шапку левой панели:
```tsx
// БЫЛО:
<div className="flex justify-between items-center mb-3">
  <h3 className="font-semibold text-gray-800 text-sm">Промты</h3>
  <button onClick={onResetAll} ...>↩ Все к дефолту</button>
</div>

// СТАЛО:
<div className="bg-gradient-to-r from-rose-900 to-rose-700 px-4 py-3
                rounded-t-lg flex items-center justify-between mb-3 -mx-0">
  <h3 className="text-white font-semibold text-sm">📝 Промты</h3>
  <button onClick={onResetAll} ...>⟲ Все к дефолту</button>
</div>
```

**Изменение 2 (строка ~93):** Кнопка «Показать оригинал»:
```tsx
// БЫЛО:
className={`... ${showDiff ? 'bg-gray-800 text-white' : 'border-gray-300 text-gray-600'}`}

// СТАЛО:
className={`... ${showDiff ? 'bg-rose-800 text-white' : 'border-rose-200 text-rose-600'}`}
```

**Изменение 3 (строка ~103):** Кнопка «Сохранить»:
```tsx
// БЫЛО:
className="... bg-blue-600 text-white ..."

// СТАЛО:
className="... bg-rose-600 text-white ..."
```

**Изменение 4 (строка ~68):** Активный промт в списке:
```tsx
// БЫЛО:
'bg-blue-50 border border-blue-200 text-blue-800'

// СТАЛО:
'bg-rose-50 border border-rose-200 text-rose-800'
```

**Verification:**
```bash
cd web_ui
npx tsc --noEmit
# Ожидаем: 0 errors
```

---

## ✅ Phase 3: Verification

### Task V.1: TypeScript compilation check
**Priority:** P0  
**Files:** N/A (testing)  
**Type:** TEST

**Execute:**
```bash
cd bot_psychologist/web_ui
npx tsc --noEmit
```

**Expected:** 0 errors

---

### Task V.2: Visual UI check
**Priority:** P0  
**Files:** N/A (testing)  
**Type:** TEST

**Steps:**
1. Запустить API сервер: `python -m uvicorn api.main:app --reload --port 8001`
2. Запустить Web UI: `npm run dev`
3. Открыть `http://localhost:3000/admin`
4. Проверить все 7 вкладок

**Checklist:**
- [ ] Header — тёмный градиент `slate-900 → slate-700`
- [ ] Tabs — тёмные `slate-800`, активный с `violet-400`
- [ ] LLM карточка — фиолетовая полоса + кнопки
- [ ] Поиск карточка — синяя полоса + кнопки
- [ ] Память карточка — зелёная полоса + кнопки
- [ ] Хранилище карточка — янтарная полоса + кнопки
- [ ] Runtime карточка — серая полоса + кнопки
- [ ] История — indigo-шапка
- [ ] Промты — rose-шапка + кнопки

---

### Task B1-Verify: Bug Fix B1 — температура реагирует на черновик
**Priority:** P0  
**Files:** N/A (testing)  
**Type:** TEST

**Steps:**
1. Открыть `/admin` → вкладка LLM
2. Сохранить `gpt-5-mini` (температура заблокирована)
3. **Не сохраняя**, сменить в дропдауне на `gpt-4o-mini`
4. Температура должна **разблокироваться мгновенно** (без нажатия «Сохранить»)

**Expected:**
- При смене на `gpt-5*`, `o1`, `o3`, `o4` → температура блокируется
- При смене на `gpt-4*` → температура разблокируется

---

### Task B2-Verify: Bug Fix B2 — `reset_prompt_override` удаляет ключ
**Priority:** P0  
**Files:** N/A (testing)  
**Type:** TEST

**Steps:**
1. Открыть `/admin` → вкладка Промты
2. Изменить любой промт → Сохранить
3. Сбросить к дефолту (↩)
4. Проверить `bot_psychologist/data/admin_overrides.json`

**Expected:**
- В JSON **нет ключа** с `null` значением
- Ключ полностью удалён из `prompts`

---

## 📊 Definition of Done

### Bug Fixes:
- [ ] Смена модели на `gpt-4o-mini` в дропдауне **мгновенно** разблокирует температуру (без сохранения)
- [ ] Смена на `gpt-5-mini` **мгновенно** блокирует температуру
- [ ] После `reset_prompt_override` в `admin_overrides.json` **нет ключей** со значением `null`
- [ ] `pytest tests/test_runtime_config_reset.py` — **4 passed, 0 failed**

### UI Redesign:
- [ ] Header — тёмный градиент `slate-900 → slate-700`
- [ ] Tab-бар тёмный `slate-800`, активный таб с `violet-400`-подчёркиванием
- [ ] Карточка LLM — фиолетовая полоса + фиолетовые кнопки
- [ ] Карточка Поиск — синяя полоса + синие кнопки
- [ ] Карточка Память — зелёная полоса + зелёные кнопки
- [ ] Карточка Хранилище — янтарная полоса + янтарные кнопки
- [ ] Карточка Runtime — серая полоса + серые кнопки
- [ ] История — indigo-шапка, красный для старого значения, зелёный для нового
- [ ] Промты — rose-шапка, rose-кнопки, rose-активный элемент в списке

### Качество:
- [ ] `npx tsc --noEmit` — **0 errors**
- [ ] Цветовые константы только в `src/constants/adminColors.ts`
- [ ] PR создан в ветку `feature/v2.2-admin-ui`, не напрямую в `main`

---

## 🚀 Implementation Order

**Выполнять строго по порядку:**

1. **Task 0.1** → Создать ветку `feature/v2.2-admin-ui`
2. **Task B2.1** → Исправить `reset_prompt_override`
3. **Task V.3** → Создать тесты, запустить pytest (4 passed)
4. **Task UI.0** → Создать `adminColors.ts`
5. **Task UI.2** → Переписать `ConfigGroupPanel.tsx` (содержит фикс B1!)
6. **Task UI.1** → Переписать `AdminPanel.tsx`
7. **Task UI.3** → Переписать `HistoryPanel.tsx`
8. **Task UI.4** → Обновить `PromptEditorPanel.tsx`
9. **Task V.1** → TypeScript check (0 errors)
10. **Task V.2** → Visual check (7 вкладок)
11. **Task B1-Verify** → Температура (мгновенная реакция)
12. **Task B2-Verify** → Reset prompt (удаление ключа)
13. **Git push** → `origin feature/v2.2-admin-ui`
14. **PR** → Создать PR в `main`

---

## ⚠️ Critical Warnings

1. **Task UI.2 содержит Bug Fix B1** — если выполняется UI.2, таски B1.1 и B1.2 **НЕ выполнять отдельно**
2. **Цветовые константы** — только в `adminColors.ts`, не хардкодить классы в компонентах
3. **Ветка** — все изменения только в `feature/v2.2-admin-ui`, не в `main`
4. **Тесты B2** — запускать **до** UI изменений, чтобы убедиться что бэкэнд работает

---

## 📌 Out of Scope (v2.2)

- Изменение логики работы API endpoints
- Новые endpoints
- Изменение структуры `admin_overrides.json` (кроме фикса `null`)
- Мобильная адаптация UI
- Темная тема (dark mode)

---

**Ready for implementation. Start with Task 0.1.**
