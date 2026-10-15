import React, { useState } from "react";

export default function VoterRegistrationTab({ onRegistered }) {
  const [aadhar, setAadhar] = useState("");
  const [wallet, setWallet] = useState("0x0da4053142a6a5d1dbe82d8173574bf3c2c9e740");

  const handleSubmit = (e) => {
    e.preventDefault();
    onRegistered(aadhar, wallet);
    alert("Đăng ký cử tri thành công!");
  };

  return (
    <div className="max-w-2xl mx-auto bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden mt-10">
      <div className="bg-[#38c8e6] text-white px-6 py-4 text-xl font-semibold">ĐĂNG KÝ CỬ TRI</div>
      <form onSubmit={handleSubmit} className="p-8 space-y-8">
        <div>
          <input
            type="text"
            placeholder="Số CCCD"
            value={aadhar}
            onChange={(e) => setAadhar(e.target.value)}
            required
            className="w-full border-b-2 border-gray-300 py-2 outline-none focus:border-[#38c8e6] text-gray-700 transition-colors"
          />
        </div>
        <div>
          <input
            type="text"
            placeholder="Account Address (Metamask Wallet)"
            value={wallet}
            onChange={(e) => setWallet(e.target.value)}
            required
            className="w-full border-b-2 border-gray-300 py-2 outline-none focus:border-[#38c8e6] text-gray-700 transition-colors font-mono text-sm"
          />
        </div>
        <button
          type="submit"
          className="w-full bg-[#38c8e6] hover:bg-cyan-600 text-white font-bold py-3 rounded-md transition-all shadow-sm"
        >
          ĐĂNG KÝ
        </button>
      </form>
    </div>
  );
}