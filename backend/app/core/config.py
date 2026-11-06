import json
from typing import List, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    APP_NAME: str = "LedgerLine"
    APP_VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # Security
    JWT_SECRET_KEY: str = "ledgerline-dev-super-secret-key-at-least-32-characters-long"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://ledger_user:ledger_password@localhost:5432/ledgerline_db"
    SYNC_DATABASE_URL: str = "postgresql+psycopg://ledger_user:ledger_password@localhost:5432/ledgerline_db"

    # CORS
    CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://ledgerline.vercel.app"
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            if v.startswith("["):
                return json.loads(v)
            return [i.strip() for i in v.split(",") if i.strip()]
        return v

    # System Clearing Account ID (Default UUID for system deposits and withdrawals)
    SYSTEM_CLEARING_ACCOUNT_ID: str = "00000000-0000-0000-0000-000000000001"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()
