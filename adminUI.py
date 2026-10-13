import gradio as gr
import pandas as pd

from blockchain_client import ElectionClient, ElectionError
import storage
from storage import StorageError

# ==============================================================================
# KẾT NỐI BLOCKCHAIN (khởi tạo lúc mở app; có thể "Kết nối lại" từ Dashboard
# nếu lúc mở app Ganache chưa chạy hoặc .env chưa đúng)
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
# KẾT NỐI MYSQL (lưu metadata off-chain: mã SBD, đơn vị, mô tả/thời gian phiên)
# ==============================================================================
storage_error = None


def init_storage():
    """Tạo database/bảng nếu chưa có. Không raise ra ngoài, để app vẫn mở
    được ngay cả khi MySQL chưa chạy (có thể 'Kết nối lại' ở Dashboard)."""
    global storage_error
    try:
        storage.init_db()
        storage_error = None
    except StorageError as e:
        storage_error = str(e)
    except Exception as e:
        storage_error = f"Lỗi không xác định khi khởi tạo MySQL: {e}"


init_storage()

draft_candidates = []            # Danh sách ứng viên đang soạn thảo, CHƯA đẩy lên chain

ELECTION_COLS = ["Mã Phiên", "Tên Cuộc Bầu Cử", "Số Ứng Viên", "Thời Gian Bắt Đầu", "Thời Gian Kết Thúc", "Trạng Thái"]
CANDIDATE_COLS = ["STT", "Họ Và Tên", "Mã Định Danh / SBD", "Đơn Vị / Chi Đoàn"]
CANDIDATE_RESULT_COLS = ["ID On-chain", "Họ Và Tên", "Mã Định Danh / SBD", "Đơn Vị / Chi Đoàn", "Số Phiếu Bầu"]


def _require_client():
    """Dùng ở đầu mỗi handler cần gọi blockchain: trả None nếu đã kết nối,
    hoặc một thông báo lỗi tiếng Việt nếu chưa."""
    if client is None:
        return (f"Chưa kết nối được blockchain: {client_error}\n"
                f"Hãy kiểm tra Ganache đã chạy, cấu hình trong file .env, "
                f"rồi bấm 'Kết nối lại' ở tab Dashboard.")
    return None


def _require_storage():
    """Tương tự _require_client() nhưng cho MySQL."""
    if storage_error is not None:
        return (f"Chưa kết nối được MySQL: {storage_error}\n"
                f"Hãy kiểm tra MySQL server đã chạy, cấu hình DB_* trong .env, "
                f"rồi bấm 'Kết nối lại' ở tab Dashboard.")
    return None


# ==============================================================================
# HÀM XỬ LÝ SỰ KIỆN (HANDLERS)
# ==============================================================================

# ---------- TAB 1: DASHBOARD ----------

def on_check_connection():
    """Kiểm tra/làm mới trạng thái kết nối blockchain VÀ MySQL."""
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
            admin_note = ("Tài khoản cấu hình chính là Admin của hợp đồng."
                           if is_admin else
                           "CẢNH BÁO: Tài khoản cấu hình KHÔNG trùng với Admin trên chain "
                           "— mọi thao tác ghi (thêm ứng viên, cấp quyền, mở/đóng phiên) sẽ bị từ chối!")
            lines.append(f"Blockchain: đã kết nối tới {client.rpc_url}\n"
                         f"   Hợp đồng: {client.contract_address}\n"
                         f"   Tài khoản đang dùng: {client.account}\n"
                         f"   {admin_note}\n"
                         f"   Trạng thái bầu cử trên chain: {'ĐANG DIỄN RA' if active else 'Chưa mở / đã đóng'}")
        except Exception as e:
            lines.append(f"Blockchain: kết nối được node nhưng lỗi khi đọc hợp đồng: {e}")

    lines.append(storage.check_connection() if storage_error is None else f"MySQL: {storage_error}")

    status = "\n\n".join(lines)
    results = _build_results_table() if client is not None else pd.DataFrame(columns=empty_cols)
    return status, results


