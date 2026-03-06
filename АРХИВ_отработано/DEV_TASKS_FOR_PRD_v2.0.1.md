# DEV_TASKS_FOR_PRD_v2.0.1 — Admin Config Panel

**PRD Version:** 2.0.1 (финальная, исправленная, актуальная)  
**Project Root:** `bot_psychologist/`  
**Date Created:** 2026-03-06  
**Status:** Ready for implementation

---

## 📋 Implementation Plan Overview

This implementation adds a browser-based admin panel for hot-reloading configuration of the bot without server restart. The architecture uses a two-layer approach:

- **Layer 1 (Read-only):** `config.py` class attributes + 10 `.md` prompt files
- **Layer 2 (Overrides):** `data/admin_overrides.json` (created via API)

**Key Files:** 15 files to create/modify  
**Estimated Complexity:** High (requires understanding of Python metaclasses, async FastAPI, React TypeScript)

---

## 🎯 Phase 1: Backend Foundation

### Task 1.1: Create `data/.gitkeep` and update `.gitignore`
**Priority:** P0 (must be first)  
**Files:** `bot_psychologist/data/.gitkeep`, `bot_psychologist/.gitignore`  
**Type:** CREATE, MODIFY

**Steps:**
1. Create empty file `bot_psychologist/data/.gitkeep`
2. Add line to `bot_psychologist/.gitignore`:
   ```
   # Admin Config Panel runtime overrides
   data/admin_overrides.json
   ```

**Verification:**
- `git status` shows `data/.gitkeep` as new file
- `data/admin_overrides.json` is ignored

---

### Task 1.2: Create `runtime_config.py`
**Priority:** P0  
**Files:** `bot_psychologist/bot_agent/runtime_config.py`  
**Type:** CREATE

**Steps:**
1. Create file with full implementation from PRD Section 5, File 1
2. Key components:
   - `RuntimeConfig` class inherits from `Config`
   - `__getattribute__` intercepts editable config params
   - `_BYPASS_ATTRS` excludes class methods and sensitive attrs
   - `EDITABLE_CONFIG` dict with 28 editable parameters
   - `EDITABLE_PROMPTS` list with 10 prompt names
   - Thread-safe caching with `threading.Lock`
   - mtime-based file reloading
   - Atomic file writes via `tempfile + os.replace`

**Key Methods to Implement:**
- `__getattribute__(self, name)` — hot intercept
- `_load_overrides()` — cached JSON read
- `_save_overrides(data)` — atomic write
- `get_all_config()` — grouped params for UI
- `set_config_override(key, value)` — validate & save
- `reset_config_override(key)` — delete override
- `get_prompt(name)` — prompt with override logic
- `set_prompt_override(name, text)` — save prompt override

**Verification:**
```python
from bot_agent.runtime_config import RuntimeConfig
rc = RuntimeConfig()
print(rc.LLM_TEMPERATURE)   # → 0.7 (default)
print(rc.TOP_K_BLOCKS)      # → 5
print(type(rc))             # → RuntimeConfig class
```

---

### Task 1.3: Modify `config.py` last line
**Priority:** P0  
**Files:** `bot_psychologist/bot_agent/config.py`  
**Type:** MODIFY (only last line!)

**Steps:**
1. Find at end of file: `config = Config()`
2. Replace with:
   ```python
   # RuntimeConfig наследует Config и добавляет горячий override-слой.
   # Circular import безопасен: класс Config уже полностью определён выше,
   # runtime_config.py успешно импортирует его из частично загруженного
   # модуля — стандартное поведение Python для взаимных импортов.
   from .runtime_config import RuntimeConfig
   config = RuntimeConfig()
   ```

**⚠️ Warning:** Do NOT modify any other lines in `config.py`

**Verification:**
```python
from bot_agent.config import config
print(type(config))          # → RuntimeConfig
print(config.LLM_TEMPERATURE)  # → 0.7
```

---

### Task 1.4: Scan and update prompt reading in modules
**Priority:** P1  
**Files:** All files listed in PRD Section 5, File 3  
**Type:** SCAN, MODIFY

