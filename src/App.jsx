import React, { useState, useCallback, useEffect } from "react";
import Landing from "./components/Landing";
import Auth from "./components/Auth";
import Sidebar from "./components/Sidebar";
import InformationTab from "./components/tabs/InformationTab";
import AccountTab from "./components/tabs/AccountTab";
import VotingAreaTab from "./components/tabs/VotingAreaTab";
import MyVoteTab from "./components/tabs/MyVoteTab";
import * as api from "./api";

const SESSION_STORAGE_KEY = "voter_session_token";
const POLL_INTERVAL_MS = 8000; // tự làm mới trạng thái bầu cử mỗi 8s

export default function App() {
  const [view, setView] = useState("landing");
  const [activeTab, setActiveTab] = useState("info");
  const [resuming, setResuming] = useState(true); // đang kiểm tra phiên cũ lúc tải trang

  // Không còn provider/signer/account (MetaMask) — chỉ còn session_token,
  // vì mọi thao tác ký giao dịch giờ xảy ra ở server (voter_api.py).
  const [sessionToken, setSessionToken] = useState(null);
  const [fullName, setFullName] = useState("");
  const [candidates, setCandidates] = useState([]); // chỉ {id, name}, KHÔNG có số phiếu
  const [electionActive, setElectionActive] = useState(false);
  const [hasVoted, setHasVoted] = useState(false);

  const [globalError, setGlobalError] = useState("");

  const loadMe = useCallback(async (token) => {
    const t = token || sessionToken;
    if (!t) return false;
    try {
      const data = await api.getMe(t);
      setFullName(data.fullName || "");
      setElectionActive(data.electionActive);
      setHasVoted(data.hasVoted);
      setCandidates(data.candidates);
      setGlobalError("");
      return true;
    } catch (err) {
      setGlobalError(err.message);
      return false;
    }
  }, [sessionToken]);

  // BUG #2 — F5/tải lại trang không còn đăng xuất người dùng: session_token
  // được lưu ở sessionStorage (không mất khi reload, chỉ mất khi đóng tab),
  // nên lúc App mount lại, ta thử khôi phục phiên bằng token đã lưu trước
  // khi cho hiển thị trang Landing/Auth.
  useEffect(() => {
    const saved = sessionStorage.getItem(SESSION_STORAGE_KEY);
    if (!saved) {
      setResuming(false);
      return;
    }
    (async () => {
      const ok = await loadMe(saved);
      if (ok) {
        setSessionToken(saved);
        setView("dashboard");
      } else {
        // Token cũ không còn hợp lệ ở server (đã đăng xuất/khóa) -> xóa, về Landing.
        sessionStorage.removeItem(SESSION_STORAGE_KEY);
        setGlobalError("");
      }
      setResuming(false);
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // BUG #1 — nếu Admin mở cuộc bầu cử SAU khi cử tri đã đăng nhập, trang
  // trước đây không có cách nào biết để tự cập nhật. Giờ poll định kỳ lại
  // /me để lấy electionActive mới nhất (kèm nút "Làm mới" thủ công trong
  // VotingAreaTab cho ai muốn cập nhật ngay, không cần chờ 8s).
  useEffect(() => {
    if (view !== "dashboard" || !sessionToken) return;
    const id = setInterval(() => {
      loadMe();
    }, POLL_INTERVAL_MS);
    return () => clearInterval(id);
  }, [view, sessionToken, loadMe]);

  const handleLoggedIn = async (token) => {
    sessionStorage.setItem(SESSION_STORAGE_KEY, token);
    setSessionToken(token);
    setView("dashboard");
    await loadMe(token);
  };

  const handleVote = async (candidateId) => {
    try {
      await api.castVote(sessionToken, candidateId);
      await loadMe();
    } catch (err) {
      throw new Error(err.message);
    }
  };

  // Đăng xuất là hành động KHÔNG THỂ HOÀN TÁC (khóa vĩnh viễn phiên này ở
  // server), nên xác nhận lại trước khi thực hiện.
  const handleLogout = async () => {
    if (!window.confirm("Đăng xuất sẽ khóa vĩnh viễn tài khoản này, không thể đăng nhập lại. Bạn chắc chắn chứ?")) {
      return;
    }
    try {
      await api.logout(sessionToken);
    } catch (err) {
      // Dù API lỗi, vẫn đưa người dùng về Landing — phiên phía client coi như kết thúc.
    }
    sessionStorage.removeItem(SESSION_STORAGE_KEY);
    setSessionToken(null);
    setFullName("");
    setCandidates([]);
    setHasVoted(false);
    setView("landing");
    setActiveTab("info");
  };

  // Đang kiểm tra phiên cũ (chỉ xảy ra trong khoảnh khắc đầu khi tải trang)
  if (resuming) {
    return (
      <div className="min-h-screen flex items-center justify-center text-gray-400 font-sans">
        Đang tải...
      </div>
    );
  }

  if (view === "landing") {
    return <Landing onNavigate={() => setView("auth")} />;
  }

  if (view === "auth") {
    return <Auth onLoggedIn={handleLoggedIn} />;
  }

  return (
    <div className="min-h-screen bg-gray-100 flex font-sans">
      <Sidebar activeTab={activeTab} onSelectTab={setActiveTab} onLogout={handleLogout} />

      <main className="flex-1 p-10 overflow-y-auto">
        {globalError && (
          <div className="max-w-2xl mx-auto mb-6 bg-red-50 text-red-600 text-sm rounded-lg p-4">
            {globalError}
          </div>
        )}

        {activeTab === "info" && <InformationTab />}

        {activeTab === "account" && <AccountTab fullName={fullName} hasVoted={hasVoted} />}

        {activeTab === "voting" && (
          <VotingAreaTab
            candidates={candidates}
            hasVoted={hasVoted}
            electionActive={electionActive}
            onVote={handleVote}
            onRefresh={() => loadMe()}
          />
        )}

        {activeTab === "myvote" && <MyVoteTab sessionToken={sessionToken} />}
      </main>
    </div>
  );
}
