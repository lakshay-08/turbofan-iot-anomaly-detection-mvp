from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.db_models import User


class UserRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_email(self, email: str) -> User | None:
        return self.session.execute(select(User).where(User.email == email)).scalar_one_or_none()

    def get_by_id(self, user_id: str) -> User | None:
        return self.session.execute(select(User).where(User.id == user_id)).scalar_one_or_none()

    def list_users(self) -> list[User]:
        return self.session.execute(select(User).order_by(User.created_at.asc())).scalars().all()

    def create_user(self, *, email: str, password_hash: str, role: str, is_active: bool = True) -> User:
        user = User(email=email, password_hash=password_hash, role=role, is_active=is_active)
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user
