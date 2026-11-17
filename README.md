# Hướng dẫn triển khai và demo Blockchain Vote trên 4 máy

> **Windows + PowerShell | Besu 26.11.0 | QBFT (4 validator) | Tailscale | Không dùng VPS.**
>
> **Trạng thái:** Bộ cấu hình đã được đối chiếu genesis, enode, IP và lệnh khởi chạy. **Chưa kiểm thử liên máy hoặc deploy hợp đồng trên mạng mới.** Làm theo thứ tự bên dưới; khi gặp lỗi thì dừng và báo người điều phối.

## 1. Kiến trúc và lưu ý

| Node | Máy | IP Tailscale | Chạy | Gói nhận |
|---|---|---|---|---|
| 1 | `admin-pc` | `100.110.188.113` | Besu + JDK đi kèm, không Docker | `Node1-Java.zip` |
| 2 | `phong` | `100.122.169.118` | Besu + JDK đi kèm, không Docker | `Node2-Java.zip` |
| 3 | `inspiron-5420` | `100.125.228.77` | Docker Desktop | `Node3-Docker.zip` |
| 4 | `bc` | `100.83.127.103` | Docker: Besu + Frontend + API + Admin + MySQL | Thư mục repo của người điều phối |

- Cả bốn validator dùng **cùng genesis**, **khóa riêng khác nhau**; P2P **TCP/UDP 30303** qua Tailscale; chain ID **1337** (`0x539`).
- Mạng cần **ít nhất 3/4 validator kết nối và đồng thuận** để tiếp tục tạo block. Chạy được container **không đồng nghĩa** mạng đã hoạt động.
- **Không xóa** `data/`, Docker volume, không chạy `docker compose down -v`, không sinh lại genesis/khóa; **không đưa ZIP, file `key`, `.env` lên GitHub công khai**.
- Node 4 cung cấp giao diện. Các máy Node 1–3 chủ yếu xác thực blockchain; không cần chạy Frontend/API/MySQL.

## 2. Thiết lập chung — làm một lần trên cả 4 máy

1. Cài **Tailscale**, đăng nhập tailnet nhóm, bật kết nối. Trong PowerShell kiểm tra:

   ```powershell
   tailscale ip -4
   tailscale status
   ```

   IP máy phải khớp bảng trên. Nếu khác, báo người điều phối.

2. Node 1–3: nhận **đúng ZIP của máy**, giải nén, mở thư mục `Node1-Java`, `Node2-Java` hoặc `Node3-Docker`. Node 4: dùng thư mục gốc repo hiện có.
3. Mở **PowerShell bằng Run as administrator**, chuyển tới thư mục chứa `setup-besu-firewall.ps1` (có thể mở PowerShell ngay trong thư mục rồi chọn Run as administrator và `cd` lại). Chạy:

   ```powershell
   Set-ExecutionPolicy -Scope Process Bypass
   .\setup-besu-firewall.ps1
   ```

   Script mở inbound TCP/UDP `30303` cho bốn IP Tailscale. Nếu rule cũ đã tồn tại nhưng IP thay đổi, cần nhờ người điều phối sửa rule.

## 3. Node 1 — `admin-pc` (Java)

1. Giải nén `Node1-Java.zip` → mở thư mục `Node1-Java`.
2. Hoàn thành **mục 2**. **Không cần cài Java** vì đã có thư mục `jdk/`.
3. Nhấp đúp `start-node1.bat`, hoặc chạy PowerShell trong thư mục:

   ```powershell
   .\start-node1.bat
   ```

4. **Giữ cửa sổ Besu mở** suốt buổi demo. Muốn dừng: `Ctrl+C`; chạy lại bằng `.\start-node1.bat`.

**Kiểm tra trên Node 1** (PowerShell thứ hai, không đóng Besu):

```powershell
$body = '{"jsonrpc":"2.0","method":"eth_chainId","params":[],"id":1}'
Invoke-RestMethod -Uri http://127.0.0.1:8545 -Method Post -ContentType application/json -Body $body
```

Kết quả mong đợi `result: 0x539`.

## 4. Node 2 — `phong` (Java)

1. Giải nén `Node2-Java.zip` → mở thư mục `Node2-Java`.
2. Hoàn thành **mục 2**. Không cần cài Java.
3. Chạy:

   ```powershell
   .\start-node2.bat
   ```

