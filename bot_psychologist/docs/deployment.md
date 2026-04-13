# Р Р°Р·РІС‘СЂС‚С‹РІР°РЅРёРµ

## РќР°РІРёРіР°С†РёСЏ

- [РќР°Р·Р°Рґ Рє README](../README.md)
- [РћР±Р·РѕСЂ РїСЂРѕРµРєС‚Р°](./overview.md)
- [РљРѕРЅС„РёРіСѓСЂР°С†РёСЏ](./configuration.md)

---

## РћРїРёСЃР°РЅРёРµ Рё РЅР°Р·РЅР°С‡РµРЅРёРµ

**РќР°Р·РЅР°С‡РµРЅРёРµ РґРѕРєСѓРјРµРЅС‚Р°**: РћРїРёСЃР°С‚СЊ РїСЂРѕС†РµСЃСЃ СЂР°Р·РІС‘СЂС‚С‹РІР°РЅРёСЏ Bot Psychologist РґР»СЏ Р»РѕРєР°Р»СЊРЅРѕР№ СЂР°Р·СЂР°Р±РѕС‚РєРё Рё production.

**Р”Р»СЏ РєРѕРіРѕ**: Р Р°Р·СЂР°Р±РѕС‚С‡РёРєРё, DevOps РёРЅР¶РµРЅРµСЂС‹.

**Р§С‚Рѕ СЃРѕРґРµСЂР¶РёС‚**:
- Р›РѕРєР°Р»СЊРЅС‹Р№ Р·Р°РїСѓСЃРє
- Production СЂР°Р·РІС‘СЂС‚С‹РІР°РЅРёРµ
- Docker (РѕРїС†РёРѕРЅР°Р»СЊРЅРѕ)
- РњРѕРЅРёС‚РѕСЂРёРЅРі Рё Р»РѕРіРёСЂРѕРІР°РЅРёРµ

---

## Р›РѕРєР°Р»СЊРЅС‹Р№ Р·Р°РїСѓСЃРє

### РџСЂРµРґРІР°СЂРёС‚РµР»СЊРЅС‹Рµ С‚СЂРµР±РѕРІР°РЅРёСЏ

- Python 3.10+
- Node.js 18+ (РґР»СЏ Web UI)
- Р”Р°РЅРЅС‹Рµ РёР· `voice_bot_pipeline` (SAG v2.0 JSON С„Р°Р№Р»С‹)

### РЁР°Рі 1: РЈСЃС‚Р°РЅРѕРІРєР° Р·Р°РІРёСЃРёРјРѕСЃС‚РµР№

```bash
cd bot_psychologist

# Python Р·Р°РІРёСЃРёРјРѕСЃС‚Рё
pip install -r requirements_bot.txt
pip install -r api/requirements.txt

# Node.js Р·Р°РІРёСЃРёРјРѕСЃС‚Рё (РґР»СЏ Web UI)
cd web_ui
npm install
cd ..
```

### РЁР°Рі 2: РќР°СЃС‚СЂРѕР№РєР° РїРµСЂРµРјРµРЅРЅС‹С… РѕРєСЂСѓР¶РµРЅРёСЏ

РЎРѕР·РґР°Р№С‚Рµ `.env` С„Р°Р№Р»:

```bash
cp .env.example .env
# РћС‚СЂРµРґР°РєС‚РёСЂСѓР№С‚Рµ .env Рё РґРѕР±Р°РІСЊС‚Рµ OPENAI_API_KEY
```

### РЁР°Рі 3: РџСЂРѕРІРµСЂРєР° РґР°РЅРЅС‹С…

РЈР±РµРґРёС‚РµСЃСЊ, С‡С‚Рѕ РґР°РЅРЅС‹Рµ РґРѕСЃС‚СѓРїРЅС‹:

```bash
# РџСЂРѕРІРµСЂРёС‚СЊ РЅР°Р»РёС‡РёРµ sag_final РґР°РЅРЅС‹С…
ls ../voice_bot_pipeline/data/sag_final/
```

