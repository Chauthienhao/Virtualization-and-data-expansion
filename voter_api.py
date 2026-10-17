"""
voter_api.py
======================================================================
API server riêng cho CỬ TRI (khác hẳn adminUI.py — Admin dùng Gradio, cử
tri dùng app React gọi vào đây). Lý do cần một server riêng: cử tri không
có MetaMask, nên mọi giao dịch ký hộ (vote) PHẢI xảy ra ở backend bằng ví
custodial lưu trong MySQL (xem voter_accounts.py), frontend chỉ gọi API
bằng fetch(), không tự ký gì cả.

CHẠY:
    pip install fastapi "uvicorn[standard]"
    uvicorn voter_api:app --reload --port 8001

LUỒNG ĐĂNG NHẬP (2 bước, xem thêm ghi chú trong storage.py/voter_accounts.py):
    POST /login        {cccd}            -> {code}             (hiện mã ngay trên màn hình)
    POST /verify-code   {cccd, code}      -> {session_token}
    GET  /me?session_token=...           -> trạng thái + danh sách ứng viên
    POST /vote          {session_token, candidate_id} -> ký & gửi giao dịch vote()
    GET  /my-vote?session_token=...      -> CHỈ lựa chọn của chính cử tri này
    POST /logout        {session_token}  -> khóa vĩnh viễn phiên

LƯU Ý: dữ liệu blockchain về bản chất là CÔNG KHAI — ai có RPC_URL + địa chỉ
hợp đồng + ABI đều tự đọc được số phiếu trực tiếp từ chain, kể cả không qua
API này. Việc API không trả tổng kết quả cho cử tri chỉ ngăn được hiển thị
NGAY TRONG GIAO DIỆN cử tri, không che giấu được dữ liệu ở tầng blockchain —
đây là giới hạn cố hữu của một sổ cái công khai, không phải lỗi thiết kế có
thể vá được ở tầng ứng dụng.
======================================================================
"""

from datetime import datetime, timedelta

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from blockchain_client import ElectionClient, ElectionError
import storage
from storage import StorageError
import voter_accounts
from voter_accounts import VoterAccountError

CODE_EXPIRE_MINUTES = 10

app = FastAPI(title="Voter API — Hệ thống Bầu cử Điện tử")

# Cho phép frontend React (chạy cổng khác, ví dụ 5173 của Vite) gọi vào.
# Môi trường thật nên giới hạn allow_origins đúng domain frontend thay vì "*".
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==============================================================================
# KẾT NỐI BLOCKCHAIN + MYSQL lúc khởi động server (không chặn server mở nếu
# lỗi — các endpoint sẽ tự báo lỗi rõ ràng cho từng request thay vì sập hẳn).
# ==============================================================================
client = None
client_error = None


def _init_client():
    global client, client_error
    try:
        client = ElectionClient()
        client_error = None
    except ElectionError as e:
        client = None
        client_error = str(e)


_init_client()

try:
    storage.init_db()
except StorageError as e:
    print(f"[voter_api] CẢNH BÁO: chưa kết nối được MySQL lúc khởi động: {e}")


def _require_client():
    # Client chỉ tạo một lần lúc khởi động, nên nếu sau đó Ganache bị restart
    # (chain reset) hoặc deploy lại sang địa chỉ mới thì client sẽ trỏ vào
    # địa chỉ rỗng. Kiểm tra mỗi request và tự tạo lại (đọc lại .env).
    if client is None or not client.is_contract_deployed():
        _init_client()
    if client is None:
        raise HTTPException(status_code=503, detail=f"Hệ thống chưa kết nối được blockchain: {client_error}")


# ==============================================================================
# SCHEMA REQUEST (Pydantic)
# ==============================================================================

class LoginRequest(BaseModel):
    cccd: str


class VerifyCodeRequest(BaseModel):
    cccd: str
    code: str


class VoteRequest(BaseModel):
    session_token: str
    candidate_id: int


class SessionRequest(BaseModel):
    session_token: str


# ==============================================================================
# HELPER NỘI BỘ
# ==============================================================================

def _get_session_voter(session_token: str) -> dict:
    try:
        voter = storage.get_voter_by_session(session_token)
    except StorageError as e:
        raise HTTPException(status_code=500, detail=str(e))
    if voter is None:
        raise HTTPException(status_code=401, detail="Phiên không hợp lệ hoặc đã bị khóa. Vui lòng đăng nhập lại.")
    return voter


# ==============================================================================
# ENDPOINTS
# ==============================================================================

@app.post("/login")
def login(req: LoginRequest):
    """Bước 1: nhận CCCD. Nếu hợp lệ, sinh mã truy cập (và sinh ví custodial
    NẾU đây là lần đầu CCCD này đăng nhập thành công)."""
    _require_client()
    cccd_hash = voter_accounts.hash_cccd(req.cccd)

    try:
        voter = storage.get_voter_by_cccd_hash(cccd_hash)
    except StorageError as e:
        raise HTTPException(status_code=500, detail=str(e))

    if voter is None:
        raise HTTPException(status_code=404, detail="CCCD không có trong danh sách cử tri đủ điều kiện.")
    if voter["status"] == "da_khoa":
        raise HTTPException(status_code=403, detail="CCCD này đã sử dụng quyền bầu cử, không thể đăng nhập lại.")
    if voter["status"] == "dang_trong_phien":
        raise HTTPException(
            status_code=409,
            detail="Phiên đăng nhập trước đó của CCCD này vẫn đang mở. Hãy hoàn tất hoặc đăng xuất trước khi thử lại.",
        )

    if voter["wallet_address"] is None:
        # Lần đầu CCCD này đăng nhập hợp lệ -> sinh ví + bơm ETH + cấp quyền
        # trên chain NGAY BÂY GIỜ (chỉ xảy ra đúng 1 lần cho mỗi CCCD).
        try:
            provisioned = voter_accounts.provision_voter(client, req.cccd, voter["full_name"])
            storage.attach_wallet(cccd_hash, provisioned["wallet_address"], provisioned["encrypted_private_key"])
        except (VoterAccountError, ElectionError, StorageError) as e:
            raise HTTPException(status_code=500, detail=f"Lỗi khi khởi tạo tài khoản bầu cử: {e}")

    code = voter_accounts.generate_access_code()
    code_hash = voter_accounts.hash_access_code(code)
    try:
        storage.set_access_code(cccd_hash, code_hash)
    except StorageError as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"code": code, "expires_in_minutes": CODE_EXPIRE_MINUTES}


