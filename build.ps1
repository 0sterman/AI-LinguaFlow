$ErrorActionPreference = "Stop"

python -m PyInstaller `
  --noconfirm `
  --clean `
  --windowed `
  --name WindowsTranslator `
  --hidden-import keyring.backends.Windows `
  translator_app\__main__.py

Write-Host "Built dist\WindowsTranslator\WindowsTranslator.exe"
