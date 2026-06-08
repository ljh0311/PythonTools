# Fixed Gradle Wrapper Download Script

$ErrorActionPreference = "Stop"

Write-Host "=== Downloading Gradle Wrapper JAR ===" -ForegroundColor Cyan

$wrapperPath = "gradle\wrapper\gradle-wrapper.jar"
New-Item -ItemType Directory -Path "gradle\wrapper" -Force | Out-Null

# Remove corrupted file if exists
if (Test-Path $wrapperPath) {
    $size = (Get-Item $wrapperPath).Length
    if ($size -lt 50000 -or $size -gt 100000) {
        Write-Host "Removing corrupted file ($size bytes)..." -ForegroundColor Yellow
        Remove-Item $wrapperPath -Force
    }
}

# Try multiple download methods
$urls = @(
    "https://raw.githubusercontent.com/gradle/gradle/v8.5/gradle/wrapper/gradle-wrapper.jar",
    "https://github.com/gradle/gradle/raw/v8.5/gradle/wrapper/gradle-wrapper.jar"
)

foreach ($url in $urls) {
    Write-Host "`nTrying: $url" -ForegroundColor Yellow
    try {
        # Method 1: Use WebClient with proper headers
        $webClient = New-Object System.Net.WebClient
        $webClient.Headers.Add("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        $webClient.DownloadFile($url, $wrapperPath)
        
        if (Test-Path $wrapperPath) {
            $size = (Get-Item $wrapperPath).Length
            Write-Host "Downloaded: $size bytes" -ForegroundColor $(if ($size -gt 50000 -and $size -lt 100000) { "Green" } else { "Yellow" })
            
            if ($size -gt 50000 -and $size -lt 100000) {
                Write-Host "`nSUCCESS! File downloaded correctly." -ForegroundColor Green
                Write-Host "Size: $size bytes (expected: ~60-70 KB)" -ForegroundColor Green
                exit 0
            } else {
                Write-Host "File size suspicious. Trying next method..." -ForegroundColor Yellow
                Remove-Item $wrapperPath -Force -ErrorAction SilentlyContinue
            }
        }
    } catch {
        Write-Host "Failed: $($_.Exception.Message)" -ForegroundColor Red
        Remove-Item $wrapperPath -Force -ErrorAction SilentlyContinue
    }
}

# If all automated methods fail, provide manual instructions
Write-Host "`n=== Automated download failed ===" -ForegroundColor Yellow
Write-Host "`nPlease download manually:" -ForegroundColor Cyan
Write-Host "1. Open browser" -ForegroundColor White
Write-Host "2. Go to: https://github.com/gradle/gradle/releases/tag/v8.5" -ForegroundColor White
Write-Host "3. Look for 'gradle-wrapper.jar' in the release assets" -ForegroundColor White
Write-Host "   OR go directly to:" -ForegroundColor White
Write-Host "   https://github.com/gradle/gradle/raw/v8.5/gradle/wrapper/gradle-wrapper.jar" -ForegroundColor Cyan
Write-Host "4. Save as: $wrapperPath" -ForegroundColor White
Write-Host "`nOr install Gradle and run: gradle wrapper --gradle-version 8.5" -ForegroundColor Yellow

exit 1
