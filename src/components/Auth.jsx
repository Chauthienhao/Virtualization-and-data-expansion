import React, { useState } from "react";
import { User, Lock, LoaderCircle, CircleAlert } from "lucide-react";
import * as api from "../api";

// Luồng đăng nhập 2 bước, KHÔNG dùng MetaMask: cử tri không hề biết (và
// không cần biết) có một ví blockchain đứng sau hệ thống này — xem
// voter_accounts.py/voter_api.py để biết ví được sinh và ký hộ ra sao.
export default function Auth({ onLoggedIn }) {
  const [step, setStep] = useState("cccd"); // "cccd" | "code"
  const [cccd, setCccd] = useState("");
  const [code, setCode] = useState("");
  const [displayedCode, setDisplayedCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmitCccd = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await api.login(cccd.trim());
      setDisplayedCode(res.code);
      setStep("code");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmitCode = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await api.verifyCode(cccd.trim(), code.trim());
      onLoggedIn(res.session_token);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-white flex flex-col md:flex-row font-sans">
      <div className="w-full md:w-1/2 bg-[#38c8e6] text-white p-12 flex flex-col justify-center items-center text-center relative rounded-b-[100px] md:rounded-b-none md:rounded-r-[250px]">
        <div className="max-w-md space-y-4 z-10">
          <h2 className="text-3xl font-bold">Xác thực cử tri</h2>
          <p className="text-cyan-50">
            Nhập đúng số CCCD đã được Ban tổ chức đăng ký trước. Hệ thống sẽ cấp một mã xác
            thực ngay trên màn hình — nhập lại đúng mã đó ở bước tiếp theo để vào khu vực bỏ phiếu.
          </p>
        </div>
      </div>

      <div className="w-full md:w-1/2 flex items-center justify-center p-8 bg-white">
        <div className="w-full max-w-md">
          {step === "cccd" && (
            <form onSubmit={handleSubmitCccd} className="space-y-6 text-center">
              <h2 className="text-4xl font-bold text-gray-800">Nhập Số CCCD</h2>
              <div className="relative">
                <User className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400 w-5 h-5" />
                <input
                  type="text"
                  value={cccd}
                  onChange={(e) => setCccd(e.target.value)}
                  placeholder="Số căn cước công dân"
                  className="w-full pl-12 pr-4 py-3 border border-gray-200 rounded-full focus:outline-none focus:border-[#38c8e6]"
                  required
                />
              </div>
              {error && (
                <div className="flex items-start gap-2 bg-red-50 text-red-600 text-sm rounded-lg p-4 text-left">
                  <CircleAlert className="w-5 h-5 flex-shrink-0 mt-0.5" />
                  <span>{error}</span>
                </div>
              )}
              <button
                type="submit"
                disabled={loading}
                className="w-full flex items-center justify-center gap-2 bg-[#38c8e6] hover:bg-cyan-600 disabled:bg-gray-300 text-white font-bold px-8 py-3.5 rounded-full transition-all shadow-md"
              >
                {loading ? (
                  <>
                    <LoaderCircle className="w-5 h-5 animate-spin" /> Đang kiểm tra...
                  </>
                ) : (
                  "TIẾP TỤC"
                )}
              </button>
            </form>
          )}

          {step === "code" && (
            <form onSubmit={handleSubmitCode} className="space-y-6 text-center">
              <h2 className="text-4xl font-bold text-gray-800">Nhập Mã Xác Thực</h2>
              <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
                <p className="text-xs text-gray-500 mb-1">Mã của bạn (chỉ hiện một lần)</p>
                <p className="font-mono text-2xl tracking-[0.3em] text-gray-800">{displayedCode}</p>
              </div>
              <div className="relative">
                <Lock className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400 w-5 h-5" />
                <input
                  type="text"
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                  placeholder="Nhập lại mã ở trên"
                  className="w-full pl-12 pr-4 py-3 border border-gray-200 rounded-full focus:outline-none focus:border-[#38c8e6] text-center tracking-[0.3em]"
                  required
                />
              </div>
              {error && (
                <div className="flex items-start gap-2 bg-red-50 text-red-600 text-sm rounded-lg p-4 text-left">
                  <CircleAlert className="w-5 h-5 flex-shrink-0 mt-0.5" />
                  <span>{error}</span>
                </div>
              )}
              <button
                type="submit"
                disabled={loading}
                className="w-full flex items-center justify-center gap-2 bg-[#38c8e6] hover:bg-cyan-600 disabled:bg-gray-300 text-white font-bold px-8 py-3.5 rounded-full transition-all shadow-md"
              >
                {loading ? (
                  <>
                    <LoaderCircle className="w-5 h-5 animate-spin" /> Đang xác thực...
                  </>
                ) : (
                  "XÁC NHẬN"
                )}
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
