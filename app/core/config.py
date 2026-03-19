from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/blackbox"
    redis_url: str = "redis://localhost:6379"
    qdrant_url: str = "http://localhost:6333"
    
    # Security
    platform_key: str = "bb_platform_demo_key_change_in_prod"
    
    # LLM
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    groq_api_key: str | None = None
    
    # App
    debug: bool = True
    
    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()