### РЁР°Рі 4: Р—Р°РїСѓСЃРє С‚РµСЃС‚РѕРІ

```bash
# Phase 1
python test_phase1.py

# Phase 2
python test_phase2.py

# Phase 3
python test_phase3.py

# Phase 4
python test_phase4.py
```

### РЁР°Рі 5: Р—Р°РїСѓСЃРє API СЃРµСЂРІРµСЂР°

```bash
cd api
uvicorn main:app --reload --port 8000
```

API Р±СѓРґРµС‚ РґРѕСЃС‚СѓРїРµРЅ РїРѕ Р°РґСЂРµСЃСѓ `http://localhost:8000`.

### РЁР°Рі 6: Р—Р°РїСѓСЃРє Web UI

```bash
cd web_ui
npm run dev
```

Web UI Р±СѓРґРµС‚ РґРѕСЃС‚СѓРїРµРЅ РїРѕ Р°РґСЂРµСЃСѓ `http://localhost:5173`.

---

## Production СЂР°Р·РІС‘СЂС‚С‹РІР°РЅРёРµ

### Р РµРєРѕРјРµРЅРґР°С†РёРё

1. **РСЃРїРѕР»СЊР·СѓР№С‚Рµ РїСЂРѕС†РµСЃСЃ-РјРµРЅРµРґР¶РµСЂ**: systemd, supervisor, РёР»Рё PM2
2. **РќР°СЃС‚СЂРѕР№С‚Рµ reverse proxy**: Nginx РёР»Рё Apache
3. **РСЃРїРѕР»СЊР·СѓР№С‚Рµ HTTPS**: SSL/TLS СЃРµСЂС‚РёС„РёРєР°С‚С‹
4. **РќР°СЃС‚СЂРѕР№С‚Рµ РјРѕРЅРёС‚РѕСЂРёРЅРі**: Р»РѕРіРёСЂРѕРІР°РЅРёРµ, РјРµС‚СЂРёРєРё, Р°Р»РµСЂС‚С‹
5. **РСЃРїРѕР»СЊР·СѓР№С‚Рµ СЃРµРєСЂРµС‚С‹**: С…СЂР°РЅРёС‚Рµ API РєР»СЋС‡Рё РІ СЃРµРєСЂРµС‚Р°С…

### Systemd Service

РЎРѕР·РґР°Р№С‚Рµ С„Р°Р№Р» `/etc/systemd/system/bot-psychologist-api.service`:

```ini
[Unit]
Description=Bot Psychologist API
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/app/bot_psychologist/api
Environment="PATH=/app/venv/bin"
ExecStart=/app/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

**Р—Р°РїСѓСЃРє**:
```bash
sudo systemctl enable bot-psychologist-api
sudo systemctl start bot-psychologist-api
```

### Nginx Reverse Proxy

РЎРѕР·РґР°Р№С‚Рµ С„Р°Р№Р» `/etc/nginx/sites-available/bot-psychologist`:

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location / {
        root /app/bot_psychologist/web_ui/dist;
        try_files $uri $uri/ /index.html;
    }
}
```

**РђРєС‚РёРІР°С†РёСЏ**:
```bash
sudo ln -s /etc/nginx/sites-available/bot-psychologist /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## Docker СЂР°Р·РІС‘СЂС‚С‹РІР°РЅРёРµ (РѕРїС†РёРѕРЅР°Р»СЊРЅРѕ)

### Dockerfile РґР»СЏ API

РЎРѕР·РґР°Р№С‚Рµ `Dockerfile` РІ `api/`:

```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Dockerfile РґР»СЏ Web UI

РЎРѕР·РґР°Р№С‚Рµ `Dockerfile` РІ `web_ui/`:

```dockerfile
FROM node:18-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
```

### Docker Compose

РЎРѕР·РґР°Р№С‚Рµ `docker-compose.yml`:

