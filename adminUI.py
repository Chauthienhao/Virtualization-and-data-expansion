import gradio as gr
import pandas as pd

from blockchain_client import ElectionClient, ElectionError
import storage
from storage import StorageError
import voter_accounts

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
CANDIDATE_COLS = ["Mã SBD (dự kiến)", "Họ Và Tên", "Đơn Vị / Chi Đoàn"]
CANDIDATE_RESULT_COLS = ["Mã SBD", "Họ Và Tên", "Đơn Vị / Chi Đoàn", "Số Phiếu Bầu"]
RESULTS_COLS = ["Mã SBD", "Tên Ứng Viên", "Đơn Vị", "Số Phiếu Bầu"]
# Mã SBD (UV-01, UV-02, ...) do storage cấp từ bộ đếm AUTO_INCREMENT của MySQL,
# không dùng ID on-chain — deploy lại contract thì ID on-chain đếm lại từ 1.


def _require_client():
    """Dùng ở đầu mỗi handler cần gọi blockchain: trả None nếu đã kết nối,
    hoặc một thông báo lỗi tiếng Việt nếu chưa."""
    # Tự tạo lại client nếu Ganache bị restart / hợp đồng được deploy lại
    # sang địa chỉ khác kể từ lúc mở app (đọc lại .env).
    if client is None or not client.is_contract_deployed():
        init_client()
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
    empty_cols = RESULTS_COLS

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
    results = pd.DataFrame(columns=empty_cols)
    if client is not None:
        try:
            results = _build_results_table()
        except ElectionError as e:
            status += f"\n\nKhông đọc được kết quả trên chain: {e}"
    return status, results


def _build_results_table():
    """Đọc toàn bộ ứng viên + số phiếu trực tiếp từ chain, ghép với metadata off-chain.
    Nếu MySQL đang lỗi, vẫn hiển thị đúng dữ liệu trên chain (chỉ để trống Đơn vị),
    vì đây là hai nguồn dữ liệu độc lập — chain hỏng hay MySQL hỏng không nên kéo nhau."""
    cols = RESULTS_COLS
    candidates = client.get_all_candidates()
    try:
        meta_map = storage.get_candidate_meta_bulk(client.contract_address, [c["id"] for c in candidates])
    except StorageError:
        meta_map = {}

    rows = []
    for cand in candidates:
        meta = meta_map.get(cand["id"], {"code": "", "unit": ""})
        rows.append({
            "Mã SBD": meta["code"],
            "Tên Ứng Viên": cand["name"],
            "Đơn Vị": meta["unit"],
            "Số Phiếu Bầu": cand["votes"],
        })
    return pd.DataFrame(rows, columns=cols) if rows else pd.DataFrame(columns=cols)


# ---------- TAB 2: THÊM CUỘC BẦU CỬ & ỨNG VIÊN ----------

def _draft_df():
    """Bảng ứng viên tạm. SBD chỉ là DỰ KIẾN (= số thứ tự SBD tiếp theo trong
    MySQL + vị trí trong danh sách tạm); SBD chính thức được cấp khi ghi lên
    blockchain."""
    base = None
    if _require_storage() is None:
        try:
            base = storage.peek_next_sbd_seq()
        except StorageError:
            base = None
    rows = [{
        "Mã SBD (dự kiến)": f"UV-{base + i - 1:02d}" if base is not None else "(cấp khi ghi lên chain)",
        "Họ Và Tên": c["Họ Và Tên"],
        "Đơn Vị / Chi Đoàn": c["Đơn Vị / Chi Đoàn"],
    } for i, c in enumerate(draft_candidates, start=1)]
    return pd.DataFrame(rows, columns=CANDIDATE_COLS)


def on_add_candidate(name, unit):
    """Thêm một ứng viên vào danh sách soạn thảo tạm thời (CHƯA lên chain)."""
    if not name.strip():
        return _draft_df(), "Vui lòng nhập họ và tên ứng viên!"

    draft_candidates.append({
        "Họ Và Tên": name.strip(),
        "Đơn Vị / Chi Đoàn": unit.strip() if unit.strip() else "Tự do",
    })
    return _draft_df(), f"Đã thêm ứng viên: {name} (Hiện có {len(draft_candidates)} ứng viên trong danh sách tạm)."


