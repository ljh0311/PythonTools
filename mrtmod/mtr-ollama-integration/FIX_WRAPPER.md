# Fix Gradle Wrapper Error

## Error
```
Error: Could not find or load main class org.gradle.wrapper.GradleWrapperMain
```

This means the `gradle-wrapper.jar` file is either:
- Missing
- Corrupted
- Too small (incomplete download)

## Solution

### Option 1: Download with Browser (Recommended)

1. **Open browser** and go to:
   ```
   https://github.com/gradle/gradle/raw/v8.5/gradle/wrapper/gradle-wrapper.jar
   ```

2. **Right-click** → "Save As" (or browser auto-downloads)

3. **Save to:**
   ```
   C:\Users\user\Documents\brightnessControl\PythonTools\mrtmod\mtr-ollama-integration\gradle\wrapper\gradle-wrapper.jar
   ```

4. **Verify size:** Should be about **60-70 KB** (60,000-70,000 bytes)

### Option 2: Use curl (if available)

```powershell
cd "C:\Users\user\Documents\brightnessControl\PythonTools\mrtmod\mtr-ollama-integration"
curl.exe -L "https://raw.githubusercontent.com/gradle/gradle/v8.5/gradle/wrapper/gradle-wrapper.jar" -o "gradle\wrapper\gradle-wrapper.jar"
```

### Option 3: Install Gradle

1. Download Gradle from: https://gradle.org/releases/
2. Extract and add to PATH
3. Run:
   ```powershell
   cd "C:\Users\user\Documents\brightnessControl\PythonTools\mrtmod\mtr-ollama-integration"
   gradle wrapper --gradle-version 8.5
   ```

## Verify After Download

```powershell
cd "C:\Users\user\Documents\brightnessControl\PythonTools\mrtmod\mtr-ollama-integration"
$file = Get-Item "gradle\wrapper\gradle-wrapper.jar"
Write-Host "Size: $($file.Length) bytes"
# Should be around 60,000-70,000 bytes
```

If the file is less than 50,000 bytes, it's corrupted - delete it and download again.

## Then Try Again

```powershell
.\gradlew.bat setupDecompWorkspace
```
