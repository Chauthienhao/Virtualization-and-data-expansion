$ErrorActionPreference = "Stop"

$peers = @(
    "100.110.188.113",
    "100.122.169.118",
    "100.125.228.77",
    "100.83.127.103"
)

foreach ($protocol in @("TCP", "UDP")) {
    $name = "Besu QBFT P2P $protocol"

    if (-not (Get-NetFirewallRule -DisplayName $name -ErrorAction SilentlyContinue)) {
        New-NetFirewallRule `
            -DisplayName $name `
            -Direction Inbound `
            -Action Allow `
            -Protocol $protocol `
            -LocalPort 30303 `
            -RemoteAddress $peers `
            -Profile Any | Out-Null

        Write-Host "Created: $name"
    }
    else {
        Write-Host "Already exists: $name"
    }
}

Write-Host "Firewall configuration completed."
