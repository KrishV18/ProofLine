"""ProofLine API configuration loaded from environment variables."""
from __future__ import annotations

from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://proofline:proofline@localhost:5432/proofline"
    jwt_secret: str = "change-me-in-production"
    jwt_expire_minutes: int = 60
    environment: str = "development"
    llm_api_key: str = ""
    llm_model: str = "gemini-pro"
    cors_origins: Union[str, List[str]] = ["http://localhost:3000"]
    mock_ai: bool = True

    @field_validator("cors_origins", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            if v == "*":
                return ["*"]
            return [i.strip() for i in v.split(",") if i.strip()]
        return v

    model_config = {
        "env_file": (".env", "backend/.env", "../.env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()
