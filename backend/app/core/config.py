"""CIRUS — Centralised configuration via Pydantic Settings v2."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import List, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SQLITE_PATH = PROJECT_ROOT / "cirus_dev.db"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ── App ───────────────────────────────────────────────────────────────────
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    MODE: Literal["mock", "live"] = "mock"
    SECRET_KEY: str = "changeme-dev-secret-key"
    API_KEY_HEADER: str = "X-API-Key"
    ALLOWED_API_KEYS: str = ""

    # ── CORS ──────────────────────────────────────────────────────────────────
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:3001"

    # ── Database ──────────────────────────────────────────────────────────────
    DATABASE_URL: str = f"sqlite+aiosqlite:///{DEFAULT_SQLITE_PATH.as_posix()}"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_ECHO: bool = False

    # ── Redis / Celery ────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_ENABLED: bool = False

    # ── LLM ───────────────────────────────────────────────────────────────────
    LLM_PROVIDER: Literal["featherless", "groq", "openai", "anthropic", "mock"] = "mock"
    FEATHERLESS_API_KEY: str = ""
    FEATHERLESS_BASE_URL: str = "https://api.featherless.ai/v1"
    FEATHERLESS_MODEL: str = "meta-llama/Llama-3.3-70B-Instruct"
    GROQ_API_KEY: str = ""
    GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    LLM_TEMPERATURE: float = 0.2
    LLM_MAX_TOKENS: int = 4096
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-3-5-sonnet-20241022"

    # ── Firecrawl ─────────────────────────────────────────────────────────────
    FIRECRAWL_API_KEY: str = ""
    FIRECRAWL_BASE_URL: str = "https://api.firecrawl.dev/v1"
    FIRECRAWL_ENABLED: bool = False

    # ── Wolfram ───────────────────────────────────────────────────────────────
    WOLFRAM_APP_ID: str = ""
    WOLFRAM_BASE_URL: str = "https://api.wolframalpha.com/v2"
    WOLFRAM_ENABLED: bool = False

    # ── Pipeline ──────────────────────────────────────────────────────────────
    PIPELINE_TIMEOUT_SECONDS: int = 120
    MAX_RETRIES: int = 3
    RETRY_BACKOFF_BASE: float = 1.5
    RETRY_BACKOFF_MAX: float = 30.0

    # ── Export ────────────────────────────────────────────────────────────────
    EXPORT_DIR: str = "./exports"

    # ── Validators ────────────────────────────────────────────────────────────
    @field_validator("ALLOWED_API_KEYS", mode="before")
    @classmethod
    def parse_api_keys(cls, v) -> str:
        # Accept list (e.g. from code) and join back to string
        if isinstance(v, list):
            return ",".join(v)
        return str(v) if v else ""

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v) -> str:
        if isinstance(v, list):
            return ",".join(v)
        return str(v) if v else "http://localhost:3000"

    @property
    def allowed_api_keys_list(self) -> List[str]:
        return [k.strip() for k in self.ALLOWED_API_KEYS.split(",") if k.strip()]

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings: Settings = get_settings()
