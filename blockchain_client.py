"""
blockchain_client.py
======================================================================
Lớp bao bọc (wrapper) giao tiếp giữa Backend Python và Smart Contract
Election.sol thông qua Web3.py.

Mọi lời gọi đọc (read) và ghi (write/transaction) tới hợp đồng đều đi qua
class ElectionClient bên dưới, giúp adminUI.py không phải tự xử lý chi tiết
kỹ thuật RPC/ký giao dịch/đọc lỗi revert.

THIẾT KẾ KÝ GIAO DỊCH (quan trọng khi vấn đáp/báo cáo):
- Nếu có ADMIN_PRIVATE_KEY trong .env: giao dịch được KÝ CỤC BỘ (local sign)
  bằng eth_account rồi gửi qua send_raw_transaction. Cách này hoạt động trên
  mọi mạng, kể cả Sepolia Testnet hay mạng thật, vì node không cần giữ khóa.
- Nếu KHÔNG có private key: giả định đang chạy với Ganache, nơi node giữ sẵn
  khóa của các tài khoản "unlocked". Lúc này dùng fn.transact() để Ganache tự
  ký giúp. Cách này KHÔNG dùng được với Sepolia/mạng thật.
======================================================================
"""

import os
import re
import json
from pathlib import Path

from web3 import Web3
from web3.exceptions import ContractLogicError, TimeExhausted

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # python-dotenv là tiện ích, không bắt buộc: nếu chưa cài, chỉ cần đảm bảo
    # các biến môi trường đã được set sẵn theo cách khác.
    pass


class ElectionError(Exception):
    """Lỗi nghiệp vụ/kết nối đã được diễn giải sang tiếng Việt dễ hiểu,
    để lớp giao diện (Gradio) chỉ cần hiển thị str(e) cho người dùng."""
    pass


# Các thông báo require() trong Election.sol, dùng để dịch lỗi revert
# sang tiếng Việt thân thiện hơn khi hiển thị lên giao diện Admin.
_REVERT_MESSAGES = {
    "Loi: Chi Admin moi co quyen thuc hien":
        "Tài khoản đang cấu hình KHÔNG phải là Admin của hợp đồng này. "
        "Hãy kiểm tra lại ADMIN_PRIVATE_KEY / ADMIN_ACCOUNT_INDEX trong .env.",
    "Khong the them ung vien khi dang bau cu":
        "Không thể thêm ứng viên khi cuộc bầu cử đang diễn ra. "
        "Hãy Đóng phiên (End Election) trước, hoặc thêm ứng viên trước khi Bắt đầu.",
    "Chi cap quyen truoc khi bau cu dien ra":
        "Chỉ có thể cấp quyền (whitelist) cử tri TRƯỚC khi cuộc bầu cử bắt đầu.",
    "Cuoc bau cu chua dien ra hoac da dong":
        "Cuộc bầu cử hiện chưa mở hoặc đã đóng.",
    "Dia chi vi nay chua duoc cap quyen bo phieu":
        "Địa chỉ ví này chưa được Admin cấp quyền bầu cử.",
    "Cu tri nay da thuc hien bo phieu":
        "Cử tri này đã bầu rồi, không thể bầu lần hai.",
    "ID Ung vien khong hop le":
        "Mã ứng viên không hợp lệ.",
}


def _humanize_error(exc: Exception, rpc_url: str = "") -> str:
    """Chuyển exception kỹ thuật (web3/requests) thành câu tiếng Việt dễ hiểu."""
    text = str(exc)

    # 1. Lỗi do require()/revert trong Smart Contract
    for raw_msg, friendly in _REVERT_MESSAGES.items():
        if raw_msg in text:
            return friendly
    match = re.search(r"revert(?:ed)?[:\s]+([^']+)", text, re.IGNORECASE)
    if match:
        return f"Giao dịch bị từ chối bởi Smart Contract: {match.group(1).strip()}"

    # 2. Lỗi không kết nối được tới node
    if "Could not connect" in text or "Max retries exceeded" in text or "ConnectionError" in text:
        return (f"Không kết nối được tới node blockchain tại {rpc_url}. "
                f"Hãy kiểm tra Ganache (hoặc mạng khác) đã khởi động chưa.")

    # 3. Lỗi địa chỉ ví sai định dạng
    if "ENS name" in text or "checksum" in text.lower():
        return "Địa chỉ ví không hợp lệ. Vui lòng kiểm tra lại định dạng (phải bắt đầu bằng 0x, đủ 42 ký tự)."

    # 4. Không rõ nguyên nhân -> trả nguyên văn để còn debug được
    return f"Lỗi không xác định: {text[:300]}"