**Files to scan:**
```
bot_agent/answer_basic.py
bot_agent/answer_adaptive.py
bot_agent/answer_graph_powered.py
bot_agent/answer_sag_aware.py
bot_agent/llm_answerer.py
bot_agent/sd_classifier.py
bot_agent/state_classifier.py
bot_agent/path_builder.py
bot_agent/practices_recommender.py
bot_agent/user_level_adapter.py
bot_agent/decision/*.py       (all files)
bot_agent/response/*.py       (all files)
bot_agent/retrieval/*.py      (all files)
bot_agent/storage/*.py        (all files)
```

**Search patterns:**
```python
# Pattern A
(Path(__file__).parent / "prompt_XXX.md").read_text(encoding="utf-8")

# Pattern B
open(... / "prompt_XXX.md").read()

# Pattern C
with open(... / f"prompt_{something}.md") as f:
    prompt = f.read()
```

**Replacement rules:**

**If inside function/method:**
```python
# BEFORE:
prompt_text = (Path(__file__).parent / "prompt_sd_green.md").read_text(encoding="utf-8")

# AFTER:
from bot_agent.config import config
prompt_text = config.get_prompt("prompt_sd_green")["text"]
```

**If in global module scope:**
```python
# DO NOT CHANGE, add comment:
# TODO(admin-panel): чтение промта на уровне модуля — не hot-reloadable.
# Для горячей замены перенести в функцию и использовать config.get_prompt().
PROMPT_TEXT = (Path(__file__).parent / "prompt_sd_green.md").read_text(encoding="utf-8")
```

**Verification:**
```bash
grep -rn "prompt_.*\.md.*read_text" bot_psychologist/bot_agent/ --include="*.py"
# Should return only commented TODO lines or global scope reads
```

---

### Task 1.5: Create `api/admin_routes.py`
**Priority:** P0  
**Files:** `bot_psychologist/api/admin_routes.py`  
**Type:** CREATE

**Steps:**
1. Create file with full implementation from PRD Section 5, File 4
2. Implement 11 endpoints:

**Config Endpoints (5):**
- `GET /api/admin/config` — get all grouped params
- `PUT /api/admin/config` — save one param override
- `DELETE /api/admin/config/{key}` — reset one param
- `POST /api/admin/config/reset-all` — reset all config
- `POST /api/admin/prompts/reset-all` — reset all prompts

**Prompt Endpoints (5):**
- `GET /api/admin/prompts` — list all prompts with preview
- `GET /api/admin/prompts/{name}` — get full prompt text
- `PUT /api/admin/prompts/{name}` — save prompt override
- `DELETE /api/admin/prompts/{name}` — reset prompt
- `POST /api/admin/prompts/reset-all` — reset all prompts

**History & Utility (3):**
- `GET /api/admin/history` — last 50 changes
- `GET /api/admin/export` — export overrides JSON
- `POST /api/admin/import` — import overrides JSON
- `POST /api/admin/reset-all` — full reset

**Security:**
- All endpoints require `X-API-Key: dev-key-001` header
- Use `require_dev_key()` dependency

**Verification:**
```python
from api.admin_routes import admin_router
print(admin_router.prefix)   # → /api/admin
```

---

### Task 1.6: Register router in `main.py`
**Priority:** P0  
**Files:** `bot_psychologist/api/main.py`  
**Type:** MODIFY

**Steps:**
1. Find router registration block:
   ```python
   app.include_router(router)
   app.include_router(debug_router)
   ```
2. Add after it:
   ```python
   from .admin_routes import admin_router
   app.include_router(admin_router)
   ```

**Verification:**
- Start server: `python -m uvicorn api.main:app --reload`
- Open `http://localhost:8000/api/docs`
- Verify `⚙️ Admin Config` section appears with 11 endpoints

---

### Task 1.7: Backend smoke tests
**Priority:** P0  
**Files:** N/A (testing)  
**Type:** TEST

**Execute all curl commands from PRD Section 7:**