```yaml
version: '3.8'

services:
  api:
    build: ./api
    ports:
      - "8000:8000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - DATA_ROOT=/app/data
    volumes:
      - ../voice_bot_pipeline/data:/app/data:ro
    restart: unless-stopped

  web:
    build: ./web_ui
    ports:
      - "80:80"
    depends_on:
      - api
    restart: unless-stopped
```

**Р—Р°РїСѓСЃРє**:
```bash
docker-compose up -d
```

---

## РњРѕРЅРёС‚РѕСЂРёРЅРі Рё Р»РѕРіРёСЂРѕРІР°РЅРёРµ

### Р›РѕРіРёСЂРѕРІР°РЅРёРµ

Р›РѕРіРё СЃРѕС…СЂР°РЅСЏСЋС‚СЃСЏ РІ:
- `logs/bot_agent/bot_agent.log` вЂ” Р»РѕРіРё Bot Agent
- РљРѕРЅСЃРѕР»СЊ вЂ” Р»РѕРіРё API СЃРµСЂРІРµСЂР°

### РњРµС‚СЂРёРєРё

Р РµРєРѕРјРµРЅРґСѓРµС‚СЃСЏ РґРѕР±Р°РІРёС‚СЊ:
- РљРѕР»РёС‡РµСЃС‚РІРѕ Р·Р°РїСЂРѕСЃРѕРІ
- Р’СЂРµРјСЏ РѕР±СЂР°Р±РѕС‚РєРё
- РћС€РёР±РєРё
- РСЃРїРѕР»СЊР·РѕРІР°РЅРёРµ СЂРµСЃСѓСЂСЃРѕРІ

### Health Check

РСЃРїРѕР»СЊР·СѓР№С‚Рµ endpoint `/api/v1/health` РґР»СЏ РїСЂРѕРІРµСЂРєРё СЃРѕСЃС‚РѕСЏРЅРёСЏ:

```bash
curl http://localhost:8000/api/v1/health
```

---

## Р РµР·РµСЂРІРЅРѕРµ РєРѕРїРёСЂРѕРІР°РЅРёРµ

### Р”Р°РЅРЅС‹Рµ РґР»СЏ СЂРµР·РµСЂРІРЅРѕРіРѕ РєРѕРїРёСЂРѕРІР°РЅРёСЏ

1. **РСЃС‚РѕСЂРёСЏ РґРёР°Р»РѕРіРѕРІ**: `.cache_bot_agent/conversations/`
2. **РљРѕРЅС„РёРіСѓСЂР°С†РёСЏ**: `.env` (Р±РµР· СЃРµРєСЂРµС‚РѕРІ)
3. **Р›РѕРіРё**: `logs/`

### РџСЂРёРјРµСЂ СЃРєСЂРёРїС‚Р° СЂРµР·РµСЂРІРЅРѕРіРѕ РєРѕРїРёСЂРѕРІР°РЅРёСЏ

```bash
#!/bin/bash
BACKUP_DIR="/backups/bot-psychologist"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Р РµР·РµСЂРІРЅРѕРµ РєРѕРїРёСЂРѕРІР°РЅРёРµ РёСЃС‚РѕСЂРёРё РґРёР°Р»РѕРіРѕРІ
tar -czf $BACKUP_DIR/conversations_$DATE.tar.gz .cache_bot_agent/conversations/

# Р РµР·РµСЂРІРЅРѕРµ РєРѕРїРёСЂРѕРІР°РЅРёРµ Р»РѕРіРѕРІ
tar -czf $BACKUP_DIR/logs_$DATE.tar.gz logs/

echo "Backup completed: $DATE"
```

---

## РћР±РЅРѕРІР»РµРЅРёРµ

### РћР±РЅРѕРІР»РµРЅРёРµ РєРѕРґР°

