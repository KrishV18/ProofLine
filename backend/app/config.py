"""ProofLine API configuration loaded from environment variables."""

from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite:///./proofline.db"
    jwt_secret: str = "proofline-super-secret-jwt-key-2026-secure"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440  # 24 hours
    llm_api_key: str = ""
    llm_model: str = "gemini-1.5-flash"
    llm_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
    cors_origins: Union[str, List[str]] = ["*"]
    mock_ai: bool = False

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
