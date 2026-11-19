param([switch]$ConfirmRemoteMutation)
if (-not $ConfirmRemoteMutation) {
  throw "Esta prueba crea una sesion remota QSTS de 3 pasos. Use -ConfirmRemoteMutation de forma explicita."
}
$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)
& .\.venv\Scripts\python.exe scripts
emote_smoke.py
