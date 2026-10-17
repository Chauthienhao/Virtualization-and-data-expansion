// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

contract Election {
    // Biến lưu trữ địa chỉ ví của Ban tổ chức (Admin)
    address public admin;
    
    // Trạng thái cuộc bầu cử (Mở/Đóng)
    bool public electionActive;

    // 1. Cấu trúc dữ liệu Ứng cử viên
    struct Candidate {
        uint id;
        string name;
        uint voteCount;
    }

    // 2. Cấu trúc dữ liệu Cử tri
    struct Voter {
        bool isAuthorized; // Được phép bầu cử hay chưa (Whitelist)
        bool hasVoted;     // Đã bầu cử chưa
        uint votedCandidateId; // Bầu cho ai
    }

    // 3. Cơ sở dữ liệu On-chain
    mapping(address => Voter) public voters;
    mapping(uint => Candidate) public candidates;
    uint public candidatesCount;

    // 3b. Hàng đợi yêu cầu xác thực cử tri (cử tri tự gửi, Admin duyệt/từ chối)
    mapping(address => bool) public hasRequested; // true = đang chờ Admin duyệt
    address[] public pendingRequests; // nhật ký mọi địa chỉ từng gửi yêu cầu

    // 4. Các sự kiện (Events) để Frontend (ReactJS) lắng nghe
    event VotedEvent(address indexed _voter, uint _candidateId);
    event ElectionStarted();
    event ElectionEnded();
    event AuthorizationRequested(address indexed _voter);

    // 5. Bộ lọc quyền (Modifier)
    modifier onlyAdmin() {
        require(msg.sender == admin, "Loi: Chi Admin moi co quyen thuc hien");
        _;
    }

    // Hàm khởi tạo chạy 1 lần duy nhất khi Deploy Contract
    constructor() {
        admin = msg.sender; // Gán người deploy làm Admin
    }

    // ==========================================
    // CÁC HÀM DÀNH CHO ADMIN (GỌI TỪ PYTHON BACKEND)
    // ==========================================

    function addCandidate(string memory _name) public onlyAdmin {
        require(!electionActive, "Khong the them ung vien khi dang bau cu");
        candidatesCount++;
        candidates[candidatesCount] = Candidate(candidatesCount, _name, 0);
    }

    // LƯU Ý: KHÔNG còn require(!electionActive) ở đây như bản trước. Trong
    // kiến trúc ví custodial (xem voter_api.py), một cử tri có thể đăng
    // nhập LẦN ĐẦU TIÊN vào bất kỳ lúc nào trong suốt thời gian mở cuộc bầu
    // cử — không phải ai cũng đăng nhập trước khi Admin bấm "Bắt đầu". Nếu
    // giữ require này, bất kỳ ai đăng nhập lần đầu SAU khi bầu cử đã mở sẽ
    // không bao giờ cấp quyền được, bị khóa ngoài vĩnh viễn.
    function authorizeVoter(address _voter) public onlyAdmin {
        voters[_voter].isAuthorized = true;
        hasRequested[_voter] = false; // duyệt xong thì không còn "đang chờ" nữa
    }

    // Admin từ chối một yêu cầu: gỡ khỏi hàng đợi "đang chờ", KHÔNG cấp quyền.
    function rejectVoterRequest(address _voter) public onlyAdmin {
        hasRequested[_voter] = false;
    }

    function startElection() public onlyAdmin {
        electionActive = true;
        emit ElectionStarted();
    }

    function endElection() public onlyAdmin {
        electionActive = false;
        emit ElectionEnded();
    }

    // ==========================================
    // HÀM DÀNH CHO CỬ TRI (GỌI TỪ REACTJS + METAMASK)
    // ==========================================

    // Cử tri tự gửi yêu cầu xin cấp quyền bầu cử — KHÔNG tự động được cấp
    // quyền, chỉ được thêm vào hàng đợi để Admin xem và quyết định duyệt
    // hay từ chối (qua authorizeVoter/rejectVoterRequest ở trên).
    function requestToVote() public {
        require(!electionActive, "Chi gui yeu cau truoc khi bau cu dien ra");
        require(!voters[msg.sender].isAuthorized, "Dia chi vi nay da duoc cap quyen roi");
        require(!hasRequested[msg.sender], "Ban da gui yeu cau truoc do, vui long cho Admin duyet");
        hasRequested[msg.sender] = true;
        pendingRequests.push(msg.sender);
        emit AuthorizationRequested(msg.sender);
    }

    function getPendingRequestsCount() public view returns (uint) {
        return pendingRequests.length;
    }

    function vote(uint _candidateId) public {
        // Kiểm tra các điều kiện tiên quyết
        require(electionActive, "Cuoc bau cu chua dien ra hoac da dong");
        require(voters[msg.sender].isAuthorized, "Dia chi vi nay chua duoc cap quyen bo phieu");
        require(!voters[msg.sender].hasVoted, "Cu tri nay da thuc hien bo phieu");
        require(_candidateId > 0 && _candidateId <= candidatesCount, "ID Ung vien khong hop le");

        // Cập nhật trạng thái cử tri
        voters[msg.sender].hasVoted = true;
        voters[msg.sender].votedCandidateId = _candidateId;

        // Tăng số phiếu cho ứng cử viên
        candidates[_candidateId].voteCount++;

        // Phát tín hiệu sự kiện ra ngoài mạng lưới
        emit VotedEvent(msg.sender, _candidateId);
    }
}