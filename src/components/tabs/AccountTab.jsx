import React from "react";
import { CircleCheckBig, CircleX } from "lucide-react";

// LƯU Ý: khác với bản trước (MetaMask), giờ bất kỳ ai đăng nhập được bằng
// CCCD+mã ĐỀU đã tự động được cấp quyền bầu cử ngay trong lúc đăng nhập
// (xem voter_api.py /login) — không còn trạng thái "đang chờ duyệt" hay
// "chưa được cấp quyền" để tra cứu nữa, nên tab này chỉ còn cần hiện thông
// tin cơ bản + trạng thái đã bầu hay chưa.
export default function AccountTab({ fullName, hasVoted }) {
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
