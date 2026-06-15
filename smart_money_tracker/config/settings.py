"""Configuration settings for Smart Money Tracker using Pydantic BaseSettings."""

from pydantic_settings import BaseSettings
from pydantic import ConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    # OpenAI Configuration
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"

    # Email Configuration (SMTP)
    smtp_email: str | None = None
    smtp_password: str | None = None

    # Email Configuration (Resend)
    resend_api_key: str | None = None

    # Report Recipient
    report_email: str  # Required

    # Database Configuration
    database_path: str = "smart_money.db"

    # Scoring Configuration
    min_score_for_email: int = 60

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
