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

    @model_validator(mode="after")
    def demo_only(self) -> "Settings":
        if not self.demo_mode:
            raise ValueError("Authentication is not implemented; only demo mode is available")
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
