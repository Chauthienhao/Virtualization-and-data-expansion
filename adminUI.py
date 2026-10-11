import gradio as gr
import pandas as pd

# ==============================================================================
# BỘ LƯU TRỮ TRONG PHIÊN LÀM VIỆC (LOCAL SESSION STATE)
# ==============================================================================
elections_db = []          # Lưu danh sách các cuộc bầu cử
draft_candidates = []      # Danh sách ứng viên đang soạn thảo tạm thời

ELECTION_COLS = ["Mã Phiên", "Tên Cuộc Bầu Cử", "Số Ứng Viên", "Thời Gian Bắt Đầu", "Thời Gian Kết Thúc", "Trạng Thái"]
CANDIDATE_COLS = ["STT", "Họ Và Tên", "Mã Định Danh / SBD", "Đơn Vị / Chi Đoàn"]

# ==============================================================================
# HÀM XỬ LÝ SỰ KIỆN (HANDLERS)
# ==============================================================================

def on_add_candidate(name, code, unit):
    """Thêm một ứng viên vào danh sách soạn thảo tạm thời"""
    if not name.strip():
        df_current = pd.DataFrame(draft_candidates, columns=CANDIDATE_COLS)
        return df_current, "⚠️ Vui lòng nhập họ và tên ứng viên!"
    
    new_candidate = {
        "STT": len(draft_candidates) + 1,
        "Họ Và Tên": name.strip(),
        "Mã Định Danh / SBD": code.strip() if code.strip() else f"UV-{len(draft_candidates)+1:02d}",
        "Đơn Vị / Chi Đoàn": unit.strip() if unit.strip() else "Tự do"
    }
    draft_candidates.append(new_candidate)
    
    df_updated = pd.DataFrame(draft_candidates, columns=CANDIDATE_COLS)
    return df_updated, f"✅ Đã thêm ứng viên: {name} (Hiện có {len(draft_candidates)} ứng viên trong danh sách tạm)."

def on_clear_candidates():
    """Xóa sạch danh sách ứng viên tạm"""
    global draft_candidates
    draft_candidates = []
    return pd.DataFrame(columns=CANDIDATE_COLS), "Đã làm trống danh sách ứng viên tạm."

def on_submit_election(title, desc, start_time, end_time):
    """Tạo cuộc bầu cử, gom ứng viên, cập nhật bảng quản lý và tự động nhảy Tab"""
    global draft_candidates
    
    if not title.strip():
        df_elections = pd.DataFrame(get_elections_table(), columns=ELECTION_COLS)
        df_draft = pd.DataFrame(draft_candidates, columns=CANDIDATE_COLS)
        return "⚠️ Tên cuộc bầu cử không được để trống!", df_draft, df_elections, gr.Tabs(selected="tab_create")
    
    new_id = f"BC-{len(elections_db) + 1:03d}"
    
    # Lưu phiên bầu cử mới kèm danh sách ứng viên
    elections_db.append({
        "id": new_id,
        "title": title.strip(),
        "desc": desc.strip(),
        "start": start_time.strip() if start_time.strip() else "Bắt đầu ngay",
        "end": end_time.strip() if end_time.strip() else "Chưa đặt",
        "status": "Sẵn sàng",
        "candidates": list(draft_candidates)
    })
    
    # Xóa trắng danh sách tạm để sẵn sàng cho lần tạo tiếp theo
    total_added = len(draft_candidates)
    draft_candidates = []
    
    msg = f"✅ Khởi tạo thành công cuộc bầu cử '{title}' (Mã: {new_id}) cùng với {total_added} ứng viên!"
    df_empty_draft = pd.DataFrame(columns=CANDIDATE_COLS)
    df_elections = pd.DataFrame(get_elections_table(), columns=ELECTION_COLS)
    
    # Nhảy sang tab_manage
    return msg, df_empty_draft, df_elections, gr.Tabs(selected="tab_manage")

def get_elections_table():
    """Chuyển đổi dữ liệu phiên sang bảng"""
    data = []
    for item in elections_db:
        data.append({
            "Mã Phiên": item["id"],
            "Tên Cuộc Bầu Cử": item["title"],
            "Số Ứng Viên": len(item["candidates"]),
            "Thời Gian Bắt Đầu": item["start"],
            "Thời Gian Kết Thúc": item["end"],
            "Trạng Thái": item["status"]
        })
    return data

def on_view_candidates_of_election(election_id):
    """Tra cứu ứng viên của một phiên cụ thể ở Tab 3"""
    if not election_id.strip():
        return pd.DataFrame(columns=CANDIDATE_COLS), "⚠️ Vui lòng nhập mã phiên bầu cử!"
    
    for item in elections_db:
        if item["id"] == election_id.strip():
            df_cand = pd.DataFrame(item["candidates"], columns=CANDIDATE_COLS)
            return df_cand, f"Danh sách ứng viên của phiên: {item['title']}"
            
    return pd.DataFrame(columns=CANDIDATE_COLS), f"❌ Không tìm thấy mã phiên: {election_id}"

def on_update_election_status(election_id, new_status):
    """Đổi trạng thái phiên"""
    if not election_id.strip():
        return pd.DataFrame(get_elections_table(), columns=ELECTION_COLS), "⚠️ Vui lòng nhập mã phiên!"
    
    found = False
    for item in elections_db:
        if item["id"] == election_id.strip():
            item["status"] = new_status
            found = True
            break
            
    df_updated = pd.DataFrame(get_elections_table(), columns=ELECTION_COLS)
    if found:
        return df_updated, f"✅ Đã đổi trạng thái phiên {election_id} thành: '{new_status}'"
    return df_updated, f"❌ Không tìm thấy mã phiên: {election_id}"

