# Web UI (Веб-интерфейс)

## Purpose (Назначение)
React-приложение для chat, diagnostics и admin-adjacent operator workflows поверх REST API.

## Current contract alignment (Согласование с текущим contract)
- Backend API — multiagent-only на уровне runtime.
- Trace widgets потребляют multiagent trace payloads.
- UI не должен показывать legacy cascade как active runtime option.
- Admin включает отдельную вкладку `Diagnostic Center`, backed by:
  - `GET /api/v1/admin/diagnostic-center/effective`
  - `POST /api/v1/admin/diagnostic-center/control`
  - `POST /api/v1/admin/diagnostic-center/reset`
- `developer_local_all_users` должен быть явно помечен как single-developer local mode, а не production rollout.

## Local start (Локальный запуск)
```powershell
cd C:\My_practice\Text_transcription\bot_psychologist\web_ui
npm install
npm run dev
```

URL по умолчанию:
- `http://localhost:3000`

## Build (Сборка)
```powershell
npm run build
```

## Required env (Обязательные env)
- `VITE_API_URL` (пример: `http://localhost:8001/api/v1`)
- `VITE_API_KEY` (dev/test key)

## Minimal UI smoke (Минимальный UI smoke)
1. Откройте chat page и отправьте одно сообщение.
2. Убедитесь, что response непустой.
3. Откройте trace panel и подтвердите видимость writer model metadata.
4. Подтвердите, что runtime badge указывает multiagent runtime.
