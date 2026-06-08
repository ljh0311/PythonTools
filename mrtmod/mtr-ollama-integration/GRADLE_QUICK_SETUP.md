# Quick Gradle Setup Guide

## ✅ Step 1: MTR JAR - DONE
The MTR JAR has been copied to `libs/` folder.

## Step 2: Gradle Wrapper

You have two options:

### Option A: Download Gradle Wrapper (Recommended)

I've created a script to download it. Run:
```powershell
cd "C:\Users\user\Documents\brightnessControl\PythonTools\mrtmod\mtr-ollama-integration"
.\download_gradle_wrapper.ps1
```

### Option B: Install Gradle and Create Wrapper

1. **Download Gradle**: https://gradle.org/releases/
2. **Extract** to a folder (e.g., `C:\gradle`)
3. **Add to PATH** or use full path
4. **Run**:
   ```powershell
   gradle wrapper --gradle-version 8.5
   ```

### Option C: Manual Download

1. **Download wrapper JAR**:
   - Go to: https://github.com/gradle/gradle/tree/v8.5/gradle/wrapper
   - Download `gradle-wrapper.jar`
   - Save to: `gradle\wrapper\gradle-wrapper.jar`

2. **Create `gradle\wrapper\gradle-wrapper.properties`**:
   ```properties
   distributionBase=GRADLE_USER_HOME
   distributionPath=wrapper/dists
   distributionUrl=https\://services.gradle.org/distributions/gradle-8.5-bin.zip
   networkTimeout=10000
   validateDistributionUrl=true
   zipStoreBase=GRADLE_USER_HOME
   zipStorePath=wrapper/dists
   ```

3. **Create `gradlew.bat`** (simplified version):
   ```batch
   @echo off
   set DIRNAME=%~dp0
   set APP_HOME=%DIRNAME%
   set CLASSPATH=%APP_HOME%gradle\wrapper\gradle-wrapper.jar
   java -classpath "%CLASSPATH%" org.gradle.wrapper.GradleWrapperMain %*
   ```

## Step 3: Run setupDecompWorkspace

Once `gradlew.bat` exists:

```powershell
.\gradlew.bat setupDecompWorkspace
```

This will:
- Download Forge dependencies
- Set up the development workspace
- Take 5-10 minutes (first time)

## Step 4: Build

```powershell
.\gradlew.bat build
```

This will:
- Compile all Java files
- Package into JAR
- Output to `build\libs\`

## Troubleshooting

### "gradlew.bat not found"
- Make sure you're in the project directory
- Check that `gradlew.bat` exists
- If not, use Option B or C above

### "Java not found"
- Install Java 17+ from https://adoptium.net/
- Add to PATH or set JAVA_HOME

### "Could not resolve dependencies"
- Check internet connection
- Verify Forge version in build.gradle matches 1.20.1
- Try: `.\gradlew.bat --refresh-dependencies build`

### Build fails with compilation errors
- Check that MTR JAR is in `libs/` folder
- Verify all Ollama files are in `src/main/java/org/mtr/ollama/`
- Check build.gradle has correct dependencies

## Quick Commands Reference

```powershell
# Setup workspace (first time)
.\gradlew.bat setupDecompWorkspace

# Build the mod
.\gradlew.bat build

# Clean and rebuild
.\gradlew.bat clean build

# Check Gradle version
.\gradlew.bat --version
```

## What Happens During Build

1. **Downloads dependencies** (Forge, Minecraft, etc.)
2. **Compiles Java files** in `src/main/java/`
3. **Packages resources** from `src/main/resources/`
4. **Creates JAR** in `build/libs/`

The output JAR will be something like:
`MTR-4.0.2-hotfix-1-ollama.jar`

## Next Steps After Build

1. **Copy JAR** to your mods folder
2. **Start Ollama server**: `ollama serve`
3. **Test in Minecraft** with `/mtr ollama help`
