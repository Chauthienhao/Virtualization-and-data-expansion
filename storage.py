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
- candidate_meta        : map onchain_id -> {code, unit}.

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
                onchain_id INT PRIMARY KEY,
                code VARCHAR(100),
                unit VARCHAR(255)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        conn.commit()
    except MySQLError as e:
        raise StorageError(f"Không tạo được bảng trong database '{DB_CONFIG['database']}': {e}")
    finally:
        conn.close()


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
                     status: str = "Đang khởi tạo...") -> str:
    """Tạo một phiên bầu cử MỚI, CHƯA gắn ứng viên nào (gắn dần bằng
    add_candidates_to_election khi từng ứng viên được ghi lên chain thành
    công, để nếu giữa chừng lỗi vẫn giữ được phần đã làm)."""
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO elections (title, description, start_time, end_time, status) "
            "VALUES (%s, %s, %s, %s, %s)",
            (title, desc, start, end, status),
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

def set_candidate_meta(onchain_id: int, code: str, unit: str) -> None:
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO candidate_meta (onchain_id, code, unit) VALUES (%s, %s, %s) "
            "ON DUPLICATE KEY UPDATE code = VALUES(code), unit = VALUES(unit)",
            (onchain_id, code, unit),
        )
        conn.commit()
    except MySQLError as e:
        conn.rollback()
        raise StorageError(f"Lỗi khi lưu thông tin ứng viên #{onchain_id}: {e}")
    finally:
        conn.close()


def get_candidate_meta(onchain_id: int) -> dict:
    conn = _connect()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT code, unit FROM candidate_meta WHERE onchain_id = %s", (onchain_id,))
        row = cur.fetchone()
        return {"code": row["code"] or "", "unit": row["unit"] or ""} if row else {"code": "", "unit": ""}
    except MySQLError as e:
        raise StorageError(f"Lỗi khi đọc thông tin ứng viên #{onchain_id}: {e}")
    finally:
        conn.close()


def get_candidate_meta_bulk(onchain_ids: list) -> dict:
    """Lấy metadata nhiều candidate trong 1 lần truy vấn (tránh N kết nối
    cho N candidate khi hiển thị bảng kết quả ở Dashboard)."""
    if not onchain_ids:
        return {}
    conn = _connect()
    try:
        cur = conn.cursor(dictionary=True)
        placeholders = ",".join(["%s"] * len(onchain_ids))
        cur.execute(
            f"SELECT onchain_id, code, unit FROM candidate_meta WHERE onchain_id IN ({placeholders})",
            tuple(onchain_ids),
        )
        return {r["onchain_id"]: {"code": r["code"] or "", "unit": r["unit"] or ""} for r in cur.fetchall()}
    except MySQLError as e:
        raise StorageError(f"Lỗi khi đọc metadata ứng viên (bulk): {e}")
    finally:
        conn.close()
