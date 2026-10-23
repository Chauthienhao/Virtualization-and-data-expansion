import React from "react";
import { CircleCheckBig, CircleX } from "lucide-react";

// LƯU Ý: khác với bản trước (MetaMask), giờ bất kỳ ai đăng nhập được bằng
// CCCD+mã ĐỀU đã tự động được cấp quyền bầu cử ngay trong lúc đăng nhập
// (xem voter_api.py /login) — không còn trạng thái "đang chờ duyệt" hay
// "chưa được cấp quyền" để tra cứu nữa, nên tab này chỉ còn cần hiện thông
// tin cơ bản + trạng thái đã bầu hay chưa.
//
// Địa chỉ ví (RÚT GỌN) và số dư chỉ hiển thị dạng chữ để XEM — không có ô
// nhập, và backend cũng không có API nào sửa được 2 giá trị này. Số dư đọc
// trực tiếp từ blockchain, tự cập nhật sau khi bầu (App.jsx gọi lại /me).
export default function AccountTab({ fullName, hasVoted, walletAddressShort, balanceEth, voteFee }) {
  return (
    <div className="max-w-xl mx-auto bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden mt-10">
      <div className="bg-[#38c8e6] text-white px-6 py-4 text-xl font-semibold">THÔNG TIN TÀI KHOẢN</div>
      <div className="p-8 space-y-6">
        {fullName && (
          <div>
            <p className="text-xs text-gray-500 mb-1">Họ và tên</p>
            <p className="text-gray-800 font-medium">{fullName}</p>
          </div>
        )}

        <div className="grid grid-cols-2 gap-6">
          <div>
            <p className="text-xs text-gray-500 mb-1">Địa chỉ ví</p>
            <p className="text-gray-800 font-mono">{walletAddressShort || "—"}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500 mb-1">Số dư</p>
            <p className="text-gray-800 font-medium tabular-nums">{balanceEth ? `${balanceEth} ETH` : "—"}</p>
          </div>
        </div>

        {voteFee && (
          <div className="rounded-lg p-4 border border-gray-200 bg-gray-50 space-y-1">
            <p className="text-xs text-gray-500">Phí gas đã trả khi bầu</p>
            <p className="text-gray-800 font-semibold tabular-nums">{voteFee.feeEth} ETH</p>
            <p className="text-sm text-gray-500 tabular-nums">
              {Number(voteFee.gasUsed).toLocaleString("vi-VN")} gas × {voteFee.gasPriceGwei} gwei
            </p>
            <p className="text-sm text-gray-500 tabular-nums">
              Số dư: {voteFee.balanceBeforeEth} → {voteFee.balanceAfterEth} ETH
            </p>
          </div>
        )}

        <div className={`rounded-lg p-4 border flex items-center gap-3 ${hasVoted ? "bg-green-50 border-green-200" : "bg-gray-50 border-gray-200"}`}>
          {hasVoted ? (
            <CircleCheckBig className="w-8 h-8 text-green-500 flex-shrink-0" />
          ) : (
            <CircleX className="w-8 h-8 text-gray-400 flex-shrink-0" />
          )}
          <div>
            <p className="font-semibold text-gray-800">Đã bỏ phiếu</p>
            <p className="text-sm text-gray-500">{hasVoted ? "Bạn đã bầu rồi" : "Chưa bầu"}</p>
          </div>
        </div>

        <p className="text-xs text-gray-400">
          Lưu ý: sau khi bấm "Đăng Xuất", tài khoản này sẽ khóa vĩnh viễn — không đăng nhập lại được nữa.
        </p>
      </div>
    </div>
  );
}
