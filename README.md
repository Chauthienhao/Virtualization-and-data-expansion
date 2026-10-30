# Blockchain Vote Online – Docker Deployment

## 1. Giới thiệu

Dự án hệ thống bỏ phiếu trực tuyến sử dụng Blockchain, được triển khai bằng Docker Compose nhằm đóng gói các thành phần ứng dụng và hỗ trợ triển khai trên nhiều môi trường.

## 2. Công nghệ sử dụng

- **Frontend:** React, Vite, Tailwind CSS
- **Backend API:** Python, FastAPI
- **Admin:** Python, Gradio
- **Database:** MySQL 8.4
- **Blockchain:** Ethereum Smart Contract (Solidity), Ganache
- **Containerization:** Docker, Docker Compose
- **Web Server:** Nginx

## 3. Các thành phần Docker

| Service | Chức năng | Cổng truy cập |
|---|---|---|
| frontend | Giao diện cử tri (React + Nginx) | 3000 |
| api | Backend FastAPI | 8001 |
| admin | Giao diện quản trị Gradio | 7861 |
| db | Cơ sở dữ liệu MySQL | Nội bộ Docker |
| ganache | Blockchain thử nghiệm Ethereum (Ganache CLI) | 8545 |

**Lưu ý:** Ganache đã chạy trong Docker, không cần mở Ganache Desktop. Container dùng volume `ganache_data` để lưu blockchain.

## 4. Cài đặt trên máy Windows mới

