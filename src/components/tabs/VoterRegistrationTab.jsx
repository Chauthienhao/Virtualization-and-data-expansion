import React, { useState, useEffect, useCallback } from "react";
import { Send, CheckCircle2, Clock, XCircle, ShieldCheck } from "lucide-react";

export default function VoterRegistrationTab({
  currentUser,
  walletAddress,
  voterInfo,
  onRefreshChain,
  onProceedVoting,
}) {
  const [cccd, setCccd] = useState("");
  const [name, setName] = useState(currentUser?.name || "");
  const [requestRecord, setRequestRecord] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [feedback, setFeedback] = useState("");

  useEffect(() => {
    if (currentUser?.name) {
      setName(currentUser.name);
    }
  }, [currentUser]);

  // Tải trạng thái yêu cầu xác thực của ví hiện tại từ server (/api/voter-requests)
  const fetchMyRequestStatus = useCallback(async () => {
    if (!walletAddress) return;
    try {
      const res = await fetch("/api/voter-requests");
      const data = await res.json();
      if (data.ok && Array.isArray(data.requests)) {
        const found = data.requests.find(
          (r) =>
            String(r.walletAddress || "").toLowerCase() ===
            walletAddress.toLowerCase()
        );
        if (found) {
          setRequestRecord(found);
          if (found.cccd) {
            setCccd((prev) => prev || found.cccd);
          }
        } else {
          setRequestRecord(null);
        }
      }
    } catch (err) {
      console.warn("Không thể tải trạng thái yêu cầu xác thực:", err);
    }
  }, [walletAddress]);

  useEffect(() => {
    fetchMyRequestStatus();
  }, [fetchMyRequestStatus]);

  // Gửi yêu cầu xác thực lên Admin
  const handleSubmitRequest = async (e) => {
    e.preventDefault();
    setFeedback("");

    if (!walletAddress) {
      alert("Vui lòng kết nối ví MetaMask trước khi gửi yêu cầu!");
      return;
    }
    if (!cccd.trim()) {
      alert("Vui lòng nhập Số CCCD hoặc Mã số sinh viên!");
      return;
    }

    setSubmitting(true);
    try {
      const res = await fetch("/api/voter-requests", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: name.trim() || currentUser?.name || "Cử tri",
          email: currentUser?.email || "",
          cccd: cccd.trim(),
          walletAddress: walletAddress.trim(),
        }),
      });
      const data = await res.json();
      if (!res.ok || !data.ok) {
        setFeedback(`❌ ${data.error || "Không thể gửi yêu cầu xác thực."}`);
      } else {
        setFeedback(
          "✅ Đã gửi yêu cầu xác thực thành công! Yêu cầu của bạn đã xuất hiện trên bảng danh sách của Admin."
        );
        await fetchMyRequestStatus();
      }
    } catch (err) {
      setFeedback(`❌ Lỗi kết nối khi gửi yêu cầu: ${err.message}`);
    } finally {
      setSubmitting(false);
    }
  };

  const isWhitelisted = Boolean(voterInfo?.isAuthorized);
  const currentStatus = isWhitelisted
    ? "Đã xác thực"
    : requestRecord?.status || "Chưa gửi yêu cầu";

  return (
    <div className="max-w-2xl mx-auto bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden mt-6">
      <div className="bg-[#38c8e6] text-white px-6 py-4 text-xl font-semibold flex items-center justify-between">
        <span>ĐĂNG KÝ & GỬI YÊU CẦU XÁC THỰC CỬ TRI</span>
        {isWhitelisted && (
          <span className="text-xs bg-white text-[#38c8e6] font-bold px-3 py-1 rounded-full flex items-center gap-1">
            <ShieldCheck className="w-4 h-4" /> Whitelisted
          </span>
        )}
      </div>

      <form onSubmit={handleSubmitRequest} className="p-8 space-y-6">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">
              Họ và Tên Cử tri
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Nguyễn Văn A"
              required
              disabled={isWhitelisted}
              className="w-full border-b-2 border-gray-300 py-2 outline-none focus:border-[#38c8e6] text-gray-700 disabled:bg-gray-50"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">
              Mã số Sinh viên / Số CCCD *
            </label>
            <input
              type="text"
              placeholder="Nhập MSSV hoặc Số CCCD..."
              value={cccd}
              onChange={(e) => setCccd(e.target.value)}
              required
              disabled={isWhitelisted}
              className="w-full border-b-2 border-gray-300 py-2 outline-none focus:border-[#38c8e6] text-gray-700 disabled:bg-gray-50"
            />
          </div>
        </div>

        <div>
          <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">
            Địa chỉ Ví MetaMask đã liên kết cố định với tài khoản (Không thể thay đổi)
          </label>
          <input
            type="text"
            value={walletAddress || ""}
            readOnly
            className="w-full border-b-2 border-gray-200 bg-gray-100 px-3 py-2 text-gray-600 font-mono text-sm rounded cursor-not-allowed"
          />
        </div>

        {/* Hộp hiển thị trạng thái phê duyệt thực tế */}
        <div
          className={`p-4 rounded-lg border text-sm space-y-2 ${
            currentStatus === "Đã xác thực"
              ? "bg-green-50 border-green-200 text-green-800"
              : currentStatus === "Chờ duyệt"
              ? "bg-amber-50 border-amber-200 text-amber-800"
              : currentStatus === "Từ chối"
              ? "bg-red-50 border-red-200 text-red-800"
              : "bg-gray-50 border-gray-200 text-gray-700"
          }`}
        >
          <div className="flex items-center gap-2 font-bold">
            {currentStatus === "Đã xác thực" && (
              <>
                <CheckCircle2 className="w-5 h-5 text-green-600" />
                <span>Trạng thái: ĐÃ ĐƯỢC ADMIN XÁC THỰC (WHITELISTED TRÊN BLOCKCHAIN)</span>
              </>
            )}
            {currentStatus === "Chờ duyệt" && (
              <>
                <Clock className="w-5 h-5 text-amber-600" />
                <span>Trạng thái: ĐANG CHỜ ADMIN PHÊ DUYỆT ({requestRecord?.requestedAt})</span>
              </>
            )}
            {currentStatus === "Từ chối" && (
              <>
                <XCircle className="w-5 h-5 text-red-600" />
                <span>Trạng thái: YÊU CẦU BỊ TỪ CHỐI (Bạn có thể sửa lại thông tin và gửi lại)</span>
              </>
            )}
            {currentStatus === "Chưa gửi yêu cầu" && (
              <span>Trạng thái: CHƯA GỬI YÊU CẦU XÁC THỰC</span>
            )}
          </div>

          <p className="text-xs leading-relaxed">
            {currentStatus === "Đã xác thực"
              ? voterInfo?.hasVoted
                ? `Bạn đã hoàn thành bỏ phiếu cho ứng viên #${voterInfo.votedCandidateId}.`
                : "Ví của bạn đã được Admin phê duyệt trên Smart Contract. Bạn có thể vào Khu vực bỏ phiếu ngay bây giờ!"
              : currentStatus === "Chờ duyệt"
              ? "Yêu cầu của bạn đã nằm trong bảng 'Danh sách Cử tri gửi yêu cầu xác thực' trên Cổng Admin (Tab 4). Hãy chờ Admin bấm nút Xác thực."
              : "Hãy nhập Số CCCD / MSSV và nhấn nút 'Gửi yêu cầu xác thực lên Admin' bên dưới."}
          </p>
        </div>

        {feedback && (
          <p className="text-xs font-semibold text-cyan-800 bg-cyan-50 p-3 rounded border border-cyan-200">
            {feedback}
          </p>
        )}

        <div className="flex flex-col sm:flex-row gap-4 pt-2">
          {!isWhitelisted && (
            <button
              type="submit"
              disabled={submitting}
              className="flex-1 flex items-center justify-center gap-2 bg-[#38c8e6] hover:bg-cyan-600 disabled:bg-gray-400 text-white font-bold py-3 px-4 rounded-md transition-all shadow-sm"
            >
              <Send className="w-4 h-4" />
              {submitting
                ? "Đang gửi..."
                : currentStatus === "Chờ duyệt"
                ? "CẬP NHẬT LẠI YÊU CẦU"
                : "GỬI YÊU CẦU XÁC THỰC LÊN ADMIN"}
            </button>
          )}

          <button
            type="button"
            onClick={async () => {
              await fetchMyRequestStatus();
              if (onRefreshChain) await onRefreshChain();
            }}
            className="px-5 py-3 border border-gray-300 hover:bg-gray-50 text-gray-700 font-semibold rounded-md transition-all text-sm"
          >
            🔄 Kiểm tra trạng thái duyệt
          </button>

          {isWhitelisted && (
            <button
              type="button"
              onClick={onProceedVoting}
              className="flex-1 bg-green-600 hover:bg-green-700 text-white font-bold py-3 px-4 rounded-md transition-all shadow-sm"
            >
              ➡️ ĐẾN KHU VỰC BỎ PHIẾU
            </button>
          )}
        </div>
      </form>
    </div>
  );
}
