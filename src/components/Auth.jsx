import React, { useState } from "react";
import { User, Mail, Lock, Wallet, AlertCircle, CheckCircle2 } from "lucide-react";

const USERS_STORAGE_KEY = "blockvote_registered_users";

function getStoredUsers() {
  try {
    const raw = localStorage.getItem(USERS_STORAGE_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch (_) {
    return [];
  }
}

function saveStoredUsers(users) {
  localStorage.setItem(USERS_STORAGE_KEY, JSON.stringify(users));
}

export default function Auth({
  initialMode,
  walletAddress,
  onConnectWallet,
  onSuccess,
  onSwitchMode,
}) {
  const [mode, setMode] = useState(initialMode || "login");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [errorMsg, setErrorMsg] = useState("");
  const [infoMsg, setInfoMsg] = useState("");

  const switchAuthMode = (nextMode) => {
    setMode(nextMode);
    setErrorMsg("");
    setInfoMsg("");
    if (onSwitchMode) onSwitchMode(nextMode);
  };

  // Xử lý Đăng ký / Đăng nhập bằng Email + Mật khẩu + Ràng buộc chặt 1 Ví MetaMask
  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorMsg("");
    setInfoMsg("");

    const normalizedEmail = email.trim().toLowerCase();
    if (!normalizedEmail || !password) {
      setErrorMsg("Vui lòng nhập đầy đủ Email và Mật khẩu.");
      return;
    }

    // Đảm bảo đã kết nối ví MetaMask để đối chiếu định danh 1-1
    let currentWallet = walletAddress;
    if (!currentWallet) {
      currentWallet = await onConnectWallet();
      if (!currentWallet) {
        setErrorMsg("Bắt buộc phải kết nối ví MetaMask để định danh tài khoản cử tri!");
        return;
      }
    }

    const users = getStoredUsers();

    if (mode === "signup") {
      if (!name.trim()) {
        setErrorMsg("Vui lòng nhập họ và tên cử tri.");
        return;
      }
      if (password.length < 4) {
        setErrorMsg("Mật khẩu phải có ít nhất 4 ký tự.");
        return;
      }
      if (password !== confirmPassword) {
        setErrorMsg("Mật khẩu xác nhận không khớp!");
        return;
      }

      // 1. Kiểm tra trùng Email
      const emailExists = users.find((u) => u.email.toLowerCase() === normalizedEmail);
      if (emailExists) {
        setErrorMsg("Email này đã được đăng ký! Vui lòng chuyển sang Đăng nhập.");
        return;
      }

      // 2. Kiểm tra trùng Ví MetaMask (Chống 1 ví đăng ký nhiều tài khoản)
      const walletExists = users.find(
        (u) => u.walletAddress.toLowerCase() === currentWallet.toLowerCase()
      );
      if (walletExists) {
        setErrorMsg(
          `Địa chỉ ví ${currentWallet.slice(0, 8)}... đã được liên kết cố định với tài khoản (${walletExists.email}). Mỗi ví chỉ được gắn với duy nhất 1 tài khoản!`
        );
        return;
      }

      const newUser = {
        name: name.trim(),
        email: normalizedEmail,
        password,
        walletAddress: currentWallet,
        createdAt: new Date().toLocaleString("vi-VN"),
      };

      users.push(newUser);
      saveStoredUsers(users);
      onSuccess(newUser);
      return;
    }

    // CHẾ ĐỘ ĐĂNG NHẬP (LOGIN)
    const foundUser = users.find((u) => u.email.toLowerCase() === normalizedEmail);
    if (!foundUser) {
      setErrorMsg("Tài khoản Email này chưa tồn tại! Vui lòng bấm ĐĂNG KÝ trước.");
      return;
    }

    if (foundUser.password !== password) {
      setErrorMsg("Mật khẩu không chính xác!");
      return;
    }

    // KIỂM TRA CHẶT 1 TÀI KHOẢN - 1 VÍ METAMASK (Chống đăng nhập ví thứ 2 cho cùng 1 tài khoản)
    if (foundUser.walletAddress.toLowerCase() !== currentWallet.toLowerCase()) {
      setErrorMsg(
        `🚫 Lỗi bảo mật: Tài khoản (${foundUser.email}) đã được khóa cố định với ví ${foundUser.walletAddress}, nhưng MetaMask hiện tại đang mở ví ${currentWallet}. Không được phép dùng 2 ví cho cùng 1 tài khoản! Hãy đổi lại đúng ví trên MetaMask.`
      );
      return;
    }

    onSuccess(foundUser);
  };

  // Đăng nhập nhanh bằng Ví MetaMask (chỉ vào được nếu ví đó đã đăng ký tài khoản)
  const handleMetaMaskQuickLogin = async () => {
    setErrorMsg("");
    setInfoMsg("");
    const acc = await onConnectWallet();
    if (!acc) return;

    const users = getStoredUsers();
    const boundUser = users.find(
      (u) => u.walletAddress.toLowerCase() === acc.toLowerCase()
    );

    if (boundUser) {
      onSuccess(boundUser);
    } else {
      switchAuthMode("signup");
      setInfoMsg(
        `Ví ${acc.slice(0, 8)}... chưa có tài khoản. Vui lòng điền Họ tên, Email và Mật khẩu bên dưới để tạo tài khoản gắn với ví này.`
      );
    }
  };

  return (
    <div className="min-h-screen bg-white flex flex-col md:flex-row font-sans">
      <div className="w-full md:w-1/2 bg-[#38c8e6] text-white p-12 flex flex-col justify-center items-center text-center relative rounded-b-[100px] md:rounded-b-none md:rounded-r-[250px]">
        <div className="max-w-md space-y-4 z-10">
          <h2 className="text-3xl font-bold">
            {mode === "login" ? "Cử tri mới?" : "Đã có tài khoản?"}
          </h2>
          <p className="text-cyan-50">
            {mode === "login"
              ? "Mỗi cử tri cần đăng ký một tài khoản gắn cố định 1-1 với địa chỉ ví MetaMask của mình trước khi tham gia bỏ phiếu."
              : "Nếu bạn đã đăng ký tài khoản và liên kết ví MetaMask, hãy đăng nhập ngay!"}
          </p>
          <button
            type="button"
            onClick={() => switchAuthMode(mode === "login" ? "signup" : "login")}
            className="mt-4 border-2 border-white text-white hover:bg-white hover:text-[#38c8e6] px-8 py-2.5 rounded-full font-semibold transition-all"
          >
            {mode === "login" ? "ĐĂNG KÝ TÀI KHOẢN" : "ĐĂNG NHẬP"}
          </button>
          <div className="pt-8 flex justify-center">
            <img
              src="https://illustrations.popsy.co/white/surveillance.svg"
              alt="Illustration"
              className="w-64 h-64 object-contain"
            />
          </div>
        </div>
      </div>

      <div className="w-full md:w-1/2 flex items-center justify-center p-8 bg-white">
        <div className="w-full max-w-md space-y-5">
          <h2 className="text-3xl font-bold text-gray-800 text-center">
            {mode === "login" ? "Đăng nhập Cử tri" : "Đăng ký Tài khoản & Gắn Ví"}
          </h2>

          {/* Hiển thị ví MetaMask đang kết nối */}
          <div className="bg-amber-50 border border-amber-200 rounded-xl p-3.5 text-xs space-y-2">
            <div className="flex items-center justify-between">
              <span className="font-bold text-amber-900 flex items-center gap-1.5">
                <Wallet className="w-4 h-4 text-amber-600" />
                Ví MetaMask hiện tại:
              </span>
              <button
                type="button"
                onClick={onConnectWallet}
                className="text-amber-700 hover:underline font-semibold"
              >
                {walletAddress ? "Đổi / Kiểm tra lại ví" : "Kết nối MetaMask"}
              </button>
            </div>
            <p className="font-mono text-gray-700 break-all bg-white px-2.5 py-1.5 rounded border border-amber-100">
              {walletAddress || "Chưa kết nối ví MetaMask"}
            </p>
            <p className="text-[11px] text-amber-800">
              * Quy định bảo mật: Mỗi tài khoản chỉ được liên kết cố định với <b>duy nhất 1 ví MetaMask</b>.
            </p>
          </div>

          {errorMsg && (
            <div className="bg-red-50 border-l-4 border-red-500 text-red-700 p-3 rounded text-xs flex items-start gap-2">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{errorMsg}</span>
            </div>
          )}

          {infoMsg && (
            <div className="bg-cyan-50 border-l-4 border-[#38c8e6] text-cyan-900 p-3 rounded text-xs flex items-start gap-2">
              <CheckCircle2 className="w-4 h-4 shrink-0 mt-0.5 text-[#38c8e6]" />
              <span>{infoMsg}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {mode === "signup" && (
              <div className="flex items-center bg-gray-100 rounded-full px-4 py-3">
                <User className="text-gray-400 w-5 h-5 mr-3" />
                <input
                  type="text"
                  placeholder="Họ và tên cử tri"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required
                  className="bg-transparent w-full outline-none text-gray-700"
                />
              </div>
            )}

            <div className="flex items-center bg-gray-100 rounded-full px-4 py-3">
              <Mail className="text-gray-400 w-5 h-5 mr-3" />
              <input
                type="email"
                placeholder="Địa chỉ Email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="bg-transparent w-full outline-none text-gray-700"
              />
            </div>

            <div className="flex items-center bg-gray-100 rounded-full px-4 py-3">
              <Lock className="text-gray-400 w-5 h-5 mr-3" />
              <input
                type="password"
                placeholder="Mật khẩu"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="bg-transparent w-full outline-none text-gray-700"
              />
            </div>

            {mode === "signup" && (
              <div className="flex items-center bg-gray-100 rounded-full px-4 py-3">
                <Lock className="text-gray-400 w-5 h-5 mr-3" />
                <input
                  type="password"
                  placeholder="Xác nhận mật khẩu"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  required
                  className="bg-transparent w-full outline-none text-gray-700"
                />
              </div>
            )}

            <div className="text-center pt-2 space-y-3">
              <button
                type="submit"
                className="w-full bg-[#38c8e6] text-white font-bold py-3 rounded-full hover:bg-cyan-600 transition-all shadow-md"
              >
                {mode === "login"
                  ? "ĐĂNG NHẬP VÀO HỆ THỐNG"
                  : "HOÀN TẤT ĐĂNG KÝ & KHÓA VÍ"}
              </button>

              {mode === "login" && (
                <button
                  type="button"
                  onClick={handleMetaMaskQuickLogin}
                  className="w-full flex items-center justify-center gap-2 bg-amber-500 hover:bg-amber-600 text-white font-bold py-2.5 px-6 rounded-full transition-all shadow-sm text-sm"
                >
                  <Wallet className="w-4 h-4" />
                  Đăng nhập nhanh bằng Ví MetaMask đã đăng ký
                </button>
              )}
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
