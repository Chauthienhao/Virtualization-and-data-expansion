import React from "react";
import { ClipboardList, CheckSquare, Vote, BarChart3, LogOut } from "lucide-react";

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
            Information
          </button>
          <button
            onClick={() => onSelectTab("register")}
            className={`w-full flex items-center px-6 py-4 text-left font-medium transition-all ${
              activeTab === "register" ? "bg-[#38c8e6] text-white shadow-sm" : "text-gray-600 hover:bg-gray-50"
            }`}
          >
            <CheckSquare className="w-5 h-5 mr-3" />
            Voter Registration
          </button>
          <button
            onClick={() => onSelectTab("voting")}
            className={`w-full flex items-center px-6 py-4 text-left font-medium transition-all ${
              activeTab === "voting" ? "bg-[#38c8e6] text-white shadow-sm" : "text-gray-600 hover:bg-gray-50"
            }`}
          >
            <Vote className="w-5 h-5 mr-3" />
            Voting-Area
          </button>
          <button
            onClick={() => onSelectTab("result")}
            className={`w-full flex items-center px-6 py-4 text-left font-medium transition-all ${
              activeTab === "result" ? "bg-[#38c8e6] text-white shadow-sm" : "text-gray-600 hover:bg-gray-50"
            }`}
          >
            <BarChart3 className="w-5 h-5 mr-3" />
            Result
          </button>
        </nav>
      </div>
      <div className="p-4 border-t border-gray-100">
        <button
          onClick={onLogout}
          className="w-full flex items-center px-4 py-3 text-gray-600 hover:text-red-500 hover:bg-red-50 rounded-lg transition-all font-medium"
        >
          <LogOut className="w-5 h-5 mr-3" />
          LogOut
        </button>
      </div>
    </aside>
  );
}