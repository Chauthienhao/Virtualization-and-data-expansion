# Sinh khoa admin + genesis QBFT + khoa 4 node vao besu/generated/
# Chay: powershell -ExecutionPolicy Bypass -File besu\generate.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$OUT = "generated"

if (Test-Path $OUT)   { Remove-Item -Recurse -Force $OUT }
if (Test-Path "data") { Remove-Item -Recurse -Force "data" }   # genesis moi => chain cu khong dung duoc nua
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

# 2. Sinh genesis + khoa 4 validator
besu operator generate-blockchain-config `
    --config-file="$OUT/qbftConfigFile.json" `
    --to="$OUT/networkFiles" `
    --private-key-file-name=key
if ($LASTEXITCODE -ne 0) { throw "besu operator generate-blockchain-config that bai" }
Copy-Item "$OUT/networkFiles/genesis.json" "$OUT/genesis.json"

# 3. Chia khoa vao node1..node4 va tao 2 file static-nodes:
#    - static-nodes.json        : chay tren Windows, 4 node cung may, port 30303..30306
#    - static-nodes.docker.json : chay trong Docker (compose.besu.yaml), moi container 1 IP rieng
#      172.16.239.11..14, cung port 30303
#    Dung chung genesis va khoa, chi khac dia chi ket noi giua cac node.
$enodes = @()
$enodesDocker = @()
$i = 1
foreach ($d in (Get-ChildItem "$OUT/networkFiles/keys" -Directory | Sort-Object Name)) {
    $nodeDir = "$OUT/node$i"
    New-Item -ItemType Directory $nodeDir | Out-Null
    Copy-Item "$($d.FullName)/key", "$($d.FullName)/key.pub" $nodeDir
    $pub  = (Get-Content "$($d.FullName)/key.pub" -Raw).Trim() -replace '^0x', ''
    $port = 30302 + $i
    $enodes       += "`"enode://$pub@127.0.0.1:$port`""
    $enodesDocker += "`"enode://$pub@172.16.239.1$($i):30303`""
    $i++
}
"[" + ($enodes -join ",") + "]"       | Set-Content "$OUT/static-nodes.json"        -Encoding ascii
"[" + ($enodesDocker -join ",") + "]" | Set-Content "$OUT/static-nodes.docker.json" -Encoding ascii

Write-Host ""
Write-Host "Xong. Dien vao .env:"
Write-Host "  RPC_URL=http://127.0.0.1:8545"
Write-Host "  ADMIN_PRIVATE_KEY=$ADMIN_KEY"
Write-Host "  CONTRACT_ADDRESS=   (dien sau khi chay deploy.py)"
