"""ProofLine API configuration loaded from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://proofline:proofline@localhost:5432/proofline"
    jwt_secret: str = "change-me-in-production"
    jwt_expire_minutes: int = 60
    llm_api_key: str = ""
    llm_model: str = "gemini-pro"
    cors_origins: list[str] = ["http://localhost:3000"]
    mock_ai: bool = True

    model_config = {
    "env_file": ".env",
    "env_file_encoding": "utf-8",
    "extra": "ignore",
}


settings = Settings()

