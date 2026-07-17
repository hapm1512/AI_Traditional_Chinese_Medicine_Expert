from dataclasses import dataclass


@dataclass(frozen=True)
class UserSession:
    user_id: int
    username: str
    full_name: str
    role: str
    session_id: int
    positions: tuple[str, ...] = ()
    active_position: str = ""

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    @property
    def is_doctor(self) -> bool:
        return self.has_position("doctor")

    def has_position(self, position: str) -> bool:
        if self.active_position:
            return self.active_position == position
        return position in self.positions or self.role == position


_current: UserSession | None = None


def set_current_user(user: UserSession | None) -> None:
    global _current
    _current = user


def current_user() -> UserSession | None:
    return _current


def require_role(*roles: str) -> UserSession:
    user = current_user()
    allowed = user is not None and any(
        (role == "admin" and user.role == "admin")
        or (role in {"doctor", "nurse"} and user.has_position(role))
        for role in roles
    )
    if not allowed:
        raise PermissionError("Tài khoản không có quyền thực hiện thao tác này.")
    return user
