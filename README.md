# Hệ Thống Bầu Cử Điện Tử (Blockchain E-Voting)

Đồ án công nghệ: hệ thống bầu cử điện tử dùng Smart Contract (Solidity) làm
tầng lưu trữ phiếu bầu bất biến, MySQL làm tầng quản lý cử tri/phiên off-chain,
Admin portal dựng bằng Gradio (Python), và giao diện cử tri dựng bằng ReactJS.

> ⚠️ Nhánh này là bản đang chạy được của **hao**, nhưng **chưa hoàn chỉnh** —
> xem phần [Việc còn thiếu / đang làm](#việc-còn-thiếu--đang-làm) ở cuối.

---

## Kiến trúc tổng quan

```
Ganache (blockchain giả lập, local)
        │
        ▼
Election.sol  ──deploy.py──>  đã deploy lên Ganache
        │
        ▼
blockchain_client.py (Web3.py) ── dùng chung bởi ──┬── adminUI.py   (Gradio, Admin)
                                                     └── voter_api.py (FastAPI, cử tri)
        │
        ▼
MySQL (storage.py) — danh sách cử tri, phiên đăng nhập, ví custodial đã mã hóa
        │
        ▼
Frontend ReactJS (Vite) ── gọi voter_api.py qua api.js ── người bầu cử dùng
```

Cử tri **không dùng MetaMask**: hệ thống tự sinh và giữ hộ ví (custodial
wallet) cho mỗi CCCD, ẩn hoàn toàn với người dùng — cử tri chỉ cần nhập CCCD
và mã xác thực do hệ thống cấp.

---

## Yêu cầu hệ thống

- [Ganache](https://trufflesuite.com/ganache/) (bản desktop, chạy local)
- Python 3.11+
- Node.js (khuyến nghị bản LTS mới nhất) + npm
- MySQL Server (local)
- Visual Studio Code (hoặc IDE bất kỳ)

---

## Cấu trúc thư mục chính

```
Virtualization-and-data-expansion/
├── Election.sol              # Smart contract
├── deploy.py                 # Script compile + deploy contract (không cần Remix)
├── ElectionABI.json           # ABI được deploy.py tự sinh ra
├── blockchain_client.py       # Lớp Web3.py dùng chung (Admin + cử tri)
├── storage.py                 # Lưu trữ MySQL (cử tri, phiên, bầu cử)
├── voter_accounts.py          # Sinh/mã hóa ví custodial, mã xác thực, CCCD hash
├── adminUI.py                 # Giao diện Admin (Gradio)
├── voter_api.py                # API cho cử tri (FastAPI)
├── requirements.txt
├── .env.example
├── .gitignore
└── src/                        # Frontend ReactJS (Vite)
    ├── api.js
    ├── App.jsx
    └── components/...
```

---

## Hướng dẫn chạy

### 1. Cài Ganache

Tải và mở Ganache trên máy → chọn **Quick Start** để tạo một workspace mới
(chain local, 10 tài khoản sẵn ETH để test). Ghi lại **RPC Server** (thường
là `http://127.0.0.1:7545`) — cần dùng ở bước 3.

> Lưu ý: mỗi lần **Quick Start** lại hoặc restart Ganache, danh sách 10 tài
> khoản và mọi contract đã deploy trước đó sẽ **mất hết** — phải deploy lại
> (bước 4) mỗi khi làm việc này.

### 2. Cài đặt thư viện Python

Mở project bằng VS Code → mở Terminal → chạy:

```bash
pip install -r requirements.txt
```

### 3. Tạo file `.env`

Copy `.env.example` thành `.env` (cùng thư mục gốc project):

```bash
copy .env.example .env      # Windows
# hoặc
cp .env.example .env        # macOS / Linux
```

Mở `.env` và điền các giá trị của máy mình, ví dụ:

```env
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
DB_PASSWORD=123456          # đổi theo mật khẩu MySQL thật của bạn
DB_NAME=election_admin

RPC_URL=http://127.0.0.1:7545
CONTRACT_ADDRESS=            # sẽ điền ở bước 4, sau khi deploy

VOTER_KEY_ENCRYPTION_KEY=    # xem lệnh sinh khóa ở bước 3b
CCCD_HASH_PEPPER=mot-chuoi-bi-mat-tuy-chon
VOTER_FUNDING_AMOUNT_ETH=0.01

VITE_API_BASE_URL=http://127.0.0.1:8001
```

**3b. Sinh `VOTER_KEY_ENCRYPTION_KEY`** (khóa mã hóa private key cử tri —
bắt buộc phải có, nếu không sẽ lỗi khi cử tri đăng nhập lần đầu):

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Copy kết quả in ra, dán vào `VOTER_KEY_ENCRYPTION_KEY` trong `.env`.
⚠️ Không đổi lại khóa này sau khi đã có cử tri dùng hệ thống — đổi khóa sẽ
khiến mọi private key đã mã hóa trước đó không giải mã được nữa.

### 4. Deploy Smart Contract

Trong VS Code, mở file `deploy.py` → **Run** (hoặc `python deploy.py` trong
terminal). Script sẽ tự compile `Election.sol` và deploy lên Ganache, rồi in
ra địa chỉ contract, ví dụ:

```
CONTRACT_ADDRESS=0xABCDEF1234567890...
```

Copy địa chỉ này, dán vào `CONTRACT_ADDRESS` trong `.env`.

### 5. Tạo database MySQL

Đảm bảo MySQL Server đang chạy và `.env` đã khai đúng `DB_PASSWORD`. Database
và các bảng cần thiết (`elections`, `voters`, ...) sẽ được tự tạo khi chạy
`adminUI.py` lần đầu (gọi `storage.init_db()`), không cần tạo tay bằng
`CREATE DATABASE`.

### 6. Chạy Backend + Frontend (3 terminal song song)

**Terminal 1 — API cho cử tri:**
```bash
uvicorn voter_api:app --reload --port 8001
```

**Terminal 2 — Giao diện Admin:**
```bash
python adminUI.py
```

**Terminal 3 — Frontend ReactJS:**
```bash
npm install
npm run dev
```

Sau khi cả 3 chạy xong, Admin portal thường mở ở `http://127.0.0.1:7860`,
trang cử tri ở địa chỉ mà `npm run dev` in ra (thường `http://localhost:5173`).

---

## `.gitignore`

Nếu project chưa có file `.gitignore`, tạo mới ở thư mục gốc với nội dung
sau (tránh push nhầm thông tin nhạy cảm hoặc file build/cache lên nhánh):

```gitignore
.env
__pycache__/
node_modules/
dist/
```

---

## Lưu ý khi gặp lỗi

- **`ModuleNotFoundError: No module named 'solcx'`** khi chạy `deploy.py` →
  chưa chạy `pip install -r requirements.txt`, hoặc thiếu `py-solc-x` trong
  `requirements.txt` → cài thêm: `pip install py-solc-x`.
- **Sửa `Election.sol` xong nhưng chạy vẫn lỗi như cũ** → nhớ chạy lại
  `python deploy.py` để lấy `CONTRACT_ADDRESS` mới, dán lại vào `.env`, rồi
  **tắt hẳn và chạy lại** `voter_api.py`/`adminUI.py` (không chỉ để
  `--reload` tự load lại — `--reload` chỉ theo dõi file `.py`, không theo
  dõi `.env`, nên đổi `.env` mà không restart tay thì process vẫn giữ giá
  trị cũ).
- **`BadFunctionCallOutput` / `InsufficientDataBytes`** khi gọi contract →
  `.env` đang trỏ vào một địa chỉ không có contract thật trên Ganache hiện
  tại (do Ganache đã Quick Start lại, hoặc `.env` chưa cập nhật đúng).
- **Cử tri báo "Phiên đăng nhập trước đó vẫn đang mở"** dù họ chưa đăng
  xuất chủ động (do tắt/crash trình duyệt giữa chừng) → vào tab **"Danh
  Sách Cử Tri"** trong Admin portal, dùng mục **"Mở khóa phiên bị kẹt"** với
  CCCD tương ứng.

---

## Việc còn thiếu / đang làm

- [ ] Hoàn thiện giao diện/luồng còn thiếu ở phía Admin hoặc cử tri (bổ sung
      dần theo tiến độ đồ án).
- [ ] Viết sẵn script/migration để clear dữ liệu `voters` khi redeploy contract
      mới (tránh lẫn ví đã cấp quyền trên contract cũ).
- [ ] Hướng dẫn deploy lên testnet thật (ví dụ Sepolia) nếu đồ án yêu cầu.
