# Batch-export SmartAI chassis STLs via OpenSCAD CLI.
# Usage: .\export_all.ps1 [-OutputDir <path>] [-OpenScadPath <path>]

param(
    [string]$OutputDir = (Join-Path $PSScriptRoot "stl"),
    [string]$OpenScadPath = ""
)

$ErrorActionPreference = "Stop"
$variants = @(
    "variant-a-compact-home.scad",
    "variant-b-tall-navigator.scad",
    "variant-c-wide-stable.scad"
)

function Find-OpenScad {
    param([string]$Explicit)
    if ($Explicit -and (Test-Path $Explicit)) { return $Explicit }
    $cmd = Get-Command openscad -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    $candidates = @(
        "${env:ProgramFiles}\OpenSCAD\openscad.exe",
        "${env:ProgramFiles(x86)}\OpenSCAD\openscad.exe",
        "$env:LOCALAPPDATA\Programs\OpenSCAD\openscad.exe"
    )
    foreach ($p in $candidates) {
        if (Test-Path $p) { return $p }
    }
    return $null
}

$openscad = Find-OpenScad -Explicit $OpenScadPath
if (-not $openscad) {
    Write-Error "OpenSCAD not found. Install from https://openscad.org/ or pass -OpenScadPath."
}

if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir | Out-Null
}

Write-Host "OpenSCAD: $openscad"
Write-Host "Output:   $OutputDir"
Write-Host ""

$failed = @()
foreach ($scad in $variants) {
    $src = Join-Path $PSScriptRoot $scad
    if (-not (Test-Path $src)) {
        Write-Warning "Missing: $scad"
        $failed += $scad
        continue
    }
    $stl = Join-Path $OutputDir ($scad -replace '\.scad$', '.stl')
    Write-Host "Exporting $scad -> $(Split-Path $stl -Leaf) ..."
    $before = if (Test-Path $stl) { (Get-Item $stl).LastWriteTimeUtc.Ticks } else { 0 }
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    & $openscad -o $stl $src 2>&1 | Out-Null
    $exit = $LASTEXITCODE
    $ErrorActionPreference = $prevEap
    $after = if (Test-Path $stl) { (Get-Item $stl).LastWriteTimeUtc.Ticks } else { 0 }
    if (-not (Test-Path $stl) -or ($exit -ne 0 -and $after -le $before)) {
        $failed += $scad
        Write-Warning "Failed: $scad (exit $exit)"
    }
}

Write-Host ""
if ($failed.Count -eq 0) {
    Write-Host "Done. $($variants.Count) STL files in $OutputDir"
    exit 0
}
Write-Host "Completed with $($failed.Count) failure(s): $($failed -join ', ')"
exit 1
