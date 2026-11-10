import secrets
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="NETVAULT_", extra="ignore")

    database_host: str = "localhost"
    database_name: str = "netvault"
    database_user: str = "netvault"
    database_password_file: Path = Path("../.local/secrets/postgres_password")
    demo_mode: bool = True
    static_dir: Path = Path("../frontend/out")
    cors_origins: list[str] = []

    # Auth / session configuration
    jwt_secret: str = ""
    access_token_ttl_seconds: int = 900  # 15 minutes
    refresh_token_ttl_seconds: int = 604800  # 7 days
    refresh_idle_ttl_seconds: int = 1800  # 30 minutes of inactivity
    max_failed_logins: int = 5
    lockout_duration_seconds: int = 900  # 15 minutes

    @model_validator(mode="after")
    def _derive_jwt_secret(self) -> "Settings":
        if not self.jwt_secret:
            if not self.demo_mode:
                raise ValueError(
                    "NETVAULT_JWT_SECRET must be set when demo_mode is disabled"
                )
            # Ephemeral secret for demo/dev. Sessions won't survive a process restart.
            self.jwt_secret = secrets.token_urlsafe(48)
        if len(self.jwt_secret) < 32:
            raise ValueError("NETVAULT_JWT_SECRET must be at least 32 characters")
        return self

    def database_url(self) -> URL:
        try:
            password = self.database_password_file.read_text(encoding="utf-8").strip()
        except OSError as exc:
            raise ValueError(
                f"Cannot read database password file: {self.database_password_file}"
            ) from exc
        if not password:
            raise ValueError("Database password file must not be empty")
        return URL.create(
            "postgresql+asyncpg",
            username=self.database_user,
            password=password,
            host=self.database_host,
            database=self.database_name,
        )
