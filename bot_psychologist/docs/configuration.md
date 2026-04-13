# РљРѕРЅС„РёРіСѓСЂР°С†РёСЏ

## РќР°РІРёРіР°С†РёСЏ

- [РќР°Р·Р°Рґ Рє README](../README.md)
- [РћР±Р·РѕСЂ РїСЂРѕРµРєС‚Р°](./overview.md)
- [Р Р°Р·РІС‘СЂС‚С‹РІР°РЅРёРµ](./deployment.md)

---

## РћРїРёСЃР°РЅРёРµ Рё РЅР°Р·РЅР°С‡РµРЅРёРµ

**РќР°Р·РЅР°С‡РµРЅРёРµ РґРѕРєСѓРјРµРЅС‚Р°**: РћРїРёСЃР°С‚СЊ РІСЃРµ РЅР°СЃС‚СЂРѕР№РєРё РєРѕРЅС„РёРіСѓСЂР°С†РёРё РїСЂРѕРµРєС‚Р° Bot Psychologist, РїРµСЂРµРјРµРЅРЅС‹Рµ РѕРєСЂСѓР¶РµРЅРёСЏ Рё РїР°СЂР°РјРµС‚СЂС‹.

**Р”Р»СЏ РєРѕРіРѕ**: Р Р°Р·СЂР°Р±РѕС‚С‡РёРєРё, РЅР°СЃС‚СЂР°РёРІР°СЋС‰РёРµ РїСЂРѕРµРєС‚, DevOps РёРЅР¶РµРЅРµСЂС‹.

**Р§С‚Рѕ СЃРѕРґРµСЂР¶РёС‚**:
- РџРµСЂРµРјРµРЅРЅС‹Рµ РѕРєСЂСѓР¶РµРЅРёСЏ
- РљРѕРЅС„РёРіСѓСЂР°С†РёСЏ Bot Agent
- РљРѕРЅС„РёРіСѓСЂР°С†РёСЏ API
- РљРѕРЅС„РёРіСѓСЂР°С†РёСЏ Web UI
- РџСЂРёРјРµСЂС‹ РєРѕРЅС„РёРіСѓСЂР°С†РёРѕРЅРЅС‹С… С„Р°Р№Р»РѕРІ

---

## РџРµСЂРµРјРµРЅРЅС‹Рµ РѕРєСЂСѓР¶РµРЅРёСЏ

### .env С„Р°Р№Р»

РЎРѕР·РґР°Р№С‚Рµ С„Р°Р№Р» `.env` РІ РєРѕСЂРЅРµ `bot_psychologist/`:

```env
# OpenAI API
OPENAI_API_KEY=sk-proj-...
PRIMARY_MODEL=gpt-4o-mini

# Р”Р°РЅРЅС‹Рµ
DATA_ROOT=../voice_bot_pipeline/data

# РћС‚Р»Р°РґРєР°
DEBUG=False

# API (РґР»СЏ Phase 5)
API_HOST=0.0.0.0
API_PORT=8000

# Web UI (РґР»СЏ Phase 6)
VITE_API_URL=http://localhost:8000/api/v1
VITE_API_KEY=test-key-001
```

### РћР±СЏР·Р°С‚РµР»СЊРЅС‹Рµ РїРµСЂРµРјРµРЅРЅС‹Рµ

- **OPENAI_API_KEY** вЂ” РєР»СЋС‡ OpenAI API (РѕР±СЏР·Р°С‚РµР»СЊРЅРѕ)
- **DATA_ROOT** вЂ” РїСѓС‚СЊ Рє РґР°РЅРЅС‹Рј `voice_bot_pipeline` (РїРѕ СѓРјРѕР»С‡Р°РЅРёСЋ: `../voice_bot_pipeline/data`)

### РћРїС†РёРѕРЅР°Р»СЊРЅС‹Рµ РїРµСЂРµРјРµРЅРЅС‹Рµ

