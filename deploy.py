"""
deploy.py
======================================================================
Triển khai (deploy) Election.sol lên Ganache bằng dòng lệnh — KHÔNG cần
Remix hay trình duyệt. Dùng cho đồ án này vì chỉ cần deploy MỘT lần duy
nhất (một cuộc bầu cử tại một thời điểm).

CÁCH DÙNG:
    pip install py-solc-x          (chỉ cần 1 lần)
    python deploy.py

Script sẽ tự:
1. Tải về đúng phiên bản trình biên dịch Solidity (solc) ghi trong
   Election.sol, nếu máy chưa có (chỉ tải 1 lần đầu, cần mạng).
2. Biên dịch Election.sol -> lấy ABI + bytecode, GHI ĐÈ ElectionABI.json
   để luôn khớp với mã nguồn .sol mới nhất.
3. Deploy lên mạng chỉ định trong .env (RPC_URL), ký bằng tài khoản cấu
   hình trong .env (ADMIN_ACCOUNT_INDEX hoặc ADMIN_PRIVATE_KEY) — ĐÚNG
   tài khoản này sẽ trở thành Admin của hợp đồng (constructor gán
   admin = msg.sender), nên không còn rủi ro deploy nhầm tài khoản như
   khi chọn thủ công trong Remix.
4. In ra địa chỉ hợp đồng vừa deploy để copy dán vào CONTRACT_ADDRESS
   trong file .env.

LƯU Ý: nếu máy không có mạng để tải solc, bạn vẫn có thể biên dịch bằng
Remix một lần rồi dán ABI vào ElectionABI.json như cũ — deploy.py chỉ là
một lựa chọn thay thế, không bắt buộc.
======================================================================
"""

import json
import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

HERE = Path(__file__).parent
SOL_FILE = HERE / "Election.sol"
ABI_FILE = HERE / "ElectionABI.json"
SOLC_VERSION = "0.8.19"  # khớp với "pragma solidity ^0.8.19" trong Election.sol


def compile_contract():
    try:
        import solcx
    except ImportError:
        sys.exit("❌ Chưa cài py-solc-x. Chạy: pip install py-solc-x")

    print(f"[1/4] Kiểm tra/cài trình biên dịch Solidity {SOLC_VERSION}...")
    installed = [str(v) for v in solcx.get_installed_solc_versions()]
    if SOLC_VERSION not in installed:
        print("      Chưa có sẵn, đang tải về (cần mạng, chỉ 1 lần)...")
        solcx.install_solc(SOLC_VERSION)
    solcx.set_solc_version(SOLC_VERSION)

    print("[2/4] Biên dịch Election.sol...")
    if not SOL_FILE.exists():
        sys.exit(f"❌ Không tìm thấy {SOL_FILE}")
    source = SOL_FILE.read_text(encoding="utf-8")
    compiled = solcx.compile_source(source, output_values=["abi", "bin"], solc_version=SOLC_VERSION)
    _, contract_interface = next(iter(compiled.items()))
    abi = contract_interface["abi"]
    bytecode = contract_interface["bin"]

    ABI_FILE.write_text(json.dumps(abi, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"      Đã cập nhật {ABI_FILE.name} theo đúng mã nguồn vừa biên dịch.")
    return abi, bytecode


def deploy(abi, bytecode):
    from web3 import Web3

    print("[3/4] Kết nối blockchain và gửi giao dịch deploy...")
    rpc_url = os.getenv("RPC_URL", "http://127.0.0.1:7545")
    w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": 10}))
    if not w3.is_connected():
        sys.exit(f"❌ Không kết nối được tới {rpc_url}. Hãy khởi động Ganache trước rồi chạy lại.")

    if not bytecode.startswith("0x"):
        bytecode = "0x" + bytecode
    Election = w3.eth.contract(abi=abi, bytecode=bytecode)

    private_key = os.getenv("ADMIN_PRIVATE_KEY") or None
    account_index = int(os.getenv("ADMIN_ACCOUNT_INDEX", "0"))

    if private_key:
        if not private_key.startswith("0x"):
            private_key = "0x" + private_key
        account = w3.eth.account.from_key(private_key).address
        tx = Election.constructor().build_transaction({
            "from": account,
            "nonce": w3.eth.get_transaction_count(account, "pending"),
            "chainId": w3.eth.chain_id,
            "gas": 4_000_000,
        })
        signed = w3.eth.account.sign_transaction(tx, private_key=private_key)
        raw = getattr(signed, "raw_transaction", None) or getattr(signed, "rawTransaction")
        tx_hash = w3.eth.send_raw_transaction(raw)
    else:
        accounts = w3.eth.accounts
        if not accounts or account_index >= len(accounts):
            sys.exit("❌ Không lấy được tài khoản từ node. Nếu đang deploy lên Sepolia/mạng thật, "
                      "hãy điền ADMIN_PRIVATE_KEY trong .env.")
        account = accounts[account_index]
        tx_hash = Election.constructor().transact({"from": account})

    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
    if receipt.status != 1 or not receipt.contractAddress:
        sys.exit("❌ Giao dịch deploy thất bại.")

    print("[4/4] Hoàn tất!")
    print(f"      Deploy bằng tài khoản : {account}")
    print(f"      Địa chỉ hợp đồng mới  : {receipt.contractAddress}")
    print()
    print(f"      Dán dòng này vào file .env:")
    print(f"      CONTRACT_ADDRESS={receipt.contractAddress}")


if __name__ == "__main__":
    abi, bytecode = compile_contract()
    deploy(abi, bytecode)
