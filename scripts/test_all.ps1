$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)
& .\.venv\Scripts\python.exe -m ruff check backend tests scripts
& .\.venv\Scripts\python.exe -m ruff format --check backend tests scripts
& .\.venv\Scripts\python.exe -m pytest -q
Push-Location frontend
try { npm run lint; npm run test; npm run build } finally { Pop-Location }
