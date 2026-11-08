# Chay 1 node Besu. Vi du: powershell -ExecutionPolicy Bypass -File besu\start-node.ps1 -N 1
# node N: RPC = 8544+N (8545..8548), P2P = 30302+N (30303..30306)
param([Parameter(Mandatory = $true)][ValidateRange(1, 4)][int]$N)
Set-Location $PSScriptRoot
$G       = "generated"
$p2pPort = 30302 + $N
$rpcPort = 8544 + $N

if (-not (Test-Path "$G/genesis.json")) { throw "Chua co $G/genesis.json - hay chay generate.ps1 truoc" }

$env:BESU_OPTS = "-Xmx768m"   # gioi han RAM moi node, 4 node chay cung may
$host.UI.RawUI.WindowTitle = "Besu node$N (RPC $rpcPort)"

besu `
    "--data-path=data/node$N" `
    "--genesis-file=$G/genesis.json" `
    "--node-private-key-file=$G/node$N/key" `
    "--static-nodes-file=$G/static-nodes.json" `
    "--p2p-host=127.0.0.1" "--p2p-port=$p2pPort" `
    "--rpc-http-enabled" "--rpc-http-host=127.0.0.1" "--rpc-http-port=$rpcPort" `
    "--rpc-http-api=ETH,NET,WEB3,QBFT,ADMIN,TXPOOL" `
    "--rpc-http-cors-origins=*" "--host-allowlist=*" `
    "--min-gas-price=0"
