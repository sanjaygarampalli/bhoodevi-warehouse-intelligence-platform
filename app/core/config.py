from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ==========================================
    # Application Settings
    # ==========================================
    APP_NAME: str = "BHOODEVI Warehouse Intelligence Platform"
    APP_VERSION: str = "0.1.0"
    APP_ENV: str = "development"
    DEBUG: bool = True

    # ==========================================
    # Database
    # ==========================================
    DATABASE_URL: str = (
        "postgresql://postgres:password@localhost:5432/bwip_db"
    )

    # ==========================================
    # AI API Keys
    # ==========================================
    OPENAI_API_KEY: str = ""
    GOOGLE_API_KEY: str = ""
    TAVILY_API_KEY: str = ""
    SERPER_API_KEY: str = ""

    # ==========================================
    # Security
    # ==========================================
    SECRET_KEY: str = ""

    @model_validator(mode="after")
    def validate_deployment_safety(self):
        """Reject unsafe settings for environments intended to serve traffic."""
        if self.APP_ENV.lower() not in {"production", "staging"}:
            return self

        if self.DEBUG:
            raise ValueError("DEBUG must be False in staging and production")

        if len(self.SECRET_KEY) < 32:
            raise ValueError("SECRET_KEY must contain at least 32 characters in staging and production")

        database_url = self.DATABASE_URL.lower()
        if not database_url.startswith(("postgresql://", "postgresql+psycopg2://")):
            raise ValueError("DATABASE_URL must use PostgreSQL in staging and production")
        if "username:password@" in database_url or "postgres:password@" in database_url:
            raise ValueError("DATABASE_URL contains a placeholder credential")

        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()