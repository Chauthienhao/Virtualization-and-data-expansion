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

## 4. Yêu cầu môi trường

- Docker Desktop
- Docker Compose
- Git
- Python và các thư viện trong `requirements.txt` nếu cần deploy hợp đồng từ Windows

## 5. Cấu hình môi trường

Tạo file `.env` và `.env.docker` dựa trên `.env.example`, sau đó điền các giá trị cấu hình phù hợp.

Một số biến môi trường quan trọng trong **`.env.docker`** (dùng cho container Python):

```env
RPC_URL=http://ganache:8545
CONTRACT_ADDRESS=<dia_chi_smart_contract_da_deploy>
ADMIN_ACCOUNT_INDEX=0
ADMIN_PRIVATE_KEY=
ABI_PATH=ElectionABI.json
DB_HOST=db
DB_PORT=3306
DB_NAME=election_admin
```

Trong **`.env`** (dùng khi chạy `python deploy.py` trực tiếp trên Windows), đặt:

```env
RPC_URL=http://127.0.0.1:8545
ADMIN_ACCOUNT_INDEX=0
ADMIN_PRIVATE_KEY=
CONTRACT_ADDRESS=<dia_chi_smart_contract_da_deploy>
```

Hai file cần dùng cùng địa chỉ hợp đồng sau khi deploy. Các biến khác giữ theo `.env.example` và cấu hình dự án. `ADMIN_PRIVATE_KEY` để trống khi dùng tài khoản Ganache đã mở khóa theo chỉ số `ADMIN_ACCOUNT_INDEX`.

Các biến khác như mật khẩu MySQL, khóa mã hóa và thông tin tài khoản blockchain cần được cấu hình đầy đủ theo yêu cầu ứng dụng.

**Không commit `.env`, `.env.docker`, mật khẩu hoặc private key lên GitHub.**

## 6. Khởi chạy hệ thống

### Bước 1: Khởi động Ganache Docker và deploy hợp đồng lần đầu

Chạy Ganache Docker trước:

```bash
docker compose --env-file .env.docker up -d ganache
```

Với lần cài mới, đảm bảo `.env` trỏ tới `http://127.0.0.1:8545` và chạy trên Windows (Python đã cài các thư viện trong `requirements.txt`):

```bash
python deploy.py
```

Lệnh deploy biên dịch `Election.sol`, cập nhật `ElectionABI.json` và in ra địa chỉ hợp đồng mới. Chép địa chỉ này vào `CONTRACT_ADDRESS` trong **cả** `.env` và `.env.docker`.

**Kiểm tra quyền Admin:** tài khoản dùng deploy phải trùng với tài khoản Admin của ứng dụng. Nếu dùng `ADMIN_ACCOUNT_INDEX=0`, không cấu hình `ADMIN_PRIVATE_KEY` khác. Nếu Ganache báo `insufficient funds for gas * price + value`, kiểm tra số dư ETH thử nghiệm của tài khoản; không chạy deploy lặp lại khi chưa xử lý lỗi.

**Chỉ cần deploy lại** khi hợp đồng chưa tồn tại trên chain, chain bị reset hoặc cần triển khai phiên bản Solidity mới. Khởi động lại Docker thông thường không yêu cầu deploy lại.

### Bước 2: Build và chạy Docker

Mở terminal tại thư mục dự án:

```bash
docker compose --env-file .env.docker up -d --build
```

### Bước 3: Kiểm tra container

```bash
docker compose --env-file .env.docker ps
```

### Bước 4: Truy cập ứng dụng

- React Frontend: http://localhost:3000
- FastAPI Swagger: http://localhost:8001/docs
- Gradio Admin: http://localhost:7861

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