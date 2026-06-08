# PowerShell script to build MTR JAR with Ollama integration
# This script helps compile and package the modified MTR mod

$ErrorActionPreference = "Stop"

Write-Host "=== MTR Ollama Integration Build Script ===" -ForegroundColor Cyan

# Paths
$workspace = "C:\Users\user\Documents\brightnessControl\PythonTools\mrtmod"
$mtrJar = "C:\Users\user\AppData\Roaming\ATLauncher\instances\originigor\mods\MTR-forge-4.0.2-hotfix-1+1.20.1.jar"
$outputJar = "C:\Users\user\AppData\Roaming\ATLauncher\instances\originigor\mods\MTR-forge-4.0.2-hotfix-1+1.20.1-ollama.jar"
$extractedDir = "$workspace\mtr_build_extracted"
$buildDir = "$workspace\build"

# Step 1: Create backup
Write-Host "`n[1/6] Creating backup..." -ForegroundColor Yellow
if (Test-Path $mtrJar) {
    $backupJar = $mtrJar -replace "\.jar$", "-backup.jar"
    if (-not (Test-Path $backupJar)) {
        Copy-Item $mtrJar $backupJar
        Write-Host "  Backup created: $backupJar" -ForegroundColor Green
    } else {
        Write-Host "  Backup already exists: $backupJar" -ForegroundColor Gray
    }
} else {
    Write-Host "  ERROR: MTR JAR not found at $mtrJar" -ForegroundColor Red
    exit 1
}

# Step 2: Extract JAR
Write-Host "`n[2/6] Extracting MTR JAR..." -ForegroundColor Yellow
if (Test-Path $extractedDir) {
    Remove-Item -Recurse -Force $extractedDir
}
New-Item -ItemType Directory -Path $extractedDir -Force | Out-Null

# Extract using jar command or rename to zip
Copy-Item $mtrJar "$extractedDir\temp.zip"
Expand-Archive -Path "$extractedDir\temp.zip" -DestinationPath $extractedDir -Force
Remove-Item "$extractedDir\temp.zip"
Write-Host "  Extracted to: $extractedDir" -ForegroundColor Green

# Step 3: Copy Ollama source files
Write-Host "`n[3/6] Preparing Ollama integration files..." -ForegroundColor Yellow
$ollamaSourceDir = "$workspace\src\main\java\org\mtr\ollama"
$ollamaTargetDir = "$extractedDir\org\mtr\ollama"

if (Test-Path $ollamaSourceDir) {
    if (Test-Path $ollamaTargetDir) {
        Remove-Item -Recurse -Force $ollamaTargetDir
    }
    New-Item -ItemType Directory -Path $ollamaTargetDir -Force | Out-Null
    
    # Copy source files (will need to be compiled)
    Get-ChildItem -Path $ollamaSourceDir -Filter "*.java" | ForEach-Object {
        Copy-Item $_.FullName $ollamaTargetDir
        Write-Host "  Copied: $($_.Name)" -ForegroundColor Gray
    }
    Write-Host "  Ollama source files copied" -ForegroundColor Green
} else {
    Write-Host "  WARNING: Ollama source directory not found at $ollamaSourceDir" -ForegroundColor Yellow
}

# Step 4: Update mods.toml
Write-Host "`n[4/6] Updating mods.toml..." -ForegroundColor Yellow
$modsToml = "$workspace\mods.toml"
$targetModsToml = "$extractedDir\META-INF\mods.toml"
if (Test-Path $modsToml) {
    Copy-Item $modsToml $targetModsToml -Force
    Write-Host "  mods.toml updated" -ForegroundColor Green
} else {
    Write-Host "  WARNING: mods.toml not found at $modsToml" -ForegroundColor Yellow
}

# Step 5: Copy modified Init.java (source)
Write-Host "`n[5/6] Copying modified Init.java..." -ForegroundColor Yellow
$initSource = "$workspace\mtr_decompiled\org\mtr\mod\Init.java"
$initTarget = "$extractedDir\org\mtr\mod\Init.java"
if (Test-Path $initSource) {
    Copy-Item $initSource $initTarget -Force
    Write-Host "  Modified Init.java copied (needs compilation)" -ForegroundColor Green
} else {
    Write-Host "  WARNING: Modified Init.java not found" -ForegroundColor Yellow
}

# Step 6: Instructions for compilation
Write-Host "`n[6/6] Build Summary" -ForegroundColor Yellow
Write-Host "`n=== NEXT STEPS ===" -ForegroundColor Cyan
Write-Host "1. Compile the Ollama integration classes:" -ForegroundColor White
Write-Host "   You need to compile with Forge/Minecraft dependencies" -ForegroundColor Gray
Write-Host "`n2. Compile the modified Init.java:" -ForegroundColor White
Write-Host "   javac -cp 'forge.jar:minecraft.jar:dependencies/*' Init.java" -ForegroundColor Gray
Write-Host "`n3. Recreate the JAR:" -ForegroundColor White
Write-Host "   cd $extractedDir" -ForegroundColor Gray
Write-Host "   jar -cfm `"$outputJar`" META-INF\MANIFEST.MF *" -ForegroundColor Gray
Write-Host "`n=== ALTERNATIVE: Manual JAR Modification ===" -ForegroundColor Cyan
Write-Host "If you have compiled .class files, you can:" -ForegroundColor White
Write-Host "1. Copy compiled classes to: $extractedDir\org\mtr\ollama\" -ForegroundColor Gray
Write-Host "2. Copy compiled Init.class to: $extractedDir\org\mtr\mod\Init.class" -ForegroundColor Gray
Write-Host "3. Recreate JAR as shown above" -ForegroundColor Gray

Write-Host "`nExtracted files ready at: $extractedDir" -ForegroundColor Green
Write-Host "`n=== Build preparation complete! ===" -ForegroundColor Cyan
