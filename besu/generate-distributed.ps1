# Sinh khoa admin + genesis QBFT + khoa 4 node vao besu/distributed/
# Chay: powershell -ExecutionPolicy Bypass -File besu\generate-distributed.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$OUT = "distributed"

if (Test-Path $OUT) {
    throw "Thu muc besu/distributed da ton tai. Dung lai de tranh ghi de khoa."
}

New-Item -ItemType Directory $OUT | Out-Null

# 1. Khoa admin (ADMIN_PRIVATE_KEY), duoc nap san ETH trong genesis
$line = python -c "from eth_account import Account; a=Account.create(); print(a.address, '0x'+a.key.hex().removeprefix('0x'))"
if ($LASTEXITCODE -ne 0) { throw "Khong sinh duoc khoa admin (can: pip install eth-account)" }
$parts = $line.Trim().Split(" ")
$ADMIN_ADDR = $parts[0]
$ADMIN_KEY  = $parts[1]
Set-Content "$OUT/admin_address.txt"     $ADMIN_ADDR -Encoding ascii
Set-Content "$OUT/admin_private_key.txt" $ADMIN_KEY  -Encoding ascii
(Get-Content "qbftConfigFile.template.json" -Raw).Replace("__ADMIN_ADDRESS__", $ADMIN_ADDR.Substring(2)) |
    Set-Content "$OUT/qbftConfigFile.json" -Encoding ascii

# Kiem tra xem Besu da duoc cai dat chua
if (-not (Get-Command besu -ErrorAction SilentlyContinue)) {
    throw "Khong tim thay Besu trong PATH. Hay cai Besu hoac them Besu vao PATH."
}
# 2. Sinh genesis + khoa 4 validator
besu operator generate-blockchain-config `
    --config-file="$OUT/qbftConfigFile.json" `
    --to="$OUT/networkFiles" `
    --private-key-file-name=key
if ($LASTEXITCODE -ne 0) { throw "besu operator generate-blockchain-config that bai" }
Copy-Item "$OUT/networkFiles/genesis.json" "$OUT/genesis.json"

# 3. Tao static-nodes.json cho 4 node
$enodes = @()
$tailscaleIPs = @(
    "100.110.188.113",
    "100.122.169.118",
    "100.125.228.77",
    "100.83.127.103"
)
$i = 1
foreach ($d in (Get-ChildItem "$OUT/networkFiles/keys" -Directory | Sort-Object Name)) {
    $nodeDir = "$OUT/node$i"
    New-Item -ItemType Directory $nodeDir | Out-Null
    Copy-Item "$($d.FullName)/key", "$($d.FullName)/key.pub" $nodeDir
    $pub  = (Get-Content "$($d.FullName)/key.pub" -Raw).Trim() -replace '^0x', ''
    $ip = $tailscaleIPs[$i - 1]
    $enodes += "`"enode://$pub@${ip}:30303`""
    $i++
}
"[" + ($enodes -join ",") + "]" |
    Set-Content "$OUT/static-nodes.json" -Encoding ascii

Write-Host ""
Write-Host "Xong. Cau hinh cho Node 4:"
Write-Host "  RPC_URL=http://127.0.0.1:8554 (Windows)"
Write-Host "  RPC_URL=http://besu-node4:8545 (Docker)"
Write-Host "  ADMIN_PRIVATE_KEY=$ADMIN_KEY"
Write-Host "  CONTRACT_ADDRESS= (dien sau khi deploy Election.sol)"