@app.post("/verify-code")
def verify_code(req: VerifyCodeRequest):
    """Bước 2: xác thực mã, mở phiên làm việc (session_token)."""
    cccd_hash = voter_accounts.hash_cccd(req.cccd)
    try:
        voter = storage.get_voter_by_cccd_hash(cccd_hash)
    except StorageError as e:
        raise HTTPException(status_code=500, detail=str(e))

    if voter is None:
        raise HTTPException(status_code=404, detail="CCCD không hợp lệ.")
    if voter["status"] == "da_khoa":
        raise HTTPException(status_code=403, detail="CCCD này đã sử dụng quyền bầu cử rồi.")
    if voter["status"] != "da_cap_ma":
        raise HTTPException(
            status_code=400,
            detail="Chưa có mã nào đang chờ xác thực cho CCCD này. Vui lòng nhập lại CCCD để nhận mã mới.",
        )
    if voter["code_generated_at"] and datetime.now() - voter["code_generated_at"] > timedelta(minutes=CODE_EXPIRE_MINUTES):
        raise HTTPException(status_code=410, detail="Mã đã hết hạn. Vui lòng nhập lại CCCD để nhận mã mới.")
    if voter_accounts.hash_access_code(req.code) != voter["access_code_hash"]:
        raise HTTPException(status_code=401, detail="Mã truy cập không đúng.")

    session_token = voter_accounts.generate_session_token()
    try:
        storage.start_session(cccd_hash, session_token)
    except StorageError as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"session_token": session_token}


@app.get("/me")
def me(session_token: str):
    """Trạng thái cử tri + danh sách ứng viên (CHỈ id/name, KHÔNG kèm số
    phiếu — xem lưu ý ở đầu file về việc không công bố kết quả cho cử tri)."""
    _require_client()
    voter = _get_session_voter(session_token)
    try:
        candidates = client.get_all_candidates()
        election_active = client.get_election_active()
        voter_chain = client.get_voter(voter["wallet_address"])
    except ElectionError as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "fullName": voter["full_name"],
        "electionActive": election_active,
        "isAuthorized": voter_chain["is_authorized"],
        "hasVoted": voter_chain["has_voted"],
        "candidates": [{"id": c["id"], "name": c["name"]} for c in candidates],
    }


@app.post("/vote")
def vote(req: VoteRequest):
    """Ký và gửi giao dịch vote() bằng ví custodial của cử tri đang trong
    phiên này. Sau khi thành công, XÓA NGAY private key khỏi MySQL."""
    _require_client()
    voter = _get_session_voter(req.session_token)

    if voter["encrypted_private_key"] is None:
        raise HTTPException(status_code=409, detail="Bạn đã bỏ phiếu rồi, không thể bầu lần hai.")

    try:
        private_key = voter_accounts.decrypt_private_key(voter["encrypted_private_key"])
    except VoterAccountError as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Dùng một ElectionClient RIÊNG, ký bằng khóa của cử tri (khác với
    # `client` dùng chung ở trên vốn ký bằng khóa Admin), để giao dịch vote()
    # đứng tên đúng cử tri, không phải đứng tên Admin.
    try:
        voter_client = ElectionClient(private_key=private_key)
        voter_client.vote(req.candidate_id)
    except ElectionError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi gửi giao dịch bầu cử: {e}")

    try:
        storage.wipe_private_key(req.session_token)
    except StorageError:
        pass  # không chặn phản hồi thành công chỉ vì lỗi dọn dẹp phụ, giao dịch đã lên chain rồi

    return {"success": True}


@app.get("/my-vote")
def my_vote(session_token: str):
    """CHỈ trả về lựa chọn của CHÍNH cử tri đang gọi — không bao giờ trả
    tổng số phiếu/kết quả chung (kết quả tổng chỉ công bố ở Admin UI)."""
    _require_client()
    voter = _get_session_voter(session_token)
    try:
        voter_chain = client.get_voter(voter["wallet_address"])
    except ElectionError as e:
        raise HTTPException(status_code=500, detail=str(e))

    if not voter_chain["has_voted"]:
        return {"hasVoted": False}

    try:
        candidate = client.get_candidate(voter_chain["voted_candidate_id"])
    except ElectionError as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"hasVoted": True, "votedCandidate": {"id": candidate["id"], "name": candidate["name"]}}


@app.post("/logout")
def logout(req: SessionRequest):
    """Khóa VĨNH VIỄN phiên này — CCCD + mã cũ không dùng lại được nữa, dù
    đã bầu hay chưa (đúng yêu cầu: phiên chỉ dùng được 1 lần)."""
    try:
        storage.lock_session(req.session_token)
    except StorageError as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"success": True}
