from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", hide_input_in_errors=True)
    database_url: str = "postgresql+psycopg://helpdesk:helpdesk@localhost:5432/helpdesk"
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_dimensions: int = Field(default=384, ge=384, le=384)
    database_pool_size: int = Field(default=2, ge=1, le=5)
    database_max_overflow: int = Field(default=1, ge=0, le=5)
    jwt_secret: str = Field(min_length=32)
    cors_origins: list[str] = ["http://localhost:5173"]
    chunk_tokens: int = Field(default=700, ge=100, le=1000)
    overlap_tokens: int = Field(default=100, ge=0, le=200)
    top_k: int = Field(default=3, ge=1, le=10)
    intent_minimum: float = Field(default=0.72, ge=0, le=1)
    intent_without_keyword: float = Field(default=0.81, ge=0, le=1)
    specificity_window: float = Field(default=0.08, ge=0, le=1)
    intent_margin: float = Field(default=0.025, ge=0, le=1)
    short_query_margin: float = Field(default=0.06, ge=0, le=1)
    faq_similarity: float = Field(default=0.94, ge=0, le=1)
    negative_margin: float = Field(default=0.025, ge=0, le=1)
    evidence_minimum: float = Field(default=0.50, ge=0, le=1)
    minimum_similarity: float = Field(default=0.70, ge=0, le=1)
    max_upload_bytes: int = 10 * 1024 * 1024
    mindrouter_api_key: SecretStr | None = None
    mindrouter_base_url: str = "https://api.mindrouter.io/v1"
    mindrouter_model: str = "openai/gpt-4.1-nano"
    mindrouter_max_output_tokens: int = Field(default=300, ge=64, le=300)
    generation_user_daily_limit: int = Field(default=3, ge=1, le=100)
    generation_ip_daily_limit: int = Field(default=8, ge=1, le=500)
    generation_global_daily_limit: int = Field(default=20, ge=1, le=10000)


@lru_cache
def get_settings() -> Settings:
    return Settings()
