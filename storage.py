"""
storage.py (bản MySQL)
======================================================================
Lưu trữ off-chain bằng MySQL thật, cho các dữ liệu KHÔNG tồn tại trên
Smart Contract (Candidate struct trong Election.sol chỉ có
id/name/voteCount, không có "Mã định danh/SBD" hay "Đơn vị/Chi đoàn").

SCHEMA (3 bảng, InnoDB, utf8mb4):
- elections            : metadata phiên bầu cử (tiêu đề, mô tả, thời gian,
                          trạng thái cục bộ). seq là khóa chính AUTO_INCREMENT;
                          mã hiển thị "BC-00N" được suy ra từ seq (xem
                          _seq_to_code/_code_to_seq), không lưu thành cột
                          riêng để tránh lệch số khi có lỗi/rollback.
- election_candidates   : bảng nối election <-> candidate (id on-chain),
                          vì một candidate trên chain thuộc về đúng 1 phiên
                          quản lý cục bộ.
- candidate_meta        : map (contract_address, onchain_id) -> {code, unit}.
                          seq AUTO_INCREMENT là nguồn sinh mã SBD "UV-NN" —
                          KHÔNG dùng onchain_id, vì deploy lại contract thì
                          onchain_id đếm lại từ 1 và sẽ trùng SBD cũ.

Mỗi phiên (elections.contract_address) và mỗi ứng viên đều ghi lại địa chỉ
contract mà nó thuộc về, để dữ liệu của các lần deploy khác nhau không lẫn
vào nhau.

LƯU Ý KIẾN TRÚC (giữ nguyên từ bản trước, vẫn đúng với MySQL):
Election.sol hiện chỉ hỗ trợ MỘT cuộc bầu cử đang hoạt động tại một thời
điểm cho cả hợp đồng (electionActive, candidatesCount là toàn cục, không
có electionId). "elections" ở đây là NHÃN QUẢN LÝ off-chain để nhóm ứng
viên theo đợt tạo, không phải nhiều cuộc bầu cử độc lập thật trên chain.

CẤU HÌNH: đọc từ biến môi trường (.env) — DB_HOST, DB_PORT, DB_USER,
DB_PASSWORD, DB_NAME. Xem .env.example.
======================================================================
"""

import os
from datetime import datetime

import mysql.connector
from mysql.connector import Error as MySQLError

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class StorageError(Exception):
    """Lỗi kết nối/truy vấn MySQL đã diễn giải sang tiếng Việt, để lớp
    giao diện (Gradio) chỉ cần hiển thị str(e)."""
    pass


