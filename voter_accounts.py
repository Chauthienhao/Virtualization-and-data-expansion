"""
voter_accounts.py
======================================================================
Quản lý "ví do hệ thống giữ hộ" (custodial wallet) cho cử tri — thay cho
việc cử tri tự có MetaMask. Module này là nơi DUY NHẤT xử lý:

1. Sinh ví mới hoàn toàn cho mỗi cử tri (KHÔNG dùng danh sách tài khoản có
   sẵn của Ganache, vì danh sách đó đổi khác mỗi lần Ganache restart và chỉ
   có ~10 cái — không đủ, không bền cho một danh sách cử tri thật).
2. Bơm một ít ETH từ tài khoản Admin sang ví cử tri để họ đủ gas bầu 1 lần.
3. Mã hóa private key trước khi lưu xuống MySQL (bằng Fernet, khóa bí mật
   nằm trong biến môi trường VOTER_KEY_ENCRYPTION_KEY, KHÔNG BAO GIỜ nằm
   trong DB — nếu chỉ có DB mà không có biến môi trường này thì các khóa
   đã mã hóa vô dụng, không giải mã được).
4. Sinh và kiểm tra "mã truy cập" (access code) cho luồng đăng nhập 2 bước
   CCCD -> mã.

LƯU Ý BẢO MẬT (ghi rõ để báo cáo/vấn đáp): việc Backend giữ private key hộ
cử tri là một đánh đổi UX-dễ-dùng lấy mức độ phi tập trung thấp hơn — tính
TOÀN VẸN (không double-vote, không sửa phiếu) vẫn do Smart Contract đảm bảo
độc lập với ai giữ khóa, nhưng tính BÍ MẬT (ai bầu cho ai) giờ phụ thuộc
vào việc bảo vệ VOTER_KEY_ENCRYPTION_KEY và quyền truy cập MySQL. Vì vậy
private key được XÓA khỏi DB ngay sau khi dùng xong (xem storage.wipe_private_key).
======================================================================
"""

import os
import re
import secrets
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from eth_account import Account

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class VoterAccountError(Exception):
    """Lỗi nghiệp vụ đã diễn giải sang tiếng Việt, để lớp giao diện/API chỉ
    cần hiển thị str(e)."""
    pass


# ----------------------------------------------------------------------
# Mã hóa / giải mã private key (Fernet — mã hóa đối xứng, an toàn, đơn giản)
# ----------------------------------------------------------------------