4. Giữ cửa sổ Besu mở. Dừng `Ctrl+C`; chạy lại bằng lệnh trên. Kiểm tra RPC bằng **cùng lệnh Node 1** (`http://127.0.0.1:8545`), mong đợi `0x539`.

## 5. Node 3 — `inspiron-5420` (Docker)

1. Cài **Docker Desktop**; bật WSL 2/Linux containers theo hướng dẫn cài đặt, mở Docker Desktop và chờ Engine chạy. Cài Tailscale.
2. Giải nén `Node3-Docker.zip` → mở PowerShell tại **thư mục `Node3-Docker`** (nơi có file YAML).
3. Hoàn thành **mục 2** (firewall).
4. Chạy lần lượt:

   ```powershell
   docker info --format '{{.OSType}}'
   docker compose -f .\compose.distributed.node3.yaml config --quiet
   docker compose -f .\compose.distributed.node3.yaml up -d
   docker compose -f .\compose.distributed.node3.yaml ps
   ```

   Dòng đầu phải in `linux`; container cần ở trạng thái `Up` (nếu có healthcheck thì đợi `healthy`).

5. Kiểm tra RPC (PowerShell):

   ```powershell
   $body = '{"jsonrpc":"2.0","method":"eth_chainId","params":[],"id":1}'
   Invoke-RestMethod -Uri http://127.0.0.1:8553 -Method Post -ContentType application/json -Body $body
   ```

   Mong đợi `0x539`. Xem log nếu lỗi:

   ```powershell
   docker compose -f .\compose.distributed.node3.yaml logs --tail=60
   ```

**Dừng/chạy lại:**

```powershell
docker compose -f .\compose.distributed.node3.yaml stop
docker compose -f .\compose.distributed.node3.yaml start
```

> Nếu lỗi `bind` địa chỉ `100.125.228.77`, báo người điều phối; không tự sửa IP hoặc xóa volume.

## 6. Node 4 — `bc` (Docker + ứng dụng)

**Chỉ người điều phối làm**, tại thư mục gốc `D:\CodeNam3\Virtualization-and-data-expansion`. Cần Docker Desktop, Tailscale, các file `compose.distributed.node4.yaml`, `compose.distributed.app.yaml`, `.env.distributed.docker`, `.env`/biến mật khẩu MySQL theo cấu hình hiện tại. Không dùng `compose.besu.yaml` của mạng cục bộ cũ.

**Lần đầu hoặc sau khi tạo lại Docker network:**

```powershell
docker network inspect besu-distributed-app-net 2>$null
# Nếu báo network không tồn tại thì chạy:
docker network create besu-distributed-app-net
```

**Bật Node 4:**

```powershell
docker compose -f .\compose.distributed.node4.yaml up -d
docker compose -f .\compose.distributed.node4.yaml ps
```

**Bật bốn container ứng dụng:**

```powershell
docker compose --env-file .env.distributed.docker -f .\compose.distributed.app.yaml up -d --build
docker compose --env-file .env.distributed.docker -f .\compose.distributed.app.yaml ps
```

> Lần sau, khi không đổi mã nguồn, có thể bỏ `--build`. `.env.distributed.docker` phải có `RPC_URL=http://besu-node4:8545` (tên mạng Docker đã cấu hình), DB trỏ `db:3306`, mật khẩu DB đồng nhất, và `ADMIN_PRIVATE_KEY` đúng tài khoản triển khai. Để `CONTRACT_ADDRESS=` trống cho đến khi deploy mạng mới.

**Mở trên máy Node 4:**

| Giao diện | URL |
|---|---|
| Cử tri | http://localhost:3002 |
| Quản trị | http://localhost:7862 |
| API Swagger | http://localhost:8002/docs |

## 7. Kiểm tra đủ validator — Node 4 thực hiện trước khi deploy

Trong PowerShell Node 4, tạo hàm RPC dùng lại:

```powershell
function Rpc($method, $params = @()) {
    $body = @{jsonrpc='2.0'; method=$method; params=$params; id=1} | ConvertTo-Json -Depth 10 -Compress
    (Invoke-RestMethod -Uri 'http://127.0.0.1:8554' -Method Post -ContentType 'application/json' -Body $body).result
}
Rpc 'eth_chainId'       # 0x539
Rpc 'net_peerCount'     # ví dụ 0x2 hoặc 0x3
Rpc 'eth_blockNumber'   # ghi lại số block
Start-Sleep -Seconds 6
Rpc 'eth_blockNumber'   # phải lớn hơn lần trước
```

