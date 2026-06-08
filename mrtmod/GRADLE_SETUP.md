# Gradle Setup for MTR Ollama Integration

Yes! You can absolutely use Gradle for the MTR mod. This is actually the **recommended and easiest** approach.

## Option 1: Use MTR Source Code (Best)

If MTR has a public GitHub repository with source code:

1. **Clone MTR Repository**
   ```powershell
   git clone https://github.com/Minecraft-Transit-Railway/Minecraft-Transit-Railway.git
   cd Minecraft-Transit-Railway
   ```

2. **Checkout Correct Version**
   ```powershell
   git checkout 4.0.2-hotfix-1  # or the version tag matching your JAR
   ```

3. **Add Ollama Integration Files**
   ```powershell
   # Copy our integration files
   Copy-Item -Recurse "C:\Users\user\Documents\brightnessControl\PythonTools\mrtmod\src\main\java\org\mtr\ollama" `
     "src\main\java\org\mtr\ollama"
   ```

4. **Modify Init.java**
   - Open `src/main/java/org/mtr/mod/Init.java`
   - Add import: `import org.mtr.ollama.MTROllamaIntegration;`
   - Add call: `MTROllamaIntegration.init();` after `SoundEvents.init();`

5. **Build with Gradle**
   ```powershell
   .\gradlew.bat build
   ```

6. **Output JAR**
   - Find the built JAR in `build/libs/`
   - It will be named something like `MTR-forge-4.0.2-hotfix-1.jar`

## Option 2: Create New Forge MDK Project

If MTR source isn't available, create a new Forge project:

### Step 1: Download Forge MDK

1. Go to https://files.minecraftforge.net/
2. Download **Forge 1.20.1** MDK (version 36+)
3. Extract to a new folder

### Step 2: Set Up Project

```powershell
# Navigate to MDK folder
cd path\to\forge-mdk-1.20.1-36.x.x

# Run setup (this downloads dependencies)
.\gradlew.bat setupDecompWorkspace
.\gradlew.bat genIntellijRuns  # For IntelliJ IDEA
# OR
.\gradlew.bat genEclipseRuns   # For Eclipse
```

### Step 3: Add MTR as Dependency

Edit `build.gradle` to add MTR:

```gradle
dependencies {
    // Minecraft and Forge
    minecraft 'net.minecraftforge:forge:1.20.1-47.2.0'
    
    // Add MTR dependency (if available in a repository)
    // Or manually add the JAR to libs/ folder and reference it
    implementation files('libs/MTR-forge-4.0.2-hotfix-1+1.20.1.jar')
}
```

### Step 4: Add Ollama Integration

1. **Copy Integration Files**
   ```powershell
   # Create package directory
   New-Item -ItemType Directory -Path "src\main\java\org\mtr\ollama" -Force
   
   # Copy files
   Copy-Item "C:\Users\user\Documents\brightnessControl\PythonTools\mrtmod\src\main\java\org\mtr\ollama\*" `
     "src\main\java\org\mtr\ollama\"
   ```

2. **Modify MTR's Init.java** (if you can access it)
   - Or create a mixin/event listener to hook into MTR's initialization

### Step 5: Build

```powershell
.\gradlew.bat build
```

## Option 3: Modify Existing MTR Build (If You Have Access)

If you have access to MTR's build.gradle:

### Add to build.gradle

```gradle
// In dependencies section
dependencies {
    // ... existing dependencies ...
    
    // Google Gson (if not already included)
    implementation 'com.google.code.gson:gson:2.10.1'
}

// In sourceSets section (if needed)
sourceSets {
    main {
        java {
            srcDirs = ['src/main/java']
        }
    }
}
```

### Project Structure

```
your-project/
├── build.gradle
├── gradlew.bat
├── src/
│   └── main/
│       ├── java/
│       │   └── org/
│       │       └── mtr/
│       │           ├── mod/
│       │           │   └── Init.java (modified)
│       │           └── ollama/
│       │               ├── OllamaClient.java
│       │               ├── OllamaConfig.java
│       │               ├── MTRWorldContext.java
│       │               ├── MTROllamaCommands.java
│       │               └── MTROllamaIntegration.java
│       └── resources/
│           └── META-INF/
│               └── mods.toml
└── build/
    └── libs/
        └── MTR-with-Ollama.jar
```

## Quick Gradle Commands

```powershell
# Build the mod
.\gradlew.bat build

# Clean build (remove old build files)
.\gradlew.bat clean build

# Run in development environment
.\gradlew.bat runClient    # Run client
.\gradlew.bat runServer    # Run server

# Generate IDE run configurations
.\gradlew.bat genIntellijRuns
.\gradlew.bat genEclipseRuns
```

## Dependencies in build.gradle

Make sure these are included:

```gradle
dependencies {
    // Forge
    minecraft 'net.minecraftforge:forge:1.20.1-47.2.0'
    
    // Gson (for JSON - usually included with Forge)
    // implementation 'com.google.code.gson:gson:2.10.1'
    
    // MTR (if available as dependency)
    // Or use: implementation files('libs/MTR.jar')
}
```

## Troubleshooting

### "Could not resolve dependency"
- Check Forge version matches (1.20.1)
- Ensure MTR JAR is in `libs/` folder if using `files()`

### "Package org.mtr.ollama does not exist"
- Verify files are in `src/main/java/org/mtr/ollama/`
- Run `.\gradlew.bat clean build`

### "ClassNotFoundException"
- Ensure all dependencies are in `build.gradle`
- Check that MTR classes are accessible

## Recommended Approach

**Best option**: Find MTR's GitHub repository and use their existing Gradle setup. This ensures:
- ✅ Correct dependencies
- ✅ Proper build configuration
- ✅ Easy to maintain
- ✅ Can contribute back if desired

## Next Steps

1. **Find MTR Source**: Check GitHub for Minecraft-Transit-Railway repository
2. **Clone/Download**: Get the source code for version 4.0.2-hotfix-1
3. **Add Integration**: Copy our Ollama files
4. **Modify Init**: Add integration call
5. **Build**: Run `gradlew build`
6. **Test**: Use the built JAR

Would you like me to help you find MTR's repository or set up a Forge MDK project?