DB_CONFIG = {
    "host": os.getenv("DB_HOST", "127.0.0.1"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", "123456"),
    "database": os.getenv("DB_NAME", "election_admin"),
}


def _connect():
    try:
        return mysql.connector.connect(**DB_CONFIG)
    except MySQLError as e:
        raise StorageError(
            f"Không kết nối được MySQL tại {DB_CONFIG['host']}:{DB_CONFIG['port']} "
            f"(database='{DB_CONFIG['database']}'). Chi tiết: {e}. "
            f"Kiểm tra MySQL server đã chạy, đã tạo database (hoặc đã chạy init_db()), "
            f"và thông tin trong .env."
        )


def init_db():
    """Tạo database (nếu chưa có) và các bảng cần thiết. Gọi 1 lần lúc khởi
    động app (an toàn để gọi lại nhiều lần nhờ IF NOT EXISTS)."""
    cfg_no_db = {k: v for k, v in DB_CONFIG.items() if k != "database"}
    try:
        conn = mysql.connector.connect(**cfg_no_db)
    except MySQLError as e:
        raise StorageError(
            f"Không kết nối được MySQL server tại {DB_CONFIG['host']}:{DB_CONFIG['port']}. "
            f"Chi tiết: {e}. Kiểm tra MySQL đã chạy và DB_USER/DB_PASSWORD trong .env đúng chưa."
        )
    try:
        cur = conn.cursor()
        cur.execute(
            f"CREATE DATABASE IF NOT EXISTS `{DB_CONFIG['database']}` "
            f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
        conn.commit()
    except MySQLError as e:
        raise StorageError(f"Không tạo được database '{DB_CONFIG['database']}': {e}")
    finally:
        conn.close()

    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS elections (
                seq INT AUTO_INCREMENT PRIMARY KEY,
                contract_address VARCHAR(42) NOT NULL DEFAULT '',
                title VARCHAR(255) NOT NULL,
                description TEXT,
                start_time VARCHAR(50),
                end_time VARCHAR(50),
                status VARCHAR(50) NOT NULL DEFAULT 'Sẵn sàng',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS election_candidates (
                election_seq INT NOT NULL,
                onchain_id INT NOT NULL,
                PRIMARY KEY (election_seq, onchain_id),
                FOREIGN KEY (election_seq) REFERENCES elections(seq) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS candidate_meta (
                seq INT AUTO_INCREMENT PRIMARY KEY,
                contract_address VARCHAR(42) NOT NULL,
                onchain_id INT NOT NULL,
                code VARCHAR(100),
                unit VARCHAR(255),
                UNIQUE KEY uq_contract_candidate (contract_address, onchain_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        _migrate_contract_columns(cur)
        # ------------------------------------------------------------------
        # Bảng cử tri (danh tính CCCD + ví do hệ thống giữ hộ).
        # LƯU Ý BẢO MẬT: encrypted_private_key được mã hóa bằng Fernet (khóa
        # bí mật nằm trong .env, KHÔNG BAO GIỜ trong DB) trước khi lưu, và sẽ
        # bị XÓA (set NULL) ngay sau khi cử tri bầu thành công — vì sau khi
        # hasVoted=true trên chain, khóa đó không còn tác dụng dùng tiếp (hợp
        # đồng chặn bầu lần 2 bất kể có khóa hay không), nên không có lý do
        # giữ thêm, giảm diện tích rủi ro nếu CSDL bị rò rỉ về sau.
        # cccd_hash dùng SHA-256(CCCD + pepper) — không lưu CCCD dạng thô.
        # wallet_address/encrypted_private_key để NULL được: Admin chỉ nhập
        # CCCD đủ điều kiện trước (chưa có ví); ví CHỈ được sinh ra đúng lúc
        # CCCD đó đăng nhập thành công LẦN ĐẦU (xem voter_api.py sau này).
        cur.execute("""
            CREATE TABLE IF NOT EXISTS voters (
                id INT AUTO_INCREMENT PRIMARY KEY,
                cccd_hash CHAR(64) NOT NULL UNIQUE,
                full_name VARCHAR(255),
                wallet_address VARCHAR(42) NULL,
                encrypted_private_key TEXT,
                access_code_hash CHAR(64),
                code_generated_at DATETIME,
                status VARCHAR(30) NOT NULL DEFAULT 'chua_kich_hoat',
                session_token CHAR(64),
                session_started_at DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        conn.commit()
    except MySQLError as e:
        raise StorageError(f"Không tạo được bảng trong database '{DB_CONFIG['database']}': {e}")
    finally:
        conn.close()


def _norm_contract(address) -> str:
    """Chuẩn hóa địa chỉ contract (chữ thường) để so khớp không phụ thuộc
    kiểu viết checksum hoa/thường."""
    return (address or "").strip().lower()


def _column_exists(cur, table: str, column: str) -> bool:
    cur.execute(
        "SELECT COUNT(*) FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND COLUMN_NAME = %s",
        (DB_CONFIG["database"], table, column),
    )
    return cur.fetchone()[0] > 0


def _migrate_contract_columns(cur) -> None:
    """Nâng cấp database tạo bởi bản cũ (chưa có cột contract_address).
    Dữ liệu cũ được gán cho CONTRACT_ADDRESS đang cấu hình trong .env —
    đó là contract mà dữ liệu này nhiều khả năng thuộc về nhất."""
    legacy = _norm_contract(os.getenv("CONTRACT_ADDRESS", ""))

    if not _column_exists(cur, "elections", "contract_address"):
        cur.execute("ALTER TABLE elections ADD COLUMN contract_address VARCHAR(42) NOT NULL DEFAULT '' AFTER seq")
        cur.execute("UPDATE elections SET contract_address = %s", (legacy,))

    if not _column_exists(cur, "candidate_meta", "seq"):
        cur.execute(
            "ALTER TABLE candidate_meta DROP PRIMARY KEY, "
            "ADD COLUMN seq INT NOT NULL AUTO_INCREMENT PRIMARY KEY FIRST, "
            "ADD COLUMN contract_address VARCHAR(42) NOT NULL DEFAULT '' AFTER seq"
        )
        cur.execute("UPDATE candidate_meta SET contract_address = %s", (legacy,))
        cur.execute("ALTER TABLE candidate_meta ADD UNIQUE KEY uq_contract_candidate (contract_address, onchain_id)")
        cur.execute("UPDATE candidate_meta SET code = CONCAT('UV-', LPAD(seq, 2, '0'))")


def check_connection() -> str:
    """Trả về chuỗi trạng thái để hiển thị ở Dashboard. Không raise."""
    try:
        conn = _connect()
        conn.close()
        return f"MySQL OK ({DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']})"
    except StorageError as e:
        return f"{e}"


# ----------------------------------------------------------------------
# Chuyển đổi "BC-003" <-> seq (3). Mã hiển thị luôn suy ra từ seq thật của
# MySQL (AUTO_INCREMENT), để không bao giờ bị trùng/lệch số dù có lỗi giữa
# chừng hay nhiều admin cùng thao tác (khác với cách đếm len(list)+1 trước đây).
# ----------------------------------------------------------------------

def _seq_to_code(seq: int) -> str:
    return f"BC-{seq:03d}"


def _code_to_seq(election_code: str):
    try:
        return int(election_code.strip().split("-")[-1])
    except (ValueError, IndexError, AttributeError):
        return None


# ----------------------------------------------------------------------
#region ELECTIONS
# ----------------------------------------------------------------------

def create_election(title: str, desc: str, start: str, end: str,
                     status: str = "Đang khởi tạo...", contract_address: str = "") -> str:
    """Tạo một phiên bầu cử MỚI, CHƯA gắn ứng viên nào (gắn dần bằng
    add_candidates_to_election khi từng ứng viên được ghi lên chain thành
    công, để nếu giữa chừng lỗi vẫn giữ được phần đã làm)."""
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO elections (contract_address, title, description, start_time, end_time, status) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (_norm_contract(contract_address), title, desc, start, end, status),
        )
        conn.commit()
        return _seq_to_code(cur.lastrowid)
    except MySQLError as e:
        conn.rollback()
        raise StorageError(f"Lỗi khi tạo phiên bầu cử trong MySQL: {e}")
    finally:
        conn.close()


def list_elections() -> list:
    conn = _connect()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT e.seq, e.title, e.description, e.start_time, e.end_time, e.status,
                   COUNT(ec.onchain_id) AS candidate_count
            FROM elections e
            LEFT JOIN election_candidates ec ON ec.election_seq = e.seq
            GROUP BY e.seq, e.title, e.description, e.start_time, e.end_time, e.status
            ORDER BY e.seq ASC
        """)
        rows = cur.fetchall()
        return [{
            "id": _seq_to_code(r["seq"]),
            "title": r["title"],
            "desc": r["description"] or "",
            "start": r["start_time"] or "",
            "end": r["end_time"] or "",
            "status": r["status"],
            "candidate_count": r["candidate_count"],
        } for r in rows]
    except MySQLError as e:
        raise StorageError(f"Lỗi khi đọc danh sách phiên bầu cử: {e}")
    finally:
        conn.close()


def get_election(election_code: str):
    """Trả về dict đầy đủ (gồm candidate_ids), hoặc None nếu không tìm thấy."""
    seq = _code_to_seq(election_code)
    if seq is None:
        return None
    conn = _connect()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM elections WHERE seq = %s", (seq,))
        row = cur.fetchone()
        if row is None:
            return None
        cur.execute(
            "SELECT onchain_id FROM election_candidates WHERE election_seq = %s ORDER BY onchain_id",
            (seq,),
        )
        candidate_ids = [r["onchain_id"] for r in cur.fetchall()]
        return {
            "id": _seq_to_code(row["seq"]),
            "title": row["title"],
            "desc": row["description"] or "",
            "start": row["start_time"] or "",
            "end": row["end_time"] or "",
            "status": row["status"],
            "contract_address": row["contract_address"] or "",
            "candidate_ids": candidate_ids,
        }
    except MySQLError as e:
        raise StorageError(f"Lỗi khi đọc phiên bầu cử {election_code}: {e}")
    finally:
        conn.close()


def get_latest_election_code():
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute("SELECT seq FROM elections ORDER BY seq DESC LIMIT 1")
        row = cur.fetchone()
        return _seq_to_code(row[0]) if row else None
    except MySQLError as e:
        raise StorageError(f"Lỗi khi đọc phiên mới nhất: {e}")
    finally:
        conn.close()


def update_election_status(election_code: str, status: str) -> None:
    seq = _code_to_seq(election_code)
    if seq is None:
        raise StorageError(f"Mã phiên không hợp lệ: {election_code}")
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute("UPDATE elections SET status = %s WHERE seq = %s", (status, seq))
        conn.commit()
        if cur.rowcount == 0:
            raise StorageError(f"Không tìm thấy phiên: {election_code}")
    except MySQLError as e:
        conn.rollback()
        raise StorageError(f"Lỗi khi cập nhật trạng thái phiên: {e}")
    finally:
        conn.close()


def set_election_time(election_code: str, which: str) -> None:
    """Ghi thời điểm HIỆN TẠI vào start_time (which='start') hoặc end_time
    (which='end') — gọi ngay sau khi startElection/endElection trên chain
    thành công, để thời gian do hệ thống tự ghi chứ không nhập tay."""
    column = {"start": "start_time", "end": "end_time"}[which]
    seq = _code_to_seq(election_code)
    if seq is None:
        raise StorageError(f"Mã phiên không hợp lệ: {election_code}")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(f"UPDATE elections SET {column} = %s WHERE seq = %s", (now, seq))
        conn.commit()
    except MySQLError as e:
        conn.rollback()
        raise StorageError(f"Lỗi khi ghi thời gian phiên: {e}")
    finally:
        conn.close()


def add_candidates_to_election(election_code: str, onchain_ids: list) -> None:
    """Gắn thêm (các) candidate on-chain vào một phiên đã tồn tại.
    Gọi NGAY sau mỗi lần addCandidate() on-chain thành công (không gom hết
    rồi mới lưu 1 lần), để nếu giữa chừng có lỗi thì những candidate đã
    ghi thành công vẫn không bị mất dấu trong MySQL."""
    seq = _code_to_seq(election_code)
    if seq is None or not onchain_ids:
        return
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.executemany(
            "INSERT IGNORE INTO election_candidates (election_seq, onchain_id) VALUES (%s, %s)",
            [(seq, cid) for cid in onchain_ids],
        )
        conn.commit()
    except MySQLError as e:
        conn.rollback()
        raise StorageError(f"Lỗi khi gắn ứng viên vào phiên {election_code}: {e}")
    finally:
        conn.close()


# ----------------------------------------------------------------------
#region CANDIDATE METADATA (mã SBD, đơn vị — không có trên chain)
# ----------------------------------------------------------------------

def _seq_to_sbd(seq: int) -> str:
    return f"UV-{seq:02d}"


def set_candidate_meta(contract_address: str, onchain_id: int, unit: str) -> str:
    """Lưu đơn vị của ứng viên và cấp mã SBD (lấy từ seq AUTO_INCREMENT nên
    luôn duy nhất, tăng dần, kể cả qua nhiều lần deploy lại contract).
    Trả về mã SBD đã cấp."""
    contract_address = _norm_contract(contract_address)
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO candidate_meta (contract_address, onchain_id, unit) VALUES (%s, %s, %s) "
            "ON DUPLICATE KEY UPDATE unit = VALUES(unit)",
            (contract_address, onchain_id, unit),
        )
        cur.execute(
            "SELECT seq FROM candidate_meta WHERE contract_address = %s AND onchain_id = %s",
            (contract_address, onchain_id),
        )
        code = _seq_to_sbd(cur.fetchone()[0])
        cur.execute(
            "UPDATE candidate_meta SET code = %s WHERE contract_address = %s AND onchain_id = %s",
            (code, contract_address, onchain_id),
        )
        conn.commit()
        return code
    except MySQLError as e:
        conn.rollback()
        raise StorageError(f"Lỗi khi lưu thông tin ứng viên #{onchain_id}: {e}")
    finally:
        conn.close()


def get_candidate_meta(contract_address: str, onchain_id: int) -> dict:
    return get_candidate_meta_bulk(contract_address, [onchain_id]).get(onchain_id, {"code": "", "unit": ""})


def peek_next_sbd_seq() -> int:
    """Seq dự kiến của ứng viên tiếp theo (chỉ để hiển thị SBD 'dự kiến' ở
    danh sách tạm — mã chính thức do set_candidate_meta cấp)."""
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute("SELECT COALESCE(MAX(seq), 0) + 1 FROM candidate_meta")
        return int(cur.fetchone()[0])
    except MySQLError as e:
        raise StorageError(f"Lỗi khi đọc số thứ tự SBD: {e}")
    finally:
        conn.close()


def create_eligible_voter(cccd_hash: str, full_name: str) -> int:
    """Admin nhập một CCCD vào danh sách ĐỦ ĐIỀU KIỆN bầu cử — CHƯA sinh ví,
    CHƯA đụng blockchain gì cả. Ví + bơm ETH + authorizeVoter chỉ xảy ra sau
    này, đúng lúc CCCD này đăng nhập thành công lần đầu (xem attach_wallet)."""
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO voters (cccd_hash, full_name, status) VALUES (%s, %s, 'chua_kich_hoat')",
            (cccd_hash, full_name),
        )
        conn.commit()
        return cur.lastrowid
    except MySQLError as e:
        conn.rollback()
        if "Duplicate entry" in str(e):
            raise StorageError("CCCD này đã có trong danh sách cử tri rồi.")
        raise StorageError(f"Lỗi khi thêm cử tri đủ điều kiện vào MySQL: {e}")
    finally:
        conn.close()


def attach_wallet(cccd_hash: str, wallet_address: str, encrypted_private_key: str) -> None:
    """Gắn ví vừa sinh (lúc đăng nhập lần đầu thành công) vào đúng bản ghi
    CCCD đó. Chỉ chạy khi wallet_address còn NULL, để không lỡ tay sinh và
    gắn đè một ví thứ hai nếu hàm này vô tình được gọi lại."""
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE voters SET wallet_address = %s, encrypted_private_key = %s "
            "WHERE cccd_hash = %s AND wallet_address IS NULL",
            (wallet_address, encrypted_private_key, cccd_hash),
        )
        conn.commit()
        if cur.rowcount == 0:
            raise StorageError("CCCD không tồn tại, hoặc đã có ví gắn sẵn từ trước (không gắn đè).")
    except MySQLError as e:
        conn.rollback()
        raise StorageError(f"Lỗi khi gắn ví cho cử tri: {e}")
    finally:
        conn.close()


def list_voters() -> list:
    """Danh sách cử tri cho Admin xem (KHÔNG trả về private key, chỉ trạng thái)."""
    conn = _connect()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT id, cccd_hash, full_name, wallet_address, status, created_at, session_started_at "
            "FROM voters ORDER BY id ASC"
        )
        return cur.fetchall()
    except MySQLError as e:
        raise StorageError(f"Lỗi khi đọc danh sách cử tri: {e}")
    finally:
        conn.close()


def get_voter_by_cccd_hash(cccd_hash: str):
    conn = _connect()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM voters WHERE cccd_hash = %s", (cccd_hash,))
        return cur.fetchone()
    except MySQLError as e:
        raise StorageError(f"Lỗi khi tra cứu cử tri: {e}")
    finally:
        conn.close()


def get_voter_by_session(session_token: str):
    conn = _connect()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM voters WHERE session_token = %s AND status = 'dang_trong_phien'", (session_token,))
        return cur.fetchone()
    except MySQLError as e:
        raise StorageError(f"Lỗi khi tra cứu phiên: {e}")
    finally:
        conn.close()


def set_access_code(cccd_hash: str, code_hash: str) -> None:
    """Lưu mã truy cập (đã băm) vừa sinh cho một cử tri, chuyển trạng thái
    sang 'da_cap_ma' (đã cấp mã, chờ xác thực). Cho phép gọi lại khi trạng
    thái đã là 'da_cap_ma' (cấp lại mã mới, mã cũ tự mất hiệu lực) — trường
    hợp cử tri lỡ không kịp xem mã và phải nhập CCCD lại lần nữa."""
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE voters SET access_code_hash = %s, code_generated_at = NOW(), status = 'da_cap_ma' "
            "WHERE cccd_hash = %s AND status IN ('chua_kich_hoat', 'da_cap_ma')",
            (code_hash, cccd_hash),
        )
        conn.commit()
        if cur.rowcount == 0:
            raise StorageError(
                "CCCD không tồn tại trong danh sách cử tri, hoặc cử tri này đã đăng nhập/đã khóa trước đó."
            )
    except MySQLError as e:
        conn.rollback()
        raise StorageError(f"Lỗi khi cấp mã truy cập: {e}")
    finally:
        conn.close()


def start_session(cccd_hash: str, session_token: str) -> None:
    """Xác thực mã thành công: chuyển sang 'dang_trong_phien', gắn session_token."""
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE voters SET session_token = %s, session_started_at = NOW(), status = 'dang_trong_phien' "
            "WHERE cccd_hash = %s AND status = 'da_cap_ma'",
            (session_token, cccd_hash),
        )
        conn.commit()
        if cur.rowcount == 0:
            raise StorageError("Mã không hợp lệ, đã hết hạn, hoặc phiên này đã được kích hoạt trước đó.")
    except MySQLError as e:
        conn.rollback()
        raise StorageError(f"Lỗi khi mở phiên: {e}")
    finally:
        conn.close()