class ElectionClient:
    def __init__(self, rpc_url=None, contract_address=None, abi_path=None,
                 private_key=None, account_index=None):
        self.rpc_url = rpc_url or os.getenv("RPC_URL", "http://127.0.0.1:7545")
        self.contract_address = contract_address or os.getenv("CONTRACT_ADDRESS", "")
        abi_path = abi_path or os.getenv("ABI_PATH", "ElectionABI.json")
        self.private_key = private_key or os.getenv("ADMIN_PRIVATE_KEY") or None
        self.account_index = int(account_index if account_index is not None
                                  else os.getenv("ADMIN_ACCOUNT_INDEX", "0"))

        # --- Kết nối RPC ---
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url, request_kwargs={"timeout": 10}))
        if not self.w3.is_connected():
            raise ElectionError(
                f"Không kết nối được tới node blockchain tại {self.rpc_url}. "
                f"Hãy khởi động Ganache (hoặc kiểm tra lại RPC_URL trong .env)."
            )

        # --- Nạp ABI ---
        abi_file = Path(abi_path)
        if not abi_file.is_absolute():
            abi_file = Path(__file__).parent / abi_file
        if not abi_file.exists():
            raise ElectionError(f"Không tìm thấy file ABI tại: {abi_file}")
        with open(abi_file, "r", encoding="utf-8") as f:
            self.abi = json.load(f)

        # --- Địa chỉ hợp đồng ---
        if not self.contract_address or "YourDeployedContractAddressHere" in self.contract_address:
            raise ElectionError(
                "Chưa cấu hình CONTRACT_ADDRESS trong .env. "
                "Hãy deploy Election.sol (ví dụ qua Remix/Truffle trỏ vào Ganache) "
                "rồi dán địa chỉ hợp đồng vào .env."
            )
        try:
            self.contract_address = self.w3.to_checksum_address(self.contract_address)
        except ValueError:
            raise ElectionError(f"CONTRACT_ADDRESS trong .env không đúng định dạng: {self.contract_address}")

        self.contract = self.w3.eth.contract(address=self.contract_address, abi=self.abi)

        # --- Xác định tài khoản Admin sẽ dùng để ký giao dịch ---
        if self.private_key:
            if not self.private_key.startswith("0x"):
                self.private_key = "0x" + self.private_key
            self.account = self.w3.eth.account.from_key(self.private_key).address
        else:
            accounts = self.w3.eth.accounts
            if not accounts or self.account_index >= len(accounts):
                raise ElectionError(
                    "Không lấy được danh sách tài khoản từ node (thường do đang trỏ tới Sepolia/mạng "
                    "thật mà chưa cấu hình ADMIN_PRIVATE_KEY). Hãy điền ADMIN_PRIVATE_KEY trong .env."
                )
            self.account = accounts[self.account_index]

    # NỘI BỘ: gửi giao dịch ghi (transaction), kèm mô phỏng trước để bắt
    # lỗi revert sớm (không tốn gas) và dịch lỗi sang tiếng Việt.
    def _send(self, fn):
        try:
            fn.call({"from": self.account})  # mô phỏng trước, bắt lỗi require()
        except ContractLogicError as e:
            raise ElectionError(_humanize_error(e, self.rpc_url))
        except Exception as e:
            raise ElectionError(_humanize_error(e, self.rpc_url))

        try:
            if self.private_key:
                tx = fn.build_transaction({
                    "from": self.account,
                    "nonce": self.w3.eth.get_transaction_count(self.account, "pending"),
                    "chainId": self.w3.eth.chain_id,
                })
                try:
                    tx["gas"] = int(self.w3.eth.estimate_gas(tx) * 1.2)
                except Exception:
                    tx["gas"] = 3_000_000
                signed = self.w3.eth.account.sign_transaction(tx, private_key=self.private_key)
                raw = getattr(signed, "raw_transaction", None) or getattr(signed, "rawTransaction")
                tx_hash = self.w3.eth.send_raw_transaction(raw)
            else:
                tx_hash = fn.transact({"from": self.account})

            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
            if receipt.status != 1:
                raise ElectionError("Giao dịch bị mạng lưới từ chối (status=0). Có thể hết gas hoặc xung đột trạng thái.")
            return receipt
        except TimeExhausted:
            raise ElectionError("Đã gửi giao dịch nhưng chờ xác nhận quá lâu (timeout). Kiểm tra lại Ganache/mạng.")
        except ElectionError:
            raise
        except Exception as e:
            raise ElectionError(_humanize_error(e, self.rpc_url))

    # CÁC HÀM ĐỌC (READ) - không tốn gas, không cần ký
    def get_admin_address(self) -> str:
        return self.contract.functions.admin().call()

    def is_configured_account_admin(self) -> bool:
        return self.get_admin_address().lower() == self.account.lower()

    def get_election_active(self) -> bool:
        return self.contract.functions.electionActive().call()

    def get_candidates_count(self) -> int:
        return self.contract.functions.candidatesCount().call()

    def get_candidate(self, candidate_id: int) -> dict:
        cid, name, votes = self.contract.functions.candidates(candidate_id).call()
        return {"id": cid, "name": name, "votes": votes}

    def get_all_candidates(self) -> list:
        count = self.get_candidates_count()
        return [self.get_candidate(i) for i in range(1, count + 1)]

    def get_voter(self, address: str) -> dict:
        address = self._checksum(address)
        is_authorized, has_voted, voted_candidate_id = self.contract.functions.voters(address).call()
        return {
            "address": address,
            "is_authorized": is_authorized,
            "has_voted": has_voted,
            "voted_candidate_id": voted_candidate_id,
        }

    def _checksum(self, address: str) -> str:
        try:
            return self.w3.to_checksum_address(address.strip())
        except ValueError:
            raise ElectionError("Địa chỉ ví không hợp lệ. Phải bắt đầu bằng 0x và đủ 42 ký tự.")

    # CÁC HÀM GHI (WRITE) - chỉ Admin được phép gọi (onlyAdmin trong Solidity)
    def add_candidate(self, name: str) -> dict:
        name = name.strip()
        if not name:
            raise ElectionError("Tên ứng viên không được để trống.")
        self._send(self.contract.functions.addCandidate(name))
        # Hợp đồng không trả về id qua return value của transaction, nên đọc
        # lại candidatesCount ngay sau khi giao dịch được xác nhận để suy ra id.
        new_id = self.get_candidates_count()
        return {"id": new_id, "name": name}

    def authorize_voter(self, address: str) -> dict:
        address = self._checksum(address)
        self._send(self.contract.functions.authorizeVoter(address))
        return {"address": address}

    def start_election(self) -> None:
        self._send(self.contract.functions.startElection())

    def end_election(self) -> None:
        self._send(self.contract.functions.endElection())
