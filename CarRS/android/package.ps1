# Build CarRS-android-arm64 release zip on Windows.
# Output: CarRS\dist\CarRS-android-arm64.zip

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$OutDir = Join-Path $Root "dist"
$Stage = Join-Path $OutDir "CarRS-android-arm64"
$ZipPath = Join-Path $OutDir "CarRS-android-arm64.zip"

$Files = @(
    "car_rental_recommender_core.py",
    "run_recommendations.py",
    "run_cleaning_pipeline.py",
    "pricing_config.json",
    "settings.json",
    "22 - Sheet1.csv"
)

if (Test-Path $Stage) { Remove-Item -Recurse -Force $Stage }
New-Item -ItemType Directory -Force -Path (Join-Path $Stage "android") | Out-Null
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

foreach ($f in $Files) {
    $src = Join-Path $Root $f
    if (Test-Path $src) {
        Copy-Item $src (Join-Path $Stage $f) -Force
    } else {
        Write-Warning "Missing: $f"
    }
}

Copy-Item (Join-Path $Root "android\*") (Join-Path $Stage "android") -Recurse -Force

# Termux/bash requires Unix (LF) line endings — Windows editors often save CRLF.
$Utf8NoBom = New-Object System.Text.UTF8Encoding $false
$ShellScripts = @(
    (Join-Path $Stage "android\install.sh"),
    (Join-Path $Stage "android\carrs"),
    (Join-Path $Stage "android\verify_install.sh"),
    (Join-Path $Stage "android\package.sh"),
    (Join-Path $Stage "android\go.sh")
)
foreach ($scriptPath in $ShellScripts) {
    if (Test-Path $scriptPath) {
        $text = [System.IO.File]::ReadAllText($scriptPath) -replace "`r`n", "`n" -replace "`r", "`n"
        [System.IO.File]::WriteAllText($scriptPath, $text, $Utf8NoBom)
    }
}

if (Test-Path $ZipPath) { Remove-Item $ZipPath -Force }
Compress-Archive -Path $Stage -DestinationPath $ZipPath -Force

Write-Host "Created: $ZipPath"
Write-Host ""
Write-Host "Transfer to S23 Ultra:"
Write-Host "  USB: copy zip to Internal storage > Download"
Write-Host "  ADB: adb push `"$ZipPath`" /sdcard/Download/"
