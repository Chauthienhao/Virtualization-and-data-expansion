import React from "react";
import { User, CheckCircle2, AlertCircle } from "lucide-react";

export default function VotingAreaTab({
  candidates,
  electionActive,
  voterInfo,
  walletAddress,
  votingLoading,
  lastVoteReceipt,
  onVote,
  onConnectWallet,
}) {
  const canVote =
    Boolean(walletAddress) &&
    electionActive &&
    voterInfo.isAuthorized &&
    !voterInfo.hasVoted &&
    !votingLoading;

  return (
    <div className="space-y-8">
      <div className="text-center space-y-2">
        <h2 className="text-4xl font-bold text-gray-700">KHU VỰC BỎ PHIẾU</h2>
        <p className="text-sm text-gray-500">
          Mỗi cử tri hợp lệ chỉ được bỏ phiếu duy nhất 1 lần. Giao dịch được ký số qua MetaMask và ghi bất biến lên Blockchain.
        </p>
      </div>

      {/* Thông báo trạng thái điều kiện bỏ phiếu */}
      {!walletAddress && (
        <div className="max-w-2xl mx-auto bg-amber-50 border border-amber-200 text-amber-800 p-4 rounded-lg flex items-center justify-between">
          <div className="flex items-center gap-3 text-sm">
            <AlertCircle className="w-5 h-5 shrink-0" />
            <span>Bạn cần kết nối ví MetaMask trước khi thực hiện bỏ phiếu.</span>
          </div>
          <button
            onClick={onConnectWallet}
            className="px-4 py-1.5 bg-amber-500 hover:bg-amber-600 text-white text-xs font-bold rounded-md"
          >
            Kết nối MetaMask
          </button>
        </div>
      )}

      {walletAddress && !electionActive && (
        <div className="max-w-2xl mx-auto bg-gray-100 border border-gray-300 text-gray-700 p-4 rounded-lg text-center text-sm font-medium">
          ⏸️ Phiên bầu cử hiện <b>CHƯA MỞ</b> hoặc <b>ĐÃ KẾT THÚC</b>. Vui lòng chờ Ban tổ chức mở hòm phiếu.
        </div>
      )}

      {walletAddress && electionActive && !voterInfo.isAuthorized && (
        <div className="max-w-2xl mx-auto bg-red-50 border border-red-200 text-red-700 p-4 rounded-lg text-center text-sm">
          ❌ Địa chỉ ví <span className="font-mono font-bold">{walletAddress}</span> chưa có trong danh sách Whitelist. Hãy cấp quyền cho ví này trên Cổng Admin trước!
        </div>
      )}

      {voterInfo.hasVoted && (
        <div className="max-w-2xl mx-auto bg-green-50 border border-green-200 text-green-800 p-4 rounded-lg space-y-2 text-sm">
          <div className="flex items-center gap-2 font-bold">
            <CheckCircle2 className="w-5 h-5 text-green-600" />
            <span>
              Bạn đã hoàn thành bỏ phiếu cho Ứng cử viên số #{voterInfo.votedCandidateId}!
            </span>
          </div>
          {lastVoteReceipt && (
            <div className="text-xs font-mono bg-white p-3 rounded border border-green-200 space-y-1 text-gray-700">
              <p>
                <b>Mã giao dịch (Transaction Hash):</b> {lastVoteReceipt.txHash}
              </p>
              <p>
                <b>Khối xác nhận (Block):</b> #{lastVoteReceipt.blockNumber} |{" "}
                <b>Gas tiêu thụ:</b> {lastVoteReceipt.gasUsed}
              </p>
            </div>
          )}
        </div>
      )}

      {/* Danh sách ứng cử viên đọc từ Smart Contract */}
      {candidates.length === 0 ? (
        <div className="bg-white rounded-lg p-12 text-center text-gray-500 border border-gray-200">
          Chưa có ứng cử viên nào được ghi trên Smart Contract. Hãy thêm ứng viên từ Cổng Quản Trị (Admin Portal).
        </div>
      ) : (
        <div className="flex flex-wrap justify-center gap-8 pt-2">
          {candidates.map((candidate) => {
            const isVotedForThis =
              voterInfo.hasVoted && voterInfo.votedCandidateId === candidate.id;
            return (
              <div
                key={candidate.id}
                className={`bg-white border-2 rounded-lg p-8 w-72 shadow-sm hover:shadow-md transition-all flex flex-col items-center ${
                  isVotedForThis ? "border-green-500 ring-2 ring-green-100" : "border-gray-200"
                }`}
              >
                <span className="text-xs font-bold px-3 py-1 rounded-full bg-cyan-50 text-[#38c8e6] mb-4">
                  Mã Ứng Viên #{candidate.id}
                </span>

                <div className="w-32 h-32 text-[#38c8e6] border-4 border-[#38c8e6] rounded-full p-4 mb-4 flex items-center justify-center">
                  <User className="w-full h-full" />
                </div>

                <h3 className="text-xl font-bold text-gray-800 mb-2 text-center">
                  {candidate.name}
                </h3>

                <p className="text-sm text-gray-500 mb-6">
                  Số phiếu hiện tại:{" "}
                  <span className="font-bold text-[#38c8e6]">{candidate.votes}</span>
                </p>

                <button
                  onClick={() => onVote(candidate.id)}
                  disabled={!canVote}
                  className={`w-full font-bold py-2.5 px-4 rounded-md transition-all text-sm uppercase tracking-wider ${
                    isVotedForThis
                      ? "bg-green-600 text-white cursor-default"
                      : "bg-[#38c8e6] hover:bg-cyan-600 disabled:bg-gray-300 disabled:text-gray-500 text-white"
                  }`}
                >
                  {votingLoading
                    ? "Đang ký giao dịch..."
                    : isVotedForThis
                    ? "✓ Đã bầu ứng viên này"
                    : voterInfo.hasVoted
                    ? "Đã bỏ phiếu"
                    : "BỎ PHIẾU (VOTE)"}
                </button>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
