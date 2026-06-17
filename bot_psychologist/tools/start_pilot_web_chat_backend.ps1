Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$botRoot = Resolve-Path (Join-Path $scriptDir "..")
Set-Location $botRoot

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    throw "Missing bot_psychologist/.venv. Restore the virtualenv first."
}

$env:APP_ENV = "local"
$env:DEBUG_TRACE_ENABLED = "true"
$env:PYTHONUTF8 = "1"

Write-Host "Starting Bot backend for pilot/manual Web Chat parity..."
Write-Host "APP_ENV=$env:APP_ENV"
Write-Host "DEBUG_TRACE_ENABLED=$env:DEBUG_TRACE_ENABLED"
Write-Host "WRITER_KB_PAYLOAD_ENABLED effective default is resolved from APP_ENV."

& ".venv\Scripts\python.exe" -m uvicorn api.main:app --host 0.0.0.0 --port 8001
