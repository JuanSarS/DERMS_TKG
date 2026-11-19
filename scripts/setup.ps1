$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)
if (-not (Test-Path .venv)) { py -3 -m venv .venv }
& .\.venv\Scripts\python.exe -m pip install -e ".[dev]"
if (-not (Test-Path secrets\opendss.local.json)) {
  Copy-Item secrets\opendss.example.json secrets\opendss.local.json
  Write-Host "Configure usuario y contrasena en secrets/opendss.local.json (solo local)." -ForegroundColor Yellow
}
& .\.venv\Scripts\python.exe -m ruff format backend tests scripts
& .\.venv\Scripts\python.exe -m ruff check --fix backend tests scripts
& .\.venv\Scripts\python.exe -m ruff format backend tests scripts
Set-Location frontend
npm install
npm run format
npx biome check --write .
npm run lint
Write-Host "Setup concluido. Los secretos NO se incluyen en Git." -ForegroundColor Green
