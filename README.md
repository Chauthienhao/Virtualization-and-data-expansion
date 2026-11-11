# Blockchain Vote Online — Hướng dẫn Docker (Hyperledger Besu QBFT)

Hệ thống bỏ phiếu trực tuyến gồm React/Vite (cử tri), FastAPI, Gradio (quản trị), MySQL 8.4 và mạng blockchain riêng **Hyperledger Besu QBFT gồm 4 validator**. Docker Compose chạy **8 container**. Ganache là cấu hình thử nghiệm cũ, không khởi chạy mặc định.

> Tài liệu dành cho **Windows 10/11 + PowerShell + Docker Desktop (Linux containers)**.

## 1. Kiến trúc và cổng

| Service | Chức năng | Địa chỉ trên máy Windows |
|---|---|---|
| `frontend` | React qua Nginx | http://localhost:3000 |
| `api` | FastAPI, Swagger | http://localhost:8001/docs |
| `admin` | Gradio Admin | http://localhost:7861 |
| `db` | MySQL 8.4, dữ liệu ngoài blockchain | Chỉ nội bộ Docker (`db:3306`) |
| `besu-node1` | Validator QBFT, RPC cho ứng dụng | http://localhost:8545 |
| `besu-node2` | Validator QBFT | http://localhost:8546 |
| `besu-node3` | Validator QBFT | http://localhost:8547 |
| `besu-node4` | Validator QBFT | http://localhost:8548 |

Các container ứng dụng gọi Besu qua `http://besu-node1:8545` và MySQL qua `db:3306`. Frontend chạy trong **trình duyệt Windows** nên gọi API qua `http://127.0.0.1:8001` (cấu hình build hiện tại). Bốn validator cùng nằm trên **một máy Docker**, chưa phải mô hình chịu lỗi khi mất cả máy chủ.

## 2. Chuẩn bị máy chưa cài Docker

1. Máy Windows 10/11 hỗ trợ ảo hóa; bật **Virtualization** trong BIOS/UEFI nếu đang tắt. Nên có **16 GB RAM máy vật lý** để chạy Docker Desktop và các ứng dụng khác; tài nguyên thực tế cần đo thêm.
2. Mở **PowerShell bằng quyền Administrator**, cài WSL nếu chưa có:
   ```powershell
   wsl --install
   ```
   Khởi động lại Windows khi được yêu cầu. Kiểm tra `wsl --status` và `wsl -l -v`. Nếu hệ thống đã có WSL 2 thì không cần cài lại.
