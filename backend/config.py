"""Backend configuration helpers."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True, slots=True)
class Settings:
	api_host: str = os.getenv("API_HOST", "0.0.0.0")
	api_port: int = int(os.getenv("API_PORT", "5002"))
	artifact_dir: Path = PROJECT_ROOT / "artifacts" / "isolation_forest"
	jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "dev-secret-change-me")
	jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
	access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
	bootstrap_admin_email: str | None = os.getenv("BOOTSTRAP_ADMIN_EMAIL")
	bootstrap_admin_password: str | None = os.getenv("BOOTSTRAP_ADMIN_PASSWORD")
	bootstrap_admin_role: str = os.getenv("BOOTSTRAP_ADMIN_ROLE", "admin")


settings = Settings()
