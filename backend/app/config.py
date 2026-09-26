from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "postgresql+psycopg://helpdesk:helpdesk@localhost:5432/helpdesk"
    openrouter_api_key: str = ""
    deepseek_api_key: str = ""
    ai_provider: str = "deepseek"
    embedding_provider: str = "fastembed"
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_dimensions: int = Field(default=384, ge=1, le=2000)
    llm_model: str = "deepseek-flash"
    jwt_secret: str = Field(min_length=32)
    cors_origins: list[str] = ["http://localhost:5173"]
    chunk_tokens: int = Field(default=700, ge=100, le=1000)
    overlap_tokens: int = Field(default=100, ge=0, le=200)
    top_k: int = Field(default=5, ge=1, le=10)
    minimum_similarity: float = Field(default=0.70, ge=0, le=1)
    max_upload_bytes: int = 10 * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
