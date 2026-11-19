$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)
if (-not (Test-Path .venv\Scripts\python.exe)) { throw "Ejecute primero scripts/setup.ps1" }
$backend = Start-Process -FilePath (Resolve-Path .venv\Scripts\python.exe) `
   -ArgumentList "-m uvicorn backend.app.main:app --host 127.0.0.1 --port 8088" -PassThru
try {
  Set-Location frontend
  Write-Host "Frontend http://127.0.0.1:5173 (cerrar con Ctrl+C)" -ForegroundColor Green
  npm run dev
} finally {
  Stop-Process -Id $backend.Id -ErrorAction SilentlyContinue
}