def _get_fernet() -> Fernet:
    key = os.getenv("VOTER_KEY_ENCRYPTION_KEY", "")
    if not key:
        raise VoterAccountError(
            "Chưa cấu hình VOTER_KEY_ENCRYPTION_KEY trong .env. "
            "Chạy `python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"` "
            "để tạo 1 khóa mới, dán vào .env, rồi KHÔNG BAO GIỜ đổi lại (đổi khóa này sẽ khiến mọi "
            "private key đã mã hóa trước đó không giải mã được nữa)."
        )
    try:
        return Fernet(key.encode())
    except Exception:
        raise VoterAccountError("VOTER_KEY_ENCRYPTION_KEY trong .env không hợp lệ (phải là khóa Fernet 32 byte, dạng base64).")


def encrypt_private_key(private_key_hex: str) -> str:
    return _get_fernet().encrypt(private_key_hex.encode()).decode()


def decrypt_private_key(encrypted: str) -> str:
    try:
        return _get_fernet().decrypt(encrypted.encode()).decode()
    except InvalidToken:
        raise VoterAccountError("Không giải mã được private key (sai VOTER_KEY_ENCRYPTION_KEY, hoặc dữ liệu đã hỏng).")


# ----------------------------------------------------------------------
# CCCD: không lưu dạng thô, chỉ lưu hash để tra cứu (giống cách lưu mật khẩu)
# ----------------------------------------------------------------------

def _pepper() -> str:
    # "Pepper" là một chuỗi bí mật server-side cộng thêm vào trước khi băm,
    # để nếu ai đó có bảng cccd_hash cũng không dò ngược được bằng cách
    # băm thử các dãy CCCD phổ biến (brute-force / rainbow table).
    return os.getenv("CCCD_HASH_PEPPER", "")


def hash_cccd(cccd: str) -> str:
    cccd_normalized = re.sub(r"\s+", "", cccd).strip()
    return hashlib.sha256((cccd_normalized + _pepper()).encode()).hexdigest()


# ----------------------------------------------------------------------
# Mã truy cập (access code): số 6 chữ số, chỉ lưu hash, có hạn dùng
# ----------------------------------------------------------------------

CODE_LENGTH = 6


def generate_access_code() -> str:
    return "".join(secrets.choice("0123456789") for _ in range(CODE_LENGTH))


def hash_access_code(code: str) -> str:
    return hashlib.sha256(code.strip().encode()).hexdigest()


def generate_session_token() -> str:
    return secrets.token_hex(32)


# ----------------------------------------------------------------------
# Sinh ví mới + bơm ETH (cần một ElectionClient đã kết nối, để lấy w3 và
# tài khoản Admin làm nguồn vốn)
# ----------------------------------------------------------------------

def create_new_wallet() -> dict:
    """Sinh một ví Ethereum HOÀN TOÀN MỚI, độc lập với danh sách tài khoản
    của Ganache. Trả về {"address":..., "private_key": "0x..."}."""
    acct = Account.create()
    return {"address": acct.address, "private_key": acct.key.hex()}


def fund_wallet(client, address: str, amount_eth: float = 0.01):
    """Chuyển một ít ETH từ tài khoản Admin (client.account) sang ví cử tri
    mới sinh, để họ đủ gas bầu 1 lần. `client` là một ElectionClient đã kết
    nối (dùng chung với Admin UI)."""
    try:
        tx = {
            "from": client.account,
            "to": client.w3.to_checksum_address(address),
            "value": client.w3.to_wei(amount_eth, "ether"),
        }
        if client.private_key:
            tx["nonce"] = client.w3.eth.get_transaction_count(client.account, "pending")
            tx["chainId"] = client.w3.eth.chain_id
            tx["gas"] = 21000
            signed = client.w3.eth.account.sign_transaction(tx, private_key=client.private_key)
            raw = getattr(signed, "raw_transaction", None) or getattr(signed, "rawTransaction")
            tx_hash = client.w3.eth.send_raw_transaction(raw)
        else:
            tx_hash = client.w3.eth.send_transaction(tx)
        receipt = client.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
        if receipt.status != 1:
            raise VoterAccountError(f"Giao dịch bơm ETH cho {address} thất bại.")
    except VoterAccountError:
        raise
    except Exception as e:
        raise VoterAccountError(f"Lỗi khi bơm ETH cho ví {address}: {e}")


def provision_voter(client, cccd: str, full_name: str, amount_eth: float = 0.01) -> dict:
    """Quy trình đầy đủ cho MỘT cử tri mới, gọi khi Admin nhập danh sách cử
    tri: sinh ví -> bơm ETH -> cấp quyền trên chain (authorizeVoter) -> mã
    hóa private key -> trả về dữ liệu để lưu xuống MySQL (storage.create_voter).
    Không tự lưu DB ở đây, để lớp gọi (Admin UI) kiểm soát transaction/thứ tự."""
    wallet = create_new_wallet()
    fund_wallet(client, wallet["address"], amount_eth)
    client.authorize_voter(wallet["address"])  # dùng lại hàm đã có sẵn trong blockchain_client.py
    encrypted_key = encrypt_private_key(wallet["private_key"])
    return {
        "cccd_hash": hash_cccd(cccd),
        "full_name": full_name,
        "wallet_address": wallet["address"],
        "encrypted_private_key": encrypted_key,
    }