**Chỉ deploy khi block thực sự tăng.** `net_peerCount` là số peer mà **Node 4** thấy, không phải tổng số validator online toàn mạng; Node 4 có thể thấy 2 peer trong mạng 3 validator đang hoạt động.

## 8. Deploy `Election.sol` — chỉ Node 4, làm một lần khi mạng tạo block

**Đã kiểm tra `deploy.py` trong bản mã nguồn đính kèm trước đây:** script dùng `RPC_URL`, `ADMIN_PRIVATE_KEY`, biên dịch `Election.sol` bằng `py-solc-x`, ký giao dịch và in `CONTRACT_ADDRESS=0x...`. **Chưa xác minh được phiên bản `deploy.py` mới nhất trên nhánh `bangchau`**, vì vậy kiểm tra nhanh file tại máy trước khi chạy:

```powershell
Select-String .\deploy.py -Pattern 'RPC_URL|ADMIN_PRIVATE_KEY|compile_contract|wait_for_transaction_receipt'
Select-String .\requirements.txt -Pattern 'py-solc-x'
```

**Bước 1. Kiểm tra RPC và tài khoản deploy từ container API:**

```powershell
docker exec blockchain_distributed_api python -c "import os; from web3 import Web3; w=Web3(Web3.HTTPProvider(os.environ['RPC_URL'])); a=w.eth.account.from_key(os.environ['ADMIN_PRIVATE_KEY']).address; print('Connected:',w.is_connected()); print('Chain:',w.eth.chain_id); print('Admin address:',a); print('Balance (ETH):',w.from_wei(w.eth.get_balance(a),'ether'))"
```

Phải thấy `Connected: True`, `Chain: 1337` và **balance đủ trả gas**. Nếu balance bằng 0, **dừng lại**: cần cấp tiền cho đúng tài khoản trong genesis hoặc nạp từ tài khoản đã được cấp tiền; không tự sinh lại genesis khi đã chạy mạng.

**Bước 2. Deploy bằng container Python của ứng dụng:**

```powershell
docker compose --env-file .env.distributed.docker -f .\compose.distributed.app.yaml run --rm --no-deps admin python deploy.py
```

> Nếu báo không tìm thấy `py-solc-x`/`solcx`, phải bổ sung dependency vào image Python và build lại trước khi chạy. Lần đầu tải Solidity compiler cần Internet. Nếu lỗi `transaction underpriced`, `insufficient funds`, `timeout`, hoặc `revert`, **không deploy lặp vô điều kiện**; kiểm tra transaction/receipt trước.
>
> **ABI:** `deploy.py` có ghi `ElectionABI.json` trong container. Vì container `run --rm` là tạm thời, file ABI đó **không tự đồng bộ về repo Windows**. Trước khi demo cần xác nhận `ElectionABI.json` đang được build vào API/Admin **khớp với `Election.sol`**; nếu khác, phải cập nhật ABI trên host và rebuild image ứng dụng.

**Bước 3. Sau khi script báo deploy thành công**, sao chép đúng dòng địa chỉ hợp đồng, mở:

```powershell
notepad .\.env.distributed.docker
```

Đặt:

```dotenv
CONTRACT_ADDRESS=0xDIA_CHI_HOP_DONG_MOI_VUA_DEPLOY
```

**Bước 4. Tạo lại API và Admin để đọc biến môi trường mới:**

```powershell
docker compose --env-file .env.distributed.docker -f .\compose.distributed.app.yaml up -d --force-recreate --no-deps api admin
```

**Bước 5. Xác nhận hợp đồng thực sự tồn tại trên blockchain:**

```powershell
docker exec blockchain_distributed_api python -c "import os; from web3 import Web3; w=Web3(Web3.HTTPProvider(os.environ['RPC_URL'])); a=os.environ['CONTRACT_ADDRESS']; print('Contract:',a); print('Code bytes:',len(w.eth.get_code(Web3.to_checksum_address(a))))"
```

`Code bytes` phải **lớn hơn 0**. Mở lại Admin `http://localhost:7862`; không còn cảnh báo thiếu `CONTRACT_ADDRESS`. Nếu lỗi, xem `docker logs --tail=80 blockchain_distributed_admin` và `docker logs --tail=80 blockchain_distributed_api`.

**Chỉ deploy lại nếu hợp đồng thực sự chưa tồn tại/không còn phù hợp.** Nếu hợp đồng đã có trên mạng đang chạy, giữ nguyên địa chỉ và dữ liệu.

