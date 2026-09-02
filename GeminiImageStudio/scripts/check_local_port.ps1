# Exit codes:

#   0 = port in use and (optional) health URL OK — safe to reuse

#   1 = port free — caller should start the service

#   2 = port in use but health check failed / not our service

param(

    [string]$HostAddress = "127.0.0.1",

    [Parameter(Mandatory = $true)][int]$Port,

    [string]$HealthUrl = ""

)



$listening = Get-NetTCPConnection -LocalAddress $HostAddress -LocalPort $Port -State Listen -ErrorAction SilentlyContinue

if (-not $listening) {

    # Also match Any / 0.0.0.0 binds

    $listening = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |

        Where-Object { $_.LocalAddress -in @($HostAddress, "0.0.0.0", "::", "::1") }

}



if (-not $listening) {

    exit 1

}



if ($HealthUrl) {

    try {

        $resp = Invoke-WebRequest -Uri $HealthUrl -UseBasicParsing -TimeoutSec 3

        if ($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 300) {

            exit 0

        }

        exit 2

    }

    catch {

        exit 2

    }

}



# Port occupied; no health URL — treat as reusable listener (e.g. Vite)

exit 0


