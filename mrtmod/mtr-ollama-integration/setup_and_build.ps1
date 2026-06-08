# PowerShell script to set up and build MTR Ollama integration

$ErrorActionPreference = "Stop"

Write-Host "=== MTR Ollama Integration - Gradle Setup & Build ===" -ForegroundColor Cyan

# Check prerequisites
Write-Host "`n[1/4] Checking prerequisites..." -ForegroundColor Yellow

# Check Java
try {
    $javaVersion = java -version 2>&1 | Select-Object -First 1
    Write-Host "  ✓ Java found: $javaVersion" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Java not found! Please install Java 17+" -ForegroundColor Red
    exit 1
}

# Check MTR JAR
$mtrJar = "libs\MTR-forge-4.0.2-hotfix-1+1.20.1.jar"
if (Test-Path $mtrJar) {
    Write-Host "  ✓ MTR JAR found" -ForegroundColor Green
} else {
    Write-Host "  ✗ MTR JAR not found at $mtrJar" -ForegroundColor Red
    exit 1
}

# Check build.gradle
if (Test-Path "build.gradle") {
    Write-Host "  ✓ build.gradle found" -ForegroundColor Green
} else {
    Write-Host "  ✗ build.gradle not found" -ForegroundColor Red
    exit 1
}

# Step 2: Set up Gradle wrapper
Write-Host "`n[2/4] Setting up Gradle wrapper..." -ForegroundColor Yellow

if (Test-Path "gradlew.bat") {
    Write-Host "  ✓ Gradle wrapper already exists" -ForegroundColor Green
} else {
    Write-Host "  Creating Gradle wrapper..." -ForegroundColor Gray
    
    # Check if gradle is available
    if (Get-Command gradle -ErrorAction SilentlyContinue) {
        gradle wrapper
        Write-Host "  ✓ Gradle wrapper created" -ForegroundColor Green
    } else {
        Write-Host "  Downloading Gradle wrapper manually..." -ForegroundColor Gray
        
        # Create gradle wrapper files manually
        $gradleVersion = "8.5"
        $wrapperUrl = "https://raw.githubusercontent.com/gradle/gradle/v$gradleVersion/gradle/wrapper/gradle-wrapper.jar"
        
        New-Item -ItemType Directory -Path "gradle\wrapper" -Force | Out-Null
        
        try {
            Invoke-WebRequest -Uri $wrapperUrl -OutFile "gradle\wrapper\gradle-wrapper.jar"
            Write-Host "  ✓ Gradle wrapper JAR downloaded" -ForegroundColor Green
        } catch {
            Write-Host "  ⚠ Could not download wrapper. Please run: gradle wrapper" -ForegroundColor Yellow
            Write-Host "  Or download manually from: https://gradle.org/releases/" -ForegroundColor Yellow
        }
        
        # Create gradle-wrapper.properties
        $wrapperProps = @"
distributionBase=GRADLE_USER_HOME
distributionPath=wrapper/dists
distributionUrl=https\://services.gradle.org/distributions/gradle-$gradleVersion-bin.zip
networkTimeout=10000
zipStoreBase=GRADLE_USER_HOME
zipStorePath=wrapper/dists
"@
        Set-Content -Path "gradle\wrapper\gradle-wrapper.properties" -Value $wrapperProps
        
        # Create gradlew.bat (simplified)
        $gradlewBat = @"
@echo off
set DIR=%~dp0
set GRADLE_USER_HOME=%DIR%gradle
"%DIR%gradle\wrapper\gradlew.bat" %*
"@
        # We'll create a proper one after wrapper is set up
    }
}

# Step 3: Run setupDecompWorkspace
Write-Host "`n[3/4] Running setupDecompWorkspace..." -ForegroundColor Yellow
Write-Host "  This may take several minutes (downloads dependencies)..." -ForegroundColor Gray

if (Test-Path "gradlew.bat") {
    try {
        .\gradlew.bat setupDecompWorkspace --no-daemon
        Write-Host "  ✓ setupDecompWorkspace completed" -ForegroundColor Green
    } catch {
        Write-Host "  ⚠ Error during setup. Continuing anyway..." -ForegroundColor Yellow
    }
} else {
    Write-Host "  ⚠ gradlew.bat not found. Please set up Gradle wrapper first." -ForegroundColor Yellow
    Write-Host "  Run: gradle wrapper" -ForegroundColor Yellow
}

# Step 4: Build
Write-Host "`n[4/4] Building project..." -ForegroundColor Yellow

if (Test-Path "gradlew.bat") {
    try {
        .\gradlew.bat build --no-daemon
        Write-Host "`n  ✓ Build completed successfully!" -ForegroundColor Green
        
        # Find output JAR
        $outputJar = Get-ChildItem -Path "build\libs" -Filter "*.jar" -Exclude "*sources.jar","*javadoc.jar" | Select-Object -First 1
        if ($outputJar) {
            Write-Host "`n  Output JAR: $($outputJar.FullName)" -ForegroundColor Cyan
            Write-Host "  Size: $([math]::Round($outputJar.Length / 1MB, 2)) MB" -ForegroundColor Gray
        }
    } catch {
        Write-Host "`n  ✗ Build failed. Check errors above." -ForegroundColor Red
        Write-Host "  Common issues:" -ForegroundColor Yellow
        Write-Host "    - Missing dependencies" -ForegroundColor Gray
        Write-Host "    - Java version mismatch (need Java 17+)" -ForegroundColor Gray
        Write-Host "    - MTR JAR not found in libs/" -ForegroundColor Gray
        exit 1
    }
} else {
    Write-Host "  ✗ gradlew.bat not found. Cannot build." -ForegroundColor Red
    exit 1
}

Write-Host "`n=== Setup and Build Complete! ===" -ForegroundColor Cyan
Write-Host "`nNext steps:" -ForegroundColor Yellow
Write-Host "1. Test the built JAR in Minecraft" -ForegroundColor White
Write-Host "2. Start Ollama server: ollama serve" -ForegroundColor White
Write-Host "3. Test commands: /mtr ollama help" -ForegroundColor White
