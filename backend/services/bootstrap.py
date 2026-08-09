from __future__ import annotations

from backend.repositories.user_repository import UserRepository
from backend.security.auth import hash_password


def bootstrap_admin_user(session, *, email: str | None, password: str | None, role: str) -> None:
    if not email or not password:
        return

    repository = UserRepository(session)
    existing = repository.get_by_email(email)
    if existing is not None:
        return

    repository.create_user(
        email=email,
        password_hash=hash_password(password),
        role=role,
        is_active=True,
    )
