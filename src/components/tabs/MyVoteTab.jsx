import React, { useState, useEffect } from "react";
import { CircleCheckBig, RefreshCw, LoaderCircle } from "lucide-react";
import * as api from "../../api";

// LƯU Ý QUAN TRỌNG: tab này THAY THẾ "Result" ở bản trước. Theo đúng yêu
// cầu — "kết quả bầu cử chỉ được công bố trong giao diện admin sau khi
// cuộc bầu cử kết thúc" — tab này KHÔNG BAO GIỜ hiện tổng số phiếu hay
// bảng xếp hạng ứng viên, chỉ hiện đúng lựa chọn của CHÍNH người đang đăng
// nhập (API /my-vote cũng chỉ trả đúng dữ liệu đó, xem voter_api.py).
export default function MyVoteTab({ sessionToken }) {
  const [myVote, setMyVote] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const res = await api.getMyVote(sessionToken);
      setMyVote(res);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="max-w-xl mx-auto bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden mt-10">
      <div className="bg-[#38c8e6] text-white px-6 py-4 text-xl font-semibold flex items-center justify-between">
        PHIẾU CỦA TÔI
        <button
          onClick={load}
          disabled={loading}
          className="flex items-center gap-1 text-sm bg-white/20 hover:bg-white/30 px-3 py-1.5 rounded-full transition-all disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} /> Làm mới
        </button>
      </div>

      <div className="p-8 space-y-4">
        {loading && !myVote && (
          <div className="flex items-center justify-center gap-2 text-gray-400 py-8">
            <LoaderCircle className="w-5 h-5 animate-spin" /> Đang tải...
          </div>
        )}

        {error && <div className="bg-red-50 text-red-600 text-sm rounded-lg p-4">{error}</div>}

        {myVote && !myVote.hasVoted && (
          <p className="text-center text-gray-400 py-8">Bạn chưa bỏ phiếu. Vào tab "Bỏ Phiếu" để tham gia.</p>
        )}

        {myVote && myVote.hasVoted && (
          <div className="bg-green-50 border border-green-200 rounded-lg p-6 flex items-center gap-4">
            <CircleCheckBig className="w-10 h-10 text-green-500 flex-shrink-0" />
            <div>
              <p className="text-sm text-gray-500">Bạn đã bầu cho</p>
              <p className="text-xl font-bold text-gray-800">{myVote.votedCandidate.name}</p>
            </div>
          </div>
        )}

        <p className="text-xs text-gray-400 text-center pt-4">
          Hệ thống chỉ hiện lựa chọn của riêng bạn. Kết quả chung của cuộc bầu cử sẽ được
          Ban tổ chức công bố sau khi phiên bầu cử kết thúc.
        </p>
      </div>
    </div>
  );
}