3. Cài [Docker Desktop](https://www.docker.com/products/docker-desktop/). Trong **Settings → General**, bật **Use the WSL 2 based engine**; bảo đảm Docker đang ở **Linux containers**. Mở Docker Desktop và đợi Engine chạy.
4. Cài [Git for Windows](https://git-scm.com/downloads/win) và [Python 3.11](https://www.python.org/downloads/) (đánh dấu **Add Python to PATH** nếu trình cài đặt có tùy chọn). Python dùng để sinh khóa Admin; ứng dụng Python thực tế chạy trong container.
5. Kiểm tra trong PowerShell:
   ```powershell
   wsl --status
   docker --version
   docker compose version
   docker info --format '{{.OSType}}'
   git --version
   py -3.11 --version
   ```
   `docker info` phải trả về `linux`. Không cần cài MySQL, Node.js, Nginx hoặc Besu trực tiếp trên Windows.

## 3. Tải mã nguồn

```powershell
git clone -b bangchau https://github.com/Chauthienhao/Virtualization-and-data-expansion.git
cd Virtualization-and-data-expansion
```


## 4. Tạo môi trường và khóa bí mật — chỉ làm lần đầu

### 4.1. Python để chạy script sinh khóa

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install eth-account
python -c "from eth_account import Account; print('eth-account OK')"
```

Nếu PowerShell chặn kích hoạt `.venv`:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\.venv\Scripts\Activate.ps1
```

### 4.2. Sinh genesis QBFT và khóa 4 validator

**Cảnh báo:** `besu/generate.ps1` hiện tại **xóa `besu/generated/` và `besu/data/` mỗi lần chạy**. Chỉ chạy trên máy mới, trước khi có dữ liệu cần giữ. Không chạy lại khi mạng đã hoạt động.

Tải image Besu và tạo hàm `besu` trong **cùng cửa sổ PowerShell**. Hàm mount cố định thư mục `besu/` vì script tự chuyển vào thư mục này:

```powershell
docker pull hyperledger/besu:26.11.0
$BesuDir = (Resolve-Path .\besu).Path
function besu {
    docker run --rm -v "${BesuDir}:/w" -w /w hyperledger/besu:26.11.0 @args
}
besu --version
& .\besu\generate.ps1
```

Nếu script hoàn tất, kiểm tra:

```powershell
Test-Path .\besu\generated\genesis.json
Test-Path .\besu\generated\static-nodes.docker.json
Get-ChildItem .\besu\generated\node* -Directory
```

Phải có `genesis.json`, `static-nodes.docker.json` và 4 thư mục `node1`–`node4`.

**Lưu ý lỗi đã gặp với script hiện tại:** Besu có thể báo `Output directory already exists` ở bước `generate-blockchain-config`, dù đã tạo `generated/networkFiles/genesis.json` và 4 thư mục khóa. Nếu gặp lỗi, **không chạy lại toàn bộ script**. Kiểm tra `besu/generated/networkFiles/keys` có đúng 4 thư mục, sau đó hoàn tất phần chia khóa bằng đoạn sau (chạy từ thư mục gốc):

```powershell
Push-Location .\besu
$OUT = 'generated'
$dirs = @(Get-ChildItem "$OUT/networkFiles/keys" -Directory | Sort-Object Name)
if ($dirs.Count -ne 4) { Pop-Location; throw 'Khong du 4 khoa validator; dung lai de kiem tra.' }
$enodes = @(); $enodesDocker = @(); $i = 1
foreach ($d in $dirs) {
    $nodeDir = "$OUT/node$i"
    New-Item -ItemType Directory $nodeDir -Force | Out-Null
    Copy-Item "$($d.FullName)/key", "$($d.FullName)/key.pub" $nodeDir -Force
    $pub = (Get-Content "$($d.FullName)/key.pub" -Raw).Trim() -replace '^0x', ''
    $port = 30302 + $i
    $enodes += "`"enode://$pub@127.0.0.1:$port`""
    $enodesDocker += "`"enode://$pub@172.16.239.1$($i):30303`""
    $i++
}
Copy-Item "$OUT/networkFiles/genesis.json" "$OUT/genesis.json" -Force
'[' + ($enodes -join ',') + ']' | Set-Content "$OUT/static-nodes.json" -Encoding ascii
'[' + ($enodesDocker -join ',') + ']' | Set-Content "$OUT/static-nodes.docker.json" -Encoding ascii
Pop-Location
```

Nếu không có đủ 4 bộ khóa, cần kiểm tra lỗi trước khi tiếp tục. **Không xóa volume blockchain đang sử dụng để thử lại.**

### 4.3. Tạo `.env.docker`

Nếu repository có `.env.docker.example`:

```powershell
Copy-Item .env.docker.example .env.docker
notepad .env.docker
```

Điền các biến tối thiểu sau (giữ những biến khác trong file mẫu):

```dotenv
DOCKER_DB_ROOT_PASSWORD=DAT_MAT_KHAU_MYSQL_MANH
RPC_URL=http://besu-node1:8545
ADMIN_PRIVATE_KEY=DAN_KHOA_TRONG_besu/generated/admin_private_key.txt
CONTRACT_ADDRESS=
ABI_PATH=ElectionABI.json
DB_HOST=db
DB_PORT=3306
DB_USER=root
DB_PASSWORD=DAT_CUNG_MAT_KHAU_MYSQL_O_TREN
DB_NAME=election_admin
GRADIO_SERVER_NAME=0.0.0.0
VOTER_KEY_ENCRYPTION_KEY=KHOA_FERNET_DUOC_SINH_RIENG
CCCD_HASH_PEPPER=CHUOI_BI_MAT_NGAU_NHIEN
VOTER_FUNDING_AMOUNT_ETH=0.01
```

- Đọc `besu/generated/admin_private_key.txt` bằng Notepad và dán vào `ADMIN_PRIVATE_KEY`. **Không gửi/commit private key.**
- Sinh khóa Fernet (chỉ **một lần**, giữ nguyên nếu đã có dữ liệu cử tri):
  ```powershell
  python -m pip install cryptography
  python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
  ```
- `DB_PASSWORD` và `DOCKER_DB_ROOT_PASSWORD` phải thống nhất cho máy mới.
- `CONTRACT_ADDRESS` **để trống** trước khi deploy.
- Không sử dụng khóa bí mật mẫu hoặc khóa từ máy khác. File `.env.docker` phải được `.gitignore` loại trừ.

> **Không cần tạo `.env` để chạy hoàn toàn bằng Docker** theo hướng dẫn này. `.env` chỉ phục vụ các tác vụ chạy Python trực tiếp trên Windows nếu có nhu cầu riêng.

## 5. Khởi chạy lần đầu

Tất cả lệnh sau chạy tại thư mục gốc dự án:

```powershell
# Kiểm tra cú pháp và biến môi trường
docker compose --env-file .env.docker -f compose.yaml -f compose.besu.yaml config --quiet

# Khởi động 4 validator
docker compose --env-file .env.docker -f compose.yaml -f compose.besu.yaml up -d besu-node1 besu-node2 besu-node3 besu-node4

# Kiểm tra trạng thái
docker compose --env-file .env.docker -f compose.yaml -f compose.besu.yaml ps
```

Đợi 4 node báo `healthy`. Kiểm tra số block:

```powershell
$body = @{ jsonrpc='2.0'; method='eth_blockNumber'; params=@(); id=1 } | ConvertTo-Json -Compress
Invoke-RestMethod -Uri http://localhost:8545 -Method Post -ContentType 'application/json' -Body $body
```

Nếu `result` có dạng `0x...` và tăng khi gọi lại, blockchain đang tạo block.

### Deploy Smart Contract

```powershell
docker compose --env-file .env.docker -f compose.yaml -f compose.besu.yaml run --rm --build admin python deploy.py
```

Lệnh build image Python, biên dịch `Election.sol`, cập nhật ABI và deploy contract. **Sao chép địa chỉ `CONTRACT_ADDRESS=0x...` vừa in ra** vào `.env.docker` (không dùng địa chỉ từ mạng Ganache hoặc máy khác).

### Khởi động đủ 8 container

```powershell
docker compose --env-file .env.docker -f compose.yaml -f compose.besu.yaml up -d --build --force-recreate
docker compose --env-file .env.docker -f compose.yaml -f compose.besu.yaml ps
```

Mong đợi `db` và 4 node Besu `healthy`; `admin`, `api`, `frontend` ở trạng thái `Up`.

Mở:

- **Cử tri:** http://localhost:3000
- **Swagger API:** http://localhost:8001/docs
- **Quản trị:** http://localhost:7861

Thử tạo cuộc bầu cử mới, đăng ký cử tri, bỏ 1 phiếu và xem kết quả trong Admin. Giao diện mở được **chưa đủ** để khẳng định nghiệp vụ hoạt động.

## 6. Những lần chạy sau — không sinh lại khóa, không deploy lại

Mở Docker Desktop, đợi Engine chạy, vào thư mục dự án rồi chạy:

```powershell
docker compose --env-file .env.docker -f compose.yaml -f compose.besu.yaml up -d
docker compose --env-file .env.docker -f compose.yaml -f compose.besu.yaml ps
```

**Không chạy lại `generate.ps1`, không xóa volume và không deploy lại contract** nếu mạng Besu và địa chỉ hợp đồng hiện tại vẫn còn hoạt động.

## 7. Lệnh quản trị Docker

```powershell
# Xem trạng thái
docker compose --env-file .env.docker -f compose.yaml -f compose.besu.yaml ps

# Xem 100 dòng log mới nhất
docker compose --env-file .env.docker -f compose.yaml -f compose.besu.yaml logs --tail=100

# Xem RAM/CPU từng container
docker stats --no-stream

# Dừng các service (giữ dữ liệu)
docker compose --env-file .env.docker -f compose.yaml -f compose.besu.yaml stop

# Khởi động lại
docker compose --env-file .env.docker -f compose.yaml -f compose.besu.yaml up -d

# Gỡ container và network (giữ named volumes)
docker compose --env-file .env.docker -f compose.yaml -f compose.besu.yaml down
```

**TUYỆT ĐỐI không dùng `down -v` khi muốn giữ dữ liệu**: lệnh này có thể xóa volume MySQL và 4 volume Besu. Khi đổi genesis, dữ liệu chain cũ không còn tương thích; cần kế hoạch sao lưu và khởi tạo lại có chủ đích.

## 8. Xử lý lỗi thường gặp

| Hiện tượng | Kiểm tra / xử lý |
|---|---|
| `DOCKER_DB_ROOT_PASSWORD is missing` | Dùng `--env-file .env.docker`, kiểm tra biến có giá trị |
| `port 8545 already allocated` | Kiểm tra `docker ps`; dừng Ganache hoặc Besu Windows đang chiếm cổng |
| `Output directory already exists` khi sinh genesis | Kiểm tra `besu/generated/networkFiles` và làm theo mục 4.2; không chạy lại toàn script |
| `health: starting` | Chờ 30–60 giây, xem `docker logs --tail 100 besu-node1` |
| Không tạo block | Kiểm tra 4 node, genesis/khóa và `static-nodes.docker.json`; không tự sinh lại khóa |
| API trả `404` tại `/` | Bình thường nếu không có route gốc; thử `/docs` |
| Admin báo cuộc bầu cử thuộc contract cũ | Dữ liệu MySQL cũ đang trỏ contract trước đó; tạo cuộc bầu cử mới, không vội xóa DB |
| Sửa `.env.docker` nhưng app không nhận | Chạy `up -d --force-recreate` với cả hai Compose file |
| Frontend không gọi được API trên máy khác | Build arg hiện đang cố định `127.0.0.1:8001`; phải cấu hình lại URL công khai khi deploy Cloud |

## 9. Bảo mật và chuẩn bị Cloud/CI/CD

- **Không commit** `.env`, `.env.docker`, `besu/generated/`, `besu/data/`, private key hay dữ liệu blockchain. Kiểm tra `git status --short` và `git ls-files .env .env.docker besu/generated besu/data` trước khi push.
- `.dockerignore` phải loại trừ `besu/` và các file `.env*` để không đưa khóa vào image Python (`COPY . .`).
- **Cấu hình hiện tại chỉ dành cho local**: RPC của 4 Besu đang mở cổng trên host, `--rpc-http-cors-origins=*`, `--host-allowlist=*`; khi đưa lên VPS phải hạn chế truy cập bằng firewall, chỉ expose các dịch vụ thực sự cần thiết, dùng HTTPS/reverse proxy.
- Frontend đang build với `VITE_API_BASE_URL=http://127.0.0.1:8001`. Trên Cloud phải sửa thành API URL công khai (ưu tiên HTTPS) **và build lại frontend**.
- Không đẩy trực tiếp file khóa lên GitHub Actions; dùng secrets và quy trình cấp phát an toàn. Nếu giữ chain local khi chuyển Cloud, phải lập kế hoạch chuyển khóa/genesis và dữ liệu volume phù hợp; không mặc định sinh lại genesis.
- **Cloud và CI/CD chưa triển khai**; README này mô tả quy trình chạy local đã kiểm thử.

## 10. Trạng thái đồ án

- [x] Docker hóa Frontend, API, Admin và MySQL.
- [x] Docker hóa mạng Hyperledger Besu QBFT 4 validator.
- [x] Sinh genesis, validator keys và kết nối các node.
- [x] Deploy `Election.sol` lên Besu.
- [x] Kiểm thử tạo block, bỏ phiếu và hiển thị kết quả Admin trên local.
- [ ] Triển khai Cloud.
- [ ] Thiết lập GitHub Actions CI/CD.
