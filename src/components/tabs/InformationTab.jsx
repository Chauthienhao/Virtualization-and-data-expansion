import React from "react";

export default function InformationTab() {
  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
      <div className="bg-[#38c8e6] text-white px-6 py-4 text-xl font-semibold">HƯỚNG DẪN SỬ DỤNG</div>
      <div className="p-8 text-gray-700 space-y-6 leading-relaxed">
        <h3 className="text-2xl font-bold text-gray-800">Chào mừng bạn đến với BẦU CỬ TRỰC TUYẾN</h3>
        <p>Đây là một số hướng dẫn cho người dùng :</p>
        <div className="space-y-3">
          <h4 className="text-lg font-bold text-gray-800">1. Đăng ký cử tri</h4>
          <ul className="list-disc pl-6 space-y-2 text-sm text-gray-600">
            <li>Để bầu chọn, người dùng cần đăng ký trước.</li>
            <li>Người bỏ phiếu chỉ có thể đăng ký trong giai đoạn đăng ký.</li>
            <li>Để đăng ký, người dùng cần nhập số thẻ căn cước công dân và địa chỉ tài khoản.</li>
            <li>Ở giai đoạn đầu tiên, độ tuổi của người dùng sẽ được kiểm tra (18+).</li>
            <li>Giai đoạn thứ hai là xác minh OTP.</li>
          </ul>
        </div>
        <div className="space-y-3 pt-4">
          <h4 className="text-lg font-bold text-gray-800">2. Quy trình bầu chọn</h4>
          <ul className="list-disc pl-6 space-y-2 text-sm text-gray-600">
            <li>Toàn bộ quy trình bầu chọn được chia thành ba giai đoạn do quản trị viên quản lý.</li>
            <li><b>Giai đoạn Đăng ký:</b> Người dùng đăng ký tham gia bầu chọn.</li>
            <li><b>Giai đoạn Bầu chọn:</b> Người dùng bỏ phiếu bằng cách nhấn vào nút "BẦU CHỌN".</li>
            <li><b>Giai đoạn Kết quả:</b> Kết quả bầu chọn được hiển thị tại phần "Kết quả".</li>
          </ul>
        </div>
      </div>
    </div>
  );
}