import { BrowserProvider, JsonRpcProvider, Contract } from "ethers";
import ElectionABI from "../ElectionABI.json";

// Tự động đọc từ file .env ở thư mục gốc (nhờ cấu hình envPrefix trong vite.config.js)
export const DEFAULT_RPC_URL =
  import.meta.env.VITE_RPC_URL ||
  import.meta.env.RPC_URL ||
  "http://127.0.0.1:7545";

export const DEFAULT_CONTRACT_ADDRESS =
  import.meta.env.VITE_CONTRACT_ADDRESS ||
  import.meta.env.CONTRACT_ADDRESS ||
  "";

const REVERT_MESSAGES = {
  "Loi: Chi Admin moi co quyen thuc hien":
    "Chỉ tài khoản Admin mới có quyền thực hiện thao tác này.",
  "Khong the them ung vien khi dang bau cu":
    "Không thể thêm ứng viên khi cuộc bầu cử đang diễn ra.",
  "Chi cap quyen truoc khi bau cu dien ra":
    "Chỉ có thể cấp quyền cử tri trước khi cuộc bầu cử bắt đầu.",
  "Cuoc bau cu chua dien ra hoac da dong":
    "Cuộc bầu cử hiện chưa mở hoặc đã kết thúc!",
  "Dia chi vi nay chua duoc cap quyen bo phieu":
    "Địa chỉ ví của bạn chưa được Ban tổ chức (Admin) cấp quyền bỏ phiếu (Whitelist)!",
  "Cu tri nay da thuc hien bo phieu":
    "Bạn đã bỏ phiếu rồi! Mỗi cử tri chỉ được bỏ phiếu duy nhất 1 lần.",
  "ID Ung vien khong hop le":
    "Mã ứng cử viên không hợp lệ!",
};

export function parseBlockchainError(err) {
  if (!err) return "Lỗi không xác định.";
  if (err.code === "ACTION_REJECTED" || err.code === 4001) {
    return "Bạn đã từ chối ký giao dịch trên ví MetaMask.";
  }
  const raw =
    err.reason ||
    err.shortMessage ||
    err?.info?.error?.message ||
    err?.data?.message ||
    err.message ||
    String(err);

  for (const [key, friendly] of Object.entries(REVERT_MESSAGES)) {
    if (raw.includes(key)) return friendly;
  }
  return raw;
}

export function isValidAddress(addr) {
  return (
    typeof addr === "string" &&
    /^0x[a-fA-F0-9]{40}$/.test(addr.trim()) &&
    !addr.includes("YourDeployedContractAddressHere")
  );
}

/**
 * Kết nối ví MetaMask và trả về địa chỉ ví hiện tại
 */
export async function connectMetaMask() {
  if (!window.ethereum) {
    throw new Error(
      "Không tìm thấy tiện ích MetaMask! Vui lòng cài đặt MetaMask trên trình duyệt."
    );
  }
  const provider = new BrowserProvider(window.ethereum);

  // Kiểm tra xem đã có account kết nối chưa
  const existingAccounts = await provider.send("eth_accounts", []);

  if (existingAccounts && existingAccounts.length > 0) {
    // Đã có ví kết nối → buộc MetaMask mở popup chọn lại account
    // (eth_requestAccounts sẽ chỉ trả về account đang active mà không cho đổi)
    try {
      await provider.send("wallet_requestPermissions", [
        { eth_accounts: {} },
      ]);
    } catch (permErr) {
      // Người dùng đóng popup chọn ví → giữ nguyên ví hiện tại
      if (permErr.code === 4001) {
        return existingAccounts[0];
      }
      throw permErr;
    }
  }

  // Lấy lại danh sách account sau khi user chọn (hoặc lần đầu kết nối)
  const accounts = await provider.send("eth_requestAccounts", []);
  if (!accounts || accounts.length === 0) {
    throw new Error("Không lấy được tài khoản nào từ MetaMask.");
  }
  return accounts[0];
}

/**
 * Lấy đối tượng Contract để ĐỌC dữ liệu (ưu tiên đọc trực tiếp qua RPC_URL Ganache
 * để luôn nhanh và không bị lỗi lệch mạng trên MetaMask, nếu lỗi mới fallback sang MetaMask)
 */
