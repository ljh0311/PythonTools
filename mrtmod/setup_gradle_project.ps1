# PowerShell script to set up Gradle project for MTR Ollama integration

$ErrorActionPreference = "Stop"

Write-Host "=== MTR Ollama Gradle Setup ===" -ForegroundColor Cyan

$workspace = "C:\Users\user\Documents\brightnessControl\PythonTools\mrtmod"
$projectName = "mtr-ollama-integration"

Write-Host "`nThis script will help you set up a Gradle project." -ForegroundColor Yellow
Write-Host "Choose an option:" -ForegroundColor Yellow
Write-Host "1. Check if MTR source code is available" -ForegroundColor White
Write-Host "2. Set up new Forge MDK project" -ForegroundColor White
Write-Host "3. Create minimal Gradle project structure" -ForegroundColor White

$choice = Read-Host "`nEnter choice (1-3)"

if ($choice -eq "1") {
    Write-Host "`nChecking for MTR source..." -ForegroundColor Yellow
    $mtrRepo = "https://github.com/Minecraft-Transit-Railway/Minecraft-Transit-Railway"
    Write-Host "MTR Repository: $mtrRepo" -ForegroundColor Cyan
    Write-Host "`nTo use MTR source:" -ForegroundColor Yellow
    Write-Host "1. Clone: git clone $mtrRepo" -ForegroundColor White
    Write-Host "2. Checkout version: git checkout 4.0.2-hotfix-1" -ForegroundColor White
    Write-Host "3. Copy Ollama files from: $workspace\src\main\java\org\mtr\ollama" -ForegroundColor White
    Write-Host "4. Modify Init.java to add integration call" -ForegroundColor White
    Write-Host "5. Build: .\gradlew.bat build" -ForegroundColor White
}

elseif ($choice -eq "2") {
    Write-Host "`nSetting up Forge MDK project..." -ForegroundColor Yellow
    Write-Host "`nSteps:" -ForegroundColor Yellow
    Write-Host "1. Download Forge MDK 1.20.1 from https://files.minecraftforge.net/" -ForegroundColor White
    Write-Host "2. Extract to a folder" -ForegroundColor White
    Write-Host "3. Run: .\gradlew.bat setupDecompWorkspace" -ForegroundColor White
    Write-Host "4. Copy Ollama files to src/main/java/org/mtr/ollama/" -ForegroundColor White
    Write-Host "5. Add MTR JAR as dependency in build.gradle" -ForegroundColor White
    Write-Host "6. Build: .\gradlew.bat build" -ForegroundColor White
}

elseif ($choice -eq "3") {
    Write-Host "`nCreating minimal Gradle project structure..." -ForegroundColor Yellow
    
    $projectDir = Join-Path $workspace $projectName
    if (Test-Path $projectDir) {
        $overwrite = Read-Host "Directory exists. Overwrite? (y/n)"
        if ($overwrite -ne "y") {
            Write-Host "Cancelled." -ForegroundColor Red
            exit
        }
        Remove-Item -Recurse -Force $projectDir
    }
    
    New-Item -ItemType Directory -Path $projectDir -Force | Out-Null
    Set-Location $projectDir
    
    # Create directory structure
    New-Item -ItemType Directory -Path "src\main\java\org\mtr\ollama" -Force | Out-Null
    New-Item -ItemType Directory -Path "src\main\resources\META-INF" -Force | Out-Null
    New-Item -ItemType Directory -Path "libs" -Force | Out-Null
    
    # Copy Ollama files
    Write-Host "Copying Ollama integration files..." -ForegroundColor Yellow
    Copy-Item -Recurse "$workspace\src\main\java\org\mtr\ollama\*" "src\main\java\org\mtr\ollama\"
    
    # Copy mods.toml
    Copy-Item "$workspace\mods.toml" "src\main\resources\META-INF\mods.toml"
    
    # Create build.gradle
    $buildGradle = @"
buildscript {
    repositories {
        maven { url = 'https://maven.minecraftforge.net' }
        mavenCentral()
    }
    dependencies {
        classpath 'net.minecraftforge.gradle:ForgeGradle:5.1.+'
    }
}

plugins {
    id 'net.minecraftforge.gradle' version '5.1.+'
}

version = '4.0.2-hotfix-1-ollama'
group = 'org.mtr'
archivesBaseName = 'MTR'

java.toolchain.languageVersion = JavaLanguageVersion.of(17)

minecraft {
    mappings channel: 'official', version: '1.20.1'
    
    runs {
        client {
            workingDirectory project.file('run')
            property 'forge.logging.markers', 'REGISTRIES'
            property 'forge.logging.levels', 'DEBUG'
            mods {
                mtr {
                    source sourceSets.main
                }
            }
        }
        
        server {
            workingDirectory project.file('run')
            property 'forge.logging.markers', 'REGISTRIES'
            property 'forge.logging.levels', 'DEBUG'
            mods {
                mtr {
                    source sourceSets.main
                }
            }
        }
    }
}

repositories {
    mavenCentral()
    maven {
        name = "Forge"
        url = "https://maven.minecraftforge.net"
    }
}

dependencies {
    minecraft 'net.minecraftforge:forge:1.20.1-47.2.0'
    
    // MTR JAR (copy to libs/ folder)
    implementation files('libs/MTR-forge-4.0.2-hotfix-1+1.20.1.jar')
    
    // Gson (usually included with Forge, but explicit is good)
    implementation 'com.google.code.gson:gson:2.10.1'
}

tasks.withType(JavaCompile).configureEach {
    options.encoding = 'UTF-8'
}

"@
    
    Set-Content -Path "build.gradle" -Value $buildGradle
    
    # Create settings.gradle
    $settingsGradle = @"
rootProject.name = 'MTR-Ollama-Integration'
"@
    Set-Content -Path "settings.gradle" -Value $settingsGradle
    
    Write-Host "`nProject structure created at: $projectDir" -ForegroundColor Green
    Write-Host "`nNext steps:" -ForegroundColor Yellow
    Write-Host "1. Copy MTR JAR to: $projectDir\libs\" -ForegroundColor White
    Write-Host "2. Download Gradle wrapper or use: gradle wrapper" -ForegroundColor White
    Write-Host "3. Run: .\gradlew.bat setupDecompWorkspace" -ForegroundColor White
    Write-Host "4. Build: .\gradlew.bat build" -ForegroundColor White
}

else {
    Write-Host "Invalid choice." -ForegroundColor Red
}

Write-Host "`n=== Setup Complete ===" -ForegroundColor Cyan