def _build_results_table():
    """Đọc toàn bộ ứng viên + số phiếu trực tiếp từ chain, ghép với metadata off-chain.
    Nếu MySQL đang lỗi, vẫn hiển thị đúng dữ liệu trên chain (chỉ để trống Mã SBD/Đơn vị),
    vì đây là hai nguồn dữ liệu độc lập — chain hỏng hay MySQL hỏng không nên kéo nhau."""
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
    """Thêm một ứng viên vào danh sách soạn thảo tạm thời (CHƯA lên chain)."""
    if not name.strip():
        df_current = pd.DataFrame(draft_candidates, columns=CANDIDATE_COLS)
        return df_current, "Vui lòng nhập họ và tên ứng viên!"

    new_candidate = {
        "STT": len(draft_candidates) + 1,
        "Họ Và Tên": name.strip(),
        "Mã Định Danh / SBD": code.strip() if code.strip() else f"UV-{len(draft_candidates)+1:02d}",
        "Đơn Vị / Chi Đoàn": unit.strip() if unit.strip() else "Tự do",
    }
    draft_candidates.append(new_candidate)

    df_updated = pd.DataFrame(draft_candidates, columns=CANDIDATE_COLS)
    return df_updated, f"Đã thêm ứng viên: {name} (Hiện có {len(draft_candidates)} ứng viên trong danh sách tạm)."


def on_clear_candidates():
    """Xóa sạch danh sách ứng viên tạm (chỉ ảnh hưởng danh sách CHƯA submit)."""
    global draft_candidates
    draft_candidates = []
    return pd.DataFrame(columns=CANDIDATE_COLS), "Đã làm trống danh sách ứng viên tạm."


