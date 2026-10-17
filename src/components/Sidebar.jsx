import React from "react";
import { ClipboardList, SquareCheck, Vote, ChartColumn, LogOut } from "lucide-react";

export default function Sidebar({ activeTab, onSelectTab, onLogout }) {
  return (
    <aside className="w-64 bg-white shadow-md flex flex-col justify-between">
      <div>
        <div className="p-6 border-b border-gray-100">
          <h1 className="text-2xl font-bold text-[#38c8e6]">BlockVote</h1>
        </div>
        <nav className="mt-6 space-y-1">
          <button
            onClick={() => onSelectTab("info")}
            className={`w-full flex items-center px-6 py-4 text-left font-medium transition-all ${
              activeTab === "info" ? "bg-[#38c8e6] text-white shadow-sm" : "text-gray-600 hover:bg-gray-50"
            }`}
          >
            <ClipboardList className="w-5 h-5 mr-3" />
            Hướng Dẫn
          </button>
          <button
            onClick={() => onSelectTab("account")}
            className={`w-full flex items-center px-6 py-4 text-left font-medium transition-all ${
              activeTab === "account" ? "bg-[#38c8e6] text-white shadow-sm" : "text-gray-600 hover:bg-gray-50"
            }`}
          >
            <SquareCheck className="w-5 h-5 mr-3" />
            Tài Khoản
          </button>
          <button
            onClick={() => onSelectTab("voting")}
            className={`w-full flex items-center px-6 py-4 text-left font-medium transition-all ${
              activeTab === "voting" ? "bg-[#38c8e6] text-white shadow-sm" : "text-gray-600 hover:bg-gray-50"
            }`}
          >
            <Vote className="w-5 h-5 mr-3" />
            Bỏ Phiếu
          </button>
          <button
            onClick={() => onSelectTab("myvote")}
            className={`w-full flex items-center px-6 py-4 text-left font-medium transition-all ${
              activeTab === "myvote" ? "bg-[#38c8e6] text-white shadow-sm" : "text-gray-600 hover:bg-gray-50"
            }`}
          >
            <ChartColumn className="w-5 h-5 mr-3" />
            Phiếu Của Tôi
          </button>
        </nav>
      </div>
      <div className="p-4 border-t border-gray-100">
        <button
          onClick={onLogout}
          className="w-full flex items-center px-4 py-3 text-gray-600 hover:text-red-500 hover:bg-red-50 rounded-lg transition-all font-medium"
        >
          <LogOut className="w-5 h-5 mr-3" />
          Đăng Xuất
        </button>
      </div>
    </aside>
  );
}
