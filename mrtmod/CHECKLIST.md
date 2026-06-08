# MTR Ollama Integration - Step-by-Step Checklist

## ✅ Completed Steps

- [x] Decompiled OllamaMod to understand structure
- [x] Analyzed MTR mod structure
- [x] Created OllamaClient.java
- [x] Created OllamaConfig.java
- [x] Created MTRWorldContext.java
- [x] Created MTROllamaCommands.java
- [x] Created MTROllamaIntegration.java
- [x] Modified Init.java with integration call
- [x] Updated mods.toml
- [x] Created build script
- [x] Created documentation

## 🔨 Remaining Steps

### Step 1: Prepare Build Environment

- [ ] Choose build method:
  - [ ] Option A: Forge MDK (Recommended - easiest)
  - [ ] Option B: Manual compilation (Advanced)
- [ ] If using Forge MDK:
  - [ ] Download Forge MDK 1.20.1
  - [ ] Extract and run `gradlew.bat setupDecompWorkspace`
  - [ ] Set up project structure

### Step 2: Compile Integration Code

- [ ] Copy `src/main/java/org/mtr/ollama/*.java` to your build environment
- [ ] Ensure all dependencies are available:
  - [ ] Forge 1.20.1 JARs
  - [ ] Minecraft 1.20.1
  - [ ] Google Gson
  - [ ] MTR dependencies
- [ ] Compile Ollama integration classes:

  ```bash
  javac -cp "forge.jar:minecraft.jar:gson.jar:mtr-deps/*" \
    -d build/classes \
    src/main/java/org/mtr/ollama/*.java
  ```

- [ ] Compile modified Init.java:

  ```bash
  javac -cp "forge.jar:minecraft.jar:gson.jar:mtr-deps/*:build/classes" \
    -d build/classes \
    mtr_decompiled/org/mtr/mod/Init.java
  ```

### Step 3: Package into JAR

- [ ] Extract original MTR JAR:

  ```powershell
  cd "C:\Users\user\AppData\Roaming\ATLauncher\instances\originigor\mods"
  Copy-Item "MTR-forge-4.0.2-hotfix-1+1.20.1.jar" "temp.zip"
  Expand-Archive -Path "temp.zip" -DestinationPath "mtr_extracted" -Force
  Remove-Item "temp.zip"
  ```

- [ ] Copy compiled classes:

  ```powershell
  Copy-Item -Recurse "build/classes/org/mtr/ollama" "mtr_extracted/org/mtr/ollama"
  Copy-Item "build/classes/org/mtr/mod/Init.class" "mtr_extracted/org/mtr/mod/Init.class"
  ```

- [ ] Update mods.toml:

  ```powershell
  Copy-Item "mods.toml" "mtr_extracted/META-INF/mods.toml"
  ```

- [ ] Recreate JAR:

  ```powershell
  cd mtr_extracted
  jar -cfm ..\MTR-forge-4.0.2-hotfix-1+1.20.1-ollama.jar META-INF\MANIFEST.MF *
  ```

### Step 4: Install and Test

- [ ] Backup original MTR JAR (already done by script)
- [ ] Install modified JAR:

  ```powershell
  Copy-Item "MTR-forge-4.0.2-hotfix-1+1.20.1-ollama.jar" "MTR-forge-4.0.2-hotfix-1+1.20.1.jar" -Force
  ```

- [ ] Start Ollama server (if not running):

  ```bash
  ollama serve
  ```

- [ ] Launch Minecraft with modified mod
- [ ] Test commands:
  - [ ] `/mtr ollama help` - Should show help
  - [ ] `/mtr ollama status` - Should check Ollama server
  - [ ] `/mtr ollama chat test` - Should send message to AI
  - [ ] `/mtr ollama analyze` - Should analyze network
  - [ ] `/mtr ollama optimize` - Should suggest optimizations

### Step 5: Configure (Optional)

- [ ] Edit `config/mtr-ollama-common.toml` if needed
- [ ] Adjust Ollama server URL if not using localhost
- [ ] Change default model if desired
- [ ] Enable/disable features as needed

## Troubleshooting Checklist

If something doesn't work:

- [ ] Check that all .class files are in the JAR:

  ```powershell
  jar -tf MTR-forge-4.0.2-hotfix-1+1.20.1.jar | Select-String "ollama"
  ```

- [ ] Verify Init.class was updated (check file date)
- [ ] Check server logs for errors
- [ ] Verify Ollama server is running and accessible
- [ ] Check command permissions (requires OP level 2)
- [ ] Verify mods.toml was updated

## Quick Reference

**Files Location:**

- Source code: `src/main/java/org/mtr/ollama/`
- Modified Init: `mtr_decompiled/org/mtr/mod/Init.java`
- Build script: `build_integration.ps1`
- Documentation: Various .md files

**Key Commands:**

- `/mtr ollama chat <message>` - Chat with AI
- `/mtr ollama status` - Check server
- `/mtr ollama analyze` - Analyze network
- `/mtr ollama optimize` - Get suggestions
- `/mtr ollama help` - Show help

**Configuration:**

- File: `config/mtr-ollama-common.toml`
- Default URL: `http://localhost:11434`
- Default Model: `llama2`

## Need Help?

- See `QUICK_START.md` for quick reference
- See `BUILD_INSTRUCTIONS.md` for detailed build steps
- See `SUMMARY.md` for complete overview