1. Cài [Docker Desktop](https://www.docker.com/products/docker-desktop/) (sử dụng WSL 2 và **Linux containers**), [Git](https://git-scm.com/downloads/win) và [Python 3.11](https://www.python.org/downloads/). Khi cài Python, chọn **Add Python to PATH**.
2. Khởi động lại Windows nếu được yêu cầu; mở Docker Desktop và đợi Docker Engine chạy.
3. Mở **PowerShell**, kiểm tra:

```powershell
docker --version
docker compose version
git --version
py -3.11 --version
```

Không cần cài riêng MySQL, Node.js hoặc Ganache Desktop.

## 5. Tải mã nguồn và cấu hình

### Bước 1: Clone nhánh `bangchau`

Trong PowerShell, chuyển đến thư mục muốn lưu dự án, sau đó chạy:

```powershell
git clone -b bangchau https://github.com/Chauthienhao/Virtualization-and-data-expansion.git
cd Virtualization-and-data-expansion
```

Nếu đã clone nhánh `hao`, dùng `git fetch origin` rồi `git switch -c bangchau --track origin/bangchau` (chỉ khi chưa có nhánh `bangchau` trên máy và đã xử lý các thay đổi chưa lưu).

### Bước 2: Cài thư viện Python

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Nếu PowerShell chặn kích hoạt `.venv`, chạy `Set-ExecutionPolicy -Scope Process Bypass` rồi kích hoạt lại.

### Bước 3: Tạo `.env` và `.env.docker`

Tạo 2 file .env, .env.docker

```powershell
# .env
RPC_URL=http://127.0.0.1:8545
ADMIN_ACCOUNT_INDEX=0
ADMIN_PRIVATE_KEY=
CONTRACT_ADDRESS=<dia_chi_smart_contract_da_deploy>
```

```powershell
# .env.docker
RPC_URL=http://ganache:8545
CONTRACT_ADDRESS=<dia_chi_smart_contract_da_deploy>
ADMIN_ACCOUNT_INDEX=0
ADMIN_PRIVATE_KEY=
ABI_PATH=ElectionABI.json
DB_HOST=db
DB_PORT=3306
DB_NAME=election_admin
```

## 6. Khởi chạy hệ thống (lần đầu)

### Bước 4: Chạy Ganache trong Docker

```powershell
docker compose --env-file .env.docker up -d ganache
```

Kiểm tra blockchain:

```powershell
python -c "from web3 import Web3; w=Web3(Web3.HTTPProvider('http://127.0.0.1:8545')); print('Connected:',w.is_connected()); print('Chain ID:',w.eth.chain_id)"
```

Kết quả cần có `Connected: True` và `Chain ID: 1337`.

### Bước 5: Deploy Smart Contract

Kiểm tra số dư ETH thử nghiệm của tài khoản Admin:

```powershell
python -c "from web3 import Web3; w=Web3(Web3.HTTPProvider('http://127.0.0.1:8545')); a=w.eth.accounts[0]; print('Admin:',a); print('ETH:',w.from_wei(w.eth.get_balance(a),'ether'))"
```

Nếu tài khoản có **0 ETH**, cấp 100 ETH thử nghiệm trên **Ganache local**:

```powershell
python -c "from web3 import Web3; w=Web3(Web3.HTTPProvider('http://127.0.0.1:8545')); a=w.eth.accounts[0]; print(w.provider.make_request('evm_setAccountBalance',[a,hex(w.to_wei(100,'ether'))]))"
```

Nếu lỗi, bị chặn:
```powershell
docker compose --env-file .env.docker exec admin python -c "from web3 import Web3; import os; w=Web3(Web3.HTTPProvider(os.environ['RPC_URL'])); a=w.eth.accounts[0]; print(w.provider.make_request('evm_setAccountBalance',[a,hex(w.to_wei(100,'ether'))])); print('Account:',a); print('Balance:',w.from_wei(w.eth.get_balance(a),'ether'),'ETH')"
```

Sau đó deploy:

```powershell
python deploy.py
```

Nếu bị chặn:
```powershell
docker compose --env-file .env.docker exec admin python deploy.py
```

Sao chép địa chỉ hợp đồng vừa tạo vào `CONTRACT_ADDRESS` của **cả `.env` và `.env.docker`**. Mỗi máy có Ganache riêng nên không dùng địa chỉ hợp đồng từ máy khác. Nếu `deploy.py` cập nhật `ElectionABI.json`, bước build tiếp theo sẽ đưa ABI mới vào image.

### Bước 6: Build và chạy 5 container

```powershell
docker compose --env-file .env.docker up -d --build
docker compose --env-file .env.docker ps
```

Cần thấy đủ `db` (**healthy**), `ganache`, `admin`, `api`, `frontend` ở trạng thái **Up**. Lần đầu Docker cần tải image nên có thể mất vài phút.

### Bước 7: Mở 3 trang để kiểm tra

- **Frontend:** http://localhost:3000
- **FastAPI Swagger:** http://localhost:8001/docs
- **Gradio Admin:** http://localhost:7861

Nếu cả ba trang mở được, vào Admin kiểm tra thông báo blockchain đã kết nối và tài khoản đang dùng là Admin của hợp đồng. Đây mới là kiểm tra khởi động; nghiệp vụ bỏ phiếu cần được kiểm thử riêng.

**Nếu có lỗi:** xem log bằng `docker compose --env-file .env.docker logs --tail=100` và kiểm tra lại `.env.docker`, `CONTRACT_ADDRESS` cùng trạng thái Docker Desktop. Các lần chạy sau chỉ cần mở Docker Desktop rồi dùng `docker compose --env-file .env.docker up -d`; không cần deploy lại nếu blockchain và hợp đồng vẫn còn.

## 7. Các lệnh Docker thường dùng

Xem trạng thái container:

```bash
docker compose --env-file .env.docker ps
```

Xem log:

```bash
docker compose --env-file .env.docker logs -f
```

Dừng container:

```bash
docker compose --env-file .env.docker stop
```

Khởi động lại:

```bash
docker compose --env-file .env.docker up -d
```

Không sử dụng `docker compose down -v` nếu muốn giữ dữ liệu MySQL **và blockchain Ganache**. Các volume `mysql_data` và `ganache_data` lưu dữ liệu độc lập với vòng đời container.

Kiểm tra hợp đồng còn tồn tại sau khi khởi động lại Ganache:

```bash
docker compose --env-file .env.docker stop ganache
docker compose --env-file .env.docker start ganache
```

Sau đó mở lại Admin để xác nhận kết nối và hợp đồng vẫn hoạt động.

## 8. Tiến độ triển khai

- [x] Docker hóa MySQL
- [x] Docker hóa Gradio Admin
- [x] Docker hóa FastAPI
- [x] Docker hóa React Frontend
- [x] Kết nối Docker với Ganache Desktop (giai đoạn thử nghiệm ban đầu)
- [x] Kiểm tra kết nối React → FastAPI
- [x] Docker hóa Ganache và cấu hình lưu trữ blockchain
- [x] Kiểm tra hợp đồng vẫn tồn tại sau khi dừng/khởi động lại Ganache
- [x] Đồng bộ tài khoản Admin với Admin trên Smart Contract
- [x] Tối ưu Docker build bằng `.dockerignore`
- [ ] Kiểm thử toàn bộ nghiệp vụ bỏ phiếu
- [ ] Triển khai hệ thống lên Cloud
- [ ] Thiết lập CI/CD bằng GitHub Actions

## 9. Ghi chú

- MySQL sử dụng Docker Volume để lưu trữ dữ liệu.
- Ganache chạy trong Docker tại service `ganache:8545`; Windows truy cập qua `127.0.0.1:8545`.
- Nếu Ganache bị reset hoặc xóa volume, cần deploy lại Smart Contract và cập nhật `CONTRACT_ADDRESS`.
- `.dockerignore` loại trừ `.venv`, `node_modules`, file môi trường và tài liệu không cần thiết để giảm build context.
- Khi thay đổi `ElectionABI.json`, cần build lại image Python để container nhận ABI mới.
- Cấu hình hiện tại phục vụ mục đích phát triển và kiểm thử đồ án, chưa phải cấu hình production.
- Máy chạy thử nên có cấu hình từ 16GB RAM trở lên nếu không sẽ đứng máy
