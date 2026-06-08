# PowerShell script to transfer files to Raspberry Pi
param(
    [Parameter(Mandatory=$true)]
    [string]$RaspberryPiIP,
    
    [Parameter(Mandatory=$false)]
    [string]$Username = "pi"
)

Write-Host "Transferring files to Raspberry Pi at $RaspberryPiIP..."

# Create remote directory
Write-Host "Creating directory on Raspberry Pi..."
ssh ${Username}@${RaspberryPiIP} "mkdir -p ~/dlonedge"

# Transfer all files
Write-Host "Transferring files..."
scp -r ./* ${Username}@${RaspberryPiIP}:~/dlonedge/

# Set up the environment
Write-Host "Setting up the environment..."
ssh ${Username}@${RaspberryPiIP} "cd ~/dlonedge && chmod +x setup.sh && ./setup.sh"

Write-Host "`nTransfer complete! To run the tests:"
Write-Host "1. SSH into your Raspberry Pi: ssh ${Username}@${RaspberryPiIP}"
Write-Host "2. Navigate to the directory: cd ~/dlonedge"
Write-Host "3. Activate the environment: source dlonedge/bin/activate"
Write-Host "4. Run the tests: python3 run_tests.py" 