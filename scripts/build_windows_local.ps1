param(
    [switch]$SkipInstall,
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Venv = Join-Path $Root ".venv-local-build"
$Python = Join-Path $Venv "Scripts\python.exe"

function Assert-NativeSuccess([string]$Step) {
    if ($LASTEXITCODE -ne 0) {
        throw "$Step failed with exit code $LASTEXITCODE"
    }
}

if (-not (Test-Path -LiteralPath $Python)) {
    py -3 -m venv $Venv
}
if (-not $SkipInstall) {
    & $Python -m pip install --upgrade pip
    Assert-NativeSuccess "pip upgrade"
    & $Python -m pip install -r (Join-Path $Root "requirements-build.txt")
    Assert-NativeSuccess "dependency install"
}
if (-not $SkipTests) {
    & $Python -m pytest (Join-Path $Root "tests\test_local_mode.py") (Join-Path $Root "tests\test_browser_lifecycle.py") (Join-Path $Root "tests\test_packaged_paths.py") -q -p no:cacheprovider --basetemp (Join-Path $Root ".test-tmp")
    Assert-NativeSuccess "local unit tests"
    & $Python (Join-Path $Root "scripts\windows_local_smoke.py")
    Assert-NativeSuccess "source local smoke"
}

Push-Location $Root
try {
    Remove-Item -LiteralPath (Join-Path $Root "build\JobcanTool") -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath (Join-Path $Root "dist\JobcanTool") -Recurse -Force -ErrorAction SilentlyContinue
    & $Python -m PyInstaller --noconfirm JobcanTool.spec
    Assert-NativeSuccess "PyInstaller build"
    $Zip = Join-Path $Root "dist\JobcanTool-windows-x64.zip"
    Remove-Item -LiteralPath $Zip -Force -ErrorAction SilentlyContinue
    Compress-Archive -Path (Join-Path $Root "dist\JobcanTool\*") -DestinationPath $Zip -CompressionLevel Optimal
    & $Python (Join-Path $Root "scripts\windows_local_smoke.py") --executable (Join-Path $Root "dist\JobcanTool\JobcanTool.exe")
    Assert-NativeSuccess "packaged local smoke"
    Write-Host "Built: $Zip"
}
finally {
    Pop-Location
}
