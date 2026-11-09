# Mo 4 cua so PowerShell, moi cua so chay 1 node Besu.
# Chay: powershell -ExecutionPolicy Bypass -File besu\start-all.ps1
foreach ($n in 1..4) {
    Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass",
        "-File", "`"$PSScriptRoot\start-node.ps1`"", "-N", $n
}