def on_submit_election(title, desc, start_time, end_time):
    """Tạo cuộc bầu cử: tạo bản ghi 'phiên' trong MySQL TRƯỚC (để luôn có chỗ
    neo dữ liệu), rồi đẩy từng ứng viên trong danh sách tạm LÊN CHAIN thật
    (gọi addCandidate) và gắn ngay vào phiên + lưu metadata off-chain NGAY
    sau mỗi lần thành công — nên nếu giữa chừng lỗi, những gì đã làm được
    vẫn còn nguyên trong MySQL, không mất trắng như cách gộp-rồi-lưu-1-lần.
    Tự động chuyển sang Tab 3 khi xong."""
    global draft_candidates

    df_elections = pd.DataFrame(_get_elections_table(), columns=ELECTION_COLS)
    df_draft = pd.DataFrame(draft_candidates, columns=CANDIDATE_COLS)

    if not title.strip():
        return "Tên cuộc bầu cử không được để trống!", df_draft, df_elections, gr.Tabs(selected="tab_create")

    err = _require_client() or _require_storage()
    if err:
        return err, df_draft, df_elections, gr.Tabs(selected="tab_create")

    if not draft_candidates:
        return "Chưa có ứng viên nào trong danh sách tạm. Hãy thêm ít nhất 1 ứng viên trước khi khởi tạo.", \
               df_draft, df_elections, gr.Tabs(selected="tab_create")

    # Hợp đồng chỉ cho addCandidate khi electionActive == False
    try:
        if client.get_election_active():
            msg = ("Đang có một cuộc bầu cử MỞ trên blockchain (electionActive = true). "
                   "Phải vào Tab 3 bấm 'Đóng phiên chốt sổ' trước khi tạo phiên/ứng viên mới, "
                   "vì Smart Contract không cho thêm ứng viên khi đang bầu cử.")
            return msg, df_draft, df_elections, gr.Tabs(selected="tab_create")
    except Exception as e:
        return f"Lỗi khi kiểm tra trạng thái bầu cử: {e}", df_draft, df_elections, gr.Tabs(selected="tab_create")

    try:
        election_code = storage.create_election(
            title.strip(), desc.strip(),
            start_time.strip() if start_time.strip() else "Bắt đầu ngay",
            end_time.strip() if end_time.strip() else "Chưa đặt",
            status="Đang nạp ứng viên lên chain...",
        )
    except StorageError as e:
        return f"Lỗi khi tạo phiên trong MySQL: {e}", df_draft, df_elections, gr.Tabs(selected="tab_create")

    # Đẩy từng ứng viên lên chain, gắn vào phiên NGAY khi thành công.
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
                pass  # ưu tiên trả lỗi gốc cho người dùng hơn là lỗi lồng lỗi
            remaining = pd.DataFrame(draft_candidates[len(pushed_ids):], columns=CANDIDATE_COLS)
            msg = (f"Dừng lại sau khi đã đẩy thành công {len(pushed_ids)}/{total} ứng viên lên chain "
                   f"(phiên {election_code} vẫn được giữ lại trong MySQL với các ứng viên đã thành công).\n"
                   f"Lỗi ở ứng viên '{cand['Họ Và Tên']}': {e}")
            return msg, remaining, pd.DataFrame(_get_elections_table(), columns=ELECTION_COLS), gr.Tabs(selected="tab_create")

    try:
        storage.update_election_status(election_code, "Sẵn sàng (đã nạp lên chain)")
    except StorageError as e:
        return f"Đã nạp xong ứng viên lên chain nhưng lỗi khi cập nhật trạng thái phiên: {e}", \
               pd.DataFrame(columns=CANDIDATE_COLS), pd.DataFrame(_get_elections_table(), columns=ELECTION_COLS), \
               gr.Tabs(selected="tab_manage")

    total_added = len(draft_candidates)
    draft_candidates = []

    msg = f"Khởi tạo thành công cuộc bầu cử '{title}' (Mã: {election_code}) cùng với {total_added} ứng viên đã ghi lên blockchain!"
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
    """Tra cứu ứng viên của một phiên cụ thể, kèm số phiếu THẬT đọc từ chain."""
    if not election_id.strip():
        return pd.DataFrame(columns=CANDIDATE_RESULT_COLS), "Vui lòng nhập mã phiên bầu cử!"

    err = _require_storage() or _require_client()
    if err:
        return pd.DataFrame(columns=CANDIDATE_RESULT_COLS), err

    try:
        item = storage.get_election(election_id)
    except StorageError as e:
        return pd.DataFrame(columns=CANDIDATE_RESULT_COLS), f"{e}"

    if item is None:
        return pd.DataFrame(columns=CANDIDATE_RESULT_COLS), f"Không tìm thấy mã phiên: {election_id}"

    rows = []
    for cid in item["candidate_ids"]:
        try:
            cand = client.get_candidate(cid)
        except Exception as e:
            return pd.DataFrame(columns=CANDIDATE_RESULT_COLS), f"Lỗi khi đọc ứng viên #{cid} từ chain: {e}"
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
    """Bắt đầu / Đóng phiên: gọi THẬT lên chain (startElection/endElection).
    Lưu ý: hợp đồng chỉ có MỘT electionActive dùng chung, nên chỉ phiên mới
    nhất trong MySQL mới thực sự đại diện cho trạng thái trên chain."""
    if not election_id.strip():
        return pd.DataFrame(_get_elections_table(), columns=ELECTION_COLS), "⚠️ Vui lòng nhập mã phiên!"

    err = _require_storage() or _require_client()
    if err:
        return pd.DataFrame(_get_elections_table(), columns=ELECTION_COLS), err

    try:
        item = storage.get_election(election_id)
        latest_code = storage.get_latest_election_code()
    except StorageError as e:
        return pd.DataFrame(_get_elections_table(), columns=ELECTION_COLS), f"{e}"

    if item is None:
        return pd.DataFrame(_get_elections_table(), columns=ELECTION_COLS), f"Không tìm thấy mã phiên: {election_id}"

    if item["id"] != latest_code:
        return pd.DataFrame(_get_elections_table(), columns=ELECTION_COLS), (
            "Smart Contract hiện tại chỉ hỗ trợ MỘT cuộc bầu cử tại một thời điểm, "
            "nên chỉ phiên MỚI NHẤT (cũng là phiên đang giữ danh sách ứng viên hiện có trên "
            "chain) mới có thể Bắt đầu/Đóng. Đây là giới hạn của Election.sol hiện tại, "
            "muốn nhiều phiên độc lập cần nâng cấp hợp đồng."
        )

    try:
        if new_status == "Bắt đầu":
            client.start_election()
            new_db_status = "Đang diễn ra"
            result_msg = f"Đã mở phiên bầu cử {election_id} trên blockchain."
        elif new_status == "Đóng phiên chốt sổ":
            client.end_election()
            new_db_status = "Đã kết thúc"
            result_msg = f"Đã đóng phiên bầu cử {election_id} trên blockchain. Có thể xem kết quả ở Dashboard."
        else:  # "Tạm dừng"
            return pd.DataFrame(_get_elections_table(), columns=ELECTION_COLS), (
                "⚠️ Tính năng 'Tạm dừng' CHƯA được Election.sol hỗ trợ (hợp đồng hiện chỉ có "
                "startElection()/endElection(), không có pause). Cần bổ sung hàm tương ứng "
                "trong Smart Contract nếu muốn dùng chức năng này. Chưa có thao tác nào được gửi lên chain."
            )
    except ElectionError as e:
        return pd.DataFrame(_get_elections_table(), columns=ELECTION_COLS), f"{e}"

    try:
        storage.update_election_status(election_id, new_db_status)
    except StorageError as e:
        result_msg += f"\n⚠️ (Giao dịch chain đã thành công nhưng lỗi khi cập nhật trạng thái trong MySQL: {e})"

    return pd.DataFrame(_get_elections_table(), columns=ELECTION_COLS), result_msg


