param([string]$RunId)
$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)
if (-not $RunId -or $RunId -notmatch '^[a-f0-9-]{36}$') { throw "Indique -RunId UUID de una corrida valida." }
$dir = Join-Path "resultsuns" $RunId
if (-not (Test-Path $dir)) { throw "No existe la corrida." }
$dest = Join-Path "results" ("evidence_"+$RunId+".zip")
Compress-Archive -Path (Join-Path $dir '*') -DestinationPath $dest -Force
Write-Host "Exportado sin secretos: $dest"
