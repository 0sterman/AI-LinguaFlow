$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$distApp = Join-Path $root "dist\LinguaPopUp AI"
$workRoot = Join-Path ([System.IO.Path]::GetTempPath()) "LinguaPopUpAIInstallerBuild"
$payloadRoot = Join-Path $workRoot "payload"
$payloadAppRoot = Join-Path $payloadRoot "app"
$zipPath = Join-Path $payloadRoot "LinguaPopUpAI_payload.zip"
$installerWork = Join-Path $workRoot "pyinstaller"
$installerDist = Join-Path $workRoot "dist"
$installerSpec = Join-Path $workRoot "spec"
$tempInstaller = Join-Path $installerDist "LinguaPopUp AI Setup.exe"
$tempUninstaller = Join-Path $installerDist "LinguaPopUp AI Uninstall.exe"
$targetInstaller = Join-Path $root "dist\LinguaPopUp AI Setup.exe"

Get-Process -Name "LinguaPopUp AI Setup" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Get-Process -Name "LinguaPopUp AI Uninstall" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Get-Process -Name "LinguaFlow AI Setup" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Get-Process -Name "LinguaFlow AI Uninstall" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue

& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root "build.ps1")
if ($LASTEXITCODE -ne 0) {
    throw "Build failed with exit code $LASTEXITCODE"
}

if (-not (Test-Path -LiteralPath (Join-Path $distApp "LinguaPopUp AI.exe"))) {
    throw "Build output is missing: $distApp"
}

if (Test-Path -LiteralPath $workRoot) {
    Remove-Item -LiteralPath $workRoot -Recurse -Force
}

python -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --windowed `
    --uac-admin `
    --name "LinguaPopUp AI Uninstall" `
    --icon (Join-Path $root "assets\app_icon.ico") `
    --version-file (Join-Path $root "version_info_setup.txt") `
    --add-data "$(Join-Path $root "assets\app_icon.ico");assets" `
    --distpath $installerDist `
    --workpath $installerWork `
    --specpath $installerSpec `
    (Join-Path $root "installer\uninstaller_app.py")

if ($LASTEXITCODE -ne 0) {
    throw "Uninstaller build failed with exit code $LASTEXITCODE"
}

if (-not (Test-Path -LiteralPath $tempUninstaller)) {
    throw "Uninstaller was not created: $tempUninstaller"
}

Copy-Item -LiteralPath $tempUninstaller -Destination (Join-Path $distApp "LinguaPopUp AI Uninstall.exe") -Force
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root "code_sign.ps1") -Path (Join-Path $distApp "LinguaPopUp AI Uninstall.exe")

if (Test-Path -LiteralPath $workRoot) {
    Remove-Item -LiteralPath $workRoot -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $payloadAppRoot | Out-Null

Copy-Item -LiteralPath $distApp -Destination $payloadAppRoot -Recurse -Force
Compress-Archive -LiteralPath (Join-Path $payloadAppRoot "LinguaPopUp AI") -DestinationPath $zipPath -Force

python -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --windowed `
    --uac-admin `
    --name "LinguaPopUp AI Setup" `
    --icon (Join-Path $root "assets\app_icon.ico") `
    --version-file (Join-Path $root "version_info_setup.txt") `
    --add-data "$zipPath;." `
    --add-data "$(Join-Path $root "assets\app_icon.ico");." `
    --add-data "$(Join-Path $root "assets\app_icon.png");." `
    --add-data "$(Join-Path $root "assets\installer_logo.png");." `
    --distpath $installerDist `
    --workpath $installerWork `
    --specpath $installerSpec `
    (Join-Path $root "installer\installer_app.py")

if ($LASTEXITCODE -ne 0) {
    throw "Installer build failed with exit code $LASTEXITCODE"
}

if (-not (Test-Path -LiteralPath $tempInstaller)) {
    throw "Installer was not created: $tempInstaller"
}

Get-Process -Name "LinguaPopUp AI Setup" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Get-Process -Name "LinguaFlow AI Setup" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Copy-Item -LiteralPath $tempInstaller -Destination $targetInstaller -Force
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root "code_sign.ps1") -Path $targetInstaller
Write-Host "Built $targetInstaller"

