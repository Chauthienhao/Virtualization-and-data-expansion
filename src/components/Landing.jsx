import React from "react";

export default function Landing({ onNavigate, onAdminPortal }) {
  return (
    <div className="min-h-screen bg-[#38c8e6] text-white flex flex-col justify-between relative overflow-hidden font-sans">
      <header className="p-6 text-2xl font-semibold">BẦU CỬ TRỰC TUYẾN</header>
      <main className="flex-1 flex flex-col md:flex-row items-center justify-around px-8 z-10">
        <div className="w-full md:w-1/2 flex justify-center mb-8 md:mb-0">
          <div className="relative w-80 h-80 flex items-center justify-center">
            <img
              src="https://illustrations.popsy.co/cyan/surveillance.svg"
              alt="Voting Illustration"
              className="w-full object-contain drop-shadow-xl"
            />
          </div>
        </div>
        <div className="w-full md:w-1/2 text-center md:text-left flex flex-col items-center md:items-start space-y-6">
          <h1 className="text-5xl md:text-6xl font-bold tracking-wider">BLOCK-VOTE</h1>
          <p className="text-xl tracking-wide font-light text-cyan-100">
            HỆ THỐNG BẦU CỬ PHI TẬP TRUNG TRÊN BLOCKCHAIN
          </p>
          <div className="flex flex-col sm:flex-row gap-4 pt-4 w-full max-w-lg">
            <button
              onClick={() => onNavigate("login")}
              className="flex-1 border-2 border-white/80 bg-white/20 hover:bg-white hover:text-[#38c8e6] text-white py-3 px-6 rounded-full font-bold transition-all shadow-md"
            >
              CỬ TRI ĐĂNG NHẬP / BỎ PHIẾU
            </button>
            <button
              onClick={onAdminPortal}
              className="flex-1 border-2 border-white/80 bg-white/20 hover:bg-white hover:text-[#38c8e6] text-white py-3 px-6 rounded-full font-bold transition-all shadow-md"
            >
              CỔNG QUẢN TRỊ VIÊN (ADMIN)
            </button>
          </div>
        </div>
      </main>
      <div className="w-full h-32 bg-white transform -skew-y-3 origin-bottom-right translate-y-12"></div>
    </div>
  );
}
