$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent
Set-Location $Root

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    & "$PSScriptRoot\setup.ps1"
}

& .\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
& "$PSScriptRoot\check.ps1"

Remove-Item build, dist, release -Recurse -Force -ErrorAction SilentlyContinue
& .\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean TCMExpert.spec

New-Item -ItemType Directory -Force release | Out-Null
Copy-Item README.md, USER_GUIDE.md, BACKUP_GUIDE.md, LICENSE dist\TCMExpert
Compress-Archive -Path dist\TCMExpert\* -DestinationPath release\TCMExpert-2.1.5-Windows-x64.zip

$Iscc = Get-Command ISCC.exe -ErrorAction SilentlyContinue
if ($Iscc) {
    & $Iscc.Source installer\TCMExpert.iss
} else {
    Write-Host "Inno Setup chưa cài; đã tạo bản portable." -ForegroundColor Yellow
}

Write-Host "Build hoàn tất trong thư mục release." -ForegroundColor Green
