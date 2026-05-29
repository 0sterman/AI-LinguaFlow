param(
  [Parameter(Mandatory = $true)]
  [string]$Path
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $Path)) {
  throw "File to sign does not exist: $Path"
}

$timestampUrl = if ($env:CODESIGN_TIMESTAMP_URL) { $env:CODESIGN_TIMESTAMP_URL } else { "http://timestamp.digicert.com" }
$thumbprint = $env:CODESIGN_CERT_SHA1
$certPath = $env:CODESIGN_CERT_PATH
$certPassword = $env:CODESIGN_CERT_PASSWORD

if (-not $thumbprint -and -not $certPath) {
  Write-Host "Code signing skipped for $Path. Set CODESIGN_CERT_SHA1 or CODESIGN_CERT_PATH to enable signing."
  exit 0
}

$signtool = Get-Command signtool.exe -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty Source
if (-not $signtool) {
  $windowsKits = Join-Path ${env:ProgramFiles(x86)} "Windows Kits\10\bin"
  if (Test-Path -LiteralPath $windowsKits) {
    $signtool = Get-ChildItem -LiteralPath $windowsKits -Recurse -Filter signtool.exe |
      Where-Object { $_.FullName -like "*\x64\signtool.exe" } |
      Sort-Object FullName -Descending |
      Select-Object -First 1 -ExpandProperty FullName
  }
}
if (-not $signtool) {
  throw "signtool.exe was not found. Install Windows SDK or put signtool.exe on PATH."
}

if ($thumbprint) {
  & $signtool sign /fd SHA256 /tr $timestampUrl /td SHA256 /sha1 $thumbprint $Path
} else {
  $args = @("sign", "/fd", "SHA256", "/tr", $timestampUrl, "/td", "SHA256", "/f", $certPath)
  if ($certPassword) {
    $args += @("/p", $certPassword)
  }
  $args += $Path
  & $signtool @args
}

if ($LASTEXITCODE -ne 0) {
  throw "Code signing failed with exit code $LASTEXITCODE"
}

Write-Host "Signed $Path"
