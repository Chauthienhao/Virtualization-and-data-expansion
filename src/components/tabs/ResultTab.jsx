import React from "react";

export default function ResultTab({ walletAddress, candidates }) {
  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
      <div className="bg-[#38c8e6] text-white px-6 py-4 text-xl font-semibold">Results</div>
      <div className="p-8 space-y-6">
        <p className="text-center text-sm text-gray-500 font-mono">
          Your account: <span className="text-gray-700 font-semibold">{walletAddress}</span>
        </p>
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-gray-200 text-gray-600 text-sm font-semibold">
                <th className="py-4 px-4">#</th>
                <th className="py-4 px-4">Họ Và Tên</th>
                <th className="py-4 px-4">Tuổi</th>
                <th className="py-4 px-4">Đảng</th>
                <th className="py-4 px-4">Trình độ</th>
                <th className="py-4 px-4">Số phiếu</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 text-gray-700 text-sm">
              {candidates.map((candidate) => (
                <tr key={candidate.id} className="hover:bg-gray-50">
                  <td className="py-4 px-4 font-bold">{candidate.id}</td>
                  <td className="py-4 px-4 font-medium">{candidate.name}</td>
                  <td className="py-4 px-4">{candidate.age}</td>
                  <td className="py-4 px-4">{candidate.party}</td>
                  <td className="py-4 px-4">{candidate.qualification}</td>
                  <td className="py-4 px-4 font-bold text-[#38c8e6]">{candidate.votes}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}