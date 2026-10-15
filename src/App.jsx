import React, { useState } from "react";
import Landing from "./components/Landing";
import Auth from "./components/Auth";
import Sidebar from "./components/Sidebar";
import InformationTab from "./components/tabs/InformationTab";
import VoterRegistrationTab from "./components/tabs/VoterRegistrationTab";
import VotingAreaTab from "./components/tabs/VotingAreaTab";
import ResultTab from "./components/tabs/ResultTab";

export default function App() {
  const [view, setView] = useState("landing");
  const [authMode, setAuthMode] = useState("login");
  const [activeTab, setActiveTab] = useState("info");
  const [walletAddress, setWalletAddress] = useState("0x0da4053142a6a5d1dbe82d8173574bf3c2c9e740");
  const [hasVoted, setHasVoted] = useState(false);

  const [candidates, setCandidates] = useState([
    { id: 1, name: "Yash", age: 34, party: "BJP", qualification: "B.E", votes: 0 },
    { id: 2, name: "Kunal", age: 43, party: "INC", qualification: "B.Sc", votes: 1 },
  ]);

  const handleVote = (candidateId) => {
    if (hasVoted) {
      alert("Bạn đã thực hiện bầu chọn rồi!");
      return;
    }
    setCandidates((prev) =>
      prev.map((c) => (c.id === candidateId ? { ...c, votes: c.votes + 1 } : c))
    );
    setHasVoted(true);
    alert("Bỏ phiếu thành công!");
  };

  // 1. Màn hình Landing
  if (view === "landing") {
    return (
      <Landing
        onNavigate={(mode) => {
          setAuthMode(mode);
          setView("auth");
        }}
      />
    );
  }

  // 2. Màn hình Đăng nhập / Đăng ký
  if (view === "auth") {
    return (
      <Auth
        initialMode={authMode}
        onSuccess={() => setView("dashboard")}
        onSwitchMode={(mode) => setAuthMode(mode)}
      />
    );
  }

  // 3. Màn hình Dashboard chính
  return (
    <div className="min-h-screen bg-gray-100 flex font-sans">
      {/* Sidebar bên trái chứa menu tabs và nút LogOut dưới cùng */}
      <Sidebar
        activeTab={activeTab}
        onSelectTab={(tab) => setActiveTab(tab)}
        onLogout={() => setView("landing")}
      />

      {/* Khu vực nội dung bên phải thay đổi theo từng tab */}
      <main className="flex-1 p-10 overflow-y-auto">
        {activeTab === "info" && <InformationTab />}
        {activeTab === "register" && (
          <VoterRegistrationTab
            onRegistered={(_, wallet) => {
              setWalletAddress(wallet);
              setActiveTab("voting");
            }}
          />
        )}
        {activeTab === "voting" && (
          <VotingAreaTab
            candidates={candidates}
            hasVoted={hasVoted}
            onVote={handleVote}
          />
        )}
        {activeTab === "result" && (
          <ResultTab walletAddress={walletAddress} candidates={candidates} />
        )}
      </main>
    </div>
  );
}