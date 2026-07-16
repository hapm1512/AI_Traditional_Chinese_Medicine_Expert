from dataclasses import dataclass


@dataclass(frozen=True)
class UserSession:
    user_id: int
    username: str
    full_name: str
    role: str
    session_id: int

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    @property
    def is_doctor(self) -> bool:
        return self.role == "doctor"


_current: UserSession | None = None


def set_current_user(user: UserSession | None) -> None:
    global _current
    _current = user


def current_user() -> UserSession | None:
    return _current


def require_role(*roles: str) -> UserSession:
    user = current_user()
    if user is None or user.role not in roles:
        raise PermissionError("Tài khoản không có quyền thực hiện thao tác này.")
    return user