```bash
# РћСЃС‚Р°РЅРѕРІРёС‚СЊ СЃРµСЂРІРёСЃС‹
sudo systemctl stop bot-psychologist-api

# РћР±РЅРѕРІРёС‚СЊ РєРѕРґ
git pull

# РћР±РЅРѕРІРёС‚СЊ Р·Р°РІРёСЃРёРјРѕСЃС‚Рё
pip install -r requirements_bot.txt
pip install -r api/requirements.txt

# РџРµСЂРµР·Р°РїСѓСЃС‚РёС‚СЊ СЃРµСЂРІРёСЃС‹
sudo systemctl start bot-psychologist-api
```

### РћР±РЅРѕРІР»РµРЅРёРµ РґР°РЅРЅС‹С…

РџСЂРё РѕР±РЅРѕРІР»РµРЅРёРё РґР°РЅРЅС‹С… РёР· `voice_bot_pipeline`:

1. РћР±РЅРѕРІРёС‚Рµ РґР°РЅРЅС‹Рµ РІ `voice_bot_pipeline`
2. РџРµСЂРµР·Р°РїСѓСЃС‚РёС‚Рµ API СЃРµСЂРІРµСЂ (РґР°РЅРЅС‹Рµ Р·Р°РіСЂСѓР·СЏС‚СЃСЏ Р°РІС‚РѕРјР°С‚РёС‡РµСЃРєРё)

---

## Troubleshooting

### РџСЂРѕР±Р»РµРјР°: API РЅРµ Р·Р°РїСѓСЃРєР°РµС‚СЃСЏ

**Р РµС€РµРЅРёРµ**:
1. РџСЂРѕРІРµСЂСЊС‚Рµ РїРµСЂРµРјРµРЅРЅС‹Рµ РѕРєСЂСѓР¶РµРЅРёСЏ: `python -c "from bot_agent.config import config; config.validate()"`
2. РџСЂРѕРІРµСЂСЊС‚Рµ РЅР°Р»РёС‡РёРµ РґР°РЅРЅС‹С…: `ls ../voice_bot_pipeline/data/sag_final/`
3. РџСЂРѕРІРµСЂСЊС‚Рµ Р»РѕРіРё: `tail -f logs/bot_agent/bot_agent.log`

### РџСЂРѕР±Р»РµРјР°: Web UI РЅРµ РїРѕРґРєР»СЋС‡Р°РµС‚СЃСЏ Рє API

**Р РµС€РµРЅРёРµ**:
1. РџСЂРѕРІРµСЂСЊС‚Рµ `VITE_API_URL` РІ `.env.local`
2. РџСЂРѕРІРµСЂСЊС‚Рµ CORS РЅР°СЃС‚СЂРѕР№РєРё РІ API
3. РџСЂРѕРІРµСЂСЊС‚Рµ РґРѕСЃС‚СѓРїРЅРѕСЃС‚СЊ API: `curl http://localhost:8000/api/v1/health`

### РџСЂРѕР±Р»РµРјР°: РњРµРґР»РµРЅРЅС‹Рµ РѕС‚РІРµС‚С‹

**Р РµС€РµРЅРёРµ**:
1. РџСЂРѕРІРµСЂСЊС‚Рµ РєРѕР»РёС‡РµСЃС‚РІРѕ Р±Р»РѕРєРѕРІ РІ РґР°РЅРЅС‹С…
2. РћРїС‚РёРјРёР·РёСЂСѓР№С‚Рµ `TOP_K_BLOCKS` РІ РєРѕРЅС„РёРіСѓСЂР°С†РёРё
3. РСЃРїРѕР»СЊР·СѓР№С‚Рµ Р±РѕР»РµРµ Р±С‹СЃС‚СЂСѓСЋ РјРѕРґРµР»СЊ LLM

---

## РќР°РІРёРіР°С†РёСЏ

- [РћР±Р·РѕСЂ РїСЂРѕРµРєС‚Р°](./overview.md)
- [РљРѕРЅС„РёРіСѓСЂР°С†РёСЏ](./configuration.md)
- [РўРµСЃС‚РёСЂРѕРІР°РЅРёРµ](./testing.md)

