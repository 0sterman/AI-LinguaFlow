$ErrorActionPreference = "Stop"

Get-Process -Name "LinguaPopUp AI" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Get-Process -Name "LinguaFlow AI" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue

python -m PyInstaller `
  --noconfirm `
  --clean `
  --windowed `
  --name "LinguaPopUp AI" `
  --icon assets\app_icon.ico `
  --version-file version_info_app.txt `
  --add-data "assets\app_icon.ico;assets" `
  --add-data "assets\app_icon.png;assets" `
  --add-data "assets\dropdown_arrow.svg;assets" `
  --hidden-import keyring.backends.Windows `
  translator_app\__main__.py

if ($LASTEXITCODE -ne 0) {
  throw "PyInstaller failed with exit code $LASTEXITCODE"
}

& powershell -NoProfile -ExecutionPolicy Bypass -File .\code_sign.ps1 -Path "dist\LinguaPopUp AI\LinguaPopUp AI.exe"

Write-Host "Built dist\LinguaPopUp AI\LinguaPopUp AI.exe"

