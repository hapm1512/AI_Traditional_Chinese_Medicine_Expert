$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
& .\.venv\Scripts\python.exe -m ruff check .
& .\.venv\Scripts\python.exe -m pytest -q
Write-Host "All checks passed." -ForegroundColor Green