- **PRIMARY_MODEL** вЂ” РјРѕРґРµР»СЊ LLM (РїРѕ СѓРјРѕР»С‡Р°РЅРёСЋ: `gpt-4o-mini`)
- **DEBUG** вЂ” СЂРµР¶РёРј РѕС‚Р»Р°РґРєРё (РїРѕ СѓРјРѕР»С‡Р°РЅРёСЋ: `False`)
- **API_HOST** вЂ” С…РѕСЃС‚ API СЃРµСЂРІРµСЂР° (РїРѕ СѓРјРѕР»С‡Р°РЅРёСЋ: `0.0.0.0`)
- **API_PORT** вЂ” РїРѕСЂС‚ API СЃРµСЂРІРµСЂР° (РїРѕ СѓРјРѕР»С‡Р°РЅРёСЋ: `8000`)

---

## РљРѕРЅС„РёРіСѓСЂР°С†РёСЏ Bot Agent

### Config (`bot_agent/config.py`)

**РџСѓС‚Рё Рє РґР°РЅРЅС‹Рј**:
```python
PROJECT_ROOT = Path(__file__).parent.parent  # bot_psychologist/
DATA_ROOT = Path(os.getenv("DATA_ROOT", "../voice_bot_pipeline/data"))
LEGACY_legacy_sag_final_DIR = DATA_ROOT / "LEGACY_legacy_sag_final"
```

**РџР°СЂР°РјРµС‚СЂС‹ РїРѕРёСЃРєР°**:
```python
TOP_K_BLOCKS = 5                    # РљРѕР»РёС‡РµСЃС‚РІРѕ СЂРµР»РµРІР°РЅС‚РЅС‹С… Р±Р»РѕРєРѕРІ
MIN_RELEVANCE_SCORE = 0.1          # РњРёРЅРёРјР°Р»СЊРЅС‹Р№ РїРѕСЂРѕРі СЂРµР»РµРІР°РЅС‚РЅРѕСЃС‚Рё (0-1)
```

**LLM РїР°СЂР°РјРµС‚СЂС‹**:
```python
LLM_MODEL = os.getenv("PRIMARY_MODEL", "gpt-4o-mini")
LLM_TEMPERATURE = 0.7              # РўРµРјРїРµСЂР°С‚СѓСЂР° РіРµРЅРµСЂР°С†РёРё (0-1)
LLM_MAX_TOKENS = 1500              # РњР°РєСЃРёРјР°Р»СЊРЅР°СЏ РґР»РёРЅР° РѕС‚РІРµС‚Р°
```

**РљСЌС€РёСЂРѕРІР°РЅРёРµ**:
```python
ENABLE_CACHING = True
CACHE_DIR = PROJECT_ROOT / ".cache_bot_agent"
```

**Р›РѕРіРё**:
```python
LOG_DIR = PROJECT_ROOT / "logs" / "bot_agent"
```

---

## РљРѕРЅС„РёРіСѓСЂР°С†РёСЏ API

### FastAPI (`api/main.py`)

**CORS**:
```python
allow_origins=[
    "http://localhost:3000",
    "http://localhost:8080",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8080",
    "*"  # TODO: РІ production РѕРіСЂР°РЅРёС‡РёС‚СЊ
]
```

**Trusted Host**:
```python
allowed_hosts=["localhost", "127.0.0.1", "*.example.com"]
```

### API Keys (`api/auth.py`)

**РџСЂРµРґСѓСЃС‚Р°РЅРѕРІР»РµРЅРЅС‹Рµ РєР»СЋС‡Рё**:
```python
{
    "test-key-001": {
        "name": "Test Client",
        "rate_limit": 100  # requests per minute
    },
    "dev-key-001": {
        "name": "Development",
        "rate_limit": 1000
    }
}
```

**Р”РѕР±Р°РІР»РµРЅРёРµ РЅРѕРІРѕРіРѕ РєР»СЋС‡Р°**:
```python
api_key_manager.add_api_key(
    key="your-key-here",
    name="Your Client",
    rate_limit=500
)
```

---

## РљРѕРЅС„РёРіСѓСЂР°С†РёСЏ Web UI

### Vite (`web_ui/vite.config.ts`)

```typescript
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  }
})
```

### Tailwind CSS (`web_ui/tailwind.config.js`)

```javascript
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
```

### РџРµСЂРµРјРµРЅРЅС‹Рµ РѕРєСЂСѓР¶РµРЅРёСЏ (`web_ui/.env.local`)

```env
VITE_API_URL=http://localhost:8000/api/v1
VITE_API_KEY=test-key-001
```

---

