# Manual Gradle Wrapper Download

The automated download failed because GitHub redirects the raw URL. Here are **3 easy ways** to get the wrapper JAR:

## Method 1: Browser Download (Easiest - 30 seconds)

1. **Open your web browser**
2. **Go to this URL:**
   ```
   https://github.com/gradle/gradle/raw/v8.5/gradle/wrapper/gradle-wrapper.jar
   ```
3. **Right-click** on the page and select "Save As" (or the browser will auto-download)
4. **Save the file** to:
   ```
   C:\Users\user\Documents\brightnessControl\PythonTools\mrtmod\mtr-ollama-integration\gradle\wrapper\gradle-wrapper.jar
   ```

**That's it!** The file should be about 60-70 KB.

## Method 2: Use curl (if available)

Open PowerShell and run:
```powershell
cd "C:\Users\user\Documents\brightnessControl\PythonTools\mrtmod\mtr-ollama-integration"
curl.exe -L -o "gradle\wrapper\gradle-wrapper.jar" "https://github.com/gradle/gradle/raw/v8.5/gradle/wrapper/gradle-wrapper.jar"
```

## Method 3: Install Gradle (if you plan to use it more)

1. **Download Gradle** from: https://gradle.org/releases/
   - Get version 8.5 or later
   - Download the "binary-only" zip
2. **Extract** to a folder (e.g., `C:\gradle`)
3. **Add to PATH** (optional, or use full path)
4. **Run:**
   ```powershell
   cd "C:\Users\user\Documents\brightnessControl\PythonTools\mrtmod\mtr-ollama-integration"
   gradle wrapper --gradle-version 8.5
   ```

## Verify Download

After downloading, verify the file exists:
```powershell
cd "C:\Users\user\Documents\brightnessControl\PythonTools\mrtmod\mtr-ollama-integration"
Test-Path "gradle\wrapper\gradle-wrapper.jar"
```

Should return `True` and the file should be about 60-70 KB.

## Then Continue

Once the file is downloaded, you can proceed:

```powershell
# Setup workspace (downloads dependencies)
.\gradlew.bat setupDecompWorkspace

# Build the mod
.\gradlew.bat build
```

## Quick Check

Run this to see what's ready:
```powershell
cd "C:\Users\user\Documents\brightnessControl\PythonTools\mrtmod\mtr-ollama-integration"
Write-Host "MTR JAR: $((Test-Path 'libs\MTR-forge-4.0.2-hotfix-1+1.20.1.jar'))"
Write-Host "build.gradle: $((Test-Path 'build.gradle'))"
Write-Host "gradlew.bat: $((Test-Path 'gradlew.bat'))"
Write-Host "gradle-wrapper.jar: $((Test-Path 'gradle\wrapper\gradle-wrapper.jar'))"
```

All should be `True` before building.