def on_clear_candidates():
    """Xóa sạch danh sách ứng viên tạm (chỉ ảnh hưởng danh sách CHƯA submit)."""
    global draft_candidates
    draft_candidates = []
    return pd.DataFrame(columns=CANDIDATE_COLS), "Đã làm trống danh sách ứng viên tạm."


def on_submit_election(title, desc):
    """Tạo cuộc bầu cử: tạo bản ghi 'phiên' trong MySQL TRƯỚC (để luôn có chỗ
    neo dữ liệu), rồi đẩy từng ứng viên trong danh sách tạm LÊN CHAIN thật
    (gọi addCandidate) và gắn ngay vào phiên + lưu metadata off-chain NGAY
    sau mỗi lần thành công — nên nếu giữa chừng lỗi, những gì đã làm được
    vẫn còn nguyên trong MySQL, không mất trắng như cách gộp-rồi-lưu-1-lần.
    Tự động chuyển sang Tab 3 khi xong."""
    global draft_candidates

    df_elections = pd.DataFrame(_get_elections_table(), columns=ELECTION_COLS)
    df_draft = _draft_df()

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

    # Phiên đang tạm dừng thì chain tắt electionActive nhưng phiên CHƯA xong;
    # nếu tạo phiên mới lúc này, phiên tạm dừng sẽ không còn là phiên mới nhất
    # và không bao giờ tiếp tục/đóng được nữa.
    try:
        latest = storage.get_election(storage.get_latest_election_code() or "")
    except StorageError as e:
        return f"{e}", df_draft, df_elections, gr.Tabs(selected="tab_create")
    if latest and latest["status"] == STATUS_PAUSED and _same_contract(latest):
        msg = (f"Phiên {latest['id']} đang TẠM DỪNG (chưa kết thúc). Hãy vào Tab 3 bấm "
               f"'Bắt đầu' để tiếp tục hoặc 'Đóng phiên chốt sổ' trước khi tạo phiên mới.")
        return msg, df_draft, df_elections, gr.Tabs(selected="tab_create")

    # Thời gian bắt đầu/kết thúc thực tế do nút Bắt đầu/Đóng phiên ở Tab 3
    # điều khiển trên chain, nên không nhập tay nữa (cột trong DB để trống).
    try:
        election_code = storage.create_election(
            title.strip(), desc.strip(), "", "",
            status="Đang nạp ứng viên lên chain...",
            contract_address=client.contract_address,
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
            storage.set_candidate_meta(client.contract_address, onchain_id, cand["Đơn Vị / Chi Đoàn"])
            pushed_ids.append(onchain_id)
        except (ElectionError, StorageError) as e:
            total = len(draft_candidates)
            try:
                storage.update_election_status(election_code, f"Lỗi một phần ({len(pushed_ids)}/{total})")
            except StorageError:
                pass  # ưu tiên trả lỗi gốc cho người dùng hơn là lỗi lồng lỗi
            # Bỏ các ứng viên đã lên chain khỏi danh sách tạm, tránh bấm lại bị đẩy trùng.
            draft_candidates = draft_candidates[len(pushed_ids):]
            remaining = _draft_df()
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
        # Do hệ thống tự ghi khi bấm Bắt đầu / Đóng phiên (xem on_update_election_status)
        "Thời Gian Bắt Đầu": item["start"] or "Chưa bắt đầu",
        "Thời Gian Kết Thúc": item["end"] or "Chưa kết thúc",
        "Trạng Thái": item["status"],
    } for item in items]


def _same_contract(item):
    """True nếu phiên được tạo trên chính contract đang kết nối (ID on-chain
    của contract khác — ví dụ trước khi deploy lại — không còn ý nghĩa)."""
    return item["contract_address"].lower() == client.contract_address.lower()


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

    if not _same_contract(item):
        return pd.DataFrame(columns=CANDIDATE_RESULT_COLS), (
            f"Phiên {item['id']} thuộc một contract cũ ({item['contract_address'] or 'không rõ'}), "
            f"không phải contract đang kết nối ({client.contract_address}). "
            "Dữ liệu ứng viên/số phiếu của phiên này không còn đọc được từ chain hiện tại."
        )

    rows = []
    for cid in item["candidate_ids"]:
        try:
            cand = client.get_candidate(cid)
        except Exception as e:
            return pd.DataFrame(columns=CANDIDATE_RESULT_COLS), f"Lỗi khi đọc ứng viên #{cid} từ chain: {e}"
        try:
            meta = storage.get_candidate_meta(client.contract_address, cid)
        except StorageError:
            meta = {"code": "", "unit": ""}
        rows.append({
            "Mã SBD": meta["code"],
            "Họ Và Tên": cand["name"],
            "Đơn Vị / Chi Đoàn": meta["unit"],
            "Số Phiếu Bầu": cand["votes"],
        })

    df_cand = pd.DataFrame(rows, columns=CANDIDATE_RESULT_COLS)
    return df_cand, f"Danh sách ứng viên của phiên: {item['title']}"