# ==============================================================================
# GIAO DIỆN GRADIO BLOCKS
# ==============================================================================

with gr.Blocks(title="Cổng Quản Trị Hệ Thống Bầu Cử", theme=gr.themes.Soft()) as admin_app:
    gr.Markdown("# 🗳️ HỆ THỐNG QUẢN TRỊ BẦU CỬ ĐIỆN TỬ (ADMIN PORTAL)")
    
    with gr.Tabs() as main_tabs:
        
        # TAB 1: DASHBOARD
        with gr.TabItem("📊 1. Dashboard", id="tab_dashboard"):
            gr.Markdown("### Giám sát & Bảng kiểm phiếu thời gian thực")
            dash_status = gr.Textbox(label="Trạng thái hệ thống", value="Hệ thống sẵn sàng...", interactive=False)
            results_table = gr.Dataframe(headers=["ID", "Tên Ứng Viên", "Số Phiếu Bầu"], interactive=False)

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
            
            # Bảng danh sách ứng viên tạm
            draft_candidates_table = gr.Dataframe(
                headers=CANDIDATE_COLS,
                value=pd.DataFrame(columns=CANDIDATE_COLS),
                label="Danh sách ứng viên dự kiến trong cuộc bầu cử này",
                interactive=False
            )
            
            gr.Markdown("---")
            submit_election_btn = gr.Button("🚀 HOÀN TẤT & KHỞI TẠO CUỘC BẦU CỬ", variant="primary")
            create_msg = gr.Textbox(label="Thông báo tạo phiên", interactive=False)

        # TAB 3: QUẢN LÝ CUỘC BẦU CỬ & ỨNG VIÊN
        with gr.TabItem("📑 3. Quản Lý Cuộc Bầu Cử & Ứng Viên", id="tab_manage"):
            gr.Markdown("### Danh mục các cuộc bầu cử trên hệ thống")
            
            elections_table = gr.Dataframe(
                headers=ELECTION_COLS,
                value=pd.DataFrame(columns=ELECTION_COLS),
                label="Bảng các phiên bầu cử",
                interactive=False
            )
            
            with gr.Row():
                with gr.Column():
                    gr.Markdown("#### Điều khiển trạng thái phiên")
                    ctrl_id = gr.Textbox(label="Mã phiên cần thao tác", placeholder="Ví dụ: BC-001")
                    ctrl_action = gr.Radio(choices=["Bắt đầu", "Tạm dừng", "Đóng phiên chốt sổ"], value="Bắt đầu", label="Lệnh")
                    ctrl_btn = gr.Button("Áp dụng lệnh")
                    ctrl_msg = gr.Textbox(label="Kết quả thao tác", interactive=False)
                
                with gr.Column():
                    gr.Markdown("#### Tra cứu ứng viên theo phiên")
                    view_id = gr.Textbox(label="Nhập mã phiên để xem ứng viên", placeholder="Ví dụ: BC-001")
                    view_btn = gr.Button("🔍 Xem danh sách ứng viên", variant="secondary")
                    view_msg = gr.Textbox(label="Trạng thái tra cứu", interactive=False)
            
            election_candidates_table = gr.Dataframe(
                headers=CANDIDATE_COLS,
                label="Chi tiết ứng viên thuộc phiên bầu cử được chọn",
                interactive=False
            )

        # TAB 4: XÁC THỰC CỬ TRI
        with gr.TabItem("👥 4. Xác Thực Cử Tri", id="tab_voter"):
            gr.Markdown("### Xác thực tư cách cử tri hợp lệ")
            voter_addr = gr.Textbox(label="Địa chỉ ví cử tri (0x...)", placeholder="0x90F79...")
            voter_btn = gr.Button("Xác thực cử tri")

    # ==========================================================================
    # GẮN SỰ KIỆN NÚT BẤM
    # ==========================================================================
    
    # 1. Thêm ứng viên vào bảng tạm (chỉ lấy input từ 3 textbox, không lấy từ bảng Dataframe)
    add_cand_btn.click(
        fn=on_add_candidate,
        inputs=[cand_name, cand_code, cand_unit],
        outputs=[draft_candidates_table, cand_msg]
    )
    
    # 2. Xóa danh sách tạm
    clear_cand_btn.click(
        fn=on_clear_candidates,
        inputs=[],
        outputs=[draft_candidates_table, cand_msg]
    )
    
    # 3. Tạo cuộc bầu cử -> Nạp dữ liệu vào bảng Quản lý -> Tự động chuyển sang Tab 3
    submit_election_btn.click(
        fn=on_submit_election,
        inputs=[elect_title, elect_desc, elect_start, elect_end],
        outputs=[create_msg, draft_candidates_table, elections_table, main_tabs]
    )
    
    # 4. Đổi trạng thái phiên ở Tab 3
    ctrl_btn.click(
        fn=on_update_election_status,
        inputs=[ctrl_id, ctrl_action],
        outputs=[elections_table, ctrl_msg]
    )
    
    # 5. Xem danh sách ứng viên của phiên ở Tab 3
    view_btn.click(
        fn=on_view_candidates_of_election,
        inputs=[view_id],
        outputs=[election_candidates_table, view_msg]
    )

if __name__ == "__main__":
    admin_app.launch(server_name="127.0.0.1", server_port=7860, share=False)