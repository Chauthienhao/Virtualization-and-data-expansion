import React from "react";
import { User } from "lucide-react";

export default function VotingAreaTab({ candidates, hasVoted, onVote }) {
  return (
    <div className="text-center space-y-8">
      <h2 className="text-4xl font-bold text-gray-700">BẦU CHỌN !!!</h2>
      <div className="flex flex-wrap justify-center gap-8 pt-6">
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
              onClick={() => onVote(candidate.id)}
              disabled={hasVoted}
              className="w-full bg-[#38c8e6] hover:bg-cyan-600 disabled:bg-gray-400 text-white font-bold py-2.5 rounded-md transition-all text-sm uppercase tracking-wider"
            >
              {hasVoted ? "Đã bỏ phiếu" : "CLICK HERE TO VOTE"}
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}