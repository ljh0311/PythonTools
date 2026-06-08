# MTR Ollama Integration - Gradle Build

## ✅ What's Ready

1. ✅ MTR JAR copied to `libs/` folder
2. ✅ `build.gradle` configured
3. ✅ `gradlew.bat` created
4. ✅ `gradle-wrapper.properties` created
5. ✅ All Ollama integration source files in `src/main/java/org/mtr/ollama/`

## ⏳ What You Need to Do

### 1. Download Gradle Wrapper JAR

**Option A: Direct Download (Easiest)**
1. Go to: https://github.com/gradle/gradle/raw/v8.5/gradle/wrapper/gradle-wrapper.jar
2. Save as: `gradle\wrapper\gradle-wrapper.jar`

**Option B: PowerShell**
```powershell
Invoke-WebRequest -Uri "https://github.com/gradle/gradle/raw/v8.5/gradle/wrapper/gradle-wrapper.jar" `
  -OutFile "gradle\wrapper\gradle-wrapper.jar"
```

**Option C: Install Gradle**
```powershell
# Download from https://gradle.org/releases/
# Then run:
gradle wrapper --gradle-version 8.5
```

### 2. Run Setup

```powershell
.\gradlew.bat setupDecompWorkspace
```

This downloads dependencies (takes 5-10 minutes first time).

### 3. Build

```powershell
.\gradlew.bat build
```

Output JAR will be in: `build\libs\MTR-4.0.2-hotfix-1-ollama.jar`

### 4. Install

Copy the built JAR to your mods folder and test!

## Files Structure

```
mtr-ollama-integration/
├── build.gradle                    ✅ Ready
├── gradlew.bat                     ✅ Ready
├── gradle/
│   └── wrapper/
│       ├── gradle-wrapper.properties  ✅ Ready
│       └── gradle-wrapper.jar          ⏳ Need to download
├── libs/
│   └── MTR-forge-4.0.2-hotfix-1+1.20.1.jar  ✅ Ready
└── src/
    └── main/
        └── java/
            └── org/
                └── mtr/
                    └── ollama/     ✅ All files ready
                        ├── OllamaClient.java
                        ├── OllamaConfig.java
                        ├── MTRWorldContext.java
                        ├── MTROllamaCommands.java
                        └── MTROllamaIntegration.java
```

## Quick Commands

```powershell
# Setup workspace (first time)
.\gradlew.bat setupDecompWorkspace

# Build
.\gradlew.bat build

# Clean build
.\gradlew.bat clean build
```

## Need Help?

- See `STEP_BY_STEP.md` for detailed instructions
- See `GRADLE_QUICK_SETUP.md` for troubleshooting

## Next Action

**Download `gradle-wrapper.jar` and you're ready to build!**
