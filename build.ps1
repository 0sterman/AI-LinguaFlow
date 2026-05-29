$ErrorActionPreference = "Stop"

Get-Process -Name "LinguaFlow AI" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue

python -m PyInstaller `
  --noconfirm `
  --clean `
  --windowed `
  --name "LinguaFlow AI" `
  --icon assets\app_icon.ico `
  --add-data "assets\app_icon.ico;assets" `
  --add-data "assets\app_icon.png;assets" `
  --add-data "assets\dropdown_arrow.svg;assets" `
  --hidden-import keyring.backends.Windows `
  translator_app\__main__.py

if ($LASTEXITCODE -ne 0) {
  throw "PyInstaller failed with exit code $LASTEXITCODE"
}

Write-Host "Built dist\LinguaFlow AI\LinguaFlow AI.exe"