def wipe_private_key(session_token: str) -> None:
    """Xóa private key ngay sau khi bầu thành công (xem lưu ý bảo mật ở
    init_db) — KHÔNG đổi status, vẫn 'dang_trong_phien' để cử tri còn tra
    cứu lại phiếu mình đã bầu trước khi đăng xuất."""
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute("UPDATE voters SET encrypted_private_key = NULL WHERE session_token = %s", (session_token,))
        conn.commit()
    except MySQLError as e:
        conn.rollback()
        raise StorageError(f"Lỗi khi xóa private key: {e}")
    finally:
        conn.close()


def force_unlock_voter(cccd_hash: str) -> None:
    """Admin chủ động mở lại một phiên bị KẸT — dùng khi trình duyệt của cử
    tri bị đóng/crash giữa chừng (quên bấm "Đăng xuất") nên phiên vẫn nằm ở
    trạng thái 'dang_trong_phien' mãi, khiến họ không bao giờ đăng nhập lại
    được (lỗi "Phiên đăng nhập trước đó vẫn đang mở"). CHỈ áp dụng khi đang
    'dang_trong_phien'. KHÔNG áp dụng cho 'da_khoa' (khóa đó là vĩnh viễn —
    cử tri đã chủ động đăng xuất, không được mở lại, đúng yêu cầu "phiên chỉ
    dùng 1 lần")."""
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE voters SET status = 'chua_kich_hoat', session_token = NULL, access_code_hash = NULL "
            "WHERE cccd_hash = %s AND status = 'dang_trong_phien'",
            (cccd_hash,),
        )
        conn.commit()
        if cur.rowcount == 0:
            raise StorageError(
                "CCCD này hiện không ở trạng thái 'đang trong phiên' — không cần mở khóa "
                "(hoặc CCCD đã đăng xuất chủ động, khóa đó không thể mở lại)."
            )
    except MySQLError as e:
        conn.rollback()
        raise StorageError(f"Lỗi khi mở khóa phiên: {e}")
    finally:
        conn.close()


