"""
Configuration for the Agent Worker Service.
"""

from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Worker settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Service identification
    service_name: str = Field(default="agent-worker")
    service_version: str = Field(default="1.0.0")
    environment: str = Field(default="development")
    debug: bool = Field(default=False)

    # Worker Configuration
    worker_id: Optional[str] = Field(default=None)
    worker_host: str = Field(default="0.0.0.0", alias="AGENT_WORKER_HOST")
    worker_port: int = Field(default=8001, alias="AGENT_WORKER_PORT")
    max_concurrent_tasks: int = Field(default=5)

    # Orchestrator Connection
    orchestrator_url: str = Field(default="http://localhost:8000")

    # Database Configuration
    database_url: str = Field(
        default="postgresql+asyncpg://agent_user:agent_pass@localhost:5432/agents_db"
    )

    # Redis Configuration
    redis_url: str = Field(default="redis://localhost:6379")

    # Kafka Configuration
    kafka_bootstrap_servers: str = Field(default="localhost:9092")
    kafka_group_id: str = Field(default="agent-workers")
    kafka_auto_offset_reset: str = Field(default="earliest")

    # LLM Configuration
    anthropic_api_key: Optional[str] = Field(default=None)
    openai_api_key: Optional[str] = Field(default=None)
    openrouter_api_key: Optional[str] = Field(default=None)
    openrouter_base_url: str = Field(default="https://openrouter.ai/api/v1")
    default_model: str = Field(default="anthropic/claude-3.5-sonnet")
    llm_timeout: int = Field(default=120)
    llm_max_tokens: int = Field(default=4096)
    llm_temperature: float = Field(default=0.7)
    use_openrouter: bool = Field(default=True)

    # Memory Configuration
    memory_short_term_ttl: int = Field(default=3600)  # 1 hour
    memory_mid_term_ttl: int = Field(default=86400)  # 24 hours
    memory_max_entries: int = Field(default=1000)

    # Observability Configuration
    jaeger_agent_host: str = Field(default="localhost")
    jaeger_agent_port: int = Field(default=6831)
    log_level: str = Field(default="INFO")

    # Agent Behavior
    heartbeat_interval: int = Field(default=30)
    task_timeout: int = Field(default=300)
    retry_attempts: int = Field(default=3)
    retry_delay: int = Field(default=5)


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
