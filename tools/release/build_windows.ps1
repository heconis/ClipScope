Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Set-Location -LiteralPath (Join-Path $PSScriptRoot "..\..")

$python = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    throw "Missing virtual environment python at .\.venv\Scripts\python.exe"
}

& $python -m pip install --upgrade pip
& $python -m pip install -r requirements.txt

$iconPath = "assets\icon\clipscope.ico"
if (-not (Test-Path $iconPath)) {
    throw "Missing icon file at $iconPath"
}

$specPath = "ClipScope.spec"
if (-not (Test-Path $specPath)) {
    throw "Missing spec file at $specPath"
}

if (Test-Path ".\build") {
    Remove-Item ".\build" -Recurse -Force
}
if (Test-Path ".\dist\ClipScope") {
    Remove-Item ".\dist\ClipScope" -Recurse -Force
}

& $python -m PyInstaller `
    --noconfirm `
    --clean `
    $specPath

Write-Host ""
Write-Host "Build finished: dist\ClipScope\ClipScope.exe"
