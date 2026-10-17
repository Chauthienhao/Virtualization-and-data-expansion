import React, { useState } from "react";
import { User, LoaderCircle, RefreshCw } from "lucide-react";

// LƯU Ý: candidates ở đây CHỈ có {id, name} — API /me cố tình KHÔNG trả về
// số phiếu, để không lộ kết quả cho cử tri giữa chừng (xem voter_api.py).
export default function VotingAreaTab({ candidates, hasVoted, electionActive, onVote, onRefresh }) {
  const [votingId, setVotingId] = useState(null);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");

  const handleVote = async (candidateId) => {
    setError("");
    setVotingId(candidateId);
    try {
      await onVote(candidateId);
    } catch (err) {
      setError(err.message || String(err));
    } finally {
      setVotingId(null);
    }
  };

  // BUG #1: trang này trước đây không có cách nào tự nhận biết khi Admin mở
  // cuộc bầu cử SAU khi cử tri đã đăng nhập. App.jsx giờ tự poll lại mỗi 8s,
  // nhưng vẫn thêm nút làm mới thủ công ở đây để cử tri không cần chờ.
  const handleRefresh = async () => {
    if (!onRefresh) return;
    setRefreshing(true);
    try {
      await onRefresh();
    } finally {
      setRefreshing(false);
    }
  };

  if (!electionActive) {
    return (
      <div className="text-center space-y-4 pt-20">
        <h2 className="text-3xl font-bold text-gray-500">Cuộc bầu cử hiện chưa mở</h2>
        <p className="text-gray-400">
          Trang này sẽ tự cập nhật khi Ban tổ chức bắt đầu phiên bầu cử (trong vài giây), hoặc bấm nút bên dưới.
        </p>
        <button
          onClick={handleRefresh}
          disabled={refreshing}
          className="inline-flex items-center gap-2 bg-white border border-gray-200 hover:border-[#38c8e6] text-gray-600 font-medium px-5 py-2.5 rounded-full transition-all disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${refreshing ? "animate-spin" : ""}`} />
          Kiểm tra ngay
        </button>
      </div>
    );
  }

  return (
    <div className="text-center space-y-8">
      <div className="flex items-center justify-center gap-3">
        <h2 className="text-4xl font-bold text-gray-700">BẦU CHỌN</h2>
        <button
          onClick={handleRefresh}
          disabled={refreshing}
          title="Làm mới"
          className="text-gray-400 hover:text-[#38c8e6] disabled:opacity-50"
        >
          <RefreshCw className={`w-5 h-5 ${refreshing ? "animate-spin" : ""}`} />
        </button>
      </div>

      {hasVoted && (
        <p className="text-green-600 font-medium">
          Bạn đã bỏ phiếu — cảm ơn bạn đã tham gia! Xem lại lựa chọn của bạn ở tab "Phiếu Của Tôi".
        </p>
      )}
      {error && <p className="text-red-500 text-sm max-w-md mx-auto">{error}</p>}

      <div className="flex flex-wrap justify-center gap-8 pt-6">
        {candidates.length === 0 && (
          <p className="text-gray-400">Ban tổ chức chưa thêm ứng viên nào.</p>
        )}
        {candidates.map((candidate) => (
          <div
            key={candidate.id}
            className="bg-white border border-gray-200 rounded-lg p-8 w-72 shadow-sm hover:shadow-md transition-all flex flex-col items-center"
          >
            <div className="w-36 h-36 text-[#38c8e6] border-4 border-[#38c8e6] rounded-full p-4 mb-6 flex items-center justify-center">
              <User className="w-full h-full" />
            </div>
            <h3 className="text-xl font-semibold text-gray-800 mb-6">{candidate.name}</h3>
            <button
              onClick={() => handleVote(candidate.id)}
              disabled={hasVoted || votingId !== null}
              className="w-full flex items-center justify-center gap-2 bg-[#38c8e6] hover:bg-cyan-600 disabled:bg-gray-400 text-white font-bold py-2.5 rounded-md transition-all text-sm uppercase tracking-wider"
            >
              {votingId === candidate.id ? (
                <>
                  <LoaderCircle className="w-4 h-4 animate-spin" /> Đang gửi...
                </>
              ) : hasVoted ? (
                "Đã bỏ phiếu"
              ) : (
                "CLICK HERE TO VOTE"
              )}
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
