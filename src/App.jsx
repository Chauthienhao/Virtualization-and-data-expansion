import React, { useState, useEffect, useCallback } from "react";
import Landing from "./components/Landing";
import Auth from "./components/Auth";
import Sidebar from "./components/Sidebar";
import InformationTab from "./components/tabs/InformationTab";
import VoterRegistrationTab from "./components/tabs/VoterRegistrationTab";
import VotingAreaTab from "./components/tabs/VotingAreaTab";
import ResultTab from "./components/tabs/ResultTab";
import {
  DEFAULT_CONTRACT_ADDRESS,
  connectMetaMask,
  fetchElectionState,
  submitVoteOnChain,
  parseBlockchainError,
  isValidAddress,
} from "./blockchain";

const SESSION_USER_KEY = "blockvote_current_session_user";

export default function App() {
  const [view, setView] = useState("landing");
  const [authMode, setAuthMode] = useState("login");
  const [activeTab, setActiveTab] = useState("info");

  // Tài khoản cử tri đang đăng nhập (ràng buộc cố định 1-1 với 1 ví MetaMask)
  const [currentUser, setCurrentUser] = useState(() => {
    try {
      const saved = sessionStorage.getItem(SESSION_USER_KEY);
      return saved ? JSON.parse(saved) : null;
    } catch (_) {
      return null;
    }
  });

  // Trạng thái Web3 & Smart Contract
  // Ưu tiên giá trị user đã lưu qua giao diện (localStorage) trước,
  // fallback sang biến môi trường (.env) để tránh Vite cache giữ contract cũ
  const [contractAddress, setContractAddress] = useState(
    localStorage.getItem("contract_address") || DEFAULT_CONTRACT_ADDRESS
  );
  const [walletAddress, setWalletAddress] = useState(
    currentUser?.walletAddress || ""
  );
  const [electionActive, setElectionActive] = useState(false);
  const [adminAddress, setAdminAddress] = useState("");
  const [candidates, setCandidates] = useState([]);
  const [voterInfo, setVoterInfo] = useState({
    isAuthorized: false,
    hasVoted: false,
    votedCandidateId: 0,
  });

  const [loadingChain, setLoadingChain] = useState(false);
  const [votingLoading, setVotingLoading] = useState(false);
  const [chainError, setChainError] = useState("");
  const [lastVoteReceipt, setLastVoteReceipt] = useState(null);

  // Hàm đăng xuất sạch phiên làm việc
  const handleLogout = useCallback((reasonMsg = "") => {
    sessionStorage.removeItem(SESSION_USER_KEY);
    setCurrentUser(null);
    setWalletAddress(""); // Reset ví để tránh rò rỉ / hiển thị sai ví ở màn hình Auth
    setVoterInfo({ isAuthorized: false, hasVoted: false, votedCandidateId: 0 });
    setView("landing");
    if (reasonMsg) {
      alert(reasonMsg);
    }
  }, []);

  // Đồng bộ dữ liệu từ Smart Contract
  const loadBlockchainData = useCallback(
    async (currentWallet = walletAddress, currentContract = contractAddress) => {
      if (!isValidAddress(currentContract)) {
        setChainError(
          "Chưa có địa chỉ Smart Contract hợp lệ. Hãy kiểm tra CONTRACT_ADDRESS trong file .env."
        );
        return;
      }
      setLoadingChain(true);
      setChainError("");
      try {
        const data = await fetchElectionState(currentWallet, currentContract);
        setAdminAddress(data.admin);
        setElectionActive(data.electionActive);
        setCandidates(data.candidates);
        setVoterInfo(data.voterInfo);
      } catch (err) {
        setChainError(parseBlockchainError(err));
      } finally {
        setLoadingChain(false);
      }
    },
    [walletAddress, contractAddress]
  );

  // Khởi tạo Web3 ban đầu
  useEffect(() => {
    async function initWeb3() {
      let activeAcc = "";
      if (window.ethereum) {
        try {
          const accounts = await window.ethereum.request({
            method: "eth_accounts",
          });
          if (accounts && accounts.length > 0) {
            activeAcc = accounts[0];
          }
        } catch (_) {}
      }

      // Nếu đang có phiên đăng nhập mà ví MetaMask không khớp với ví đã đăng ký -> đăng xuất ngay
      if (currentUser && activeAcc) {
        if (currentUser.walletAddress.toLowerCase() !== activeAcc.toLowerCase()) {
          handleLogout(
            `⚠️ Ví MetaMask hiện tại (${activeAcc}) không khớp với ví đã đăng ký của tài khoản ${currentUser.email} (${currentUser.walletAddress}). Vui lòng đăng nhập lại!`
          );
          return;
        }
      }

      const targetWallet = currentUser?.walletAddress || activeAcc;
      setWalletAddress(targetWallet);
      await loadBlockchainData(targetWallet, contractAddress);
    }
    initWeb3();
  }, []);

  // MỤC 4: LẮNG NGHE SỰ KIỆN ĐỔI VÍ METAMASK — CHẶN TUYỆT ĐỐI DÙNG 2 VÍ CHO 1 TÀI KHOẢN
  useEffect(() => {
    if (!window.ethereum) return;

    const handleAccountsChanged = (accounts) => {
      if (!accounts || accounts.length === 0) {
        setWalletAddress("");
        if (currentUser || view === "dashboard") {
          handleLogout("⚠️ Bạn đã ngắt kết nối ví MetaMask. Hệ thống tự động đăng xuất.");
        }
        return;
      }

      const nextAcc = accounts[0];

      // Nếu người dùng đã đăng nhập một tài khoản cố định mà cố tình đổi sang ví thứ 2 trên MetaMask
      if (
        currentUser &&
        currentUser.walletAddress &&
        currentUser.walletAddress.toLowerCase() !== nextAcc.toLowerCase()
      ) {
        handleLogout(
          `🚫 CẢNH BÁO BẢO MẬT: Tài khoản (${currentUser.email}) chỉ được phép sử dụng duy nhất ví đã đăng ký (${currentUser.walletAddress}). Bạn vừa chuyển MetaMask sang ví thứ 2 (${nextAcc}), hệ thống tự động đăng xuất!`
        );
        return;
      }

      setWalletAddress(nextAcc);
      loadBlockchainData(nextAcc, contractAddress);
    };

    const handleChainChanged = () => {
      loadBlockchainData(walletAddress, contractAddress);
    };

    window.ethereum.on("accountsChanged", handleAccountsChanged);
    window.ethereum.on("chainChanged", handleChainChanged);
    return () => {
      if (window.ethereum.removeListener) {
        window.ethereum.removeListener("accountsChanged", handleAccountsChanged);
        window.ethereum.removeListener("chainChanged", handleChainChanged);
      }
    };
  }, [currentUser, view, walletAddress, contractAddress, loadBlockchainData, handleLogout]);

  // Kết nối ví MetaMask (và kiểm tra luôn ràng buộc nếu đang đăng nhập)
  const handleConnectWallet = async () => {
    try {
      const acc = await connectMetaMask();
      if (
        currentUser &&
        currentUser.walletAddress &&
        currentUser.walletAddress.toLowerCase() !== acc.toLowerCase()
      ) {
        handleLogout(
          `🚫 Ví MetaMask (${acc}) không trùng với ví đã gắn cố định cho tài khoản ${currentUser.email}!`
        );
        return null;
      }
      setWalletAddress(acc);
      await loadBlockchainData(acc, contractAddress);
      return acc;
    } catch (err) {
      alert(parseBlockchainError(err));
      return null;
    }
  };

  const handleUpdateContractAddress = (newAddr) => {
    setContractAddress(newAddr);
    if (isValidAddress(newAddr)) {
      localStorage.setItem("contract_address", newAddr.trim());
      loadBlockchainData(walletAddress, newAddr.trim());
    }
  };

  // Thực hiện bỏ phiếu trên Blockchain
  const handleVote = async (candidateId) => {
    if (!currentUser) {
      alert("Vui lòng đăng nhập tài khoản cử tri trước khi bỏ phiếu!");
      setView("auth");
      return;
    }

    const activeAcc = await handleConnectWallet();
    if (!activeAcc) return;

    // Kiểm tra lần cuối trước khi ký giao dịch: Ví ký phải đúng là ví của tài khoản đã đăng ký
    if (activeAcc.toLowerCase() !== currentUser.walletAddress.toLowerCase()) {
      handleLogout(
        "🚫 Phát hiện ví ký giao dịch không khớp với ví đã đăng ký của tài khoản!"
      );
      return;
    }

    setVotingLoading(true);
    try {
      const receipt = await submitVoteOnChain(candidateId, contractAddress);
      setLastVoteReceipt({
        ...receipt,
        candidateId,
        timestamp: new Date().toLocaleString("vi-VN"),
      });
      await loadBlockchainData(currentUser.walletAddress, contractAddress);
      alert(
        `✅ Bỏ phiếu thành công trên Blockchain!\nMã giao dịch (TxHash): ${receipt.txHash}`
      );
    } catch (err) {
      alert(`❌ Không thể bỏ phiếu: ${parseBlockchainError(err)}`);
    } finally {
      setVotingLoading(false);
    }
  };

  // 1. Màn hình Landing
  if (view === "landing") {
    return (
      <Landing
        onNavigate={(mode) => {
          setAuthMode(mode);
          setView("auth");
        }}
        onAdminPortal={() => {
          window.open("http://127.0.0.1:7860", "_blank");
        }}
      />
    );
  }

  // 2. Màn hình Đăng nhập / Đăng ký (Ràng buộc 1 Tài khoản - 1 Ví MetaMask)
  if (view === "auth") {
    return (
      <Auth
        initialMode={authMode}
        walletAddress={walletAddress}
        onConnectWallet={handleConnectWallet}
        onSuccess={(loggedInUser) => {
          sessionStorage.setItem(SESSION_USER_KEY, JSON.stringify(loggedInUser));
          setCurrentUser(loggedInUser);
          setWalletAddress(loggedInUser.walletAddress);
          loadBlockchainData(loggedInUser.walletAddress, contractAddress);
          setView("dashboard");
        }}
        onSwitchMode={(mode) => setAuthMode(mode)}
      />
    );
  }

  // 3. Màn hình Dashboard chính
  return (
    <div className="min-h-screen bg-gray-100 flex font-sans">
      <Sidebar
        activeTab={activeTab}
        onSelectTab={(tab) => setActiveTab(tab)}
        onLogout={() => handleLogout()}
      />

      <main className="flex-1 p-6 md:p-10 overflow-y-auto space-y-6">
        {/* Thanh trạng thái Tài khoản + Ví cố định + Trạng thái Blockchain */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4">
          <div className="space-y-1.5 text-sm">
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-bold text-gray-800">
                👤 Cử tri: {currentUser?.name} ({currentUser?.email})
              </span>
              <span className="text-gray-300">|</span>
              <span className="font-semibold text-gray-700">Hòm phiếu:</span>
              {electionActive ? (
                <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-green-100 text-green-700">
                  🟢 ĐANG MỞ BẦU CỬ
                </span>
              ) : (
                <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-gray-200 text-gray-700">
                  ⚪ CHƯA MỞ / ĐÃ ĐÓNG
                </span>
              )}
              <span className="text-gray-300">|</span>
              <span className="font-semibold text-gray-700">Quyền bầu cử:</span>
              {voterInfo.isAuthorized ? (
                <span className="text-green-600 font-bold">
                  ✅ Đã xác thực (Whitelisted)
                </span>
              ) : (
                <span className="text-amber-600 font-semibold">
                  ⏳ Chưa cấp quyền (Hãy gửi yêu cầu ở mục Voter Registration)
                </span>
              )}
            </div>

            <div className="flex flex-wrap items-center gap-2 text-xs text-gray-500">
              <span>Smart Contract:</span>
              <input
                type="text"
                value={contractAddress}
                onChange={(e) => handleUpdateContractAddress(e.target.value)}
                placeholder="0x... (Địa chỉ hợp đồng Election.sol)"
                className="font-mono bg-gray-50 border border-gray-300 rounded px-2 py-0.5 w-80 text-gray-700 focus:border-[#38c8e6] outline-none"
              />
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <button
              onClick={() => loadBlockchainData(walletAddress, contractAddress)}
              disabled={loadingChain}
              className="px-3 py-2 text-xs font-semibold rounded-md border border-gray-300 text-gray-700 hover:bg-gray-50 transition-all"
            >
              {loadingChain ? "⏳ Đang tải..." : "🔄 Làm mới từ Chain"}
            </button>

            <div
              title="Ví MetaMask đã khóa cố định với tài khoản này"
              className="px-4 py-2 text-xs font-bold rounded-md bg-cyan-50 border border-cyan-200 text-cyan-900 font-mono"
            >
              🔒 Ví cố định:{" "}
              {walletAddress
                ? `${walletAddress.slice(0, 6)}...${walletAddress.slice(-4)}`
                : "Chưa kết nối"}
            </div>
          </div>
        </div>

        {chainError && (
          <div className="bg-red-50 border-l-4 border-red-500 text-red-700 p-4 rounded text-sm">
            <p className="font-bold">⚠️ Lỗi kết nối Blockchain:</p>
            <p>{chainError}</p>
          </div>
        )}

        {activeTab === "info" && (
          <InformationTab
            contractAddress={contractAddress}
            adminAddress={adminAddress}
            electionActive={electionActive}
          />
        )}

        {activeTab === "register" && (
          <VoterRegistrationTab
            currentUser={currentUser}
            walletAddress={walletAddress}
            voterInfo={voterInfo}
            onRefreshChain={() => loadBlockchainData(walletAddress, contractAddress)}
            onProceedVoting={() => setActiveTab("voting")}
          />
        )}

        {activeTab === "voting" && (
          <VotingAreaTab
            candidates={candidates}
            electionActive={electionActive}
            voterInfo={voterInfo}
            walletAddress={walletAddress}
            votingLoading={votingLoading}
            lastVoteReceipt={lastVoteReceipt}
            onVote={handleVote}
            onConnectWallet={handleConnectWallet}
          />
        )}

        {activeTab === "result" && (
          <ResultTab
            walletAddress={walletAddress}
            candidates={candidates}
            electionActive={electionActive}
            voterInfo={voterInfo}
            lastVoteReceipt={lastVoteReceipt}
          />
        )}
      </main>
    </div>
  );
}
