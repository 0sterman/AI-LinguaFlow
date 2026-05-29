$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$distApp = Join-Path $root "dist\LinguaFlow AI"
$workRoot = Join-Path ([System.IO.Path]::GetTempPath()) "LinguaFlowAIInstallerBuild"
$payloadRoot = Join-Path $workRoot "payload"
$payloadAppRoot = Join-Path $payloadRoot "app"
$zipPath = Join-Path $payloadRoot "LinguaFlowAI_payload.zip"
$installerWork = Join-Path $workRoot "pyinstaller"
$installerDist = Join-Path $workRoot "dist"
$installerSpec = Join-Path $workRoot "spec"
$tempInstaller = Join-Path $installerDist "LinguaFlow AI Setup.exe"
$targetInstaller = Join-Path $root "dist\LinguaFlow AI Setup.exe"

Get-Process -Name "LinguaFlow AI Setup" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue

& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root "build.ps1")
if ($LASTEXITCODE -ne 0) {
    throw "Build failed with exit code $LASTEXITCODE"
}

if (-not (Test-Path -LiteralPath (Join-Path $distApp "LinguaFlow AI.exe"))) {
    throw "Build output is missing: $distApp"
}

if (Test-Path -LiteralPath $workRoot) {
    Remove-Item -LiteralPath $workRoot -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $payloadAppRoot | Out-Null

Copy-Item -LiteralPath $distApp -Destination $payloadAppRoot -Recurse -Force
Compress-Archive -LiteralPath (Join-Path $payloadAppRoot "LinguaFlow AI") -DestinationPath $zipPath -Force

python -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --windowed `
    --name "LinguaFlow AI Setup" `
    --icon (Join-Path $root "assets\app_icon.ico") `
    --add-data "$zipPath;." `
    --add-data "$(Join-Path $root "assets\app_icon.ico");." `
    --add-data "$(Join-Path $root "assets\app_icon.png");." `
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

Get-Process -Name "LinguaFlow AI Setup" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Copy-Item -LiteralPath $tempInstaller -Destination $targetInstaller -Force
Write-Host "Built $targetInstaller"
