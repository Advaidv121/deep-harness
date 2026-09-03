from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    PROJECT_NAME: str = "Deep Harness AI Companion"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"

    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    MEMORY_DIR: Path = BASE_DIR / "memory"

    # Postgres (asyncpg) — primary store, no SQLite fallback
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "companion"
    POSTGRES_USER: str = "companion"
    POSTGRES_PASSWORD: str = "companion"
    POSTGRES_DSN: str = ""  # if set, overrides individual fields

    # Qdrant (host default localhost, Docker overrides via QDRANT_URL env)
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: str = ""
    QDRANT_COLLECTION: str = "facts"

    # Redis
    REDIS_URL: str = "redis://redis:6379/0"

    # Temporal
    TEMPORAL_HOST: str = "temporal:7233"
    TEMPORAL_NAMESPACE: str = "default"
    TEMPORAL_TASK_QUEUE: str = "companion-tasks"

    # Memory Limits (assessment invariants)
    USER_MD_MAX_CHARS: int = 1500
    MEMORY_MD_MAX_CHARS: int = 2200

    # Retrieval
    TOP_K_RETRIEVAL: int = 5
    RRF_K_PARAM: int = 60
    SALIENCE_THRESHOLD: float = 0.70

    # LLM / Bedrock (assessment invariant)
    LLM_PROVIDER: str = "bedrock"
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = "https://api.openai.com/v1"
    LLM_MODEL: str = "gpt-4o-mini"

    AWS_PROFILE: str = "my-second-account"
    AWS_REGION: str = "us-east-1"
    BEDROCK_CHAT_MODEL_ID: str = "us.meta.llama3-3-70b-instruct-v1:0"
    BEDROCK_FALLBACK_MODEL_ID: str = "mistral.mistral-large-3-675b-instruct"
    BEDROCK_EMBED_MODEL_ID: str = "amazon.titan-embed-text-v2:0"
    BEDROCK_EMBED_ENABLED: bool = False
    BEDROCK_EMBED_DIMENSION: int = 1024

    HOST: str = "0.0.0.0"
    PORT: int = 8000
    CORS_ORIGINS: list[str] = ["*"]

    @property
    def database_url(self) -> str:
        if self.POSTGRES_DSN:
            dsn = self.POSTGRES_DSN
            # normalize to asyncpg driver
            if dsn.startswith("postgresql://"):
                return dsn.replace("postgresql://", "postgresql+asyncpg://", 1)
            if dsn.startswith("postgres://"):
                return dsn.replace("postgres://", "postgresql+asyncpg://", 1)
            return dsn
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def sync_database_url(self) -> str:
        # for alembic/tools if needed
        return self.database_url.replace("+asyncpg", "+psycopg2")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
    settings.MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    return settings
