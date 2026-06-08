# Build and Deploy Script - Testing Instructions

## Prerequisites

### First-Time Setup: Handling Missing Gradle Wrapper
If you get an error about `gradlew` not being recognized, **don't worry!** The script will automatically use the Gradle wrapper from your `mrtmod` project.

**Good News**: The updated script now automatically looks for:
1. Local `gradlew.bat` in mcollama folder
2. Gradle wrapper from `mrtmod` project (found!)
3. System Gradle installation

**If you still want to install Gradle (optional):**
- **Scoop (No Admin Required)**: `scoop install gradle`
- **Manual**: Download from https://gradle.org/install/
- **Chocolatey (Requires Admin)**: Open PowerShell as Administrator, then `choco install gradle`

## Quick Start

1. **Run the script**:
   - Double-click `build-and-deploy.bat` in the mcollama folder
   - OR open Command Prompt/PowerShell and run: `build-and-deploy.bat`

2. **What to expect**:
   - The script will show progress through 4 steps
   - Build process may take 2-5 minutes on first run (downloads dependencies)
   - Subsequent builds will be faster
   - You'll see [SUCCESS] messages for each completed step

3. **Verify deployment**:
   - Check: `C:\Users\user\AppData\Roaming\ATLauncher\instances\Homestead\mods`
   - You should see:
     - `ollamamod-fabric-1.0.0.jar`
     - `ollamamod-forge-1.0.0.jar`

## Troubleshooting

### If build fails:
- **"gradlew is not recognized"**: Run from the mcollama folder
- **"Permission denied"**: Run Command Prompt as Administrator
- **"Out of memory"**: Close other applications and try again
- **Network errors**: Check internet connection (Gradle downloads dependencies)

### If deployment fails:
- **Cannot copy files**: Check if Minecraft is running (locks the mods folder)
- **Access denied**: Ensure ATLauncher is closed
- **Folder not found**: Verify the mods folder path in the script

## Customization Options

### To build only Fabric:
Replace line 28 with:
```batch
call gradlew :fabric:build
```

### To build only Forge:
Replace line 28 with:
```batch
call gradlew :forge:build
```

### To change the mods folder:
Edit line 11 in the script to your desired path

## Expected Output

```
========================================
Ollama Mod - Build and Deploy Script
========================================

[1/4] Cleaning old build artifacts...
[SUCCESS] Old builds cleaned

[2/4] Building Fabric and Forge versions...
This may take a few minutes...
[SUCCESS] Build completed successfully

[3/4] Verifying build artifacts...
[FOUND] Fabric JAR: fabric\build\libs\ollamamod-fabric-1.0.0.jar
[FOUND] Forge JAR: forge\build\libs\ollamamod-forge-1.0.0.jar

[4/4] Deploying to mods folder...
[INFO] Removing old versions...
[INFO] Copying Fabric JAR...
[INFO] Copying Forge JAR...

========================================
[SUCCESS] Build and Deploy Complete!
========================================

Deployed to: C:\Users\user\AppData\Roaming\ATLauncher\instances\Homestead\mods
- ollamamod-fabric-1.0.0.jar
- ollamamod-forge-1.0.0.jar

Process finished successfully
```
