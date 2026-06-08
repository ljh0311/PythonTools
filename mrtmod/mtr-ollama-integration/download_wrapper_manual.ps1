# Manual Gradle Wrapper Download Script
# This script tries multiple methods to download the Gradle wrapper

$ErrorActionPreference = "Continue"

Write-Host "=== Downloading Gradle Wrapper JAR ===" -ForegroundColor Cyan

$wrapperPath = "gradle\wrapper\gradle-wrapper.jar"
New-Item -ItemType Directory -Path "gradle\wrapper" -Force | Out-Null

# Method 1: GitHub with proper headers
Write-Host "`n[Method 1] Trying GitHub raw URL with headers..." -ForegroundColor Yellow
try {
    $url1 = "https://raw.githubusercontent.com/gradle/gradle/v8.5/gradle/wrapper/gradle-wrapper.jar"
    $headers = @{
        'User-Agent' = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        'Accept' = 'application/octet-stream'
    }
    Invoke-WebRequest -Uri $url1 -OutFile $wrapperPath -Headers $headers -UseBasicParsing -ErrorAction Stop
    if (Test-Path $wrapperPath -PathType Leaf) {
        $size = (Get-Item $wrapperPath).Length
        if ($size -gt 50000) {  # Wrapper JAR should be ~60KB
            $sizeKB = [math]::Round($size/1KB, 1)
            Write-Host "  Successfully downloaded ($sizeKB KB)" -ForegroundColor Green
            exit 0
        }
    }
} catch {
    Write-Host "  ✗ Failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Method 2: Direct from Gradle services
Write-Host "`n[Method 2] Trying Gradle distribution service..." -ForegroundColor Yellow
try {
    $url2 = "https://services.gradle.org/distributions/gradle-wrapper.jar"
    Invoke-WebRequest -Uri $url2 -OutFile $wrapperPath -UseBasicParsing -ErrorAction Stop
    if (Test-Path $wrapperPath -PathType Leaf) {
        $size = (Get-Item $wrapperPath).Length
        if ($size -gt 50000) {
            Write-Host "  ✓ Successfully downloaded ($([math]::Round($size/1KB, 1)) KB)" -ForegroundColor Green
            exit 0
        }
    }
} catch {
    Write-Host "  ✗ Failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Method 3: Using curl if available
Write-Host "`n[Method 3] Trying with curl..." -ForegroundColor Yellow
if (Get-Command curl -ErrorAction SilentlyContinue) {
    try {
        curl.exe -L -o $wrapperPath "https://raw.githubusercontent.com/gradle/gradle/v8.5/gradle/wrapper/gradle-wrapper.jar"
        if (Test-Path $wrapperPath -PathType Leaf) {
            $size = (Get-Item $wrapperPath).Length
            if ($size -gt 50000) {
                $sizeKB = [math]::Round($size/1KB, 1)
                Write-Host "  Successfully downloaded with curl ($sizeKB" -NoNewline
                Write-Host " KB)" -ForegroundColor Green
                exit 0
            }
        }
    } catch {
        Write-Host "  ✗ Failed: $($_.Exception.Message)" -ForegroundColor Red
    }
} else {
    Write-Host "  curl not available" -ForegroundColor Gray
}

# Method 4: Manual instructions
Write-Host "`n[Method 4] All automated methods failed." -ForegroundColor Yellow
Write-Host "`n=== Manual Download Instructions ===" -ForegroundColor Cyan
Write-Host "1. Open your web browser" -ForegroundColor White
Write-Host "2. Go to: https://github.com/gradle/gradle/releases/tag/v8.5" -ForegroundColor White
Write-Host "3. Or download directly from:" -ForegroundColor White
Write-Host "   https://github.com/gradle/gradle/raw/v8.5/gradle/wrapper/gradle-wrapper.jar" -ForegroundColor Cyan
Write-Host "4. Save the file as: gradle\wrapper\gradle-wrapper.jar" -ForegroundColor White
Write-Host "`nOr install Gradle and run:" -ForegroundColor Yellow
Write-Host "   gradle wrapper --gradle-version 8.5" -ForegroundColor White

Write-Host "`n=== Alternative: Use Gradle Installation ===" -ForegroundColor Cyan
Write-Host "1. Download Gradle from: https://gradle.org/releases/" -ForegroundColor White
Write-Host "2. Extract to a folder (e.g., C:\gradle)" -ForegroundColor White
Write-Host "3. Add to PATH or use full path" -ForegroundColor White
Write-Host "4. Run: gradle wrapper --gradle-version 8.5" -ForegroundColor White

exit 1
