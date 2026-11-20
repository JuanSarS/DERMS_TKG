param([switch]$RunRemote)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
Write-Host "[1] Pruebas Python"
python -m pytest -q
if ($LASTEXITCODE -ne 0) { throw "Fallaron pruebas Python" }
Write-Host "[2] Ruff"
ruff check backend tests
if ($LASTEXITCODE -ne 0) { throw "Falló Ruff check" }
ruff format --check backend tests
if ($LASTEXITCODE -ne 0) { throw "Falló Ruff format" }
Write-Host "[3] Frontend"
Push-Location frontend
try {
  npm test
  if ($LASTEXITCODE -ne 0) { throw "Fallaron pruebas JS" }
  npm run lint
  if ($LASTEXITCODE -ne 0) { throw "Falló Biome" }
  npm run build
  if ($LASTEXITCODE -ne 0) { throw "Falló Vite" }
} finally { Pop-Location }
Write-Host "Verificación local completada. No equivale a validación cloud."
if ($RunRemote) {
  Write-Warning "Se crearán dos modelos custom en OpenDSS remoto. Se requiere servidor activo y admin."
  $answer = Read-Host "Escriba EJECUTAR para autorizar mutaciones remotas"
  if ($answer -cne 'EJECUTAR') { Write-Host 'Prueba remota cancelada'; exit 0 }
  $health = Invoke-RestMethod -Uri 'http://127.0.0.1:8088/api/status'
  if ($health.remote.state -ne 'HEALTHY') {
    throw "Compruebe la respuesta de /api/status. No se ejecutaron POST"
  }
  $body = @{resource_scale=100; max_passes=2; load_scale=1.0; profile_file='ausgrid_c12_2011-07-01.csv'} | ConvertTo-Json
  $result = Invoke-RestMethod -Uri 'http://127.0.0.1:8088/api/coupled-runs' -Method POST -ContentType 'application/json' -Body $body
  Write-Host "Corrida iniciada: $($result.run_id). Consulte /api/runs/$($result.run_id)"
}
