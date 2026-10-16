import React from "react";

export default function ResultTab({
  walletAddress,
  candidates,
  electionActive,
  voterInfo,
  lastVoteReceipt,
}) {
  const totalVotes = candidates.reduce((sum, c) => sum + Number(c.votes || 0), 0);

  // Sắp xếp ứng viên theo số phiếu giảm dần
  const sortedCandidates = [...candidates].sort((a, b) => b.votes - a.votes);

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
        <div className="bg-[#38c8e6] text-white px-6 py-4 flex items-center justify-between">
          <span className="text-xl font-semibold">
            KẾT QUẢ KIỂM PHIẾU THỜI GIAN THỰC (ON-CHAIN)
          </span>
          <span className="text-sm bg-white/20 px-3 py-1 rounded-full font-medium">
            Tổng số phiếu: {totalVotes}
          </span>
        </div>

        <div className="p-8 space-y-6">
          <div className="flex flex-col sm:flex-row justify-between items-center text-sm text-gray-600 bg-gray-50 p-4 rounded-lg border border-gray-200 gap-2">
            <p className="font-mono">
              Ví đang kết nối:{" "}
              <span className="text-gray-800 font-semibold">
                {walletAddress || "Chưa kết nối ví"}
              </span>
            </p>
            <p>
              Trạng thái lá phiếu của bạn:{" "}
              {voterInfo?.hasVoted ? (
                <span className="text-green-600 font-bold">
                  Đã bầu cho Ứng viên #{voterInfo.votedCandidateId}
                </span>
              ) : (
                <span className="text-gray-500 font-medium">Chưa bỏ phiếu</span>
              )}
            </p>
          </div>

          {lastVoteReceipt && (
            <div className="bg-cyan-50 border border-cyan-200 rounded-lg p-4 text-xs font-mono space-y-1 text-cyan-900">
              <p className="font-sans font-bold text-sm text-cyan-800 mb-1">
                🔍 Biên nhận Mật mã học (Individual Verifiability):
              </p>
              <p>
                <b>Transaction Hash:</b> {lastVoteReceipt.txHash}
              </p>
              <p>
                <b>Block Number:</b> #{lastVoteReceipt.blockNumber} |{" "}
                <b>Gas Used:</b> {lastVoteReceipt.gasUsed} |{" "}
                <b>Thời gian:</b> {lastVoteReceipt.timestamp}
              </p>
            </div>
          )}

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b-2 border-gray-200 text-gray-600 text-sm font-semibold">
                  <th className="py-4 px-4">ID On-chain</th>
                  <th className="py-4 px-4">Họ Và Tên Ứng Cử Viên</th>
                  <th className="py-4 px-4">Số Phiếu Bầu</th>
                  <th className="py-4 px-4 w-1/3">Tỷ Lệ (%)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 text-gray-700 text-sm">
                {sortedCandidates.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="py-8 text-center text-gray-400">
                      Chưa có dữ liệu ứng cử viên trên Smart Contract.
                    </td>
                  </tr>
                ) : (
                  sortedCandidates.map((candidate, idx) => {
                    const pct =
                      totalVotes > 0
                        ? ((candidate.votes / totalVotes) * 100).toFixed(1)
                        : "0.0";
                    return (
                      <tr key={candidate.id} className="hover:bg-gray-50">
                        <td className="py-4 px-4 font-bold text-gray-800">
                          #{candidate.id}
                          {idx === 0 && candidate.votes > 0 && (
                            <span className="ml-2 text-xs bg-amber-100 text-amber-800 px-2 py-0.5 rounded-full">
                              Dẫn đầu
                            </span>
                          )}
                        </td>
                        <td className="py-4 px-4 font-semibold text-base text-gray-800">
                          {candidate.name}
                        </td>
                        <td className="py-4 px-4 font-bold text-lg text-[#38c8e6]">
                          {candidate.votes}
                        </td>
                        <td className="py-4 px-4">
                          <div className="flex items-center gap-3">
                            <div className="w-full bg-gray-200 rounded-full h-2.5 overflow-hidden">
                              <div
                                className="bg-[#38c8e6] h-2.5 rounded-full transition-all duration-500"
                                style={{ width: `${pct}%` }}
                              ></div>
                            </div>
                            <span className="text-xs font-semibold text-gray-600 w-12">
                              {pct}%
                            </span>
                          </div>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
