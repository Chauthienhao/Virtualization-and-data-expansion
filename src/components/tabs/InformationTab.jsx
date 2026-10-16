import React from "react";

export default function InformationTab({
  contractAddress,
  adminAddress,
  electionActive,
}) {
  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
      <div className="bg-[#38c8e6] text-white px-6 py-4 text-xl font-semibold">
        HƯỚNG DẪN SỬ DỤNG & THÔNG TIN HỢP ĐỒNG THÔNG MINH
      </div>
      <div className="p-8 text-gray-700 space-y-6 leading-relaxed">
        <h3 className="text-2xl font-bold text-gray-800">
          Chào mừng bạn đến với Hệ thống Bầu cử Điện tử Blockchain (BlockVote)
        </h3>

        {/* Thông tin On-chain trực tiếp */}
        <div className="bg-cyan-50 border border-cyan-200 rounded-lg p-4 text-sm space-y-2">
          <p>
            <span className="font-bold text-gray-800">Địa chỉ Smart Contract (Election.sol): </span>
            <span className="font-mono text-cyan-800">{contractAddress || "Chưa cấu hình"}</span>
          </p>
          <p>
            <span className="font-bold text-gray-800">Địa chỉ Ví Ban Tổ Chức (Admin): </span>
            <span className="font-mono text-cyan-800">{adminAddress || "Đang tải..."}</span>
          </p>
          <p>
            <span className="font-bold text-gray-800">Trạng thái Phiên Bầu Cử: </span>
            {electionActive ? (
              <span className="text-green-700 font-bold">Đang mở (Cử tri có thể bỏ phiếu)</span>
            ) : (
              <span className="text-amber-700 font-bold">Chưa mở hoặc đã kết thúc</span>
            )}
          </p>
        </div>

        <div className="space-y-3">
          <h4 className="text-lg font-bold text-gray-800">1. Xác thực & Cấp quyền Cử tri (Whitelisting)</h4>
          <ul className="list-disc pl-6 space-y-2 text-sm text-gray-600">
            <li>Cử tri cần cài đặt tiện ích ví <b>MetaMask</b> trên trình duyệt và kết nối vào mạng <b>Ganache (http://127.0.0.1:7545, Chain ID: 1337)</b>.</li>
            <li>Tại mục <b>Voter Registration</b>, cử tri kết nối ví MetaMask và kiểm tra xem địa chỉ ví của mình đã được Ban tổ chức phê duyệt (Whitelist) trên Smart Contract hay chưa.</li>
            <li>Việc cấp quyền cử tri chỉ được Admin thực hiện <b>trước khi</b> cuộc bầu cử chính thức bắt đầu.</li>
          </ul>
        </div>

        <div className="space-y-3 pt-2">
          <h4 className="text-lg font-bold text-gray-800">2. Quy trình bỏ phiếu & Tự kiểm chứng lá phiếu</h4>
          <ul className="list-disc pl-6 space-y-2 text-sm text-gray-600">
            <li><b>Bước 1 (Kết nối ví):</b> Nhấn nút <b>"Kết nối Ví MetaMask"</b> ở góc trên bên phải màn hình.</li>
            <li><b>Bước 2 (Bỏ phiếu):</b> Chuyển sang tab <b>Voting-Area</b>, chọn ứng cử viên tín nhiệm và nhấn nút <b>"BỎ PHIẾU"</b>. Cửa sổ MetaMask sẽ bật lên để bạn ký số xác nhận giao dịch.</li>
            <li><b>Bước 3 (Kiểm chứng độc lập):</b> Sau khi giao dịch được xác nhận vào khối, hệ thống trả về mã băm giao dịch (<b>Transaction Hash</b>) giúp cử tri tự đối chiếu lá phiếu và theo dõi kết quả kiểm phiếu thời gian thực tại tab <b>Result</b>.</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