```bash
export DEV_KEY="dev-key-001"
export BASE="http://localhost:8000/api/admin"

# 7.1 Get config
curl -s -H "X-API-Key: $DEV_KEY" $BASE/config | python3 -m json.tool | head -30

# 7.2 Set temperature
curl -s -X PUT -H "X-API-Key: $DEV_KEY" -H "Content-Type: application/json" \
  -d '{"key": "LLM_TEMPERATURE", "value": 0.3}' $BASE/config

# 7.3 Verify override
curl -s -H "X-API-Key: $DEV_KEY" $BASE/config | \
  python3 -c "import sys,json; d=json.load(sys.stdin); \
  print(d['groups']['llm']['params']['LLM_TEMPERATURE']['value'])"

# 7.4 Reset temperature
curl -s -X DELETE -H "X-API-Key: $DEV_KEY" $BASE/config/LLM_TEMPERATURE

# 7.5 Get prompts list
curl -s -H "X-API-Key: $DEV_KEY" $BASE/prompts | python3 -m json.tool | head -20

# 7.6 Set prompt override
curl -s -X PUT -H "X-API-Key: $DEV_KEY" -H "Content-Type: application/json" \
  -d '{"text": "Тестовый текст"}' $BASE/prompts/prompt_sd_green

# 7.7 Check is_overridden
curl -s -H "X-API-Key: $DEV_KEY" $BASE/prompts | \
  python3 -c "import sys,json; d=json.load(sys.stdin); \
  [print(p['name'], p['is_overridden']) for p in d]"

# 7.8 Reset prompt
curl -s -X DELETE -H "X-API-Key: $DEV_KEY" $BASE/prompts/prompt_sd_green

# 7.9 Get history
curl -s -H "X-API-Key: $DEV_KEY" $BASE/history

# 7.10 Export/Import
curl -s -H "X-API-Key: $DEV_KEY" $BASE/export > /tmp/overrides_backup.json
curl -s -X POST -H "X-API-Key: $DEV_KEY" -H "Content-Type: application/json" \
  -d @/tmp/overrides_backup.json $BASE/import

# 7.11 Auth test (negative)
curl -s -H "X-API-Key: wrong_key" $BASE/config
# Expect: 401 Unauthorized
```

**Expected Results:**
- All commands return valid JSON
- Steps 7.2, 7.4, 7.6, 7.8 appear in history (7.9)
- Step 7.11 returns 401

---

## 🎨 Phase 2: Frontend Implementation

### Task 2.1: Create TypeScript types
**Priority:** P0  
**Files:** `web_ui/src/types/admin.types.ts`  
**Type:** CREATE

**Steps:**
1. Create file with full implementation from PRD Section 6, File 8
2. Export these types:
   - `ParamType` — 'int' | 'float' | 'bool' | 'select' | 'string'
   - `ConfigParam` — parameter schema with value, default, is_overridden
   - `ConfigGroup` — grouped params
   - `AdminConfigResponse` — API response type
   - `PromptMeta`, `PromptDetail` — prompt types
   - `HistoryEntry`, `HistoryEntryType` — history types
   - `AdminOverridesExport` — export/import type

**Verification:**
```bash
cd web_ui
npx tsc --noEmit
# Should compile without errors
```

---

### Task 2.2: Create adminConfig service
**Priority:** P0  
**Files:** `web_ui/src/services/adminConfig.service.ts`  
**Type:** CREATE

**Steps:**
1. Create file with full implementation from PRD Section 6, File 9
2. Implement `adminConfigService` with methods:
   - `getConfig()`, `setConfigParam()`, `resetConfigParam()`, `resetAllConfig()`
   - `getPrompts()`, `getPrompt()`, `setPrompt()`, `resetPrompt()`, `resetAllPrompts()`
   - `getHistory()`, `exportOverrides()`, `importOverrides()`
   - `resetAll()`
3. Use `getDevApiKey()` to retrieve API key from localStorage

**Verification:**
- TypeScript compiles without errors
- Service methods match API endpoint signatures

---

### Task 2.3: Create useAdminConfig hook
**Priority:** P0  
**Files:** `web_ui/src/hooks/useAdminConfig.ts`  
**Type:** CREATE

