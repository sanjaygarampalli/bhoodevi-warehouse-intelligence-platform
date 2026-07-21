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

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()