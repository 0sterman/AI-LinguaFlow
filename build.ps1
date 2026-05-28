$ErrorActionPreference = "Stop"

python -m PyInstaller `
  --noconfirm `
  --clean `
  --windowed `
  --name WindowsTranslator `
  --icon assets\app_icon.ico `
  --add-data "assets\app_icon.ico;assets" `
  --hidden-import keyring.backends.Windows `
  translator_app\__main__.py

Write-Host "Built dist\WindowsTranslator\WindowsTranslator.exe"