# ---------- TAB 4: XÁC THỰC CỬ TRI ----------

def on_authorize_voter(address):
    """Cấp quyền bầu cử cho một địa chỉ ví (gọi authorizeVoter trên chain).
    (Trước đây nút này tồn tại trên giao diện nhưng KHÔNG được gắn sự kiện —
    đã sửa ở phần gắn sự kiện bên dưới.)"""
    if not address.strip():
        return "Vui lòng nhập địa chỉ ví cử tri."

    err = _require_client()
    if err:
        return err

    try:
        result = client.authorize_voter(address)
        return f"Đã cấp quyền bầu cử cho địa chỉ: {result['address']}"
    except ElectionError as e:
        return f"{e}"


def on_lookup_voter(address):
    """Tra cứu trạng thái của một cử tri (đã được cấp quyền chưa, đã bầu chưa)."""
    if not address.strip():
        return "Vui lòng nhập địa chỉ ví cử tri."

    err = _require_client()
    if err:
        return err

    try:
        v = client.get_voter(address)
        return (f"Địa chỉ: {v['address']}\n"
                f"Đã được cấp quyền (Whitelist): {'Có' if v['is_authorized'] else 'Chưa'}\n"
                f"Đã bầu: {'Rồi' if v['has_voted'] else 'Chưa'}")
    except ElectionError as e:
        return f"{e}"


# ==============================================================================
# GIAO DIỆN GRADIO BLOCKS
# ==============================================================================