**Steps:**
1. Create file with full implementation from PRD Section 6, File 10
2. Implement state management for:
   - `configData`, `prompts`, `selectedPrompt`
   - `isLoading`, `isSaving`, `error`, `successMessage`
3. Implement callback methods:
   - `loadConfig()`, `loadPrompts()`, `loadPromptDetail()`
   - `saveConfigParam()`, `resetConfigParam()`, `resetAllConfig()`
   - `savePrompt()`, `resetPrompt()`, `resetAllPrompts()`
   - `exportOverrides()`, `importOverrides()`

**Verification:**
- TypeScript compiles without errors
- Hook returns all required methods

---

### Task 2.4: Create ConfigGroupPanel component
**Priority:** P0  
**Files:** `web_ui/src/components/admin/ConfigGroupPanel.tsx`  
**Type:** CREATE

**Steps:**
1. Create file with full implementation from PRD Section 6, File 11
2. Implement:
   - Group rendering with label
   - Input types: `bool` (checkbox), `select` (dropdown), `int/float` (number input)
   - Dirty state tracking (modified but not saved)
   - Override badge display
   - Reasoning model detection for temperature blocking
   - Save/Reset buttons per param and "Save All"

**Key Features:**
- Block `LLM_TEMPERATURE` when model starts with `gpt-5`, `o1`, `o3`, `o4`
- Show orange "override" badge for overridden params
- Show blue "изменено" badge for dirty params

**Verification:**
- Component renders without errors
- Temperature field is disabled for reasoning models

---

### Task 2.5: Create PromptEditorPanel component
**Priority:** P0  
**Files:** `web_ui/src/components/admin/PromptEditorPanel.tsx`  
**Type:** CREATE

**Steps:**
1. Create file with full implementation from PRD Section 6, File 12
2. Implement:
   - Left sidebar: prompt list with preview
   - Right panel: textarea editor
   - Diff mode: side-by-side original vs edited
   - Save/Reset buttons
   - Character count display
   - Override indicator

**Verification:**
- Component renders prompt list
- Diff mode shows original and edited text side-by-side
- Save button is disabled when no changes

---

### Task 2.6: Create HistoryPanel component
**Priority:** P0  
**Files:** `web_ui/src/components/admin/HistoryPanel.tsx`  
**Type:** CREATE

**Steps:**
1. Create file with full implementation from PRD Section 6, File 13
2. Implement:
   - Reverse chronological order (newest first)
   - Badge colors by type: config (blue), config_reset (gray), prompt (amber), prompt_reset (gray)
   - Old → New value display with red/green backgrounds
   - Timestamp formatting

**Verification:**
- History entries display correctly
- Badges show correct colors

---

### Task 2.7: Create AdminPanel main component
**Priority:** P0  
**Files:** `web_ui/src/components/admin/AdminPanel.tsx`  
**Type:** CREATE

**Steps:**
1. Create file with full implementation from PRD Section 6, File 14
2. Implement:
   - Header with Export/Import/Full Reset buttons
   - Tab navigation: LLM, Retrieval, Memory, Storage, Runtime, Prompts, History
   - Conditional rendering based on active tab
   - Error/success notifications
   - Loading states
   - File input for JSON import

**Verification:**
- All 7 tabs render correctly
- Tab switching works
- Notifications appear on save/reset

---

### Task 2.8: Register admin route in web_ui router
**Priority:** P0  
**Files:** `web_ui/src/App.tsx` or `web_ui/src/router.tsx`  
**Type:** MODIFY

**Steps:**
1. Find routing configuration file
2. Add import:
   ```tsx
   import { AdminPanel } from './components/admin/AdminPanel';
   ```
3. Add route:
   ```tsx
   <Route path="/admin" element={<AdminPanel />} />
   ```
4. If navigation menu exists, add link:
   ```tsx
   <NavLink to="/admin">⚙️ Admin</NavLink>
   ```
5. Show link only for dev users (check existing auth logic)

**Verification:**
- Navigate to `http://localhost:3000/admin`
- Admin Panel renders with all tabs

---

### Task 2.9: TypeScript compilation check
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

## 🧪 Phase 3: End-to-End Testing