STATUS_RUNNING = "Đang diễn ra"
STATUS_PAUSED = "Tạm dừng"
STATUS_ENDED = "Đã kết thúc"


def on_update_election_status(election_id, new_status):
    """Bắt đầu / Tạm dừng / Đóng phiên: gọi THẬT lên chain (startElection/endElection).
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

    if not _same_contract(item):
        return pd.DataFrame(_get_elections_table(), columns=ELECTION_COLS), (
            f"Phiên {item['id']} thuộc một contract cũ, không phải contract đang kết nối "
            f"({client.contract_address}) — không thể Bắt đầu/Đóng phiên này nữa."
        )

    if item["id"] != latest_code:
        return pd.DataFrame(_get_elections_table(), columns=ELECTION_COLS), (
            "Smart Contract hiện tại chỉ hỗ trợ MỘT cuộc bầu cử tại một thời điểm, "
            "nên chỉ phiên MỚI NHẤT (cũng là phiên đang giữ danh sách ứng viên hiện có trên "
            "chain) mới có thể Bắt đầu/Đóng. Đây là giới hạn của Election.sol hiện tại, "
            "muốn nhiều phiên độc lập cần nâng cấp hợp đồng."
        )

    # Contract chỉ có 1 cờ electionActive (startElection/endElection đều là
    # onlyAdmin, tức chỉ app này gọi được), nên "Tạm dừng" và "Đã kết thúc"
    # được phân biệt bằng trạng thái phiên trong MySQL:
    #   - Tạm dừng   : tắt electionActive trên chain, vẫn được Bắt đầu lại.
    #   - Đã kết thúc: tắt electionActive trên chain, KHÔNG được Bắt đầu lại.
    def _fail(msg):
        return pd.DataFrame(_get_elections_table(), columns=ELECTION_COLS), msg

    if item["status"] == STATUS_ENDED:
        return _fail(f"Phiên {election_id} đã đóng chốt sổ — không thể Bắt đầu/Tạm dừng/Đóng lại nữa. "
                     f"Muốn bầu tiếp hãy tạo một phiên mới ở Tab 2.")

    try:
        active = client.get_election_active()
        time_field = None
        if new_status == "Bắt đầu":
            if active:
                return _fail(f"Phiên {election_id} đang diễn ra rồi.")
            client.start_election()
            new_db_status = STATUS_RUNNING
            resumed = item["status"] == STATUS_PAUSED
            if not resumed:
                time_field = "start"   # chỉ ghi thời gian ở lần Bắt đầu đầu tiên, không ghi đè khi tiếp tục
            result_msg = (f"Đã tiếp tục phiên bầu cử {election_id} sau khi tạm dừng." if resumed
                          else f"Đã mở phiên bầu cử {election_id} trên blockchain.")
        elif new_status == "Tạm dừng":
            if not active:
                return _fail(f"Phiên {election_id} chưa diễn ra hoặc đang tạm dừng sẵn — không có gì để tạm dừng.")
            client.end_election()
            new_db_status = STATUS_PAUSED
            result_msg = (f"Đã tạm dừng phiên bầu cử {election_id} — cử tri tạm thời không bỏ phiếu được. "
                          f"Bấm 'Bắt đầu' để tiếp tục.")
        else:  # "Đóng phiên chốt sổ"
            if active:
                client.end_election()
            new_db_status = STATUS_ENDED
            time_field = "end"
            result_msg = (f"Đã đóng chốt sổ phiên bầu cử {election_id}. Phiên này không thể mở lại. "
                          f"Có thể xem kết quả ở Dashboard.")
    except ElectionError as e:
        return _fail(f"{e}")

    try:
        storage.update_election_status(election_id, new_db_status)
        if time_field:
            storage.set_election_time(election_id, time_field)
    except StorageError as e:
        result_msg += f"\n⚠️ (Giao dịch chain đã thành công nhưng lỗi khi cập nhật trạng thái trong MySQL: {e})"

    return pd.DataFrame(_get_elections_table(), columns=ELECTION_COLS), result_msg


# ---------- TAB 4: DANH SÁCH CỬ TRI ----------
# ĐÃ ĐỔI HƯỚNG (thay cho "hàng đợi yêu cầu" dùng MetaMask của bản trước):
# cử tri giờ không tự có ví riêng, không tự gọi contract. Admin chỉ nhập
# CCCD của người đủ điều kiện vào MySQL (CHƯA đụng blockchain ở bước này).
# Việc sinh ví + bơm ETH + authorizeVoter xảy ra TỰ ĐỘNG, đúng lúc CCCD đó
# đăng nhập thành công LẦN ĐẦU qua voter_api.py (server riêng cho cử tri,
# phục vụ frontend React) — xem storage.attach_wallet() và voter_accounts.py.

VOTER_LIST_COLS = ["ID", "Họ Và Tên", "Trạng Thái", "Địa Chỉ Ví", "Thời Điểm Tạo"]

STATUS_LABELS = {
    "chua_kich_hoat": "Chưa đăng nhập lần nào",
    "da_cap_ma": "Đã nhận mã, chờ xác thực",
    "dang_trong_phien": "Đang trong phiên bầu cử",
    "da_khoa": "Đã đăng xuất / khóa",
}


def _get_voters_table():
    err = _require_storage()
    if err:
        return pd.DataFrame(columns=VOTER_LIST_COLS)
    try:
        rows = storage.list_voters()
    except StorageError:
        return pd.DataFrame(columns=VOTER_LIST_COLS)
    data = [{
        "ID": r["id"],
        "Họ Và Tên": r["full_name"] or "",
        "Trạng Thái": STATUS_LABELS.get(r["status"], r["status"]),
        "Địa Chỉ Ví": r["wallet_address"] or "(chưa có, sẽ sinh khi đăng nhập lần đầu)",
        "Thời Điểm Tạo": str(r["created_at"]) if r["created_at"] else "",
    } for r in rows]
    return pd.DataFrame(data, columns=VOTER_LIST_COLS) if data else pd.DataFrame(columns=VOTER_LIST_COLS)


def on_refresh_voters():
    err = _require_storage()
    if err:
        return pd.DataFrame(columns=VOTER_LIST_COLS), err
    df = _get_voters_table()
    return df, f"Có {len(df)} cử tri trong danh sách."


def on_add_voter(cccd, full_name):
    if not cccd.strip():
        return _get_voters_table(), "Vui lòng nhập CCCD."
    err = _require_storage()
    if err:
        return _get_voters_table(), err
    try:
        cccd_hash = voter_accounts.hash_cccd(cccd)
        storage.create_eligible_voter(cccd_hash, full_name.strip() or None)
    except StorageError as e:
        return _get_voters_table(), f"{e}"
    tail = cccd.strip()[-4:]
    return _get_voters_table(), f"Đã thêm cử tri (CCCD kết thúc ...{tail}) vào danh sách đủ điều kiện."


def on_bulk_add_voters(bulk_text):
    """Thêm nhanh nhiều cử tri — mỗi dòng 1 người, định dạng: CCCD,Họ Và Tên
    (phần họ tên có thể bỏ trống)."""
    err = _require_storage()
    if err:
        return _get_voters_table(), err
    lines = [l.strip() for l in bulk_text.splitlines() if l.strip()]
    if not lines:
        return _get_voters_table(), "Chưa có dữ liệu. Mỗi dòng 1 cử tri, định dạng: CCCD,Họ Và Tên"
    added, failed = 0, []
    for line in lines:
        parts = line.split(",", 1)
        cccd = parts[0].strip()
        name = parts[1].strip() if len(parts) > 1 else None
        try:
            cccd_hash = voter_accounts.hash_cccd(cccd)
            storage.create_eligible_voter(cccd_hash, name)
            added += 1
        except StorageError as e:
            failed.append(f"...{cccd[-4:]}: {e}")
    msg = f"Đã thêm {added}/{len(lines)} cử tri."
    if failed:
        msg += "\nLỗi: " + "; ".join(failed[:5]) + (" ..." if len(failed) > 5 else "")
    return _get_voters_table(), msg


def on_lookup_voter(cccd):
    """Admin tra cứu nội bộ trạng thái 1 cử tri bằng CCCD (không phải địa
    chỉ ví nữa — cử tri giờ không biết và không cần biết địa chỉ ví của mình)."""
    if not cccd.strip():
        return "Vui lòng nhập CCCD cần tra cứu."
    err = _require_storage()
    if err:
        return err
    try:
        cccd_hash = voter_accounts.hash_cccd(cccd)
        voter = storage.get_voter_by_cccd_hash(cccd_hash)
    except StorageError as e:
        return f"{e}"
    if voter is None:
        return "CCCD này không có trong danh sách cử tri."

    lines = [
        f"Họ và tên: {voter['full_name'] or '(chưa rõ)'}",
        f"Trạng thái: {STATUS_LABELS.get(voter['status'], voter['status'])}",
    ]
    if voter["wallet_address"]:
        lines.append(f"Địa chỉ ví (nội bộ hệ thống): {voter['wallet_address']}")
        if client is not None:
            try:
                v = client.get_voter(voter["wallet_address"])
                lines.append(f"Đã được cấp quyền trên chain: {'Có' if v['is_authorized'] else 'Chưa'}")
                lines.append(f"Đã bầu: {'Rồi' if v['has_voted'] else 'Chưa'}")
            except ElectionError as e:
                lines.append(f"(Không đọc được trạng thái trên chain: {e})")
    else:
        lines.append("Địa chỉ ví: chưa có (sẽ sinh khi đăng nhập lần đầu)")
    return "\n".join(lines)


def on_unlock_voter(cccd):
    """Gỡ một phiên bị KẸT (trình duyệt cử tri bị đóng/crash giữa chừng,
    quên bấm "Đăng xuất"), để CCCD đó đăng nhập lại được từ đầu. KHÔNG dùng
    để mở lại CCCD đã đăng xuất chủ động — khóa đó là vĩnh viễn."""
    if not cccd.strip():
        return "Vui lòng nhập CCCD cần mở khóa."
    err = _require_storage()
    if err:
        return err
    try:
        cccd_hash = voter_accounts.hash_cccd(cccd)
        storage.force_unlock_voter(cccd_hash)
    except StorageError as e:
        return f"{e}"
    return "✅ Đã mở khóa phiên bị kẹt. CCCD này có thể đăng nhập lại từ đầu."


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
                headers=RESULTS_COLS,
                interactive=False,
            )

        # TAB 2: THÊM CUỘC BẦU CỬ & ỨNG VIÊN
        with gr.TabItem("2. Thêm Cuộc Bầu Cử & Ứng Viên", id="tab_create"):
            gr.Markdown("### Bước 1: Thông tin phiên bầu cử")
            elect_title = gr.Textbox(label="Tên cuộc bầu cử *", placeholder="Ví dụ: Đại hội Đại biểu Đoàn TNCS Khóa 2026")
            elect_desc = gr.Textbox(label="Mô tả / Thể lệ", lines=2, placeholder="Quy định bỏ phiếu...")

            gr.Markdown("---")
            gr.Markdown("### Bước 2: Thêm các ứng viên tham gia vào cuộc bầu cử này")
            gr.Markdown("*(Chỉ 'Họ và tên' được ghi lên blockchain; Đơn vị được lưu off-chain trên máy chủ Admin. "
                        "Mã SBD được hệ thống tự cấp theo dạng UV-01, UV-02, ... và không bao giờ trùng.)*")
            with gr.Row():
                cand_name = gr.Textbox(label="Họ và tên ứng viên", placeholder="Nguyễn Văn A")
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

        # TAB 4: DANH SÁCH CỬ TRI
        with gr.TabItem("👥 4. Danh Sách Cử Tri", id="tab_voter"):
            gr.Markdown("### Thêm cử tri đủ điều kiện (theo CCCD)")
            gr.Markdown(
                "*Chỉ cần nhập CCCD ở bước này — **chưa** sinh ví, **chưa** đụng blockchain. "
                "Hệ thống sẽ tự sinh ví, bơm ETH và cấp quyền trên chain đúng lúc CCCD này "
                "đăng nhập thành công **lần đầu tiên** ở trang web cử tri.*"
            )
            with gr.Row():
                add_cccd = gr.Textbox(label="Số CCCD", placeholder="001234567890")
                add_name = gr.Textbox(label="Họ và tên (tùy chọn)", placeholder="Nguyễn Văn A")
            add_voter_btn = gr.Button("➕ Thêm vào danh sách", variant="primary")

            gr.Markdown("*Hoặc thêm nhanh nhiều người cùng lúc — mỗi dòng 1 cử tri, định dạng `CCCD,Họ Và Tên`:*")
            bulk_voters = gr.Textbox(
                label="Thêm hàng loạt",
                lines=4,
                placeholder="001234567890,Nguyễn Văn A\n001234567891,Trần Thị B",
            )
            bulk_add_btn = gr.Button("➕ Thêm hàng loạt", variant="secondary")

            voter_list_msg = gr.Textbox(label="Trạng thái", interactive=False)

            gr.Markdown("---")
            voters_refresh_btn = gr.Button("🔄 Làm mới danh sách cử tri", variant="secondary")
            voters_table = gr.Dataframe(
                headers=VOTER_LIST_COLS,
                value=_get_voters_table(),
                label="Danh sách cử tri",
                interactive=False,
            )

            gr.Markdown("---")
            gr.Markdown("### Tra cứu một cử tri (theo CCCD)")
            lookup_cccd = gr.Textbox(label="CCCD cần tra cứu", placeholder="001234567890")
            lookup_btn = gr.Button("🔍 Tra cứu", variant="secondary")
            lookup_msg = gr.Textbox(label="Trạng thái cử tri", interactive=False, lines=5)

            gr.Markdown("---")
            gr.Markdown(
                "### Mở khóa phiên bị kẹt\n"
                "*Dùng khi cử tri báo lỗi \"Phiên đăng nhập trước đó vẫn đang mở\" dù trình duyệt "
                "của họ đã bị đóng/crash giữa chừng (quên bấm Đăng Xuất). "
                "**Không** dùng cho CCCD đã chủ động đăng xuất — khóa đó là vĩnh viễn.*"
            )
            unlock_cccd = gr.Textbox(label="CCCD cần mở khóa", placeholder="001234567890")
            unlock_btn = gr.Button("🔓 Mở khóa phiên", variant="stop")
            unlock_msg = gr.Textbox(label="Kết quả", interactive=False)

    # ==========================================================================
    # GẮN SỰ KIỆN NÚT BẤM
    # ==========================================================================

    # Dashboard
    dash_refresh_btn.click(fn=on_check_connection, inputs=[], outputs=[dash_status, results_table])
    admin_app.load(fn=on_check_connection, inputs=[], outputs=[dash_status, results_table])

    # 1. Thêm ứng viên vào bảng tạm
    add_cand_btn.click(
        fn=on_add_candidate,
        inputs=[cand_name, cand_unit],
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
        inputs=[elect_title, elect_desc],
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

    # 6. Danh sách cử tri (CCCD) — thêm 1 người, thêm hàng loạt, làm mới
    add_voter_btn.click(
        fn=on_add_voter,
        inputs=[add_cccd, add_name],
        outputs=[voters_table, voter_list_msg],
    )

    bulk_add_btn.click(
        fn=on_bulk_add_voters,
        inputs=[bulk_voters],
        outputs=[voters_table, voter_list_msg],
    )

    voters_refresh_btn.click(
        fn=on_refresh_voters,
        inputs=[],
        outputs=[voters_table, voter_list_msg],
    )
    admin_app.load(fn=on_refresh_voters, inputs=[], outputs=[voters_table, voter_list_msg])

    # 7. Tra cứu trạng thái cử tri (theo CCCD)
    lookup_btn.click(
        fn=on_lookup_voter,
        inputs=[lookup_cccd],
        outputs=[lookup_msg],
    )

    # 8. Mở khóa phiên bị kẹt (theo CCCD)
    unlock_btn.click(
        fn=on_unlock_voter,
        inputs=[unlock_cccd],
        outputs=[unlock_msg],
    )

if __name__ == "__main__":
    admin_app.launch(server_name="127.0.0.1", server_port=7860, share=False)
