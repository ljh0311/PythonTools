# Building the Modified MTR JAR with Ollama Integration

## Prerequisites

- Java JDK 17 or higher
- Maven or Gradle (if MTR uses a build system)
- Access to the MTR source code or ability to modify the JAR

## Option 1: Modify Decompiled Source and Rebuild

### Step 1: Prepare the Source

1. The modified `Init.java` is in `mtr_decompiled/org/mtr/mod/Init.java`
2. All Ollama integration files are in `src/main/java/org/mtr/ollama/`

### Step 2: Compile the Ollama Integration Classes

```bash
# Navigate to the workspace
cd C:\Users\user\Documents\brightnessControl\PythonTools\mrtmod

# Compile the Ollama integration classes
# You'll need the MTR mod's dependencies (Forge, Minecraft, etc.)
javac -cp "path/to/forge.jar:path/to/minecraft.jar:path/to/mtr-dependencies/*" \
  -d build/classes \
  src/main/java/org/mtr/ollama/*.java
```

### Step 3: Recompile Init.java

```bash
# Recompile Init.java with the integration
javac -cp "path/to/forge.jar:path/to/minecraft.jar:path/to/mtr-dependencies/*:build/classes" \
  -d build/classes \
  mtr_decompiled/org/mtr/mod/Init.java
```

### Step 4: Package into JAR

```bash
# Extract the original MTR JAR
cd C:\Users\user\AppData\Roaming\ATLauncher\instances\originigor\mods
jar -xf MTR-forge-4.0.2-hotfix-1+1.20.1.jar

# Copy compiled classes
cp -r build/classes/org extracted/

# Update mods.toml
cp mods.toml extracted/META-INF/mods.toml

# Recreate JAR
cd extracted
jar -cfm ../MTR-forge-4.0.2-hotfix-1+1.20.1-ollama.jar META-INF/MANIFEST.MF *
```

## Option 2: Direct JAR Modification (Simpler)

### Step 1: Extract JAR

```powershell
cd "C:\Users\user\AppData\Roaming\ATLauncher\instances\originigor\mods"
Copy-Item "MTR-forge-4.0.2-hotfix-1+1.20.1.jar" "MTR-backup.jar"
Expand-Archive -Path "MTR-forge-4.0.2-hotfix-1+1.20.1.jar" -DestinationPath "mtr_extracted" -Force
```

### Step 2: Compile Ollama Classes

You need to compile the Ollama integration classes with the correct classpath. The easiest way is to use a Forge development environment or manually compile with all dependencies.

### Step 3: Add Classes to JAR

```powershell
# Copy compiled .class files to the extracted JAR structure
# Assuming classes are compiled to build/classes/
Copy-Item -Recurse "build/classes/org/mtr/ollama" "mtr_extracted/org/mtr/ollama"

# Update Init.class (you'll need to recompile Init.java)
Copy-Item "build/classes/org/mtr/mod/Init.class" "mtr_extracted/org/mtr/mod/Init.class"

# Update mods.toml
Copy-Item "mods.toml" "mtr_extracted/META-INF/mods.toml"
```

### Step 4: Recreate JAR

```powershell
cd mtr_extracted
jar -cfm ..\MTR-forge-4.0.2-hotfix-1+1.20.1-ollama.jar META-INF\MANIFEST.MF *
```

## Option 3: Using Forge Development Environment (Recommended)

If you have access to MTR's source code or can set up a Forge dev environment:

1. **Set up Forge MDK** for Minecraft 1.20.1
2. **Copy MTR source** into the project
3. **Add Ollama integration files** to `src/main/java/org/mtr/ollama/`
4. **Modify Init.java** as shown in the patch
5. **Build with Gradle**: `./gradlew build`
6. **Output JAR** will be in `build/libs/`

## Dependencies Required

Make sure these are in your classpath when compiling:

- Forge 1.20.1 (version 36+)
- Minecraft 1.20.1
- Google Gson (for JSON parsing)
- All MTR dependencies

## Verification

After building, verify the integration:

1. Check that `org/mtr/ollama/` classes are in the JAR
2. Check that `Init.class` has been updated
3. Check that `META-INF/mods.toml` mentions Ollama integration
4. Test in-game with `/mtr ollama help`

## Troubleshooting

### ClassNotFoundException

- Ensure all dependencies are in the classpath
- Check that package structure matches (org/mtr/ollama/)

### NoSuchMethodError

- Recompile Init.java with the integration call
- Ensure all classes are compiled with the same Java version

### Commands Not Working

- Check that commands are registered in Init.java
- Verify permission levels (requires OP level 2)
- Check server logs for errors

## Quick Test Script

```powershell
# Quick test to verify JAR structure
cd "C:\Users\user\AppData\Roaming\ATLauncher\instances\originigor\mods"
jar -tf MTR-forge-4.0.2-hotfix-1+1.20.1-ollama.jar | Select-String "ollama"
# Should show:
# org/mtr/ollama/OllamaClient.class
# org/mtr/ollama/OllamaConfig.class
# org/mtr/ollama/MTRWorldContext.class
# org/mtr/ollama/MTROllamaCommands.class
# org/mtr/ollama/MTROllamaIntegration.class
```
