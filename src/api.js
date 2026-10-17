// ============================================================================
// api.js — nơi DUY NHẤT frontend nói chuyện với voter_api.py.
//
// KHÁC HẲN BẢN TRƯỚC (dùng MetaMask trực tiếp): cử tri giờ không có ví
// riêng, không tự ký giao dịch gì cả — mọi thao tác (đăng nhập, bầu, tra
// cứu) đều đi qua server voter_api.py bằng fetch() thường, server đó mới
// là nơi ký giao dịch hộ bằng ví custodial (xem voter_accounts.py).
// ============================================================================

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8001";

async function request(path, options = {}) {
  let res;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
  } catch (err) {
    throw new Error(
      `Không kết nối được tới máy chủ (${API_BASE}). Kiểm tra voter_api.py đã chạy chưa ` +
      `(uvicorn voter_api:app --port 8001).`
    );
  }

  let data = null;
  try {
    data = await res.json();
  } catch {
    // Một số response (vd lỗi mạng giữa chừng) có thể không có JSON hợp lệ — bỏ qua.
  }

  if (!res.ok) {
    throw new Error((data && data.detail) || `Lỗi máy chủ (mã ${res.status}).`);
  }
  return data;
}

/** Bước 1: gửi CCCD, nhận mã truy cập (hiện ngay trên màn hình). */
export function login(cccd) {
  return request("/login", { method: "POST", body: JSON.stringify({ cccd }) });
}

/** Bước 2: xác thực mã, nhận session_token để dùng cho các bước sau. */
export function verifyCode(cccd, code) {
  return request("/verify-code", { method: "POST", body: JSON.stringify({ cccd, code }) });
}

/** Trạng thái hiện tại + danh sách ứng viên (KHÔNG kèm số phiếu). */
export function getMe(sessionToken) {
  return request(`/me?session_token=${encodeURIComponent(sessionToken)}`);
}

/** Gửi giao dịch bầu cho một ứng viên. */
export function castVote(sessionToken, candidateId) {
  return request("/vote", {
    method: "POST",
    body: JSON.stringify({ session_token: sessionToken, candidate_id: candidateId }),
  });
}

/** Tra cứu lại CHÍNH lựa chọn của mình (không phải kết quả chung). */
export function getMyVote(sessionToken) {
  return request(`/my-vote?session_token=${encodeURIComponent(sessionToken)}`);
}

/** Đăng xuất — khóa VĨNH VIỄN phiên này ở phía server. */
export function logout(sessionToken) {
  return request("/logout", { method: "POST", body: JSON.stringify({ session_token: sessionToken }) });
}
