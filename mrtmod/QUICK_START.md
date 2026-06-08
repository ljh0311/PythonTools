# Quick Start Guide - MTR Ollama Integration

## What's Been Done ✅

1. ✅ All Ollama integration Java files created in `src/main/java/org/mtr/ollama/`
2. ✅ Modified `Init.java` with integration call
3. ✅ Updated `mods.toml` with Ollama description
4. ✅ Build script created (`build_integration.ps1`)

## Current Status

The integration code is ready, but **the Java files need to be compiled** before they can be added to the JAR.

## Option 1: Use Forge Development Environment (Recommended)

If you have or can set up a Forge MDK:

1. **Set up Forge MDK for 1.20.1**
   ```powershell
   # Download Forge MDK 1.20.1 from https://files.minecraftforge.net/
   # Extract and run: gradlew.bat setupDecompWorkspace
   ```

2. **Copy files to Forge project**
   - Copy `src/main/java/org/mtr/ollama/*.java` to your Forge project's `src/main/java/org/mtr/ollama/`
   - Copy modified `Init.java` to your MTR source
   - Add MTR as a dependency

3. **Build**
   ```powershell
   gradlew.bat build
   ```

## Option 2: Manual Compilation (Advanced)

You'll need these JARs in your classpath:
- Forge 1.20.1 (version 36+)
- Minecraft 1.20.1
- Google Gson
- All MTR dependencies

Then compile:
```powershell
javac -cp "forge.jar:minecraft.jar:gson.jar:mtr-deps/*" ^
  -d build/classes ^
  src/main/java/org/mtr/ollama/*.java
```

## Option 3: Direct JAR Injection (If you have compiled classes)

If you already have compiled `.class` files:

1. **Extract MTR JAR**
   ```powershell
   cd "C:\Users\user\AppData\Roaming\ATLauncher\instances\originigor\mods"
   Expand-Archive -Path "MTR-forge-4.0.2-hotfix-1+1.20.1.jar" -DestinationPath "mtr_extracted" -Force
   ```

2. **Add compiled classes**
   ```powershell
   # Copy your compiled .class files
   Copy-Item -Recurse "path/to/compiled/org/mtr/ollama" "mtr_extracted/org/mtr/ollama"
   Copy-Item "path/to/compiled/org/mtr/mod/Init.class" "mtr_extracted/org/mtr/mod/Init.class"
   ```

3. **Update mods.toml**
   ```powershell
   Copy-Item "mods.toml" "mtr_extracted/META-INF/mods.toml"
   ```

4. **Rebuild JAR**
   ```powershell
   cd mtr_extracted
   jar -cfm ..\MTR-forge-4.0.2-hotfix-1+1.20.1-ollama.jar META-INF\MANIFEST.MF *
   ```

## What You Need

### Dependencies Required:
- **Google Gson** - For JSON parsing (OllamaClient uses it)
- **Java 11+** - For HTTP client (Java 11+ has built-in HTTP client)
- **Forge 1.20.1** - Mod loader
- **Minecraft 1.20.1** - Game version

### Files Ready:
- ✅ `src/main/java/org/mtr/ollama/OllamaClient.java`
- ✅ `src/main/java/org/mtr/ollama/OllamaConfig.java`
- ✅ `src/main/java/org/mtr/ollama/MTRWorldContext.java`
- ✅ `src/main/java/org/mtr/ollama/MTROllamaCommands.java`
- ✅ `src/main/java/org/mtr/ollama/MTROllamaIntegration.java`
- ✅ `mtr_decompiled/org/mtr/mod/Init.java` (modified)
- ✅ `mods.toml` (updated)

## Testing After Build

Once the JAR is built and installed:

1. **Start Minecraft with the modified MTR mod**
2. **Start Ollama server** (if not running): `ollama serve`
3. **Test commands:**
   ```
   /mtr ollama help
   /mtr ollama status
   /mtr ollama chat How can I optimize my train routes?
   /mtr ollama analyze
   /mtr ollama optimize
   ```

## Troubleshooting

### "ClassNotFoundException: org.mtr.ollama.*"
- Classes not compiled or not in JAR
- Check that `org/mtr/ollama/*.class` files are in the JAR

### "Command not found"
- Check that Init.java was recompiled with the integration call
- Verify commands are registered in Init.java

### "Connection error"
- Ensure Ollama server is running: `ollama serve`
- Check `config/mtr-ollama-common.toml` for correct URL

## Next Steps

1. **Choose your build method** (Forge MDK recommended)
2. **Compile the Java files** with proper dependencies
3. **Package into JAR** using one of the methods above
4. **Test in-game** with the commands

Need help with a specific step? Let me know!
