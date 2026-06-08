# Step-by-Step Build Guide

## ✅ Completed Steps

1. ✅ MTR JAR copied to `libs/` folder
2. ✅ `build.gradle` created
3. ✅ `gradle-wrapper.properties` created
4. ✅ `gradlew.bat` created

## 🔨 Remaining Steps

### Step 1: Download Gradle Wrapper JAR

The wrapper JAR is needed. Choose one method:

#### Method A: Direct Download (Easiest)
1. Open browser and go to:
   ```
   https://github.com/gradle/gradle/raw/v8.5/gradle/wrapper/gradle-wrapper.jar
   ```
2. Save the file as: `gradle\wrapper\gradle-wrapper.jar`

#### Method B: Using PowerShell
```powershell
cd "C:\Users\user\Documents\brightnessControl\PythonTools\mrtmod\mtr-ollama-integration"
New-Item -ItemType Directory -Path "gradle\wrapper" -Force
Invoke-WebRequest -Uri "https://github.com/gradle/gradle/raw/v8.5/gradle/wrapper/gradle-wrapper.jar" -OutFile "gradle\wrapper\gradle-wrapper.jar"
```

#### Method C: Install Gradle
1. Download Gradle from: https://gradle.org/releases/
2. Extract and add to PATH
3. Run: `gradle wrapper --gradle-version 8.5`

### Step 2: Verify Setup

Check that these files exist:
- ✅ `libs/MTR-forge-4.0.2-hotfix-1+1.20.1.jar`
- ✅ `build.gradle`
- ✅ `gradlew.bat`
- ✅ `gradle/wrapper/gradle-wrapper.properties`
- ⏳ `gradle/wrapper/gradle-wrapper.jar` (need to download)

### Step 3: Run setupDecompWorkspace

```powershell
cd "C:\Users\user\Documents\brightnessControl\PythonTools\mrtmod\mtr-ollama-integration"
.\gradlew.bat setupDecompWorkspace
```

**What this does:**
- Downloads Forge and Minecraft dependencies
- Sets up the development workspace
- Takes 5-10 minutes (first time only)
- Downloads ~200-300 MB

**Expected output:**
```
> Task :setupDecompWorkspace
...
BUILD SUCCESSFUL
```

### Step 4: Build the Mod

```powershell
.\gradlew.bat build
```

**What this does:**
- Compiles all Java files
- Packages resources
- Creates JAR file

**Expected output:**
```
> Task :compileJava
> Task :processResources
> Task :classes
> Task :jar
> Task :build

BUILD SUCCESSFUL
```

**Output location:**
- JAR will be in: `build\libs\MTR-4.0.2-hotfix-1-ollama.jar`

### Step 5: Install and Test

1. **Copy JAR to mods folder:**
   ```powershell
   Copy-Item "build\libs\MTR-4.0.2-hotfix-1-ollama.jar" `
     "C:\Users\user\AppData\Roaming\ATLauncher\instances\originigor\mods\MTR-forge-4.0.2-hotfix-1+1.20.1.jar" -Force
   ```

2. **Start Ollama server** (if not running):
   ```bash
   ollama serve
   ```

3. **Launch Minecraft** and test:
   ```
   /mtr ollama help
   /mtr ollama status
   /mtr ollama chat test
   ```

## Troubleshooting

### "gradlew.bat: command not found"
- Make sure you're in the project directory
- Check that `gradlew.bat` exists

### "Could not find or load main class org.gradle.wrapper.GradleWrapperMain"
- The `gradle-wrapper.jar` is missing
- Download it (see Step 1)

### "Java not found"
- Install Java 17+ from https://adoptium.net/
- Verify: `java -version`

### "Could not resolve dependencies"
- Check internet connection
- Verify Forge version in `build.gradle` is correct
- Try: `.\gradlew.bat --refresh-dependencies build`

### Build errors about missing classes
- Check that MTR JAR is in `libs/` folder
- Verify all Ollama files are in `src/main/java/org/mtr/ollama/`

## Quick Reference

```powershell
# Navigate to project
cd "C:\Users\user\Documents\brightnessControl\PythonTools\mrtmod\mtr-ollama-integration"

# Setup (first time only)
.\gradlew.bat setupDecompWorkspace

# Build
.\gradlew.bat build

# Clean and rebuild
.\gradlew.bat clean build

# Check what tasks are available
.\gradlew.bat tasks
```

## Current Status

✅ Project structure ready
✅ MTR JAR in place
✅ Gradle configuration ready
⏳ Need to download `gradle-wrapper.jar`
⏳ Then run setup and build

Once you download the wrapper JAR, you're ready to build!
