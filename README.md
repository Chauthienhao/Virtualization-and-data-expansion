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

**Lưu ý:** Ganache Desktop hiện chạy trực tiếp trên Windows tại cổng 7545, chưa được Docker hóa.

## 4. Yêu cầu môi trường

- Docker Desktop
- Docker Compose
- Ganache Desktop
- Git
- Python và các thư viện trong `requirements.txt` nếu cần deploy hợp đồng từ Windows

## 5. Cấu hình môi trường

Tạo file `.env` và `.env.docker` dựa trên `.env.example`, sau đó điền các giá trị cấu hình phù hợp.

Một số biến môi trường quan trọng:

```env
RPC_URL=http://host.docker.internal:7545
CONTRACT_ADDRESS=<dia_chi_smart_contract>
DB_HOST=db
DB_PORT=3306
DB_NAME=election_admin
```

Các biến khác như mật khẩu MySQL, khóa mã hóa và thông tin tài khoản blockchain cần được cấu hình đầy đủ theo yêu cầu ứng dụng.

**Không commit `.env`, `.env.docker`, mật khẩu hoặc private key lên GitHub.**

## 6. Khởi chạy hệ thống

### Bước 1: Khởi động Ganache

Mở Ganache Desktop trên Windows, sử dụng blockchain đã triển khai hợp đồng hoặc deploy hợp đồng mới nếu cần.

Đảm bảo `CONTRACT_ADDRESS` trong `.env.docker` trỏ đến hợp đồng đang tồn tại.

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

Không sử dụng `docker compose down -v` nếu muốn giữ dữ liệu MySQL.

## 8. Tiến độ triển khai

- [x] Docker hóa MySQL
- [x] Docker hóa Gradio Admin
- [x] Docker hóa FastAPI
- [x] Docker hóa React Frontend
- [x] Kết nối Docker với Ganache Desktop
- [x] Kiểm tra kết nối React → FastAPI
- [ ] Docker hóa Ganache và cấu hình lưu trữ blockchain
- [ ] Kiểm thử toàn bộ nghiệp vụ bỏ phiếu
- [ ] Triển khai hệ thống lên Cloud
- [ ] Thiết lập CI/CD bằng GitHub Actions

## 9. Ghi chú

- MySQL sử dụng Docker Volume để lưu trữ dữ liệu.
- Ganache Desktop phải được khởi động trước khi kiểm thử các chức năng blockchain.
- Nếu Ganache reset blockchain, có thể cần deploy lại Smart Contract và cập nhật `CONTRACT_ADDRESS`.
- Cấu hình hiện tại phục vụ mục đích phát triển và kiểm thử đồ án, chưa phải cấu hình production.