## 9. Kịch bản demo — làm theo đúng thứ tự

| Bước | Máy | Thao tác / lệnh | Kết quả cần chứng minh |
|---|---|---|---|
| 1 | Cả 4 | Bật Tailscale, kiểm tra `tailscale ip -4` | Đúng IP; các máy online |
| 2 | Node 1 | `.\start-node1.bat` | Besu khởi chạy |
| 3 | Node 2 | `.\start-node2.bat` | Besu khởi chạy |
| 4 | Node 3 | `docker compose -f .\compose.distributed.node3.yaml up -d` | Besu container `Up` |
| 5 | Node 4 | Hai lệnh `up -d` ở **mục 6** | Besu + 4 container ứng dụng `Up` |
| 6 | Node 4 | Chạy `Rpc 'net_peerCount'` và hai lần `Rpc 'eth_blockNumber'` ở **mục 7** | Có peer, block tăng |
| 7 | Node 4 | **Lần đầu:** deploy theo **mục 8**, cập nhật địa chỉ, recreate API/Admin | Hợp đồng có bytecode, Admin kết nối |
| 8 | Node 4 | Mở `http://localhost:7862`, cấu hình cuộc bầu cử, ứng viên và quyền cử tri theo giao diện | Dữ liệu nghiệp vụ sẵn sàng |
| 9 | Node 4 | Mở `http://localhost:3002`, thực hiện đăng ký/xác thực và bỏ phiếu theo luồng giao diện | Có giao dịch thành công; kết quả được cập nhật |
| 10 | Node 4 | `Rpc 'eth_blockNumber'`, đối chiếu giao dịch/biên nhận và kết quả Admin | Phiếu được ghi nhận trên blockchain |
| 11 | Node 2 | `Ctrl+C` dừng Besu | Còn 3 validator; Node 4 kiểm tra block **vẫn tăng** |
| 12 | Node 2 | `.\start-node2.bat` | Node 2 trở lại; block đồng bộ |

> **Dữ liệu MySQL của mạng mới tách biệt mạng cục bộ cũ.** Trước bước 8–9 cần chuẩn bị tài khoản, cử tri, ứng viên và dữ liệu demo hợp lệ. Chưa thể cam kết chi tiết từng nút bấm khi chưa kiểm thử phiên bản UI hiện tại.

### Lệnh nhanh khi trình diễn — Node 4

```powershell
Rpc 'net_peerCount'
Rpc 'eth_blockNumber'
Start-Sleep -Seconds 6
Rpc 'eth_blockNumber'
Rpc 'qbft_getValidatorsByBlockNumber' @('latest')
```

### Lệnh nhanh khi trình diễn — Node 1 / Node 2

```powershell
$body = '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'
Invoke-RestMethod -Uri http://127.0.0.1:8545 -Method Post -ContentType application/json -Body $body
```

### Lệnh nhanh khi trình diễn — Node 3

```powershell
$body = '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'
Invoke-RestMethod -Uri http://127.0.0.1:8553 -Method Post -ContentType application/json -Body $body
```

## 10. Lỗi thường gặp / kết thúc demo

- **Node offline:** bật Tailscale và Besu; không cần ping liên tục khi máy đã biết offline.
- **Node chạy nhưng không có peer:** kiểm tra IP Tailscale, firewall TCP/UDP `30303`, Docker bind IP, log Besu và chính sách Tailscale.
- **Block đứng yên:** chưa đủ quorum hoặc peer chưa kết nối; không deploy cho đến khi block tăng.
- **Admin thiếu hợp đồng:** kiểm tra `CONTRACT_ADDRESS`, RPC, bytecode và recreate API/Admin.
- **Node 3 Docker lỗi bind IP Tailscale:** báo người điều phối; kiểm tra cấu hình publish cổng trước khi sửa.
- **Kết thúc demo:** Node 1–2 `Ctrl+C`; Node 3 `docker compose -f .\compose.distributed.node3.yaml stop`; Node 4 dùng `docker compose -f .\compose.distributed.node4.yaml stop` và `docker compose --env-file .env.distributed.docker -f .\compose.distributed.app.yaml stop`.
- **Không xóa volume hoặc thư mục dữ liệu** nếu muốn mở lại mạng sau demo.

**Tiêu chí hoàn thành:** 4 node có thể kết nối, block tăng, deploy hợp đồng thành công, bỏ phiếu ghi nhận giao dịch, dừng 1 validator mà 3 validator còn lại vẫn tiếp tục tạo block.
