# Render PNG previews for all SmartAI chassis variants via OpenSCAD CLI.
# Usage: .\render_previews.ps1 [-OutputDir <path>] [-OpenScadPath <path>]

param(
    [string]$OutputDir = (Join-Path $PSScriptRoot "previews"),
    [string]$OpenScadPath = "",
    [string]$ImgSize = "1280,960",
    [string]$Camera = "0,0,0,50,0,30,480"
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
        "${env:ProgramFiles(x86)}\OpenSCAD\openscad.exe"
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

foreach ($scad in $variants) {
    $src = Join-Path $PSScriptRoot $scad
    $png = Join-Path $OutputDir ($scad -replace '\.scad$', '.png')
    Write-Host "Rendering $scad -> $(Split-Path $png -Leaf) ..."
    & $openscad -o $png $src `
        --imgsize=$ImgSize `
        --viewall --autocenter `
        --render=all `
        --colorscheme=Metallic `
        --camera=$Camera
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $png)) {
        Write-Warning "Failed: $scad"
    }
}

Write-Host ""
Write-Host "Done. PNG files in $OutputDir"