async function getReadContract(contractAddress) {
  const addr = (contractAddress || DEFAULT_CONTRACT_ADDRESS).trim();
  if (!isValidAddress(addr)) {
    throw new Error(
      "Chưa cấu hình CONTRACT_ADDRESS hợp lệ trong file .env (hoặc trên thanh cấu hình)."
    );
  }

  // Thử đọc qua RPC_URL (mặc định http://127.0.0.1:7545) trước
  try {
    const rpcProvider = new JsonRpcProvider(DEFAULT_RPC_URL);
    const code = await rpcProvider.getCode(addr);
    if (code && code !== "0x") {
      return new Contract(addr, ElectionABI, rpcProvider);
    }
  } catch (_) {
    // Nếu RPC_URL không phản hồi, chuyển sang thử qua MetaMask
  }

  if (window.ethereum) {
    const browserProvider = new BrowserProvider(window.ethereum);
    const code = await browserProvider.getCode(addr);
    if (code && code !== "0x") {
      return new Contract(addr, ElectionABI, browserProvider);
    }
  }

  throw new Error(
    `Không tìm thấy Smart Contract tại địa chỉ ${addr}. Hãy kiểm tra Ganache đã bật ở ${DEFAULT_RPC_URL} và CONTRACT_ADDRESS trong file .env đã đúng chưa.`
  );
}

/**
 * Đọc toàn bộ thông tin cuộc bầu cử, danh sách ứng viên và trạng thái cử tri từ Smart Contract
 */
export async function fetchElectionState(voterAddress, contractAddress) {
  const contract = await getReadContract(contractAddress);

  const [admin, electionActive, countBig] = await Promise.all([
    contract.admin(),
    contract.electionActive(),
    contract.candidatesCount(),
  ]);

  const count = Number(countBig);
  const candidatePromises = [];
  for (let i = 1; i <= count; i++) {
    candidatePromises.push(contract.candidates(i));
  }
  const rawCandidates = await Promise.all(candidatePromises);

  const candidates = rawCandidates.map((c) => ({
    id: Number(c.id ?? c[0]),
    name: String(c.name ?? c[1]),
    votes: Number(c.voteCount ?? c[2]),
  }));

  let voterInfo = {
    isAuthorized: false,
    hasVoted: false,
    votedCandidateId: 0,
  };

  if (isValidAddress(voterAddress)) {
    const v = await contract.voters(voterAddress.trim());
    voterInfo = {
      isAuthorized: Boolean(v.isAuthorized ?? v[0]),
      hasVoted: Boolean(v.hasVoted ?? v[1]),
      votedCandidateId: Number(v.votedCandidateId ?? v[2]),
    };
  }

  return {
    admin,
    electionActive: Boolean(electionActive),
    candidatesCount: count,
    candidates,
    voterInfo,
  };
}

/**
 * Gửi giao dịch bỏ phiếu (vote) thông qua MetaMask
 */
export async function submitVoteOnChain(candidateId, contractAddress) {
  if (!window.ethereum) {
    throw new Error(
      "Vui lòng cài đặt và mở tiện ích ví MetaMask để ký giao dịch bỏ phiếu."
    );
  }
  const addr = (contractAddress || DEFAULT_CONTRACT_ADDRESS).trim();
  if (!isValidAddress(addr)) {
    throw new Error("Địa chỉ Smart Contract không hợp lệ.");
  }

  const provider = new BrowserProvider(window.ethereum);
  const code = await provider.getCode(addr);
  if (!code || code === "0x") {
    throw new Error(
      `Ví MetaMask của bạn đang kết nối sai mạng (không tìm thấy hợp đồng ${addr}). Vui lòng chuyển mạng trên MetaMask sang Ganache Localhost (RPC: ${DEFAULT_RPC_URL}, Chain ID: 1337).`
    );
  }

  const signer = await provider.getSigner();
  const contract = new Contract(addr, ElectionABI, signer);

  // Mô phỏng trước bằng staticCall để bắt lỗi require() rõ ràng trước khi bật popup MetaMask
  await contract.vote.staticCall(candidateId);

  // Gửi giao dịch thật qua MetaMask
  const tx = await contract.vote(candidateId);
  const receipt = await tx.wait();

  return {
    txHash: receipt.hash,
    blockNumber: receipt.blockNumber,
    gasUsed: receipt.gasUsed ? receipt.gasUsed.toString() : "N/A",
    from: await signer.getAddress(),
  };
}