### Task 3.1: Full E2E test
**Priority:** P0  
**Files:** N/A (testing)  
**Type:** TEST

**Execute steps from PRD Section 7, Step 10:**

1. Open `http://localhost:3000/admin`
2. Go to **🤖 LLM** tab
3. Change `LLM_TEMPERATURE` to `0.3` → click ✓
4. Verify orange "override" badge appears
5. Send test query to bot via main UI
6. Go to **🕐 History** tab → verify change record exists
7. Click ↩ next to `LLM_TEMPERATURE` → badge disappears, value returns to `0.7`
8. Go to **📝 Prompts** tab → select `🟢 SD: Green`
9. Change text → Save
10. Click "Показать оригинал" → left: original, right: edited
11. Click ↩ Вернуть оригинал → prompt resets to default

**Expected Results:**
- All UI interactions work smoothly
- Changes persist across page refreshes
- Bot uses updated config without restart

---

## 📝 Definition of Done Checklist

### Backend:
- [ ] `RuntimeConfig` inherits `Config`, `__getattribute__` intercepts only `EDITABLE_CONFIG` params
- [ ] All class methods work unchanged (`get_token_param_name`, `supports_custom_temperature`, etc.)
- [ ] `admin_overrides.json` created atomically, thread-safe
- [ ] All 11 `/api/admin/*` endpoints return correct responses
- [ ] Endpoints return `401` for invalid `X-API-Key`
- [ ] Smoke tests (Task 1.7) all pass
- [ ] `admin_overrides.json` in `.gitignore`, `data/.gitkeep` in git

### Prompts:
- [ ] All direct `.md` reads inside functions replaced with `config.get_prompt(name)["text"]`
- [ ] Global scope reads marked with TODO comment
- [ ] Hot-reload works: UI changes apply without restart

### Frontend:
- [ ] `npx tsc --noEmit` passes with 0 errors
- [ ] All 5 config groups render on tabs
- [ ] `LLM_TEMPERATURE` field blocked for reasoning models
- [ ] Override badges display correctly
- [ ] Prompt editor shows diff mode
- [ ] Export downloads JSON, Import restores state
- [ ] `/admin` route accessible with valid dev key

---

## 🚀 Implementation Order

**Execute tasks in strict order:**

1. **Task 1.1** → Create `.gitkeep`, update `.gitignore`
2. **Task 1.2** → Create `runtime_config.py`
3. **Task 1.3** → Modify `config.py` last line
4. **Task 1.4** → Scan and update prompt reads
5. **Task 1.5** → Create `admin_routes.py`
6. **Task 1.6** → Register router in `main.py`
7. **Task 1.7** → Backend smoke tests (must pass before frontend)
8. **Task 2.1** → Create TypeScript types
9. **Task 2.2** → Create adminConfig service
10. **Task 2.3** → Create useAdminConfig hook
11. **Task 2.4** → Create ConfigGroupPanel
12. **Task 2.5** → Create PromptEditorPanel
13. **Task 2.6** → Create HistoryPanel
14. **Task 2.7** → Create AdminPanel
15. **Task 2.8** → Register route in web_ui
16. **Task 2.9** → TypeScript compilation check
17. **Task 3.1** → Full E2E test

---

## ⚠️ Critical Warnings

1. **Circular Import Safety:** Task 1.3 is safe because `Config` class is fully defined before `runtime_config.py` imports it
2. **Thread Safety:** `RuntimeConfig._lock` protects concurrent access in async FastAPI
3. **Atomic Writes:** `_save_overrides()` uses `tempfile + os.replace` for crash-safe writes
4. **Caching:** Overrides cached by `mtime` — rereads only on file change
5. **Reasoning Models:** Temperature must be visually blocked for `gpt-5*`, `o1`, `o3`, `o4`

---

## 📌 Out of Scope (v2.0.1)

- Editing `MODE_MAX_TOKENS` (dict type not supported)
- Role-based access (single `dev` role only)
- Prompt versioning (only last 50 history entries)
- Real-time notifications (WebSocket/SSE)
- Editing secrets (`OPENAI_API_KEY`, etc.)

---

**Ready for implementation. Start with Task 1.1.**
