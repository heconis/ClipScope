param(
    [string]$Version = "0.1.2"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Set-Location -LiteralPath (Join-Path $PSScriptRoot "..\..")

$distExe = "dist\ClipScope.exe"
if (-not (Test-Path $distExe)) {
    throw "Missing build output at $distExe. Run tools/release/build_windows.ps1 first."
}

$releaseRoot = "release"
$packageRoot = Join-Path $releaseRoot ("ClipScope-v{0}" -f $Version)
$zipPath = Join-Path $releaseRoot ("ClipScope-v{0}-windows-x64.zip" -f $Version)

if (Test-Path $packageRoot) {
    Remove-Item $packageRoot -Recurse -Force
}
if (Test-Path $zipPath) {
    Remove-Item $zipPath -Force
}
if (-not (Test-Path $releaseRoot)) {
    New-Item -ItemType Directory -Path $releaseRoot | Out-Null
}

New-Item -ItemType Directory -Path $packageRoot | Out-Null

Copy-Item $distExe (Join-Path $packageRoot "ClipScope.exe") -Force
Copy-Item "README.md" (Join-Path $packageRoot "README.md") -Force
Copy-Item "LICENSE" (Join-Path $packageRoot "LICENSE") -Force

$releaseNotesSource = "docs\release_notes_v{0}.md" -f $Version
if (-not (Test-Path $releaseNotesSource)) {
    $releaseNotesSource = "docs\release_notes_v0.1.1.md"
}
if (Test-Path $releaseNotesSource) {
    Copy-Item $releaseNotesSource (Join-Path $packageRoot "RELEASE_NOTES.md") -Force
}

Compress-Archive -Path (Join-Path $packageRoot "*") -DestinationPath $zipPath -CompressionLevel Optimal

$hash = (Get-FileHash $zipPath -Algorithm SHA256).Hash

Write-Host ""
Write-Host "Package finished: $zipPath"
Write-Host "SHA256: $hash"