def lock_session(session_token: str) -> None:
    """Đăng xuất: khóa VĨNH VIỄN phiên này — cccd+mã cũ không dùng lại được
    nữa, dù cử tri đã bầu hay chưa (đúng yêu cầu: phiên chỉ dùng 1 lần)."""
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE voters SET status = 'da_khoa', session_token = NULL, encrypted_private_key = NULL "
            "WHERE session_token = %s",
            (session_token,),
        )
        conn.commit()
    except MySQLError as e:
        conn.rollback()
        raise StorageError(f"Lỗi khi khóa phiên: {e}")
    finally:
        conn.close()


def get_candidate_meta_bulk(contract_address: str, onchain_ids: list) -> dict:
    """Lấy metadata nhiều candidate (của ĐÚNG contract đang dùng) trong 1 lần
    truy vấn (tránh N kết nối cho N candidate khi hiển thị bảng kết quả)."""
    if not onchain_ids:
        return {}
    conn = _connect()
    try:
        cur = conn.cursor(dictionary=True)
        placeholders = ",".join(["%s"] * len(onchain_ids))
        cur.execute(
            f"SELECT seq, onchain_id, unit FROM candidate_meta "
            f"WHERE contract_address = %s AND onchain_id IN ({placeholders})",
            (_norm_contract(contract_address), *onchain_ids),
        )
        return {r["onchain_id"]: {"code": _seq_to_sbd(r["seq"]), "unit": r["unit"] or ""} for r in cur.fetchall()}
    except MySQLError as e:
        raise StorageError(f"Lỗi khi đọc metadata ứng viên (bulk): {e}")
    finally:
        conn.close()
