import json
from pathlib import Path
import gradio as gr
import pandas as pd

from blockchain_client import ElectionClient, ElectionError
import storage
from storage import StorageError

# ==============================================================================
# FILE LƯU DANH SÁCH CỬ TRI GỬI YÊU CẦU XÁC THỰC (KHÔNG CẦN SỬA DATABASE MYSQL)
# ==============================================================================
VOTER_REQUESTS_FILE = Path(__file__).parent / "voter_requests.json"
VOTER_REQ_COLS = [
    "STT",
    "Họ Và Tên",
    "Email",
    "Số CCCD / MSSV",
    "Địa Chỉ Ví",
    "Thời Gian Gửi",
    "Trạng Thái",
]


def load_voter_requests() -> list:
    if not VOTER_REQUESTS_FILE.exists():
        return []
    try:
        with open(VOTER_REQUESTS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception:
        return []


def save_voter_requests(requests_list: list) -> None:
    with open(VOTER_REQUESTS_FILE, "w", encoding="utf-8") as f:
        json.dump(requests_list, f, ensure_ascii=False, indent=2)


# ==============================================================================
# KẾT NỐI BLOCKCHAIN (khởi tạo lúc mở app; có thể "Kết nối lại" từ Dashboard)
# ==============================================================================
client = None
client_error = None


def init_client():
    """Thử kết nối tới node blockchain + Smart Contract. Không raise ra ngoài,
    để app Gradio vẫn khởi động được ngay cả khi Ganache chưa bật."""
    global client, client_error
    try:
        client = ElectionClient()
        client_error = None
    except ElectionError as e:
        client = None
        client_error = str(e)
    except Exception as e:
        client = None
        client_error = f"Lỗi không xác định khi khởi tạo kết nối: {e}"


init_client()

# ==============================================================================
# KẾT NỐI MYSQL (lưu metadata off-chain của phiên & ứng viên)
# ==============================================================================
storage_error = None


def init_storage():
    global storage_error
    try:
        storage.init_db()
        storage_error = None
    except StorageError as e:
        storage_error = str(e)
    except Exception as e:
        storage_error = f"Lỗi không xác định khi khởi tạo MySQL: {e}"


init_storage()

draft_candidates = []

ELECTION_COLS = ["Mã Phiên", "Tên Cuộc Bầu Cử", "Số Ứng Viên", "Thời Gian Bắt Đầu", "Thời Gian Kết Thúc", "Trạng Thái"]
CANDIDATE_COLS = ["STT", "Họ Và Tên", "Mã Định Danh / SBD", "Đơn Vị / Chi Đoàn"]
CANDIDATE_RESULT_COLS = ["ID On-chain", "Họ Và Tên", "Mã Định Danh / SBD", "Đơn Vị / Chi Đoàn", "Số Phiếu Bầu"]


def _require_client():
    if client is None:
        return (f"❌ Chưa kết nối được blockchain: {client_error}\n"
                f"➡️ Hãy kiểm tra Ganache đã chạy, cấu hình trong file .env, "
                f"rồi bấm 'Kết nối lại' ở tab Dashboard.")
    return None


def _require_storage():
    if storage_error is not None:
        return (f"❌ Chưa kết nối được MySQL: {storage_error}\n"
                f"➡️ Hãy kiểm tra MySQL server đã chạy, cấu hình DB_* trong .env, "
                f"rồi bấm 'Kết nối lại' ở tab Dashboard.")
    return None


# ==============================================================================
# HÀM XỬ LÝ SỰ KIỆN (HANDLERS)
# ==============================================================================

# ---------- TAB 1: DASHBOARD ----------

def on_check_connection():
    init_client()
    init_storage()
    empty_cols = ["ID", "Tên Ứng Viên", "Mã SBD", "Đơn Vị", "Số Phiếu Bầu"]

    lines = []
    if client is None:
        lines.append(f"❌ Blockchain: {client_error}")
    else:
        try:
            is_admin = client.is_configured_account_admin()
            active = client.get_election_active()
            admin_note = ("✅ Tài khoản cấu hình chính là Admin của hợp đồng."
                           if is_admin else
                           "⚠️ CẢNH BÁO: Tài khoản cấu hình KHÔNG trùng với Admin trên chain "
                           "— mọi thao tác ghi sẽ bị từ chối!")
            lines.append(f"✅ Blockchain: đã kết nối tới {client.rpc_url}\n"
                         f"   Hợp đồng: {client.contract_address}\n"
                         f"   Tài khoản đang dùng: {client.account}\n"
                         f"   {admin_note}\n"
                         f"   Trạng thái bầu cử trên chain: {'🟢 ĐANG DIỄN RA' if active else '⚪ Chưa mở / đã đóng'}")
        except Exception as e:
            lines.append(f"❌ Blockchain: kết nối được node nhưng lỗi khi đọc hợp đồng: {e}")

    lines.append(storage.check_connection() if storage_error is None else f"❌ MySQL: {storage_error}")

    status = "\n\n".join(lines)
    results = _build_results_table() if client is not None else pd.DataFrame(columns=empty_cols)
    return status, results


def _build_results_table():
    cols = ["ID", "Tên Ứng Viên", "Mã SBD", "Đơn Vị", "Số Phiếu Bầu"]
    candidates = client.get_all_candidates()
    try:
        meta_map = storage.get_candidate_meta_bulk([c["id"] for c in candidates])
    except StorageError:
        meta_map = {}

    rows = []
    for cand in candidates:
        meta = meta_map.get(cand["id"], {"code": "", "unit": ""})
        rows.append({
            "ID": cand["id"],
            "Tên Ứng Viên": cand["name"],
            "Mã SBD": meta["code"],
            "Đơn Vị": meta["unit"],
            "Số Phiếu Bầu": cand["votes"],
        })
    return pd.DataFrame(rows, columns=cols) if rows else pd.DataFrame(columns=cols)


# ---------- TAB 2: THÊM CUỘC BẦU CỬ & ỨNG VIÊN ----------

def on_add_candidate(name, code, unit):
    if not name.strip():
        df_current = pd.DataFrame(draft_candidates, columns=CANDIDATE_COLS)
        return df_current, "⚠️ Vui lòng nhập họ và tên ứng viên!"

    new_candidate = {
        "STT": len(draft_candidates) + 1,
        "Họ Và Tên": name.strip(),
        "Mã Định Danh / SBD": code.strip() if code.strip() else f"UV-{len(draft_candidates)+1:02d}",
        "Đơn Vị / Chi Đoàn": unit.strip() if unit.strip() else "Tự do",
    }
    draft_candidates.append(new_candidate)

    df_updated = pd.DataFrame(draft_candidates, columns=CANDIDATE_COLS)
    return df_updated, f"✅ Đã thêm ứng viên: {name} (Hiện có {len(draft_candidates)} ứng viên trong danh sách tạm)."


def on_clear_candidates():
    global draft_candidates
    draft_candidates = []
    return pd.DataFrame(columns=CANDIDATE_COLS), "Đã làm trống danh sách ứng viên tạm."


def on_submit_election(title, desc, start_time, end_time):
    global draft_candidates

    df_elections = pd.DataFrame(_get_elections_table(), columns=ELECTION_COLS)
    df_draft = pd.DataFrame(draft_candidates, columns=CANDIDATE_COLS)

    if not title.strip():
        return "⚠️ Tên cuộc bầu cử không được để trống!", df_draft, df_elections, gr.Tabs(selected="tab_create")

    err = _require_client() or _require_storage()
    if err:
        return err, df_draft, df_elections, gr.Tabs(selected="tab_create")

    if not draft_candidates:
        return "⚠️ Chưa có ứng viên nào trong danh sách tạm. Hãy thêm ít nhất 1 ứng viên trước khi khởi tạo.", \
               df_draft, df_elections, gr.Tabs(selected="tab_create")

    try:
        if client.get_election_active():
            msg = ("❌ Đang có một cuộc bầu cử MỞ trên blockchain (electionActive = true). "
                   "Phải vào Tab 3 bấm 'Đóng phiên chốt sổ' trước khi tạo phiên/ứng viên mới.")
            return msg, df_draft, df_elections, gr.Tabs(selected="tab_create")
    except Exception as e:
        return f"❌ Lỗi khi kiểm tra trạng thái bầu cử: {e}", df_draft, df_elections, gr.Tabs(selected="tab_create")

    try:
        election_code = storage.create_election(
            title.strip(), desc.strip(),
            start_time.strip() if start_time.strip() else "Bắt đầu ngay",
            end_time.strip() if end_time.strip() else "Chưa đặt",
            status="Đang nạp ứng viên lên chain...",
        )
    except StorageError as e:
        return f"❌ Lỗi khi tạo phiên trong MySQL: {e}", df_draft, df_elections, gr.Tabs(selected="tab_create")

    pushed_ids = []
    for cand in draft_candidates:
        try:
            result = client.add_candidate(cand["Họ Và Tên"])
            onchain_id = result["id"]
            storage.add_candidates_to_election(election_code, [onchain_id])
            storage.set_candidate_meta(onchain_id, cand["Mã Định Danh / SBD"], cand["Đơn Vị / Chi Đoàn"])
            pushed_ids.append(onchain_id)
        except (ElectionError, StorageError) as e:
            total = len(draft_candidates)
            try:
                storage.update_election_status(election_code, f"Lỗi một phần ({len(pushed_ids)}/{total})")
            except StorageError:
                pass
            remaining = pd.DataFrame(draft_candidates[len(pushed_ids):], columns=CANDIDATE_COLS)
            msg = (f"❌ Dừng lại sau khi đã đẩy thành công {len(pushed_ids)}/{total} ứng viên lên chain.\n"
                   f"Lỗi ở ứng viên '{cand['Họ Và Tên']}': {e}")
            return msg, remaining, pd.DataFrame(_get_elections_table(), columns=ELECTION_COLS), gr.Tabs(selected="tab_create")

    try:
        storage.update_election_status(election_code, "Sẵn sàng (đã nạp lên chain)")
    except StorageError as e:
        return f"⚠️ Đã nạp xong ứng viên lên chain nhưng lỗi khi cập nhật trạng thái phiên: {e}", \
               pd.DataFrame(columns=CANDIDATE_COLS), pd.DataFrame(_get_elections_table(), columns=ELECTION_COLS), \
               gr.Tabs(selected="tab_manage")

    total_added = len(draft_candidates)
    draft_candidates = []

    msg = f"✅ Khởi tạo thành công cuộc bầu cử '{title}' (Mã: {election_code}) cùng với {total_added} ứng viên đã ghi lên blockchain!"
    df_empty_draft = pd.DataFrame(columns=CANDIDATE_COLS)
    df_elections = pd.DataFrame(_get_elections_table(), columns=ELECTION_COLS)

    return msg, df_empty_draft, df_elections, gr.Tabs(selected="tab_manage")


# ---------- TAB 3: QUẢN LÝ CUỘC BẦU CỬ & ỨNG VIÊN ----------

def _get_elections_table():
    err = _require_storage()
    if err:
        return []
    try:
        items = storage.list_elections()
    except StorageError:
        return []
    return [{
        "Mã Phiên": item["id"],
        "Tên Cuộc Bầu Cử": item["title"],
        "Số Ứng Viên": item["candidate_count"],
        "Thời Gian Bắt Đầu": item["start"],
        "Thời Gian Kết Thúc": item["end"],
        "Trạng Thái": item["status"],
    } for item in items]


def on_view_candidates_of_election(election_id):
    if not election_id.strip():
        return pd.DataFrame(columns=CANDIDATE_RESULT_COLS), "⚠️ Vui lòng nhập mã phiên bầu cử!"

    err = _require_storage() or _require_client()
    if err:
        return pd.DataFrame(columns=CANDIDATE_RESULT_COLS), err

    try:
        item = storage.get_election(election_id)
    except StorageError as e:
        return pd.DataFrame(columns=CANDIDATE_RESULT_COLS), f"❌ {e}"

    if item is None:
        return pd.DataFrame(columns=CANDIDATE_RESULT_COLS), f"❌ Không tìm thấy mã phiên: {election_id}"

    rows = []
    for cid in item["candidate_ids"]:
        try:
            cand = client.get_candidate(cid)
        except Exception as e:
            return pd.DataFrame(columns=CANDIDATE_RESULT_COLS), f"❌ Lỗi khi đọc ứng viên #{cid} từ chain: {e}"
        try:
            meta = storage.get_candidate_meta(cid)
        except StorageError:
            meta = {"code": "", "unit": ""}
        rows.append({
            "ID On-chain": cand["id"],
            "Họ Và Tên": cand["name"],
            "Mã Định Danh / SBD": meta["code"],
            "Đơn Vị / Chi Đoàn": meta["unit"],
            "Số Phiếu Bầu": cand["votes"],
        })

    df_cand = pd.DataFrame(rows, columns=CANDIDATE_RESULT_COLS)
    return df_cand, f"Danh sách ứng viên của phiên: {item['title']}"


def on_update_election_status(election_id, new_status):
    if not election_id.strip():
        return pd.DataFrame(_get_elections_table(), columns=ELECTION_COLS), "⚠️ Vui lòng nhập mã phiên!"

    err = _require_storage() or _require_client()
    if err:
        return pd.DataFrame(_get_elections_table(), columns=ELECTION_COLS), err

    try:
        item = storage.get_election(election_id)
        latest_code = storage.get_latest_election_code()
    except StorageError as e:
        return pd.DataFrame(_get_elections_table(), columns=ELECTION_COLS), f"❌ {e}"

    if item is None:
        return pd.DataFrame(_get_elections_table(), columns=ELECTION_COLS), f"❌ Không tìm thấy mã phiên: {election_id}"

    if item["id"] != latest_code:
        return pd.DataFrame(_get_elections_table(), columns=ELECTION_COLS), (
            "❌ Smart Contract hiện tại chỉ hỗ trợ MỘT cuộc bầu cử tại một thời điểm, "
            "nên chỉ phiên MỚI NHẤT mới có thể Bắt đầu/Đóng."
        )

    try:
        if new_status == "Bắt đầu":
            client.start_election()
            new_db_status = "Đang diễn ra"
            result_msg = f"✅ Đã mở phiên bầu cử {election_id} trên blockchain."
        elif new_status == "Đóng phiên chốt sổ":
            client.end_election()
            new_db_status = "Đã kết thúc"
            result_msg = f"✅ Đã đóng phiên bầu cử {election_id} trên blockchain."
        else:
            return pd.DataFrame(_get_elections_table(), columns=ELECTION_COLS), (
                "⚠️ Tính năng 'Tạm dừng' CHƯA được Election.sol hỗ trợ."
            )
    except ElectionError as e:
        return pd.DataFrame(_get_elections_table(), columns=ELECTION_COLS), f"❌ {e}"

    try:
        storage.update_election_status(election_id, new_db_status)
    except StorageError as e:
        result_msg += f"\n⚠️ (Giao dịch chain đã thành công nhưng lỗi khi cập nhật trạng thái trong MySQL: {e})"

    return pd.DataFrame(_get_elections_table(), columns=ELECTION_COLS), result_msg


# ---------- TAB 4: DANH SÁCH YÊU CẦU & XÁC THỰC CỬ TRI ----------

def _build_voter_requests_df():
    """Đọc danh sách cử tri gửi yêu cầu từ voter_requests.json và đồng bộ trạng thái thật từ Smart Contract."""
    requests_list = load_voter_requests()
    changed = False
    rows = []

    for idx, req in enumerate(requests_list, start=1):
        wallet = str(req.get("walletAddress", "")).strip()
        status = req.get("status", "Chờ duyệt")

        # Kiểm tra trực tiếp trên Smart Contract xem ví này đã được whitelist chưa
        if client is not None and wallet:
            try:
                v_onchain = client.get_voter(wallet)
                if v_onchain.get("is_authorized") and status != "Đã xác thực":
                    status = "Đã xác thực"
                    req["status"] = "Đã xác thực"
                    changed = True
            except Exception:
                pass

        rows.append({
            "STT": idx,
            "Họ Và Tên": req.get("name", "Cử tri"),
            "Email": req.get("email", ""),
            "Số CCCD / MSSV": req.get("cccd", ""),
            "Địa Chỉ Ví": wallet,
            "Thời Gian Gửi": req.get("requestedAt", ""),
            "Trạng Thái": status,
        })

    if changed:
        save_voter_requests(requests_list)

    return pd.DataFrame(rows, columns=VOTER_REQ_COLS) if rows else pd.DataFrame(columns=VOTER_REQ_COLS)


def on_refresh_voter_requests():
    df = _build_voter_requests_df()
    pending_count = sum(1 for r in load_voter_requests() if r.get("status") == "Chờ duyệt")
    return df, f"🔄 Đã làm mới danh sách. Hiện có {len(df)} yêu cầu ({pending_count} đang chờ duyệt)."


def on_select_voter_row(evt: gr.SelectData, current_df: pd.DataFrame):
    """Khi Admin click vào 1 dòng trong bảng yêu cầu, tự động lấy Địa Chỉ Ví của dòng đó."""
    try:
        if current_df is None or current_df.empty:
            return "", "⚠️ Bảng đang trống."
        row_idx = evt.index[0] if isinstance(evt.index, (list, tuple)) else int(evt.index)
        row = current_df.iloc[row_idx]
        wallet = str(row["Địa Chỉ Ví"]).strip()
        name = str(row["Họ Và Tên"]).strip()
        cccd = str(row["Số CCCD / MSSV"]).strip()
        status = str(row["Trạng Thái"]).strip()
        return wallet, f"📌 Đã chọn cử tri: {name} (CCCD/MSSV: {cccd}) — Ví: {wallet} [{status}]"
    except Exception as e:
        return "", f"⚠️ Không lấy được dòng đã chọn: {e}"


def on_approve_selected_voter(selected_wallet):
    """Xác thực (gọi authorizeVoter trên Smart Contract) cho cử tri đang được chọn từ danh sách."""
    wallet = (selected_wallet or "").strip()
    if not wallet:
        return _build_voter_requests_df(), "⚠️ Vui lòng click chọn một cử tri trên bảng danh sách trước!"

    err = _require_client()
    if err:
        return _build_voter_requests_df(), err

    try:
        result = client.authorize_voter(wallet)
        checksum_addr = result["address"]

        # Cập nhật trạng thái trong voter_requests.json
        requests_list = load_voter_requests()
        for req in requests_list:
            if str(req.get("walletAddress", "")).strip().lower() == wallet.lower():
                req["status"] = "Đã xác thực"
        save_voter_requests(requests_list)

        return _build_voter_requests_df(), f"✅ Đã xác thực & cấp quyền (Whitelist) trên Blockchain cho ví: {checksum_addr}"
    except ElectionError as e:
        return _build_voter_requests_df(), f"❌ {e}"


def on_approve_all_pending_voters():
    """Xác thực hàng loạt TẤT CẢ cử tri đang ở trạng thái 'Chờ duyệt' trong danh sách."""
    err = _require_client()
    if err:
        return _build_voter_requests_df(), err

    requests_list = load_voter_requests()
    pending = [r for r in requests_list if r.get("status") == "Chờ duyệt" and r.get("walletAddress")]

    if not pending:
        return _build_voter_requests_df(), "ℹ️ Không có cử tri nào đang ở trạng thái 'Chờ duyệt'."

    success_count = 0
    errors = []
    for req in pending:
        wallet = str(req["walletAddress"]).strip()
        try:
            client.authorize_voter(wallet)
            req["status"] = "Đã xác thực"
            success_count += 1
        except ElectionError as e:
            errors.append(f"{wallet[:10]}...: {e}")

    save_voter_requests(requests_list)
    summary = f"✅ Đã xác thực thành công {success_count}/{len(pending)} cử tri lên Blockchain!"
    if errors:
        summary += "\n⚠️ Lỗi: " + "; ".join(errors)
    return _build_voter_requests_df(), summary


def on_reject_selected_voter(selected_wallet):
    """Từ chối yêu cầu xác thực của cử tri đang chọn."""
    wallet = (selected_wallet or "").strip()
    if not wallet:
        return _build_voter_requests_df(), "⚠️ Vui lòng click chọn một cử tri trên bảng trước khi từ chối!"

    requests_list = load_voter_requests()
    found = False
    for req in requests_list:
        if str(req.get("walletAddress", "")).strip().lower() == wallet.lower():
            if req.get("status") == "Đã xác thực":
                return _build_voter_requests_df(), "⚠️ Cử tri này đã được ghi Whitelist trên Blockchain, không thể hủy!"
            req["status"] = "Từ chối"
            found = True

    if not found:
        return _build_voter_requests_df(), f"❌ Không tìm thấy yêu cầu của ví {wallet} trong danh sách."

    save_voter_requests(requests_list)
    return _build_voter_requests_df(), f"🚫 Đã từ chối yêu cầu xác thực của ví {wallet}."


def on_lookup_voter(address):
    if not address.strip():
        return "⚠️ Vui lòng nhập địa chỉ ví cử tri."

    err = _require_client()
    if err:
        return err

    try:
        v = client.get_voter(address)
        return (f"Địa chỉ: {v['address']}\n"
                f"Đã được cấp quyền (Whitelist): {'✅ Có' if v['is_authorized'] else '❌ Chưa'}\n"
                f"Đã bầu: {'✅ Rồi' if v['has_voted'] else '⬜ Chưa'}")
    except ElectionError as e:
        return f"❌ {e}"


# ==============================================================================
# GIAO DIỆN GRADIO BLOCKS
# ==============================================================================

with gr.Blocks(title="Cổng Quản Trị Hệ Thống Bầu Cử", theme=gr.themes.Soft()) as admin_app:
    gr.Markdown("# 🗳️ HỆ THỐNG QUẢN TRỊ BẦU CỬ ĐIỆN TỬ (ADMIN PORTAL)")

    with gr.Tabs() as main_tabs:

        # TAB 1: DASHBOARD
        with gr.TabItem("📊 1. Dashboard", id="tab_dashboard"):
            gr.Markdown("### Giám sát kết nối Blockchain & Bảng kiểm phiếu thời gian thực")
            dash_status = gr.Textbox(label="Trạng thái hệ thống", value="Đang kiểm tra kết nối...",
                                      interactive=False, lines=5)
            dash_refresh_btn = gr.Button("🔄 Kết nối lại / Làm mới", variant="primary")
            results_table = gr.Dataframe(
                headers=["ID", "Tên Ứng Viên", "Mã SBD", "Đơn Vị", "Số Phiếu Bầu"],
                interactive=False,
            )

        # TAB 2: THÊM CUỘC BẦU CỬ & ỨNG VIÊN
        with gr.TabItem("➕ 2. Thêm Cuộc Bầu Cử & Ứng Viên", id="tab_create"):
            gr.Markdown("### Bước 1: Thông tin phiên bầu cử")
            with gr.Row():
                with gr.Column(scale=2):
                    elect_title = gr.Textbox(label="Tên cuộc bầu cử *", placeholder="Ví dụ: Đại hội Đại biểu Đoàn TNCS Khóa 2026")
                    elect_desc = gr.Textbox(label="Mô tả / Thể lệ", lines=2, placeholder="Quy định bỏ phiếu...")
                with gr.Column(scale=1):
                    elect_start = gr.Textbox(label="Thời gian bắt đầu", placeholder="2026-10-06 08:00")
                    elect_end = gr.Textbox(label="Thời gian kết thúc", placeholder="2026-10-06 17:00")

            gr.Markdown("---")
            gr.Markdown("### Bước 2: Thêm các ứng viên tham gia vào cuộc bầu cử này")
            with gr.Row():
                cand_name = gr.Textbox(label="Họ và tên ứng viên", placeholder="Nguyễn Văn A")
                cand_code = gr.Textbox(label="Mã định danh / SBD", placeholder="UV-01")
                cand_unit = gr.Textbox(label="Đơn vị / Chi đoàn", placeholder="Khoa CNTT")

            with gr.Row():
                add_cand_btn = gr.Button("➕ Thêm ứng viên vào danh sách tạm", variant="secondary")
                clear_cand_btn = gr.Button("🗑️ Xóa danh sách ứng viên tạm")

            cand_msg = gr.Textbox(label="Trạng thái thêm ứng viên", interactive=False)

            draft_candidates_table = gr.Dataframe(
                headers=CANDIDATE_COLS,
                value=pd.DataFrame(columns=CANDIDATE_COLS),
                label="Danh sách ứng viên dự kiến trong cuộc bầu cử này (chưa lên chain)",
                interactive=False,
            )

            gr.Markdown("---")
            submit_election_btn = gr.Button("🚀 HOÀN TẤT & GHI LÊN BLOCKCHAIN", variant="primary")
            create_msg = gr.Textbox(label="Thông báo tạo phiên", interactive=False, lines=3)

        # TAB 3: QUẢN LÝ CUỘC BẦU CỬ & ỨNG VIÊN
        with gr.TabItem("📑 3. Quản Lý Cuộc Bầu Cử & Ứng Viên", id="tab_manage"):
            gr.Markdown("### Danh mục các cuộc bầu cử trên hệ thống")

            elections_table = gr.Dataframe(
                headers=ELECTION_COLS,
                value=pd.DataFrame(_get_elections_table(), columns=ELECTION_COLS),
                label="Bảng các phiên bầu cử",
                interactive=False,
            )

            with gr.Row():
                with gr.Column():
                    gr.Markdown("#### Điều khiển trạng thái phiên")
                    ctrl_id = gr.Textbox(label="Mã phiên cần thao tác", placeholder="Ví dụ: BC-001")
                    ctrl_action = gr.Radio(choices=["Bắt đầu", "Tạm dừng", "Đóng phiên chốt sổ"], value="Bắt đầu", label="Lệnh")
                    ctrl_btn = gr.Button("Áp dụng lệnh (gửi giao dịch lên chain)")
                    ctrl_msg = gr.Textbox(label="Kết quả thao tác", interactive=False, lines=3)

                with gr.Column():
                    gr.Markdown("#### Tra cứu ứng viên theo phiên (số phiếu đọc trực tiếp từ chain)")
                    view_id = gr.Textbox(label="Nhập mã phiên để xem ứng viên", placeholder="Ví dụ: BC-001")
                    view_btn = gr.Button("🔍 Xem danh sách ứng viên", variant="secondary")
                    view_msg = gr.Textbox(label="Trạng thái tra cứu", interactive=False)

            election_candidates_table = gr.Dataframe(
                headers=CANDIDATE_RESULT_COLS,
                label="Chi tiết ứng viên thuộc phiên bầu cử được chọn",
                interactive=False,
            )

        # TAB 4: XÁC THỰC CỬ TRI (HIỂN THỊ DANH SÁCH YÊU CẦU TỪ CỬ TRI & DUYỆT LÊN CHAIN)
        with gr.TabItem("👥 4. Xác Thực Cử Tri", id="tab_voter"):
            gr.Markdown("### Danh sách Cử tri gửi yêu cầu xác thực (Request Whitelist)")
            gr.Markdown(
                "*(Cử tri gửi yêu cầu từ giao diện Web sẽ hiển thị tại bảng dưới đây. "
                "Admin chỉ cần **click vào dòng cử tri** trong bảng rồi bấm **Xác thực cử tri đã chọn**, "
                "hoặc bấm **Xác thực TẤT CẢ** trước khi cuộc bầu cử bắt đầu.)*"
            )

            with gr.Row():
                refresh_req_btn = gr.Button("🔄 Làm mới danh sách yêu cầu", variant="secondary")
                approve_all_btn = gr.Button("🚀 Xác thực TẤT CẢ cử tri đang chờ duyệt", variant="primary")

            voter_requests_table = gr.Dataframe(
                headers=VOTER_REQ_COLS,
                value=_build_voter_requests_df(),
                label="Bảng danh sách cử tri yêu cầu cấp quyền bỏ phiếu (Click vào 1 dòng để chọn)",
                interactive=False,
            )

            with gr.Row():
                selected_voter_addr = gr.Textbox(
                    label="Địa chỉ ví cử tri đang chọn từ bảng",
                    placeholder="Click vào một dòng trong bảng phía trên để tự động chọn...",
                    interactive=False,
                    scale=3,
                )
                voter_btn = gr.Button("✅ Xác thực cử tri đã chọn", variant="primary", scale=1)
                reject_btn = gr.Button("🚫 Từ chối yêu cầu", variant="stop", scale=1)

            voter_msg = gr.Textbox(label="Kết quả xử lý xác thực", interactive=False, lines=2)

            gr.Markdown("---")
            gr.Markdown("### Tra cứu nhanh trạng thái On-chain của một địa chỉ ví")
            with gr.Row():
                lookup_addr = gr.Textbox(label="Địa chỉ ví cần tra cứu (0x...)", placeholder="0x90F79...", scale=3)
                lookup_btn = gr.Button("🔍 Tra cứu trên Smart Contract", variant="secondary", scale=1)
            lookup_msg = gr.Textbox(label="Trạng thái cử tri trên Blockchain", interactive=False, lines=3)

    # ==========================================================================
    # GẮN SỰ KIỆN NÚT BẤM
    # ==========================================================================

    dash_refresh_btn.click(fn=on_check_connection, inputs=[], outputs=[dash_status, results_table])
    admin_app.load(fn=on_check_connection, inputs=[], outputs=[dash_status, results_table])
    admin_app.load(fn=on_refresh_voter_requests, inputs=[], outputs=[voter_requests_table, voter_msg])

    add_cand_btn.click(
        fn=on_add_candidate,
        inputs=[cand_name, cand_code, cand_unit],
        outputs=[draft_candidates_table, cand_msg],
    )

    clear_cand_btn.click(
        fn=on_clear_candidates,
        inputs=[],
        outputs=[draft_candidates_table, cand_msg],
    )

    submit_election_btn.click(
        fn=on_submit_election,
        inputs=[elect_title, elect_desc, elect_start, elect_end],
        outputs=[create_msg, draft_candidates_table, elections_table, main_tabs],
    )

    ctrl_btn.click(
        fn=on_update_election_status,
        inputs=[ctrl_id, ctrl_action],
        outputs=[elections_table, ctrl_msg],
    )

    view_btn.click(
        fn=on_view_candidates_of_election,
        inputs=[view_id],
        outputs=[election_candidates_table, view_msg],
    )

    # Sự kiện Tab 4: Xác thực cử tri theo danh sách yêu cầu
    refresh_req_btn.click(
        fn=on_refresh_voter_requests,
        inputs=[],
        outputs=[voter_requests_table, voter_msg],
    )

    voter_requests_table.select(
        fn=on_select_voter_row,
        inputs=[voter_requests_table],
        outputs=[selected_voter_addr, voter_msg],
    )

    voter_btn.click(
        fn=on_approve_selected_voter,
        inputs=[selected_voter_addr],
        outputs=[voter_requests_table, voter_msg],
    )

    approve_all_btn.click(
        fn=on_approve_all_pending_voters,
        inputs=[],
        outputs=[voter_requests_table, voter_msg],
    )

    reject_btn.click(
        fn=on_reject_selected_voter,
        inputs=[selected_voter_addr],
        outputs=[voter_requests_table, voter_msg],
    )

    lookup_btn.click(
        fn=on_lookup_voter,
        inputs=[lookup_addr],
        outputs=[lookup_msg],
    )

# ==============================================================================
# FASTAPI ENDPOINTS CHO /api/voter-requests & MOUNT VỚI GRADIO
# ==============================================================================
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

api_app = FastAPI()
api_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@api_app.get("/api/voter-requests")
async def get_voter_requests():
    """Trả về danh sách các yêu cầu xác thực của cử tri."""
    return {"ok": True, "requests": load_voter_requests()}


@api_app.post("/api/voter-requests")
async def post_voter_request(request: Request):
    """Tiếp nhận yêu cầu xác thực cử tri từ web client."""
    try:
        data = await request.json()
        wallet = str(data.get("walletAddress", "")).strip()
        cccd = str(data.get("cccd", "")).strip()
        if not wallet or not cccd:
            return JSONResponse(
                status_code=400,
                content={"ok": False, "error": "Thiếu thông tin địa chỉ ví hoặc số CCCD/MSSV."},
            )

        requests_list = load_voter_requests()
        existing = next(
            (
                r
                for r in requests_list
                if str(r.get("walletAddress", "")).lower() == wallet.lower()
            ),
            None,
        )

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if existing:
            if existing.get("status") == "Đã xác thực":
                return {
                    "ok": True,
                    "message": "Ví của bạn đã được xác thực trước đó trên hệ thống.",
                    "request": existing,
                }
            existing["name"] = data.get("name", existing.get("name", "Cử tri"))
            existing["email"] = data.get("email", existing.get("email", ""))
            existing["cccd"] = cccd
            existing["requestedAt"] = now_str
            existing["status"] = "Chờ duyệt"
        else:
            requests_list.append(
                {
                    "name": data.get("name", "Cử tri"),
                    "email": data.get("email", ""),
                    "cccd": cccd,
                    "walletAddress": wallet,
                    "requestedAt": now_str,
                    "status": "Chờ duyệt",
                }
            )

        save_voter_requests(requests_list)
        return {"ok": True, "message": "Đã gửi yêu cầu xác thực cử tri thành công!"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"ok": False, "error": str(e)})


app = gr.mount_gradio_app(api_app, admin_app, path="/")

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=7860)
