import React from "react";

export default function InformationTab() {
  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
      <div className="bg-[#38c8e6] text-white px-6 py-4 text-xl font-semibold">HƯỚNG DẪN SỬ DỤNG</div>
      <div className="p-8 text-gray-700 space-y-6 leading-relaxed">
        <h3 className="text-2xl font-bold text-gray-800">Chào mừng bạn đến với BẦU CỬ TRỰC TUYẾN</h3>
        <p>
          Hệ thống xác thực bằng số CCCD — bạn không cần cài đặt gì, không cần biết về ví điện tử
          hay blockchain. Mọi thứ liên quan tới công nghệ đều được hệ thống xử lý phía sau.
        </p>

        <div className="space-y-3">
          <h4 className="text-lg font-bold text-gray-800">1. Điều kiện tham gia</h4>
          <ul className="list-disc pl-6 space-y-2 text-sm text-gray-600">
            <li>Chỉ những CCCD đã được Ban tổ chức đăng ký trước mới đăng nhập được.</li>
            <li>Mỗi CCCD chỉ dùng được đúng <b>một lần</b>: sau khi đăng xuất, dù đã bầu hay chưa, không thể đăng nhập lại.</li>
          </ul>
        </div>

        <div className="space-y-3 pt-4">
          <h4 className="text-lg font-bold text-gray-800">2. Quy trình bầu chọn</h4>
          <ul className="list-disc pl-6 space-y-2 text-sm text-gray-600">
            <li><b>Bước 1:</b> Nhập số CCCD. Nếu hợp lệ, hệ thống hiện ngay một mã xác thực trên màn hình.</li>
            <li><b>Bước 2:</b> Nhập lại đúng mã đó để vào khu vực bỏ phiếu.</li>
            <li><b>Bước 3:</b> Chọn ứng viên và xác nhận. Mỗi người chỉ bầu được đúng một lần, không thể đổi lại sau khi đã gửi.</li>
            <li><b>Bước 4:</b> Vào tab "Phiếu Của Tôi" để xác nhận lại lựa chọn vừa bầu.</li>
            <li><b>Bước 5:</b> Đăng xuất khi đã xong. Sau khi đăng xuất, phiên này đóng vĩnh viễn.</li>
          </ul>
        </div>

        <div className="space-y-3 pt-4">
          <h4 className="text-lg font-bold text-gray-800">3. Một vài lưu ý</h4>
          <ul className="list-disc pl-6 space-y-2 text-sm text-gray-600">
            <li>Hệ thống chỉ hiện cho bạn xem <b>lựa chọn của chính bạn</b>, không hiện kết quả chung của cuộc bầu cử.</li>
            <li>Kết quả tổng chỉ được Ban tổ chức công bố sau khi cuộc bầu cử kết thúc.</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
