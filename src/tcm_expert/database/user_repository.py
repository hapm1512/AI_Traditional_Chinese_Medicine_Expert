import hashlib
import hmac
import os
import re
from datetime import datetime, timedelta

from tcm_expert.database.manager import DatabaseManager
from tcm_expert.security import UserSession


class UserRepository:
    ITERATIONS = 240_000
    DEFAULT_USERNAME = "admin"
    DEFAULT_PASSWORD = "Admin@123"

    def __init__(self, database: DatabaseManager):
        self.database = database

    @classmethod
    def _hash(cls, password: str, salt: bytes) -> str:
        return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, cls.ITERATIONS).hex()

    @staticmethod
    def _validate_password(password: str) -> None:
        if len(password) < 8 or not re.search(r"[A-Z]", password) or not re.search(r"\d", password):
            raise ValueError("Mật khẩu cần 8 ký tự, chữ hoa và số.")

    def ensure_bootstrap_admin(self) -> bool:
        with self.database.transaction() as connection:
            if connection.execute("SELECT 1 FROM app_users LIMIT 1").fetchone():
                return False
            salt = os.urandom(16)
            connection.execute(
                """INSERT INTO app_users
                   (username,full_name,password_hash,password_salt,role,must_change_password)
                   VALUES(?,?,?,?, 'admin',1)""",
                (self.DEFAULT_USERNAME, "Quản trị hệ thống", self._hash(self.DEFAULT_PASSWORD, salt), salt.hex()),
            )
            return True

    def authenticate(self, username: str, password: str) -> UserSession:
        name = username.strip()
        now = datetime.now()
        with self.database.transaction() as connection:
            row = connection.execute(
                "SELECT * FROM app_users WHERE username=? COLLATE NOCASE", (name,)
            ).fetchone()
            if row is None or not row["active"]:
                raise ValueError("Tên đăng nhập hoặc mật khẩu không đúng.")
            if row["locked_until"] and datetime.fromisoformat(row["locked_until"]) > now:
                raise ValueError("Tài khoản đang tạm khóa. Thử lại sau.")
            salt = bytes.fromhex(row["password_salt"])
            valid = hmac.compare_digest(row["password_hash"], self._hash(password, salt))
            if not valid:
                attempts = int(row["failed_attempts"]) + 1
                locked = (now + timedelta(minutes=15)).isoformat(timespec="seconds") if attempts >= 5 else None
                connection.execute(
                    "UPDATE app_users SET failed_attempts=?,locked_until=? WHERE id=?",
                    (0 if locked else attempts, locked, row["id"]),
                )
                raise ValueError("Tên đăng nhập hoặc mật khẩu không đúng.")
            connection.execute(
                "UPDATE app_users SET failed_attempts=0,locked_until=NULL,last_login_at=CURRENT_TIMESTAMP WHERE id=?",
                (row["id"],),
            )
            cursor = connection.execute("INSERT INTO user_sessions(user_id) VALUES(?)", (row["id"],))
            session = UserSession(int(row["id"]), row["username"], row["full_name"], row["role"], int(cursor.lastrowid))
            from tcm_expert.security import set_current_user
            set_current_user(session)
            self.database.audit(connection, "login", "user_session", int(cursor.lastrowid), row["role"])
            return session

    def logout(self, session: UserSession, reason: str = "manual") -> None:
        with self.database.transaction() as connection:
            connection.execute(
                "UPDATE user_sessions SET logged_out_at=CURRENT_TIMESTAMP,logout_reason=? WHERE id=? AND logged_out_at IS NULL",
                (reason, session.session_id),
            )
            self.database.audit(connection, "logout", "user_session", session.session_id, reason)

    def list_users(self) -> list:
        with self.database.transaction() as connection:
            return list(connection.execute(
                "SELECT id,username,full_name,role,active,last_login_at FROM app_users ORDER BY username"
            ))

    def save(self, username: str, full_name: str, role: str, password: str, user_id: int | None = None) -> int:
        username, full_name = username.strip(), full_name.strip()
        if not re.fullmatch(r"[A-Za-z0-9_.-]{3,32}", username):
            raise ValueError("Tên đăng nhập cần 3–32 ký tự hợp lệ.")
        if not full_name:
            raise ValueError("Bắt buộc nhập họ tên.")
        if role not in {"admin", "doctor", "nurse"}:
            raise ValueError("Vai trò không hợp lệ.")
        with self.database.transaction() as connection:
            if user_id is None:
                self._validate_password(password)
                salt = os.urandom(16)
                cursor = connection.execute(
                    """INSERT INTO app_users(username,full_name,password_hash,password_salt,role,must_change_password)
                       VALUES(?,?,?,?,?,1)""",
                    (username, full_name, self._hash(password, salt), salt.hex(), role),
                )
                saved_id = int(cursor.lastrowid)
            else:
                connection.execute(
                    "UPDATE app_users SET username=?,full_name=?,role=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",
                    (username, full_name, role, user_id),
                )
                saved_id = user_id
                if password:
                    self._validate_password(password)
                    salt = os.urandom(16)
                    connection.execute(
                        "UPDATE app_users SET password_hash=?,password_salt=?,must_change_password=1 WHERE id=?",
                        (self._hash(password, salt), salt.hex(), user_id),
                    )
            self.database.audit(connection, "save", "app_user", saved_id, role)
            return saved_id

    def set_active(self, user_id: int, active: bool) -> None:
        with self.database.transaction() as connection:
            row = connection.execute("SELECT role,active FROM app_users WHERE id=?", (user_id,)).fetchone()
            if row is None:
                raise ValueError("Không tìm thấy tài khoản.")
            if not active and row["role"] == "admin" and row["active"]:
                count = connection.execute("SELECT COUNT(*) FROM app_users WHERE role='admin' AND active=1").fetchone()[0]
                if count <= 1:
                    raise ValueError("Không thể khóa quản trị viên cuối cùng.")
            connection.execute("UPDATE app_users SET active=?,updated_at=CURRENT_TIMESTAMP WHERE id=?", (int(active), user_id))
            self.database.audit(connection, "activate" if active else "deactivate", "app_user", user_id)

    def delete(self, user_id: int) -> None:
        from tcm_expert.security import current_user

        actor = current_user()
        if actor is not None and actor.user_id == user_id:
            raise ValueError("Không thể xóa tài khoản đang đăng nhập.")
        with self.database.transaction() as connection:
            row = connection.execute(
                "SELECT username,full_name,role,active FROM app_users WHERE id=?", (user_id,)
            ).fetchone()
            if row is None:
                raise ValueError("Không tìm thấy tài khoản.")
            if row["role"] == "admin" and row["active"]:
                count = connection.execute(
                    "SELECT COUNT(*) FROM app_users WHERE role='admin' AND active=1"
                ).fetchone()[0]
                if count <= 1:
                    raise ValueError("Không thể xóa quản trị viên cuối cùng.")
            # Giữ tên người thao tác trong audit, bỏ liên kết trước khi xóa tài khoản.
            connection.execute(
                "UPDATE audit_log SET actor_user_id=NULL WHERE actor_user_id=?", (user_id,)
            )
            connection.execute("DELETE FROM user_sessions WHERE user_id=?", (user_id,))
            connection.execute("DELETE FROM app_users WHERE id=?", (user_id,))
            self.database.audit(
                connection,
                "delete",
                "app_user",
                user_id,
                f"{row['username']} | {row['full_name']} | {row['role']}",
            )

    def change_password(self, user_id: int, password: str) -> None:
        self._validate_password(password)
        salt = os.urandom(16)
        with self.database.transaction() as connection:
            connection.execute(
                "UPDATE app_users SET password_hash=?,password_salt=?,must_change_password=0,updated_at=CURRENT_TIMESTAMP WHERE id=?",
                (self._hash(password, salt), salt.hex(), user_id),
            )
            self.database.audit(connection, "change_password", "app_user", user_id)