## РџСЂРёРјРµСЂС‹ РєРѕРЅС„РёРіСѓСЂР°С†РёРѕРЅРЅС‹С… С„Р°Р№Р»РѕРІ

### .env.example

```env
# OpenAI API
OPENAI_API_KEY=sk-proj-...
PRIMARY_MODEL=gpt-4o-mini

# Р”Р°РЅРЅС‹Рµ
DATA_ROOT=../voice_bot_pipeline/data

# РћС‚Р»Р°РґРєР°
DEBUG=False

# API
API_HOST=0.0.0.0
API_PORT=8000
```

### web_ui/.env.example

```env
VITE_API_URL=http://localhost:8000/api/v1
VITE_API_KEY=test-key-001
```

---

## РџСЂРѕРІРµСЂРєР° РєРѕРЅС„РёРіСѓСЂР°С†РёРё

### Р’Р°Р»РёРґР°С†РёСЏ Bot Agent

```python
from bot_agent.config import config

try:
    config.validate()
    print("вњ… РљРѕРЅС„РёРіСѓСЂР°С†РёСЏ РІР°Р»РёРґРЅР°")
except ValueError as e:
    print(f"вќЊ РћС€РёР±РєР° РєРѕРЅС„РёРіСѓСЂР°С†РёРё: {e}")
```

### РРЅС„РѕСЂРјР°С†РёСЏ Рѕ РєРѕРЅС„РёРіСѓСЂР°С†РёРё

```python
from bot_agent.config import config

print(config.info())
```

Р’С‹РІРѕРґ:
```
в•­в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв•®
в”‚ Bot Psychologist - Configuration            в”‚
в”њв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”¤
в”‚ PROJECT_ROOT: /path/to/bot_psychologist
в”‚ DATA_ROOT:    /path/to/voice_bot_pipeline/data
в”‚ LEGACY_legacy_sag_final:    /path/to/LEGACY_legacy_sag_final
в”‚ LLM_MODEL:    gpt-4o-mini
в”‚ TOP_K:        5
в”‚ DEBUG:        False
в”‚ API_KEY:      вњ“ Set
в•°в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв•Ї
```

---

## Production РєРѕРЅС„РёРіСѓСЂР°С†РёСЏ

### Р РµРєРѕРјРµРЅРґР°С†РёРё

1. **API Keys**: РСЃРїРѕР»СЊР·СѓР№С‚Рµ СЃРёР»СЊРЅС‹Рµ РєР»СЋС‡Рё, С…СЂР°РЅРёС‚Рµ РІ СЃРµРєСЂРµС‚Р°С…
2. **CORS**: РћРіСЂР°РЅРёС‡СЊС‚Рµ СЂР°Р·СЂРµС€С‘РЅРЅС‹Рµ origins
3. **Rate Limiting**: РќР°СЃС‚СЂРѕР№С‚Рµ Р»РёРјРёС‚С‹ РґР»СЏ production
4. **Logging**: РќР°СЃС‚СЂРѕР№С‚Рµ С†РµРЅС‚СЂР°Р»РёР·РѕРІР°РЅРЅРѕРµ Р»РѕРіРёСЂРѕРІР°РЅРёРµ
5. **Monitoring**: Р”РѕР±Р°РІСЊС‚Рµ РјРѕРЅРёС‚РѕСЂРёРЅРі Рё Р°Р»РµСЂС‚С‹

### РџСЂРёРјРµСЂ production .env

```env
# OpenAI API
OPENAI_API_KEY=sk-proj-...  # РР· СЃРµРєСЂРµС‚РѕРІ

# Р”Р°РЅРЅС‹Рµ
DATA_ROOT=/app/data

# РћС‚Р»Р°РґРєР°
DEBUG=False

# API
API_HOST=0.0.0.0
API_PORT=8000

# Security
ALLOWED_ORIGINS=https://yourdomain.com
TRUSTED_HOSTS=yourdomain.com
```

---

## РќР°РІРёРіР°С†РёСЏ

- [РћР±Р·РѕСЂ РїСЂРѕРµРєС‚Р°](./overview.md)
- [Р Р°Р·РІС‘СЂС‚С‹РІР°РЅРёРµ](./deployment.md)
- [РўРµСЃС‚РёСЂРѕРІР°РЅРёРµ](./testing.md)