with gr.Blocks(title="Cổng Quản Trị Hệ Thống Bầu Cử", theme=gr.themes.Soft()) as admin_app:
    gr.Markdown("# HỆ THỐNG QUẢN TRỊ BẦU CỬ ĐIỆN TỬ (ADMIN PORTAL)")

    with gr.Tabs() as main_tabs:

        # TAB 1: DASHBOARD
        with gr.TabItem("1. Dashboard", id="tab_dashboard"):
            gr.Markdown("### Giám sát kết nối Blockchain & Bảng kiểm phiếu thời gian thực")
            dash_status = gr.Textbox(label="Trạng thái hệ thống", value="Đang kiểm tra kết nối...",
                                      interactive=False, lines=5)
            dash_refresh_btn = gr.Button("Kết nối lại / Làm mới", variant="primary")
            results_table = gr.Dataframe(
                headers=["ID", "Tên Ứng Viên", "Mã SBD", "Đơn Vị", "Số Phiếu Bầu"],
                interactive=False,
            )

        # TAB 2: THÊM CUỘC BẦU CỬ & ỨNG VIÊN
        with gr.TabItem("2. Thêm Cuộc Bầu Cử & Ứng Viên", id="tab_create"):
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
            gr.Markdown("*(Chỉ 'Họ và tên' được ghi lên blockchain; Mã SBD và Đơn vị được lưu off-chain trên máy chủ Admin.)*")
            with gr.Row():
                cand_name = gr.Textbox(label="Họ và tên ứng viên", placeholder="Nguyễn Văn A")
                cand_code = gr.Textbox(label="Mã định danh / SBD", placeholder="UV-01")
                cand_unit = gr.Textbox(label="Đơn vị / Chi đoàn", placeholder="Khoa CNTT")

            with gr.Row():
                add_cand_btn = gr.Button("Thêm ứng viên vào danh sách tạm", variant="secondary")
                clear_cand_btn = gr.Button("Xóa danh sách ứng viên tạm")

            cand_msg = gr.Textbox(label="Trạng thái thêm ứng viên", interactive=False)

            draft_candidates_table = gr.Dataframe(
                headers=CANDIDATE_COLS,
                value=pd.DataFrame(columns=CANDIDATE_COLS),
                label="Danh sách ứng viên dự kiến trong cuộc bầu cử này (chưa lên chain)",
                interactive=False,
            )

            gr.Markdown("---")
            submit_election_btn = gr.Button("HOÀN TẤT & GHI LÊN BLOCKCHAIN", variant="primary")
            create_msg = gr.Textbox(label="Thông báo tạo phiên", interactive=False, lines=3)

        # TAB 3: QUẢN LÝ CUỘC BẦU CỬ & ỨNG VIÊN
        with gr.TabItem("3. Quản Lý Cuộc Bầu Cử & Ứng Viên", id="tab_manage"):
            gr.Markdown("### Danh mục các cuộc bầu cử trên hệ thống")
            gr.Markdown("*(Smart Contract hiện chỉ hỗ trợ 1 cuộc bầu cử hoạt động tại một thời điểm — "
                        "chỉ phiên mới nhất mới điều khiển được Bắt đầu/Đóng.)*")

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
                    view_btn = gr.Button("Xem danh sách ứng viên", variant="secondary")
                    view_msg = gr.Textbox(label="Trạng thái tra cứu", interactive=False)

            election_candidates_table = gr.Dataframe(
                headers=CANDIDATE_RESULT_COLS,
                label="Chi tiết ứng viên thuộc phiên bầu cử được chọn",
                interactive=False,
            )

        # TAB 4: XÁC THỰC CỬ TRI
        with gr.TabItem("👥 4. Xác Thực Cử Tri", id="tab_voter"):
            gr.Markdown("### Cấp quyền bầu cử (Whitelist) cho cử tri")
            gr.Markdown("*(Lưu ý: Smart Contract chỉ cho cấp quyền TRƯỚC khi bầu cử bắt đầu.)*")
            voter_addr = gr.Textbox(label="Địa chỉ ví cử tri (0x...)", placeholder="0x90F79...")
            voter_btn = gr.Button("Xác thực / Cấp quyền cử tri", variant="primary")
            voter_msg = gr.Textbox(label="Kết quả cấp quyền", interactive=False)

            gr.Markdown("---")
            gr.Markdown("### Tra cứu trạng thái cử tri")
            lookup_addr = gr.Textbox(label="Địa chỉ ví cần tra cứu (0x...)", placeholder="0x90F79...")
            lookup_btn = gr.Button("🔍 Tra cứu", variant="secondary")
            lookup_msg = gr.Textbox(label="Trạng thái cử tri", interactive=False, lines=4)

    # ==========================================================================
    # GẮN SỰ KIỆN NÚT BẤM
    # ==========================================================================

    # Dashboard
    dash_refresh_btn.click(fn=on_check_connection, inputs=[], outputs=[dash_status, results_table])
    admin_app.load(fn=on_check_connection, inputs=[], outputs=[dash_status, results_table])

    # 1. Thêm ứng viên vào bảng tạm
    add_cand_btn.click(
        fn=on_add_candidate,
        inputs=[cand_name, cand_code, cand_unit],
        outputs=[draft_candidates_table, cand_msg],
    )

    # 2. Xóa danh sách tạm
    clear_cand_btn.click(
        fn=on_clear_candidates,
        inputs=[],
        outputs=[draft_candidates_table, cand_msg],
    )

    # 3. Tạo cuộc bầu cử -> ghi lên chain -> Nạp dữ liệu vào bảng Quản lý -> chuyển sang Tab 3
    submit_election_btn.click(
        fn=on_submit_election,
        inputs=[elect_title, elect_desc, elect_start, elect_end],
        outputs=[create_msg, draft_candidates_table, elections_table, main_tabs],
    )

    # 4. Đổi trạng thái phiên ở Tab 3 (gọi chain thật)
    ctrl_btn.click(
        fn=on_update_election_status,
        inputs=[ctrl_id, ctrl_action],
        outputs=[elections_table, ctrl_msg],
    )

    # 5. Xem danh sách ứng viên của phiên ở Tab 3 (đọc số phiếu từ chain)
    view_btn.click(
        fn=on_view_candidates_of_election,
        inputs=[view_id],
        outputs=[election_candidates_table, view_msg],
    )

    # 6. Cấp quyền cử tri (ĐÃ SỬA: trước đây nút này không có .click() nào cả)
    voter_btn.click(
        fn=on_authorize_voter,
        inputs=[voter_addr],
        outputs=[voter_msg],
    )

    # 7. Tra cứu trạng thái cử tri (chức năng mới, trước đây chưa có)
    lookup_btn.click(
        fn=on_lookup_voter,
        inputs=[lookup_addr],
        outputs=[lookup_msg],
    )

if __name__ == "__main__":
    admin_app.launch(server_name="127.0.0.1", server_port=7860, share=False)
