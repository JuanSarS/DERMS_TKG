$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)
& .\.venv\Scripts\python.exe scripts\remote_probe.py
