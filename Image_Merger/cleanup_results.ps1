# Script to organize the results folder
$resultsDir = "static/results"

# Create folders if they don't exist
$folders = @(
    "feature_merge",
    "blend",
    "side_by_side",
    "enhanced",
    "matches",
    "preprocessed",
    "archive"
)

foreach ($folder in $folders) {
    $path = Join-Path -Path $resultsDir -ChildPath $folder
    if (-not (Test-Path $path)) {
        New-Item -ItemType Directory -Path $path | Out-Null
        Write-Host "Created folder: $path"
    }
}

# Move files to appropriate folders
$moveMap = @{
    "feature_" = "feature_merge"
    "blend_" = "blend"
    "sidebyside_" = "side_by_side"
    "enhanced_" = "enhanced"
    "matches_" = "matches"
    "preprocessed_" = "preprocessed"
}

# Count statistics
$stats = @{
    "Moved" = 0
    "Archived" = 0
}

# Process all files in the results folder
Get-ChildItem -Path $resultsDir -File | ForEach-Object {
    $file = $_
    $handled = $false
    
    # Check if file matches any of our prefixes
    foreach ($prefix in $moveMap.Keys) {
        if ($file.Name -like "$prefix*") {
            $destFolder = Join-Path -Path $resultsDir -ChildPath $moveMap[$prefix]
            $destPath = Join-Path -Path $destFolder -ChildPath $file.Name
            
            Move-Item -Path $file.FullName -Destination $destPath -Force
            Write-Host "Moved $($file.Name) to $($moveMap[$prefix])"
            $stats["Moved"]++
            $handled = $true
            break
        }
    }
    
    # Handle old "merged_" files (move to archive)
    if (-not $handled -and $file.Name -like "merged_*") {
        $archiveFolder = Join-Path -Path $resultsDir -ChildPath "archive"
        $destPath = Join-Path -Path $archiveFolder -ChildPath $file.Name
        
        Move-Item -Path $file.FullName -Destination $destPath -Force
        Write-Host "Archived $($file.Name)"
        $stats["Archived"]++
    }
}

# Print summary
Write-Host "`n====== Summary ======"
Write-Host "Files moved to categorized folders: $($stats['Moved'])"
Write-Host "Old files archived: $($stats['Archived'])"
Write-Host "======================" 